import os
import sys
import json
import signal
import subprocess
import time
import socket
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
APPS_FILE = os.path.join(os.path.dirname(__file__), 'apps.json')
BASE_DIR = os.path.dirname(__file__)

running_processes = {}  # app_id → subprocess.Popen


def load_apps():
    if not os.path.exists(APPS_FILE):
        return []
    with open(APPS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_apps(apps):
    with open(APPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)


def is_port_open(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except:
        return False


def validate_app(app_info):
    """验证应用文件是否存在, 返回 (valid: bool, error: str)"""
    app_dir = os.path.abspath(os.path.join(BASE_DIR, app_info.get('directory', '.')))
    entry = app_info.get('entry', 'app.py')
    entry_path = os.path.join(app_dir, entry)
    if not os.path.isdir(app_dir):
        return False, f'应用目录不存在: {app_dir}'
    if not os.path.isfile(entry_path):
        return False, f'入口文件不存在: {entry_path}'
    return True, ''


def get_app_status(app_info):
    app_id = app_info['id']
    valid, _ = validate_app(app_info)
    if not valid:
        return 'broken'
    if app_id in running_processes:
        p = running_processes[app_id]
        if p.poll() is None:
            return 'running'
        else:
            del running_processes[app_id]
            return 'stopped'
    if is_port_open(app_info.get('port', 0)):
        return 'running'
    return 'stopped'


@app.route('/')
def index():
    apps = load_apps()
    for a in apps:
        a['_status'] = get_app_status(a)
    return render_template('index.html', apps=apps)


@app.route('/api/apps', methods=['GET'])
def api_apps():
    apps = load_apps()
    for a in apps:
        a['_status'] = get_app_status(a)
        a['_path'] = os.path.abspath(os.path.join(BASE_DIR, a.get('directory', '.')))
    return jsonify(apps)


@app.route('/api/start/<app_id>', methods=['POST'])
def start_app(app_id):
    apps = load_apps()
    app_info = next((a for a in apps if a['id'] == app_id), None)
    if not app_info:
        return jsonify({'error': '应用不存在'}), 404

    if get_app_status(app_info) == 'running':
        return jsonify({'status': 'already_running'})

    valid, err = validate_app(app_info)
    if not valid:
        return jsonify({'error': err}), 400

    app_dir = os.path.abspath(os.path.join(BASE_DIR, app_info['directory']))
    entry = app_info['entry']
    port = app_info.get('port', 5000)

    env = os.environ.copy()
    env['FLASK_PORT'] = str(port)

    try:
        proc = subprocess.Popen(
            [sys.executable, entry],
            cwd=app_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        running_processes[app_id] = proc
        time.sleep(1.5)
        return jsonify({'status': 'started', 'port': port})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop/<app_id>', methods=['POST'])
def stop_app(app_id):
    global running_processes
    if app_id in running_processes:
        p = running_processes[app_id]
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        del running_processes[app_id]
        return jsonify({'status': 'stopped'})

    apps = load_apps()
    app_info = next((a for a in apps if a['id'] == app_id), None)
    if app_info:
        port = app_info.get('port', 0)
        if is_port_open(port):
            return jsonify({'status': 'running_external'})
    return jsonify({'status': 'stopped'})


@app.route('/api/refresh', methods=['POST'])
def refresh():
    apps = load_apps()
    for a in apps:
        a['_status'] = get_app_status(a)
    return jsonify(apps)


@app.route('/api/save', methods=['POST'])
def save():
    apps = request.get_json()
    if not isinstance(apps, list):
        return jsonify({'error': '无效数据'}), 400
    save_apps(apps)
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
