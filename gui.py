"""
LocalVoice GUI
- 引擎选择 (Kokoro / Silero / Piper)
- 音色选择
- 文本框粘贴文字直接朗读
- 播放/暂停/停止
- 语速音量调节
"""

import os
import sys
import threading
import logging
from pathlib import Path
from configparser import ConfigParser

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gui")

from core.tts_engine import create_engine, KokoroTTSEngine, SileroTTSEngine, PiperTTSEngine
from core.audio_player import AudioPlayer
from core.tts_queue import TTSQueue

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
except ImportError:
    print("需要 tkinter")
    sys.exit(1)


# ── 模型路径 ──
KOKORO_MODEL = PROJECT_ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = PROJECT_ROOT / "models" / "kokoro" / "voices-v1.0.bin"
PIPER_DIR = PROJECT_ROOT / "models" / "piper"


def find_piper_models():
    """扫描 models/piper 目录下的 .onnx 文件"""
    models = []
    if PIPER_DIR.exists():
        for f in sorted(PIPER_DIR.glob("*.onnx")):
            name = f.stem
            parts = name.split("-")
            if len(parts) >= 3:
                lang, speaker, quality = parts[0], parts[1], parts[2]
                label = f"{speaker} ({quality})"
            else:
                label = name
            models.append((label, str(f)))
    return models


# ── 引擎注册 ──
ENGINES = []

# Kokoro
if KOKORO_MODEL.exists():
    ENGINES.append(("Kokoro", "kokoro"))
else:
    ENGINES.append(("Kokoro (未下载)", "kokoro"))

# Piper
piper_models = find_piper_models()
for label, path in piper_models:
    ENGINES.append((f"Piper-{label}", "piper"))


class LocalVoiceApp:
    def __init__(self, root):
        self.root = root
        root.title("LocalVoice - 本地离线朗读")
        root.geometry("620x620")
        root.minsize(500, 520)

        # 状态
        self.engine = None
        self.tts_queue = None
        self.player = AudioPlayer()
        self.current_engine_type = None
        self.current_voice = None

        self._build_ui()
        # 自动选择第一个可用引擎
        if ENGINES:
            self.engine_combo.current(0)
            self._on_engine_change()

    def _build_ui(self):
        # === 顶部：引擎 + 音色选择 ===
        top = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        top.pack(fill=tk.X)

        ttk.Label(top, text="引擎:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.engine_var = tk.StringVar()
        self.engine_combo = ttk.Combobox(top, textvariable=self.engine_var, state="readonly",
                                         width=16, font=("Microsoft YaHei", 9))
        engine_labels = [e[0] for e in ENGINES]
        self.engine_combo["values"] = engine_labels
        self.engine_combo.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Label(top, text="音色:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.voice_var = tk.StringVar()
        self.voice_combo = ttk.Combobox(top, textvariable=self.voice_var, state="readonly",
                                        width=20, font=("Microsoft YaHei", 9))
        self.voice_combo.pack(side=tk.LEFT, padx=(6, 0))

        self.engine_combo.bind("<<ComboboxSelected>>", self._on_engine_change)
        self.voice_combo.bind("<<ComboboxSelected>>", self._on_voice_change)

        # === 文本框 ===
        mid = ttk.Frame(self.root, padding=(10, 4))
        mid.pack(fill=tk.BOTH, expand=True)
        self.text_box = scrolledtext.ScrolledText(
            mid, font=("Microsoft YaHei", 11), wrap=tk.WORD,
            relief="solid", borderwidth=1
        )
        self.text_box.pack(fill=tk.BOTH, expand=True)
        self.text_box.insert("1.0", "在这里粘贴要朗读的文字，然后点击下方按钮开始朗读。")
        self.text_box.bind("<Control-Return>", lambda e: self._on_read_all())

        # === 控制按钮 ===
        ctrl = ttk.Frame(self.root, padding=(10, 4))
        ctrl.pack(fill=tk.X)

        self.btn_read_all = ttk.Button(ctrl, text="朗读全部", command=self._on_read_all)
        self.btn_read_all.pack(side=tk.LEFT, padx=(0, 3))

        self.btn_read_sel = ttk.Button(ctrl, text="朗读选中", command=self._on_read_selected)
        self.btn_read_sel.pack(side=tk.LEFT, padx=3)

        self.btn_pause = ttk.Button(ctrl, text="暂停", command=self._on_pause, state=tk.DISABLED)
        self.btn_pause.pack(side=tk.LEFT, padx=3)

        self.btn_stop = ttk.Button(ctrl, text="停止", command=self._on_stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=3)

        # === 语速音量 ===
        slider_frame = ttk.Frame(self.root, padding=(10, 4, 10, 4))
        slider_frame.pack(fill=tk.X)

        ttk.Label(slider_frame, text="语速", font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky=tk.W)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(slider_frame, from_=0.5, to=2.0, variable=self.speed_var,
                                     orient=tk.HORIZONTAL, command=self._on_speed_change)
        self.speed_scale.grid(row=0, column=1, sticky=tk.EW, padx=(4, 4))
        self.speed_label = ttk.Label(slider_frame, text="1.0x", width=5, font=("Microsoft YaHei", 9))
        self.speed_label.grid(row=0, column=2)

        ttk.Label(slider_frame, text="音量", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        self.vol_var = tk.DoubleVar(value=1.0)
        self.vol_scale = ttk.Scale(slider_frame, from_=0.0, to=1.0, variable=self.vol_var,
                                   orient=tk.HORIZONTAL, command=self._on_vol_change)
        self.vol_scale.grid(row=1, column=1, sticky=tk.EW, padx=(4, 4), pady=(4, 0))
        self.vol_label = ttk.Label(slider_frame, text="100%", width=5, font=("Microsoft YaHei", 9))
        self.vol_label.grid(row=1, column=2, pady=(4, 0))

        slider_frame.columnconfigure(1, weight=1)

        # === 状态栏 ===
        bottom = ttk.Frame(self.root, padding=(10, 2, 10, 8))
        bottom.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="正在加载...")
        ttk.Label(bottom, textvariable=self.status_var, font=("Microsoft YaHei", 9),
                  foreground="gray").pack(side=tk.LEFT)
        self.progress_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.progress_var, font=("Microsoft YaHei", 9),
                  foreground="blue").pack(side=tk.RIGHT)

    def _get_voices_for_engine(self, engine_type: str):
        """返回 (value, label) 列表"""
        if engine_type == "kokoro":
            return [(v[0], v[1]) for v in KokoroTTSEngine.CN_VOICES]
        elif engine_type == "silero":
            return []
        elif engine_type == "piper":
            # Piper 每个模型就是一种声音
            return [("", "默认")]
        return []

    def _on_engine_change(self, event=None):
        """引擎切换"""
        idx = self.engine_combo.current()
        if idx < 0:
            return
        engine_type = ENGINES[idx][1]

        # 停止当前朗读
        if self.tts_queue and self.tts_queue.is_reading():
            self.tts_queue.stop_reading()
        self.engine = None
        self.tts_queue = None

        # 更新音色列表
        voices = self._get_voices_for_engine(engine_type)
        voice_labels = [v[1] for v in voices]
        self.voice_combo["values"] = voice_labels
        if voice_labels:
            self.voice_combo.current(0)

        self.current_engine_type = engine_type
        self._init_engine()

    def _on_voice_change(self, event=None):
        """音色切换"""
        if not self.engine:
            return
        idx = self.voice_combo.current()
        voices = self._get_voices_for_engine(self.current_engine_type)
        if idx < 0 or idx >= len(voices):
            return
        voice = voices[idx][0]
        self.current_voice = voice

        if hasattr(self.engine, 'set_voice'):
            self.engine.set_voice(voice)

    def _init_engine(self):
        """子线程加载模型"""
        engine_type = self.current_engine_type
        if not engine_type:
            return

        def load():
            self.status_var.set(f"正在加载 {engine_type} 引擎...")

            try:
                if engine_type == "kokoro":
                    if not KOKORO_MODEL.exists():
                        self.status_var.set("Kokoro 模型未下载，请先下载")
                        return
                    self.engine = create_engine(
                        "kokoro",
                        str(KOKORO_MODEL),
                        str(KOKORO_VOICES),
                        24000
                    )
                    # 设置默认音色
                    voices = self._get_voices_for_engine("kokoro")
                    if voices:
                        self.current_voice = voices[0][0]
                        self.engine.set_voice(self.current_voice)

                elif engine_type == "silero":
                    self.status_var.set("Silero 不支持中文，请选择 Kokoro 或 Piper")
                    return

                elif engine_type == "piper":
                    # 通过引擎 label 找到对应的 piper 模型路径
                    selected_label = ENGINES[self.engine_combo.current()][0]  # e.g. "Piper-huayan (medium)"
                    piper_label_part = selected_label.replace("Piper-", "")
                    piper_entries = find_piper_models()
                    model_path = None
                    for label, path in piper_entries:
                        if label == piper_label_part:
                            model_path = path
                            break
                    if not model_path:
                        self.status_var.set("未找到 Piper 模型")
                        return
                    config_path = model_path.replace(".onnx", ".onnx.json")
                    self.engine = create_engine("piper", model_path, config_path, 22050)

                if self.engine and self.engine._initialized:
                    self.tts_queue = TTSQueue(self.engine, self.player, speed=1.0, volume=1.0)
                    self.tts_queue.set_on_state_change(self._on_state_change)
                    self.status_var.set(f"就绪 - {engine_type} 引擎已加载")
                else:
                    self.status_var.set(f"{engine_type} 引擎加载失败")

            except Exception as e:
                logger.error(f"引擎加载异常: {e}", exc_info=True)
                self.status_var.set(f"加载失败: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_state_change(self, state, info):
        def update():
            if state == "start":
                self.status_var.set(f"朗读中... {info}")
                self.btn_pause.config(state=tk.NORMAL, text="暂停")
                self.btn_stop.config(state=tk.NORMAL)
                self.btn_read_all.config(state=tk.DISABLED)
                self.btn_read_sel.config(state=tk.DISABLED)
                self.engine_combo.config(state=tk.DISABLED)
                self.voice_combo.config(state=tk.DISABLED)
            elif state == "end":
                self.status_var.set("朗读完成")
                self.btn_pause.config(state=tk.DISABLED, text="暂停")
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_read_all.config(state=tk.NORMAL)
                self.btn_read_sel.config(state=tk.NORMAL)
                self.engine_combo.config(state="readonly")
                self.voice_combo.config(state="readonly")
                self.progress_var.set("")
            elif state == "paused":
                self.status_var.set("已暂停")
                self.btn_pause.config(text="继续")
            elif state == "resumed":
                self.status_var.set("继续朗读...")
                self.btn_pause.config(text="暂停")
            elif state == "stopped":
                self.status_var.set("已停止")
                self.btn_pause.config(state=tk.DISABLED, text="暂停")
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_read_all.config(state=tk.NORMAL)
                self.btn_read_sel.config(state=tk.NORMAL)
                self.engine_combo.config(state="readonly")
                self.voice_combo.config(state="readonly")
                self.progress_var.set("")
            elif state == "speed":
                self.progress_var.set(info)
            elif state == "volume":
                self.progress_var.set(info)

        self.root.after(0, update)

    def _on_read_all(self):
        text = self.text_box.get("1.0", tk.END).strip()
        if not text:
            self.status_var.set("文本框为空")
            return
        self._read(text)

    def _on_read_selected(self):
        try:
            text = self.text_box.selection_get().strip()
        except:
            self.status_var.set("请先选中文字")
            return
        if not text:
            self.status_var.set("没有选中的文字")
            return
        self._read(text)

    def _read(self, text):
        if not self.tts_queue:
            self.status_var.set("引擎尚未加载，请稍等")
            return
        self.status_var.set("准备朗读...")
        threading.Thread(target=lambda: self.tts_queue.enqueue_text(text), daemon=True).start()

    def _on_pause(self):
        if not self.tts_queue:
            return
        if self.tts_queue.is_paused():
            self.tts_queue.resume()
        else:
            self.tts_queue.pause()

    def _on_stop(self):
        if not self.tts_queue:
            return
        self.tts_queue.stop_reading()

    def _on_speed_change(self, val):
        speed = round(float(val), 1)
        self.speed_label.config(text=f"{speed:.1f}x")
        if self.tts_queue:
            self.tts_queue.set_speed(speed)

    def _on_vol_change(self, val):
        vol = round(float(val), 2)
        self.vol_label.config(text=f"{int(vol*100)}%")
        if self.tts_queue:
            self.tts_queue.set_volume(vol)

    def on_close(self):
        if self.player:
            self.player.quit()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LocalVoiceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
