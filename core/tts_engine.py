"""
TTS 引擎抽象层 + Piper 适配器

所有 TTS 模型实现统一接口，切换模型只需新增子类 + 修改配置。
"""

import os
import wave
import logging
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class BaseTTSEngine(ABC):
    """TTS 引擎抽象基类"""

    def __init__(self, model_path: str, config_path: str = None, sample_rate: int = 22050):
        """
        Args:
            model_path: 模型文件路径
            config_path: 模型配置文件路径
            sample_rate: 采样率
        """
        self.model_path = model_path
        self.config_path = config_path
        self.sample_rate = sample_rate
        self._initialized = False

    @abstractmethod
    def synthesize(self, text: str, speed: float = 1.0, volume: float = 1.0,
                   output_path: str = None) -> Optional[str]:
        """
        文本 → 语音合成

        Args:
            text: 输入文本
            speed: 语速 0.5-2.0（1.0 = 正常语速）
            volume: 音量 0.0-1.0
            output_path: WAV 输出路径，None 则自动生成

        Returns:
            WAV 文件路径，失败返回 None
        """
        pass

    def _ensure_output_path(self, output_path: str = None) -> str:
        """确保输出路径存在"""
        if output_path is None:
            import time
            import tempfile
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            output_path = os.path.join(temp_dir, f'tts_{int(time.time()*1000)}.wav')
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return output_path

    def _save_wav(self, audio_data: np.ndarray, path: str):
        """将音频数据保存为 WAV 文件"""
        # 确保是 int16
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)

        with wave.open(path, 'w') as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())


class PiperTTSEngine(BaseTTSEngine):
    """Piper TTS 适配器 — 基于 piper-tts 官方库"""

    def __init__(self, model_path: str, config_path: str = None, sample_rate: int = 22050):
        super().__init__(model_path, config_path, sample_rate)
        self._voice = None
        self._init_engine()

    def _init_engine(self):
        """初始化 Piper 语音模型"""
        if not os.path.exists(self.model_path):
            logger.warning(f"Piper 模型文件不存在: {self.model_path}")
            logger.info("请下载 Piper 中文模型并放入 models/piper/ 目录")
            return

        # 确定配置文件路径
        if not self.config_path or not os.path.exists(self.config_path):
            base = os.path.splitext(self.model_path)[0]
            self.config_path = base + ".onnx.json"
            if not os.path.exists(self.config_path):
                logger.error(f"Piper 配置文件不存在: {self.config_path}")
                return

        try:
            from piper import PiperVoice

            self._voice = PiperVoice.load(
                self.model_path,
                config_path=self.config_path,
            )

            if hasattr(self._voice, 'config') and hasattr(self._voice.config, 'sample_rate'):
                self.sample_rate = self._voice.config.sample_rate

            self._initialized = True
            logger.info(f"Piper 引擎初始化完成: {self.model_path} (sample_rate={self.sample_rate})")

        except Exception as e:
            logger.error(f"Piper 引擎初始化失败: {e}", exc_info=True)

    def synthesize(self, text: str, speed: float = 1.0, volume: float = 1.0,
                   output_path: str = None) -> Optional[str]:
        """
        Piper 合成 — 速度控制通过 length_scale 参数实现
        """
        if not self._initialized or not self._voice:
            logger.error("Piper 引擎未初始化，无法合成")
            return None

        if not text.strip():
            return None

        output_path = self._ensure_output_path(output_path)

        try:
            import wave
            from piper import SynthesisConfig

            # Piper length_scale: >1 放慢, <1 加快
            length_scale = 1.0 / speed if speed > 0 else 1.0

            syn_config = SynthesisConfig(
                length_scale=length_scale,
                volume=volume,
            )

            # 新版 piper-tts 返回 AudioChunk 迭代器
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)

                for chunk in self._voice.synthesize(text, syn_config=syn_config):
                    wav_file.writeframes(chunk.audio_int16_bytes)

            logger.debug(f"Piper 合成完成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Piper 合成失败: {e}", exc_info=True)
            return None

    def _apply_volume(self, wav_path: str, volume: float):
        """后处理 WAV 文件调节音量"""
        try:
            import wave
            with wave.open(wav_path, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())

            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            audio = (audio * volume).clip(-32768, 32767).astype(np.int16)

            with wave.open(wav_path, "wb") as wf:
                wf.setparams(params)
                wf.writeframes(audio.tobytes())
        except Exception as e:
            logger.warning(f"音量调节失败: {e}")


def create_engine(engine_type: str, model_path: str, config_path: str = None,
                  sample_rate: int = 22050) -> Optional[BaseTTSEngine]:
    """
    工厂函数：根据类型创建 TTS 引擎

    Args:
        engine_type: 引擎类型 (piper, kokoro, ...)
        model_path: 模型路径
        config_path: 配置路径
        sample_rate: 采样率

    Returns:
        TTS 引擎实例
    """
    engines = {
        'piper': PiperTTSEngine,
    }

    engine_cls = engines.get(engine_type.lower())
    if engine_cls is None:
        logger.error(f"不支持的引擎类型: {engine_type}，可选: {list(engines.keys())}")
        return None

    return engine_cls(model_path, config_path, sample_rate)
