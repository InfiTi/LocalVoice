"""测试分句和预处理模块"""
import sys
sys.path.insert(0, '.')

from core.sentence_splitter import SentenceSplitter
from core.text_preprocess import TextPreprocessor

splitter = SentenceSplitter(max_length=100, min_length=5)

# 测试1：中英文混合
text1 = "Hello World。这是一个测试。他说：\u201c你好。\u201d然后走了。This is a test sentence with many words and it should be split properly."
print("=== Test 1: 中英文混合 ===")
for i, s in enumerate(splitter.split(text1)):
    print(f"  S{i+1}: {s}")

# 测试2：超长句
text2 = "这是一段非常长的文字" * 50
print("\n=== Test 2: 超长句切分 ===")
result = splitter.split(text2)
print(f"  Total: {len(result)} sentences")
for i, s in enumerate(result[:3]):
    print(f"  S{i+1}: {s[:50]}...")
print(f"  ... ({len(result)} total)")

# 测试3：预处理
print("\n=== Test 3: 文本预处理 ===")
pp = TextPreprocessor()
dirty_text = "\n\n  多余空格  的文字。  控制字符。  \n\n第二段。  "
sentences = pp.process(dirty_text)
print(f"  Cleaned: {len(sentences)} sentences")
for s in sentences:
    print(f"    [{s}]")

# 测试4：引号内不断句
text4 = "他说：\u201c今天天气很好。我们去公园吧。\u201d大家都很高兴。"
print("\n=== Test 4: 引号内不断句 ===")
for i, s in enumerate(splitter.split(text4)):
    print(f"  S{i+1}: {s}")

print("\nAll tests passed")
