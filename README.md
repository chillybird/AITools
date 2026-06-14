# 🧰 AI 工具箱

管理多个 AI 生成应用的中心启动器。提供统一的应用注册、启动停止、状态监控界面。

## 架构

```
AITools/
├── toolbox_app.py              # 工具箱主程序 (端口 5000)
├── apps.json                   # 应用注册表
├── skill.md                    # AI 创建新应用的指南
├── templates/index.html        # 工具箱 Web UI
└── apps/
    └── dimension-measure/      # 示例: 尺寸测量工具 (端口 5001)
        ├── app.py
        ├── manifest.json       # 应用描述清单
        ├── templates/
        └── requirements.txt
```

## 快速开始

```bash
# 安装依赖
pip install flask

# 启动工具箱
python toolbox_app.py
# 访问 http://localhost:5000
```

## 功能

| 功能 | 说明 |
|------|------|
| 📋 应用列表 | 卡片式展示已注册应用，含名称、描述、路径、功能标签 |
| ▶ 启动/停止 | 一键启动或停止子应用（子进程管理） |
| ⚠ 文件检测 | 检测应用目录是否存在，缺失时红色警告 |
| 📂 打开 | 新标签页访问运行中的应用 |
| ➕ 注册 | UI 界面手动注册新应用 |
| 🗑 移除 | 从列表删除应用 |

## 注册新应用

1. 将应用放在 `apps/<app-id>/` 目录下
2. 在工具箱 UI 点击「注册新应用」，或直接编辑 `apps.json`：

```json
{
  "id": "my-tool",
  "name": "我的工具",
  "description": "工具的功能描述和使用场景",
  "features": ["功能1", "功能2"],
  "port": 5002,
  "directory": "apps/my-tool",
  "entry": "app.py"
}
```

## 创建兼容应用

参考 `skill.md`，核心要点：

- `app.py` 必须读取 `FLASK_PORT` 环境变量作为端口
- 创建 `manifest.json` 描述应用元数据
- 保持自包含，所有资源在应用目录内

## 包含应用

| 应用 | 端口 | 说明 |
|------|------|------|
| 尺寸测量工具 | 5001 | 图片透视矫正 + 精确尺寸测量 |
