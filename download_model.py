"""下载 Piper 中文 TTS 模型"""
import os
from huggingface_hub import hf_hub_download

target_dir = r"E:\AI\LocalVoice\models\piper"
os.makedirs(target_dir, exist_ok=True)

print("Downloading zh_CN-huayan-medium.onnx ...")
p1 = hf_hub_download(
    repo_id="rhasspy/piper-voices",
    filename="zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
    local_dir=target_dir,
)
print(f"Model saved: {p1}")

print("Downloading zh_CN-huayan-medium.onnx.json ...")
p2 = hf_hub_download(
    repo_id="rhasspy/piper-voices",
    filename="zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json",
    local_dir=target_dir,
)
print(f"Config saved: {p2}")

print("Done!")
