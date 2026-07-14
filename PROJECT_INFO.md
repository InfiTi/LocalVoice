# LocalVoice 项目记录

## 基本信息
- **项目名称**: LocalVoice
- **项目路径**: E:\AI项目\LocalVoice
- **GitHub**: https://github.com/InfiTi/LocalVoice
- **创建日期**: 2026-07-14
- **当前阶段**: 阶段1 MVP (已完成)

## 项目概述
本地离线轻量化 TTS 文本朗读工具。解决长时间阅读文字导致眼睛疲劳的问题，通过本地 TTS 将文字转为语音，支持全局文本抓取、流式分句播放、模型热插拔。

## 关键设计决策
1. **音频播放选 pygame.mixer** — 支持 pause/resume/stop/volume，playsound 不支持
2. **流式分句策略** — 复制大段文字先切句，首句立即合成播放，后续异步排队，保证秒听第一句
3. **分句单独成模块** — 分句质量决定朗读体验，后续可独立升级
4. **keyboard 库** — 同时支持全局热键和键监听
5. **TTS 抽象基类** — 换模型只需新增子类，不改业务代码

## 开发阶段
- ✅ 阶段1: MVP核心功能 (2026-07-14)
- ⬜ 阶段2: 模型插拔 + 剪贴板自动监听
- ⬜ 阶段3: 交互完善 + 体验优化
- ⬜ 阶段4: 打包部署 + 拓展预留

## 如何继续开发
1. 读取 ROADMAP.md 了解总体路线和当前进度
2. 读取 ARCHITECTURE.md 了解架构设计
3. 读取 DEVLOG.md 了解已完成的开发记录
4. 从 ROADMAP.md 中标记为"⬜ 待开发"的任务中选取下一步

## 模型下载
Piper 中文模型: https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium
- 下载 .onnx 和 .onnx.json 两个文件
- 放入 models/piper/ 目录
