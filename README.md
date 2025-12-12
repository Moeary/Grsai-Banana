# Grsai Banana Image Generator

一个基于 PyQt5 和 Fluent-Widgets 构建的 Windows 桌面客户端，专为 [Grsai](https://grsai.com/zh/) 的 `Banana` 图像生成模型设计。

## ✨ 功能特性

- **现代化 UI**: 采用 Windows 11 风格的 Fluent Design 界面。
- **多图参考**: 支持拖拽/粘贴最多 13 张参考图片进行生成。
- **参数调整**: 
  - 模型选择 (nano-banana, nano-banana-fast, nano-banana-pro)
  - 宽高比 (1:1, 16:9, 9:16 等多种比例)
  - 图片尺寸 (1K, 2K, 4K)
- **历史记录**: 
  - 本地保存生成记录。
  - 支持分页浏览。
  - **一键重绘**: 可以直接从历史记录中恢复参数和参考图重新生成。
- **便捷操作**:
  - 支持剪贴板粘贴图片 (Ctrl+V)。
  - 拖拽上传。
  - 自动保存生成的图片到本地。

## 🛠️ 安装与运行

### 环境要求
- Python 3.8+
- 建议使用 Anaconda 或 Virtualenv

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行
直接运行根目录下的启动脚本：
```cmd
run.bat
```
或者使用 Python 运行：
```bash
python main.py
```

## ⚙️ 配置
首次运行后会在根目录生成 `config.json`，你可以在设置页面或直接修改文件来配置 API Key。

## 📝 目录结构
- `ui/`: 界面代码 (主窗口, 生成页, 历史页, 设置页)
- `core/`: 核心逻辑 (API 客户端, 历史记录管理, 配置管理)
- `assets/`: 资源文件
- `main.py`: 程序入口

---
*本项目非 Grsai 官方客户端，仅供学习交流使用。*