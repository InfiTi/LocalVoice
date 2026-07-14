"""
文本预处理模块

清洗输入文本，去除冗余字符，与分句模块联动。
"""

import re
import time
import logging

from core.sentence_splitter import SentenceSplitter

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self, max_sentence_length=200, min_sentence_length=5, dedup_window_ms=3000):
        """
        Args:
            max_sentence_length: 单句最大长度
            min_sentence_length: 单句最小长度
            dedup_window_ms: 去重窗口（毫秒），窗口内相同文本不重复处理
        """
        self.splitter = SentenceSplitter(max_sentence_length, min_sentence_length)
        self.dedup_window_ms = dedup_window_ms
        self._last_text = None
        self._last_text_time = 0

    def process(self, text: str) -> list[str]:
        """
        预处理 + 分句，返回句子列表

        Args:
            text: 原始文本

        Returns:
            句子列表，可能为空列表（重复文本或空文本时）
        """
        if not text:
            return []

        # 清洗文本
        text = self._clean(text)

        if not text.strip():
            return []

        # 去重检查
        now = time.time() * 1000
        if self._last_text == text and (now - self._last_text_time) < self.dedup_window_ms:
            logger.debug("文本重复，跳过")
            return []

        self._last_text = text
        self._last_text_time = now

        # 分句
        sentences = self.splitter.split(text)

        logger.info(f"文本预处理完成：{len(text)} 字 → {len(sentences)} 句")
        return sentences

    def _clean(self, text: str) -> str:
        """清洗文本"""
        # 去除控制字符（保留换行和空格）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # 多个连续空格压缩为单个
        text = re.sub(r'[ \t]+', ' ', text)

        # 多个连续换行压缩为单个
        text = re.sub(r'\n{2,}', '\n', text)

        # 去除行首尾空白
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # 去除常见的复制粘贴带有的格式字符
        text = text.replace('\u200b', '')  # 零宽空格
        text = text.replace('\u200c', '')  # 零宽非连接符
        text = text.replace('\u200d', '')  # 零宽连接符
        text = text.replace('\ufeff', '')  # BOM

        return text.strip()
