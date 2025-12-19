# Grsai Banana Image Generator

一个基于 PySide6 和 Fluent-Widgets 构建的 Windows 桌面客户端，专为国产中转网站 [Grsai](https://grsai.com/zh/) 的图像生成模型设计。支持 **Banana**、**Banana-Pro**、**GPT Image 1.5** 及 **Sora** 图像生成模型。

![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008692.png)

## ✨ 核心功能

### 🎨 生成功能
- **多模型支持**: 
  - Banana / Banana-Fast
  - Banana-Pro/Banana-Pro-vt
  - GPT Image 1.5/Sora Image

- **参数灵活配置**:
  - 模型动态选择
  - 宽高比支持 (1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 5:4, 4:5, 21:9 等)
  - 图片尺寸选择 (1K, 2K, 4K)
  - 自定义参考图片数量 (Variants)

- **多图参考**: 拖拽/粘贴最多 **13 张参考图片** (仅限于Banana-Pro模型)

### 📋 任务管理
- **实时任务列表**: 可视化任务执行状态、进度显示
- **自动重试机制**: 
  - 失败自动重试，可配置重试次数 (1-100)
  - 手动重试选项
- **并行任务处理**: 
  - 支持并行执行多个任务 (1-10个)
  - 智能队列管理
- **任务状态追踪**: 
  - 执行中 (进度环)
  - 成功 (✓ 绿色标记)
  - 失败 (✗ 红色标记)

### 📚 历史记录
- **完整历史存储**: 本地保存所有生成记录
- **智能分页浏览**: 
  - 可配置每页显示数量 (1-100项)
  - 快速翻页导航
- **一键重绘功能**: 
  - 从历史记录恢复完整参数
  - 自动加载参考图片

### ⚙️ 高级设置
- **文本格式化**:
  - 字体大小调整 (8-72pt)
  - 字体选择 (Arial, Times New Roman 等)
  - 自动换行支持

- **生成配置**:
  - 最大重试次数设置
  - 并行任务数量设置
  - 输出文件夹自定义

- **主题支持**:
  - 🌞 亮色模式 (纯白卡片)
  - 🌙 深色模式 (可见深色背景)
  - 💻 自动跟随系统
  - 一键切换主题

### 🎯 便捷操作
- **快速输入**:
  - 剪贴板粘贴图片 (Ctrl+V)
  - 拖拽上传图片
  - 快捷清空功能

- **自动保存**: 生成的图片自动保存到本地
- **响应式设计**: UI 自动适配窗口大小

## 🛠️ 安装与运行

### Windows 用户 (推荐)
直接前往 [GitHub Releases](https://github.com/Moeary/Grsai-Banana/releases) 下载最新的 `main.exe`程序，双击即用，无需配置 Python 环境。

### 开发者 / 其他系统用户
本项目使用 `pixi` 进行环境管理，确保开发环境的一致性。

1. **安装 Pixi**
   请参考 [Pixi 官方文档](https://pixi.sh/) 安装。

2. **克隆仓库**
   ```bash
   git clone https://github.com/Moeary/Grsai-Banana.git
   cd Grsai-Banana
   ```

3. **运行项目**
   Pixi 会自动下载并配置所需的 Python 环境和依赖：
   ```bash
   pixi run start
   ```

4. **打包 (可选)**
   如果你想自己编译 exe 文件：
   ```bash
   pixi run build
   ```
   编译产物将位于 `dist/` 目录下。

## ⚙️ 配置说明

首次运行后会在根目录生成 `config.json`，你可以通过以下方式配置：

### 设置页面配置 (推荐)
在应用内的 **Settings** 页面直接修改所有配置：
- API Base URL 和 API Key
- 最大重试次数 (1-100)
- 历史记录每页显示数量 (1-100)
- 文本格式化选项 (字体、大小、自动换行)
- 输出文件夹位置

![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008854.png)

如果需要，也可以直接编辑 `config.json`

## 📝 项目结构

```
Grsai-Banana/
├── ui/                          # 用户界面
│   ├── main_window.py           # 主窗口
│   ├── generator_page.py        # 生成页面 (核心功能)
│   ├── history_page.py          # 历史记录页面
│   ├── settings_page.py         # 设置页面
│   └── components/              # UI 组件
│       ├── prompt_widget.py     # 提示词输入框
│       ├── image_drop_area.py   # 图片拖拽区域
│       └── task_widget.py       # 任务卡片和任务列表
├── core/                        # 核心逻辑
│   ├── api_client.py            # API 调用客户端
│   ├── task_manager.py          # 任务管理和并行处理
│   ├── history_manager.py       # 历史记录管理
│   └── config.py                # 配置管理
├── main.py                      # 程序入口
├── config.json                  # 配置文件 (首次运行自动生成)
├── history.json                 # 历史记录存储
└── requirements.txt             # 依赖列表
```

## 🚀 快速开始

1. **设置 API Key**
   - 打开设置页面 (Settings)
   - 输入你的 Grsai API Base URL 和 API Key
   - 点击 "Save Settings"

2. **选择模型和参数**
   - 使用选项卡切换不同的生成模型
   - 调整对应的参数 (宽高比、尺寸等)

3. **上传参考图片** (可选)
   - 拖拽图片到 "Reference Images" 区域
   - 或使用 Ctrl+V 从剪贴板粘贴

4. **输入提示词**
   - 在 "Prompt" 框中输入生成描述

5. **生成图片**
   - 点击 "Generate Image" 按钮
   - 在任务列表中查看生成进度
   - 生成完成后可从历史记录中查看或重新生成

## 💡 高级技巧

- **快速重试**: 如果生成失败，直接点击任务卡片上的重试按钮
- **批量生成**: 设置更高的 "Parallel Tasks" 以同时处理多个任务
- **自动重试**: 启用 "Auto Retry on Failure" 在失败时自动重试
- **历史快速恢复**: 在历史页面点击 "Regenerate" 快速恢复参数并重新生成

## 🎨 主题系统

支持两种种主题模式：
- **亮色模式** (Light): 纯白卡片背景，适合白天使用
- **深色模式** (Dark): 暗色背景，适合夜间使用  
![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008692.png)
![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192004573.png)

在应用右下角点击切换按钮可快速切换主题，且会自动保存偏好设置。

---

## 📜 许可证

本项目采用 MIT 许可证。

---

*本项目非 Grsai 官方客户端，仅供学习交流使用。*