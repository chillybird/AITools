import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def order_points(pts):
    """将四个点排序为: 左上、右上、右下、左下"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    img = cv2.imread(filepath)
    if img is None:
        return jsonify({'error': '无法读取图片'}), 400

    h, w = img.shape[:2]
    return jsonify({
        'filename': filename,
        'width': w,
        'height': h,
        'url': f'/uploads/{filename}'
    })


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/correct', methods=['POST'])
def correct():
    """透视矫正: 接收4个点 + 目标矩形的物理尺寸, 输出矫正后的图片"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求'}), 400

    filename = data.get('filename')
    points = data.get('points')  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    real_width = data.get('real_width')   # 物理宽度 mm
    real_height = data.get('real_height')  # 物理高度 mm
    output_pixels = data.get('output_pixels', 1200)  # 输出图像最大边像素

    if not filename or not points or len(points) != 4:
        return jsonify({'error': '参数不完整'}), 400
    if not real_width or not real_height:
        return jsonify({'error': '请设置参考矩形的实际宽高'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath)
    if img is None:
        return jsonify({'error': '图片不存在'}), 400

    src_pts = np.array(points, dtype=np.float32)
    src_pts = order_points(src_pts)

    aspect = real_width / real_height
    if aspect >= 1:
        dst_w = output_pixels
        dst_h = int(output_pixels / aspect)
    else:
        dst_h = output_pixels
        dst_w = int(output_pixels * aspect)

    dst_pts = np.array([
        [0, 0],
        [dst_w - 1, 0],
        [dst_w - 1, dst_h - 1],
        [0, dst_h - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (dst_w, dst_h))

    out_filename = f"corrected_{uuid.uuid4().hex}.jpg"
    out_filepath = os.path.join(app.config['UPLOAD_FOLDER'], out_filename)
    cv2.imwrite(out_filepath, warped, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # 计算像素与毫米的换算比例
    scale_x = real_width / dst_w   # mm per pixel
    scale_y = real_height / dst_h  # mm per pixel

    return jsonify({
        'url': f'/uploads/{out_filename}',
        'width': dst_w,
        'height': dst_h,
        'scale_x': scale_x,
        'scale_y': scale_y,
        'real_width': real_width,
        'real_height': real_height
    })


@app.route('/measure', methods=['POST'])
def measure():
    """测量: 接收矫正后图像上的像素坐标, 返回实际距离或面积"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求'}), 400

    scale_x = data.get('scale_x')
    scale_y = data.get('scale_y')
    mode = data.get('mode', 'distance')  # 'distance' 或 'polygon_area'
    coords = data.get('coords')  # distance: [[x1,y1],[x2,y2]]; polygon: [[x1,y1],[x2,y2],...]

    if not scale_x or not scale_y or not coords:
        return jsonify({'error': '参数不完整'}), 400

    if mode == 'distance':
        if len(coords) != 2:
            return jsonify({'error': '距离测量需要2个点'}), 400
        p1, p2 = coords
        dx_px = p2[0] - p1[0]
        dy_px = p2[1] - p1[1]
        dx_mm = dx_px * scale_x
        dy_mm = dy_px * scale_y
        dist_mm = np.sqrt(dx_mm ** 2 + dy_mm ** 2)
        return jsonify({
            'mode': 'distance',
            'distance_mm': round(dist_mm, 2),
            'dx_mm': round(abs(dx_mm), 2),
            'dy_mm': round(abs(dy_mm), 2)
        })

    elif mode == 'polygon_area':
        if len(coords) < 3:
            return jsonify({'error': '面积测量至少需要3个点'}), 400
        pts_mm = np.array([[c[0] * scale_x, c[1] * scale_y] for c in coords])
        area = 0.0
        n = len(pts_mm)
        for i in range(n):
            j = (i + 1) % n
            area += pts_mm[i][0] * pts_mm[j][1]
            area -= pts_mm[j][0] * pts_mm[i][1]
        area = abs(area) / 2.0
        return jsonify({
            'mode': 'polygon_area',
            'area_mm2': round(area, 2)
        })

    return jsonify({'error': '未知测量模式'}), 400


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
