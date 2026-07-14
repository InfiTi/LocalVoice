# LocalVoice

> 本地离线轻量化 TTS 文本朗读工具 — 眼睛累了，让 AI 帮你读。

## 特性

- 🔒 **完全离线**：所有语音合成在本地完成，无联网、无隐私上传
- 🎯 **全场景文本抓取**：选中文字一键朗读 / 剪贴板自动监听（阶段2）
- ⚡ **流式分句播放**：复制大段文字也能秒听第一句，边播边合成
- 🔌 **模型热插拔**：统一接口，切换 TTS 模型无需改业务代码
- ⌨️ **全局快捷键**：朗读、暂停、停止、调速，全局生效
- 🪶 **轻量低耗**：适配普通 CPU，无需显卡，后台常驻低占用

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11（Mac 可用，快捷键库略有差异）
- 无需 GPU

### 安装

```bash
cd E:\AI项目\LocalVoice
pip install -r requirements.txt
```

### 下载 Piper 中文模型

1. 访问 https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium
2. 下载 `zh_CN-huayan-medium.onnx` 和 `zh_CN-huayan-medium.onnx.json`
3. 放入 `models/piper/` 目录

### 运行

```bash
python main.py
```

### 使用

1. 在任意软件中选中文字（网页、PDF、记事本等）
2. 按 `Ctrl+Alt+R` 触发朗读
3. `Ctrl+Alt+P` 暂停/继续
4. `Ctrl+Alt+X` 停止

## 项目结构

```
LocalVoice/
├── config/
│   └── settings.ini          # 配置文件
├── core/
│   ├── sentence_splitter.py  # 智能分句
│   ├── text_preprocess.py    # 文本预处理
│   ├── tts_engine.py         # TTS 引擎抽象 + Piper 适配
│   ├── audio_player.py       # 音频播放控制
│   └── tts_queue.py          # 朗读队列管理
├── hotkey/
│   └── hotkey_control.py     # 全局快捷键
├── models/                   # TTS 模型存放
│   └── piper/
├── temp/                     # 临时音频缓存
├── main.py                   # 入口
├── requirements.txt
├── ROADMAP.md                # 开发路线图
├── ARCHITECTURE.md           # 架构设计
├── DEVLOG.md                 # 开发日志
└── README.md
```

## 开发路线

详见 [ROADMAP.md](ROADMAP.md)

- ✅ 阶段 1：MVP 核心功能
- ⬜ 阶段 2：模型插拔 + 剪贴板自动监听
- ⬜ 阶段 3：交互完善 + 体验优化
- ⬜ 阶段 4：打包部署 + 拓展预留

## 换模型

1. 将新模型（ONNX 格式）放入 `models/` 对应目录
2. 在 `core/tts_engine.py` 中新增适配子类，继承 `BaseTTSEngine`
3. 修改 `config/settings.ini` 中 `model` 和 `model_path`
4. 重启程序

详见 [ARCHITECTURE.md](ARCHITECTURE.md)
