"""
朗读队列管理模块

流式处理：先切句 → 首句立即合成播放 → 后续句子异步排队合成。
实现"边播边合成"，保证复制后秒听第一句。
"""

import os
import sys
import threading
import time
import logging
from typing import Optional

from core.audio_player import AudioPlayer
from core.tts_engine import BaseTTSEngine

logger = logging.getLogger(__name__)


class TTSQueue:
    """朗读队列 — 线程安全的流式 TTS 调度器"""

    def __init__(self, engine: BaseTTSEngine, player: AudioPlayer,
                 speed: float = 1.0, volume: float = 1.0):
        """
        Args:
            engine: TTS 引擎实例
            player: 音频播放器实例
            speed: 语速
            volume: 音量
        """
        self.engine = engine
        self.player = player
        self.speed = speed
        self.volume = volume

        self._sentence_queue = []          # 待合成+播放的句子列表
        self._synth_queue = []            # 已合成待播放的 WAV 路径列表
        self._queue_lock = threading.Lock()
        self._is_reading = False
        self._is_paused = False
        self._stop_flag = False
        self._synth_thread: Optional[threading.Thread] = None
        self._play_thread: Optional[threading.Thread] = None

        # 回调
        self._on_state_change = None       # 状态变化回调 (state, info)

    def set_on_state_change(self, callback):
        """设置状态变化回调"""
        self._on_state_change = callback

    def _notify_state(self, state: str, info: str = ""):
        """通知状态变化"""
        logger.info(f"[状态] {state}: {info}")
        if self._on_state_change:
            try:
                self._on_state_change(state, info)
            except:
                pass

    def enqueue_text(self, text: str):
        """
        入队新文本（大段文字会先切句）

        如果当前正在朗读，会停止当前朗读并清空旧队列。
        """
        from core.text_preprocess import TextPreprocessor

        # 动态创建预处理器（保持独立配置）
        preprocessor = TextPreprocessor()
        sentences = preprocessor.process(text)

        if not sentences:
            logger.info("无有效文本可朗读")
            return

        # 停止当前朗读
        if self._is_reading:
            self.stop_reading()

        with self._queue_lock:
            self._sentence_queue = list(sentences)
            self._synth_queue = []
            self._stop_flag = False
            self._is_paused = False
            self._is_reading = True

        self._notify_state("start", f"{len(sentences)} 句")

        # 启动合成线程和播放线程
        self._synth_thread = threading.Thread(target=self._synth_worker, daemon=True)
        self._play_thread = threading.Thread(target=self._play_worker, daemon=True)
        self._synth_thread.start()
        self._play_thread.start()

    def _synth_worker(self):
        """合成线程：逐句合成，放入已合成队列"""
        while True:
            if self._stop_flag:
                break

            # 取一句
            with self._queue_lock:
                if self._is_paused:
                    time.sleep(0.05)
                    continue

                if not self._sentence_queue:
                    break

                sentence = self._sentence_queue.pop(0)

            # 合成
            logger.info(f"[合成] {sentence[:50]}{'...' if len(sentence)>50 else ''}")
            wav_path = self.engine.synthesize(
                text=sentence,
                speed=self.speed,
                volume=self.volume
            )

            if wav_path:
                with self._queue_lock:
                    self._synth_queue.append(wav_path)
            else:
                logger.warning(f"合成失败，跳过: {sentence[:30]}...")

        logger.debug("合成线程结束")

    def _play_worker(self):
        """播放线程：从已合成队列取音频播放"""
        while True:
            if self._stop_flag:
                break

            # 暂停时等待
            if self._is_paused:
                time.sleep(0.05)
                continue

            # 取一个已合成的音频
            wav_path = None
            with self._queue_lock:
                if self._synth_queue:
                    wav_path = self._synth_queue.pop(0)

            if wav_path:
                logger.info(f"[播放] {os.path.basename(wav_path)}")
                # 阻塞播放（player 内部处理暂停/停止）
                self.player.play_file(
                    wav_path,
                    on_end=self._on_sentence_end,
                    volume=self.volume
                )
            else:
                # 没有已合成的音频
                # 检查是否还有待合成的
                with self._queue_lock:
                    has_pending = len(self._sentence_queue) > 0 or len(self._synth_queue) > 0

                if not has_pending:
                    break
                time.sleep(0.05)  # 等待合成

        with self._queue_lock:
            self._is_reading = False

        self._notify_state("end", "朗读完成")

    def _on_sentence_end(self):
        """单句播放结束回调"""
        pass  # 播放线程会自动取下一句

    def pause(self):
        """暂停朗读（暂停播放，合成线程也暂停）"""
        with self._queue_lock:
            self._is_paused = True
        self.player.pause()
        self._notify_state("paused", "已暂停")

    def resume(self):
        """继续朗读"""
        with self._queue_lock:
            self._is_paused = False
        self.player.resume()
        self._notify_state("resumed", "已继续")

    def stop_reading(self):
        """停止当前朗读，清空队列"""
        with self._queue_lock:
            self._stop_flag = True
            self._is_paused = False
            self._sentence_queue = []
            self._synth_queue = []

        self.player.stop()

        # 等待线程结束
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2.0)
        if self._synth_thread and self._synth_thread.is_alive():
            self._synth_thread.join(timeout=2.0)

        with self._queue_lock:
            self._is_reading = False

        self._notify_state("stopped", "已停止")

    def set_speed(self, speed: float):
        """设置语速"""
        self.speed = max(0.5, min(2.0, speed))
        self._notify_state("speed", f"语速 {self.speed:.1f}x")

    def set_volume(self, volume: float):
        """设置音量"""
        self.volume = max(0.0, min(1.0, volume))
        self.player.set_volume(self.volume)
        self._notify_state("volume", f"音量 {self.volume:.1f}")

    def is_reading(self) -> bool:
        """是否正在朗读"""
        with self._queue_lock:
            return self._is_reading

    def is_paused(self) -> bool:
        """是否暂停"""
        with self._queue_lock:
            return self._is_paused

    def get_queue_length(self) -> int:
        """获取剩余队列长度"""
        with self._queue_lock:
            return len(self._sentence_queue) + len(self._synth_queue)
