# LocalVoice 架构设计

## 整体架构

```
选中文本/剪贴板 → 快捷键触发 → 文本预处理 → 智能分句 → 朗读队列 → TTS引擎 → 音频播放
                        ↑                                    ↓         ↑
                        └────────── 快捷键控制 ←─── 状态回调 └─────────┘
```

## 数据流

### 流式处理核心流程

1. 用户复制/选中文字 → 触发音量键或自动监听
2. **文本预处理**：清洗、去重
3. **智能分句**：切成短句列表 [句1, 句2, 句3, ...]
4. **首句立即合成**：句1 → TTS 引擎 → WAV 音频
5. **首句立即播放**：句1 音频 → pygame.mixer 播放
6. **后续异步合成**：句2、句3... 在后台线程依次合成
7. **逐句连续播放**：句1播完 → 句2（已合成完毕）→ 立即播放
8. 重复 6-7 直到队列清空

### 关键设计：边播边合成

```
时间线：
句1: [合成中...] [播放中..................]
句2:              [合成中...] [播放中............]
句3:                          [合成中...] [播放中......]
```

用户感知：复制后 ~0.5秒听到第一句，后续无间断连续朗读。

## 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 文本预处理 | `core/text_preprocess.py` | 清洗、去重、过滤 |
| 智能分句 | `core/sentence_splitter.py` | 切句、长度控制、引号处理 |
| TTS 引擎 | `core/tts_engine.py` | 抽象接口 + 具体模型适配 |
| 音频播放 | `core/audio_player.py` | 流式播放、暂停/继续/停止 |
| 朗读队列 | `core/tts_queue.py` | 线程安全队列、异步合成调度 |
| 快捷键 | `hotkey/hotkey_control.py` | 全局热键注册与回调 |
| 配置 | `config/settings.ini` | 模型路径、语速、热键映射 |

## 模块间通信

- **队列 → 播放器**：通过回调函数通知"新音频就绪"
- **播放器 → 队列**：播放完毕回调，请求下一句
- **快捷键 → 队列**：暂停/停止/调速指令
- **快捷键 → 播放器**：暂停/停止指令

## TTS 引擎抽象层

```python
class BaseTTSEngine:
    def synthesize(self, text: str, speed: float, volume: float) -> str:
        """输入文本，输出 WAV 文件路径"""
        pass

class PiperTTSEngine(BaseTTSEngine):
    """Piper ONNX 模型适配"""
    pass

# 阶段 2 新增：
class KokoroTTSEngine(BaseTTSEngine):
    """Kokoro 82M 模型适配"""
    pass
```

## 线程模型

- **主线程**：快捷键监听、事件分发
- **合成线程**：后台 TTS 合成，逐句生成 WAV
- **播放线程**：pygame.mixer 播放（pygame 自带音频线程）

## 配置结构

```ini
[engine]
model = piper          ; 当前模型名称
model_path = models/piper/zh_CN-huayan-medium.onnx
sample_rate = 22050

[audio]
speed = 1.0            ; 语速 0.5-2.0
volume = 1.0           ; 音量 0.0-1.0

[hotkeys]
read_selected = ctrl+alt+r
pause_resume = ctrl+alt+p
stop = ctrl+alt+x
toggle_auto = ctrl+alt+s
speed_up = ctrl+alt+up
speed_down = ctrl+alt+down

[text]
max_sentence_length = 200
min_sentence_length = 5
dedup_window_ms = 3000
```
