"""
音频播放控制模块

基于 pygame.mixer 实现流式播放、暂停/继续/停止、音量调节。
"""

import os
import time
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AudioPlayer:
    """音频播放控制器"""

    def __init__(self):
        self._initialized = False
        self._playing = False
        self._paused = False
        self._current_file = None
        self._on_playback_end: Optional[Callable] = None
        self._stop_flag = False
        self._lock = threading.Lock()
        self._init_pygame()

    def _init_pygame(self):
        """初始化 pygame 音频模块"""
        try:
            import pygame
            pygame.init()
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
            self._initialized = True
            logger.info("音频播放器初始化完成 (pygame.mixer)")
        except Exception as e:
            logger.error(f"pygame 初始化失败: {e}")
            logger.info("如果没有声音，请检查音频设备")

    def play_file(self, wav_path: str, on_end: Callable = None, volume: float = 1.0):
        """
        播放一个 WAV 文件（阻塞式，在子线程中调用）

        Args:
            wav_path: WAV 文件路径
            on_end: 播放结束回调
            volume: 音量 0.0-1.0
        """
        if not self._initialized:
            logger.error("播放器未初始化")
            if on_end:
                on_end()
            return

        if not os.path.exists(wav_path):
            logger.error(f"音频文件不存在: {wav_path}")
            if on_end:
                on_end()
            return

        with self._lock:
            self._stop_flag = False
            self._paused = False
            self._playing = True
            self._current_file = wav_path

        import pygame
        try:
            pygame.mixer.music.load(wav_path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()

            # 等待播放完成或被停止
            while pygame.mixer.music.get_busy() or self._paused:
                if self._stop_flag:
                    pygame.mixer.music.stop()
                    break
                if self._paused:
                    time.sleep(0.05)
                    continue
                time.sleep(0.05)

        except Exception as e:
            logger.error(f"播放出错: {e}", exc_info=True)
        finally:
            with self._lock:
                self._playing = False
                self._paused = False
                self._current_file = None

            # 尝试清理临时文件
            try:
                if 'temp' in wav_path:
                    os.remove(wav_path)
            except:
                pass

            if on_end and not self._stop_flag:
                on_end()

    def pause(self):
        """暂停播放"""
        if not self._initialized:
            return
        with self._lock:
            self._paused = True
        import pygame
        pygame.mixer.music.pause()
        logger.info("播放暂停")

    def resume(self):
        """继续播放"""
        if not self._initialized:
            return
        with self._lock:
            self._paused = False
        import pygame
        pygame.mixer.music.unpause()
        logger.info("播放继续")

    def stop(self):
        """停止播放"""
        if not self._initialized:
            return
        with self._lock:
            self._stop_flag = True
            self._paused = False
        import pygame
        pygame.mixer.music.stop()
        logger.info("播放停止")

    def set_volume(self, volume: float):
        """实时调节音量"""
        if not self._initialized:
            return
        volume = max(0.0, min(1.0, volume))
        import pygame
        pygame.mixer.music.set_volume(volume)
        logger.debug(f"音量调节: {volume:.1f}")

    def is_playing(self) -> bool:
        """是否正在播放"""
        with self._lock:
            return self._playing

    def is_paused(self) -> bool:
        """是否暂停中"""
        with self._lock:
            return self._paused

    def quit(self):
        """释放资源"""
        self.stop()
        if self._initialized:
            import pygame
            pygame.mixer.quit()
            pygame.quit()
