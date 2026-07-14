"""列出 Piper 中文模型"""
from huggingface_hub import list_repo_files

files = list_repo_files("rhasspy/piper-voices")
zh = [f for f in files if f.startswith("zh/") and f.endswith(".onnx")]
for f in zh:
    print(f)
