"""下载所有 Piper 中文 medium 模型"""
import os
from huggingface_hub import hf_hub_download

target_dir = r"E:\AI\LocalVoice\models\piper"

models = [
    ("zh/zh_CN/chaowen/medium/zh_CN-chaowen-medium.onnx", "zh_CN-chaowen-medium.onnx"),
    ("zh/zh_CN/chaowen/medium/zh_CN-chaowen-medium.onnx.json", "zh_CN-chaowen-medium.onnx.json"),
    ("zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx", "zh_CN-xiao_ya-medium.onnx"),
    ("zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx.json", "zh_CN-xiao_ya-medium.onnx.json"),
]

for remote_path, local_name in models:
    local_path = os.path.join(target_dir, local_name)
    if os.path.exists(local_path):
        print(f"Skip (exists): {local_name}")
        continue
    print(f"Downloading {local_name} ...")
    hf_hub_download(
        repo_id="rhasspy/piper-voices",
        filename=remote_path,
        local_dir=target_dir,
    )
    # 复制到平铺目录
    src = os.path.join(target_dir, remote_path)
    if os.path.exists(src) and not os.path.exists(local_path):
        import shutil
        shutil.copy2(src, local_path)
    print(f"Done: {local_name}")

print("\nAll models ready!")
