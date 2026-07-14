"""
智能分句模块

将长文本切分为适合 TTS 合成的短句列表。
处理中英文标点、引号内嵌句号、长度上限切分等问题。
"""

import re
import logging

logger = logging.getLogger(__name__)


class SentenceSplitter:
    """智能分句器"""

    # 句子结束标点（中英文）
    SENTENCE_ENDINGS = '。！？；!?;…\n'

    def __init__(self, max_length=200, min_length=5):
        """
        Args:
            max_length: 单句最大字符数，超长自动切分
            min_length: 最小朗读单元，短于此数不断句（避免过于碎片化）
        """
        self.max_length = max_length
        self.min_length = min_length

    def split(self, text: str) -> list[str]:
        """
        将文本切分为短句列表

        Args:
            text: 输入文本

        Returns:
            句子列表，每句已 strip 处理
        """
        if not text or not text.strip():
            return []

        # 清理文本
        text = text.strip()

        # 第一轮：按句末标点切分
        sentences = self._split_by_punctuation(text)

        # 第二轮：超长句再切分
        result = []
        for sent in sentences:
            if len(sent) > self.max_length:
                result.extend(self._split_long_sentence(sent))
            else:
                result.append(sent)

        # 第三轮：合并过短句
        result = self._merge_short_sentences(result)

        # 过滤空句
        result = [s.strip() for s in result if s.strip()]

        logger.debug(f"分句完成：{len(result)} 句")
        for i, s in enumerate(result):
            logger.debug(f"  句{i+1}: {s[:50]}{'...' if len(s)>50 else ''}")

        return result

    def _split_by_punctuation(self, text: str) -> list[str]:
        """按句末标点切分，处理引号内嵌标点"""
        sentences = []
        current = []
        in_quote = False  # 是否在引号内
        quote_char = None

        i = 0
        while i < len(text):
            char = text[i]
            current.append(char)

            # 检测引号开闭（中文引号 \u201c\u201d \u2018\u2019 和英文引号）
            if char in '\u201c\u2018"「『':
                in_quote = True
                quote_char = char
            elif char in '\u201d\u2019"」』':
                in_quote = False
                quote_char = None

            # 只在非引号内的句末标点处断句
            if char in self.SENTENCE_ENDINGS and not in_quote:
                sentence = ''.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

            i += 1

        # 处理最后剩余内容
        remaining = ''.join(current).strip()
        if remaining:
            sentences.append(remaining)

        return sentences

    def _split_long_sentence(self, sentence: str) -> list[str]:
        """超长句按逗号或空格切分"""
        # 优先按逗号切分
        parts = re.split(r'[，,、]', sentence)
        result = []
        buffer = ''

        for part in parts:
            if len(buffer) + len(part) + 1 <= self.max_length:
                buffer = buffer + '，' + part if buffer else part
            else:
                if buffer:
                    result.append(buffer)
                if len(part) > self.max_length:
                    # 单个 part 仍然太长，强制按长度切
                    for j in range(0, len(part), self.max_length):
                        result.append(part[j:j + self.max_length])
                else:
                    buffer = part

        if buffer:
            result.append(buffer)

        return result

    def _merge_short_sentences(self, sentences: list[str]) -> list[str]:
        """合并过短的句子，避免朗读碎片化"""
        if not sentences:
            return []

        merged = []
        buffer = ''

        for sent in sentences:
            if len(buffer) + len(sent) < self.max_length:
                if buffer:
                    buffer = buffer + sent
                else:
                    buffer = sent

                # 如果当前累积长度已经 >= min_length，可以输出
                if len(buffer) >= self.min_length:
                    merged.append(buffer)
                    buffer = ''
            else:
                # 累积超限，先输出 buffer
                if buffer:
                    merged.append(buffer)
                    buffer = ''
                merged.append(sent)

        # 处理剩余
        if buffer:
            merged.append(buffer)

        return merged
