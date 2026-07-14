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
    """Piper TTS 适配器 — 基于 ONNX 模型"""

    def __init__(self, model_path: str, config_path: str = None, sample_rate: int = 22050):
        super().__init__(model_path, config_path, sample_rate)
        self._session = None
        self._config = None
        self._phonemizer = None
        self._init_engine()

    def _init_engine(self):
        """初始化 Piper ONNX 模型"""
        try:
            import onnxruntime as ort
        except ImportError:
            logger.error("onnxruntime 未安装，请运行 pip install onnxruntime")
            return

        if not os.path.exists(self.model_path):
            logger.warning(f"Piper 模型文件不存在: {self.model_path}")
            logger.info("请下载 Piper 中文模型并放入 models/piper/ 目录")
            return

        # 加载 ONNX 模型
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._session = ort.InferenceSession(
            self.model_path,
            sess_options,
            providers=['CPUExecutionProvider']
        )

        # 加载模型配置
        if self.config_path and os.path.exists(self.config_path):
            import json
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            # 从配置读取采样率
            if 'audio' in self._config and 'sample_rate' in self._config['audio']:
                self.sample_rate = self._config['audio']['sample_rate']

        self._initialized = True
        logger.info(f"Piper 引擎初始化完成: {self.model_path}")

    def synthesize(self, text: str, speed: float = 1.0, volume: float = 1.0,
                   output_path: str = None) -> Optional[str]:
        """
        Piper 合成

        速度控制通过 length_scale 参数实现（Piper 特有）
        """
        if not self._initialized or not self._session:
            logger.error("Piper 引擎未初始化，无法合成")
            return None

        if not text.strip():
            return None

        output_path = self._ensure_output_path(output_path)

        try:
            audio_data = self._run_inference(text, speed, volume)
            if audio_data is not None and len(audio_data) > 0:
                self._save_wav(audio_data, output_path)
                logger.debug(f"Piper 合成完成: {output_path} ({len(audio_data)} samples)")
                return output_path
            else:
                logger.warning("Piper 合成返回空音频")
                return None
        except Exception as e:
            logger.error(f"Piper 合成失败: {e}", exc_info=True)
            return None

    def _run_inference(self, text: str, speed: float, volume: float) -> Optional[np.ndarray]:
        """运行 Piper ONNX 推理"""
        # Piper 的输入参数名和结构因模型版本而异
        # 这里实现通用逻辑，后续根据实际模型调整

        try:
            # 获取模型输入信息
            input_meta = self._session.get_inputs()

            # 简化处理：使用 espeak-ng 风格的 phonemizer
            # 实际 Piper 模型需要 piper-phonemize 或 espeak-ng
            # 这里提供基础实现，后续可安装 piper-tts 包

            # 尝试使用 piper 专用库
            try:
                from piper_phonemize import phonemize_espeak
                # 中文 phonemize
                phonemes = phonemize_espeak(text, 'cmn')  # cmn = Mandarin Chinese
            except ImportError:
                # 回退：直接用文本作为输入（部分 Piper 模型支持）
                logger.warning("piper-phonemize 未安装，尝试直接文本输入")
                phonemes = text

            # Piper length_scale: >1 放慢, <1 加快
            length_scale = 1.0 / speed if speed > 0 else 1.0

            # 构造输入
            # 不同 Piper 模型输入名可能不同，这里通用处理
            input_feed = {}
            for meta in input_meta:
                name = meta.name
                if 'text' in name.lower() or 'phoneme' in name.lower() or 'input' in name.lower():
                    # 文本/音素输入
                    if meta.type == 'int64':
                        # 将文本编码为 ID 序列
                        input_feed[name] = np.array(
                            [ord(c) for c in phonemes[:512]], dtype=np.int64
                        ).reshape(1, -1)
                    else:
                        input_feed[name] = np.array(
                            [list(phonemes[:512])], dtype=meta.type
                        )
                elif 'length' in name.lower() or 'scale' in name.lower():
                    input_feed[name] = np.array([length_scale], dtype=np.float32)
                elif 'sid' in name.lower() or 'speaker' in name.lower():
                    input_feed[name] = np.array([0], dtype=np.int64)

            # 运行推理
            outputs = self._session.run(None, input_feed)
            audio_data = outputs[0]

            # 处理输出
            audio_data = np.array(audio_data).flatten()

            # 音量调节
            if volume != 1.0:
                audio_data = audio_data * volume

            return audio_data

        except Exception as e:
            logger.error(f"Piper 推理过程出错: {e}", exc_info=True)
            return None


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
