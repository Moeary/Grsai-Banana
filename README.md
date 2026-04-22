# Grsai Banana Image Generator

一个基于 PySide6 和 Fluent-Widgets 构建的 Windows 桌面客户端，专为国产中转网站 [Grsai](https://grsai.com/zh/) 的图像生成模型设计。支持 Banana、Banana Pro/Banana 2、GPT Image 2，并提供普通生图、漫画分页生成、历史记录管理和本地配置保存。

![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008692.png)

## 核心功能

### 生成功能

- 多模型支持:
  - Banana / Banana-Fast
  - Banana Pro / Banana 2
  - GPT Image 2
- 参数灵活配置:
  - 模型动态选择
  - Banana 系列支持宽高比选择，例如 1:1、16:9、9:16、4:3、3:4、3:2、2:3、5:4、4:5、21:9 等
  - Banana Pro/Banana 2 支持 1K、2K、4K 等尺寸
  - GPT Image 2 支持 auto、1:1、3:2、2:3 尺寸
  - GPT Image 2 支持生成变体
- 多图参考:
  - 支持拖拽、点击选择、Ctrl+V 粘贴参考图片
  - 最多支持 14 张参考图片

### 漫画功能

- 使用剧情模型自动规划漫画分页脚本
- 支持项目保存、项目读取和分页内容继续编辑
- 每页可单独生成，也可以一键生成全部页面
- 出图模型支持 Banana 系列和 GPT Image 2
- 支持多张人物参考图，并可为每页指定参考图序号，减少角色混淆
- 生成结果会按项目保存到本地页面目录

### 任务管理

- 实时任务列表，展示任务状态和进度
- 支持手动重试和失败自动重试
- 可配置最大重试次数
- 支持并行任务处理
- VIP 模型的违规失败自动重试可在设置中单独控制

### 历史记录

- 使用本地 SQLite 数据库 `history.db` 保存生成记录
- 支持分页浏览，可配置每页显示数量
- 支持从历史记录恢复参数并重新生成
- 支持打开生成图片所在文件夹
- 提供历史数据库清理功能:
  - 清理运行中任务，适合程序异常关闭后清除卡在 running 的记录
  - 清理失败任务
  - 清空全部历史记录，清空前需要二次确认

### 高级设置

- API Base URL 和 API Key 配置
- 输出文件夹配置
- 最大重试次数配置
- 历史记录每页数量配置
- 界面语言支持 English / 简体中文
- 文本格式化:
  - 字体大小调整
  - 字体选择
  - 自动换行支持
- 主题支持:
  - 亮色模式
  - 深色模式
  - 自动跟随系统
  - 右下角一键切换主题

## 安装与运行

### Windows 用户

直接前往 [GitHub Releases](https://github.com/Moeary/Grsai-Banana/releases) 下载最新的 `main.exe` 程序，双击即用，无需配置 Python 环境。

### 开发者 / 其他系统用户

本项目使用 `pixi` 进行环境管理，确保开发环境一致。

1. 安装 Pixi

   请参考 [Pixi 官方文档](https://pixi.sh/) 安装。

2. 克隆仓库

   ```bash
   git clone https://github.com/Moeary/Grsai-Banana.git
   cd Grsai-Banana
   ```

3. 运行项目

   Pixi 会自动下载并配置所需的 Python 环境和依赖：

   ```bash
   pixi run start
   ```

4. 打包

   如果你想自己编译 exe 文件：

   ```bash
   pixi run build
   ```

   编译产物将位于 `dist/` 目录下。

## 配置说明

首次运行后会在根目录生成 `config.json`。推荐在应用内的 Settings 页面修改配置：

- API Base URL 和 API Key
- 最大重试次数
- VIP 违规失败自动重试
- 历史记录每页显示数量
- 文本格式化选项
- 输出文件夹位置
- 界面语言

![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008854.png)

如果需要，也可以直接编辑 `config.json`。

## 项目结构

```text
Grsai-Banana/
├── ui/                          # 用户界面
│   ├── main_window.py           # 主窗口
│   ├── generator_page.py        # 普通生成页面
│   ├── comic_page.py            # 漫画生成页面
│   ├── history_page.py          # 历史记录页面
│   ├── settings_page.py         # 设置页面
│   └── components/              # UI 组件
│       ├── prompt_widget.py     # 提示词输入框
│       ├── image_drop_area.py   # 图片拖拽区域
│       └── task_widget.py       # 任务卡片和任务列表
├── core/                        # 核心逻辑
│   ├── api_client.py            # API 调用客户端
│   ├── task_manager.py          # 任务管理和并行处理
│   ├── history_manager.py       # SQLite 历史记录管理
│   ├── comic_planner.py         # 漫画分页规划
│   ├── comic_project_manager.py # 漫画项目保存和读取
│   ├── model_catalog.py         # 模型目录
│   ├── i18n.py                  # 多语言文案
│   └── config.py                # 配置管理
├── input/                       # 输入资源目录
├── output/                      # 输出图片目录
├── main.py                      # 程序入口
├── config.json                  # 配置文件
├── history.db                   # SQLite 历史记录数据库
├── pixi.toml                    # Pixi 环境配置
└── requirements.txt             # pip 依赖列表
```

## 快速开始

1. 设置 API Key

   打开设置页面，输入你的 Grsai API Base URL 和 API Key，然后点击 Save Settings。

2. 选择模型和参数

   普通生成页面可在不同模型选项卡间切换；漫画页面可分别选择剧情模型和出图模型。

3. 上传参考图片

   拖拽图片到 Reference Images 区域，或使用 Ctrl+V 从剪贴板粘贴。

4. 输入提示词或故事需求

   普通生成输入 Prompt；漫画生成输入故事需求和可选的风格补充。

5. 生成图片

   点击 Generate Image、Plan Story Pages、Generate This Page 或 Generate All Pages，并在任务列表中查看进度。

6. 查看历史记录

   生成完成后可在 History 页面查看、打开文件夹或重新生成。

## 使用技巧

- 普通生成适合单图快速出图，漫画页面适合连续分页和项目化保存
- GPT Image 2 的尺寸使用 auto、1:1、3:2、2:3，不使用 Banana 的 1K/2K/4K 选项
- 如果程序异常关闭后历史里出现卡在 running 的任务，可以在 History 页面点击清理运行中
- 如果生成失败，可以点击任务卡片上的重试按钮，或开启失败自动重试
- 批量生成时可以调高并行任务数；使用 GPT Image 2 多变体时，程序会限制并行以避免结果混淆
- 在历史页面点击 Regenerate 可以恢复提示词、模型、尺寸和参考图参数

## 主题系统

支持亮色模式、深色模式和跟随系统。可以在应用右下角点击切换按钮快速切换主题，偏好会自动保存。

![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192008692.png)
![](https://raw.githubusercontent.com/Moeary/pic_bed/main/img/202512192004573.png)

## 许可证

本项目采用 MIT 许可证。

---

本项目非 Grsai 官方客户端，仅供学习交流使用。
