import json
with open('models/piper/zh_CN-huayan-medium.onnx.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# 打印关键信息
print("=== Model Config ===")
print("espeak voice:", cfg.get("espeak", {}).get("voice", "unknown"))
print("sample_rate:", cfg.get("audio", {}).get("sample_rate", "unknown"))
print("num_speakers:", cfg.get("num_speakers", 1))
if "speaker_id_map" in cfg:
    print("speakers:", list(cfg["speaker_id_map"].keys()))
print("dataset:", cfg.get("dataset", "unknown"))
print("language:", cfg.get("language", {}))
