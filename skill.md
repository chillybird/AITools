# Toolbox App Creation Skill

## Purpose

This skill guides AI to create applications that can be registered and managed by the AI Toolbox (`toolbox/toolbox_app.py`). The Toolbox is a central launcher that manages multiple AI-generated tools, allowing users to start, stop, and open them from a unified interface.

## When to Use This Skill

Use this skill when:
- User asks to create a new tool/application to be managed by the Toolbox
- User asks to "add an app to the toolbox"
- Creating any Flask-based utility app that should appear in the Toolbox launcher

## Application Structure Requirements

Each managed app must follow this structure:

```
app-name/
├── app.py              # Flask application entry point
├── templates/
│   └── index.html      # Main UI template
├── static/             # (optional) CSS/JS/images
├── requirements.txt    # Python dependencies
└── manifest.json       # App metadata for the Toolbox (REQUIRED)
```

### 1. app.py Requirements

- Must be a Flask application
- Must read the port from `os.environ.get('FLASK_PORT', <default>)`:
  ```python
  import os
  from flask import Flask
  app = Flask(__name__)

  if __name__ == '__main__':
      port = int(os.environ.get('FLASK_PORT', 5001))
      app.run(host='0.0.0.0', port=port)
  ```
- Keep all templates, static files, uploads within the app directory
- Use `os.path.dirname(__file__)` for relative paths

### 2. manifest.json Format

Create a `manifest.json` in the app root directory with this exact structure:

```json
{
  "id": "unique-app-id",
  "name": "应用中文名称",
  "description": "清晰描述应用的功能和使用场景，1-2 句话。",
  "features": [
    "功能点 1：具体描述",
    "功能点 2：具体描述",
    "功能点 3：具体描述"
  ],
  "port": 5002,
  "directory": ".",
  "entry": "app.py"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | 唯一标识符，英文小写+连字符，如 `image-cropper` |
| `name` | string | ✅ | 显示名称，中文或英文，简洁明了 |
| `description` | string | ✅ | 功能摘要，描述应用做什么、如何工作、适用场景 |
| `features` | array | ✅ | 核心功能列表，每个功能一句话描述 |
| `port` | number | ✅ | 指定端口号，不可与其他 app 冲突 (5002-5999) |
| `directory` | string | ✅ | 应用目录相对于工具箱的路径，`.` 表示当前目录 |
| `entry` | string | ✅ | 入口 Python 文件名 |

### 3. Registration in Toolbox

After creating the app with `manifest.json`:

1. Open `toolbox/apps.json`
2. Copy the entire `manifest.json` object into the `apps` array
3. Ensure `directory` is relative to the toolbox directory
4. Ensure `port` doesn't conflict with other registered apps

Example `apps.json` entry:
```json
{
  "id": "image-cropper",
  "name": "图片裁剪器",
  "description": "上传图片后自由选择裁剪区域，支持固定比例、自由拖拽和尺寸预设。",
  "features": ["自由拖拽裁剪", "固定比例 (1:1, 4:3, 16:9)", "实时预览", "导出裁剪结果"],
  "port": 5003,
  "directory": "../image-cropper",
  "entry": "app.py"
}
```

## App Creation Workflow

When asked to create a new toolbox-manageable app:

1. **Design**: Understand requirements, plan features
2. **Implement**: Create `app.py`, `templates/index.html`, `requirements.txt`
3. **Document**: Generate `manifest.json` with proper `id`, `name`, clear `description` and `features` list
4. **Register**: Add the entry to `toolbox/apps.json`
5. **Test**: Verify the app starts on its designated port

## Port Assignment Convention

- `5000`: Toolbox itself
- `5001`: 尺寸测量工具 (dimension-measure)
- `5002+`: New apps, incrementing

Always check `toolbox/apps.json` for existing port assignments before choosing a port.

## Best Practices

- Use descriptive `id` values (e.g., `pdf-merger` not `tool1`)
- Write `description` as a user-facing summary: what problem does it solve?
- Break `features` into discrete, testable capabilities
- Keep the Flask app self-contained (no external service dependencies if possible)
- Use `requirements.txt` with pinned versions for reproducibility
- Test before registration: `python app.py` and visit `http://localhost:<port>`
- Place app source in `apps/<app-id>/` directory; this makes `"directory": "apps/<app-id>"` in apps.json
- If an app is deleted/moved without updating apps.json, the Toolbox detects it and shows a "⚠ 文件缺失" badge instead of silently failing
