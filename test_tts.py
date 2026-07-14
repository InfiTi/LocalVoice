"""测试 Piper TTS 合成"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.tts_engine import PiperTTSEngine

model_path = r"models\piper\zh_CN-huayan-medium.onnx"
config_path = r"models\piper\zh_CN-huayan-medium.onnx.json"

print(f"Model exists: {os.path.exists(model_path)}")
print(f"Config exists: {os.path.exists(config_path)}")

engine = PiperTTSEngine(model_path, config_path)

if engine._initialized:
    print("\nSynthesizing: '你好，这是一个测试。'")
    result = engine.synthesize("你好，这是一个测试。", speed=1.0, volume=1.0)
    print(f"Result: {result}")

    if result and os.path.exists(result):
        size = os.path.getsize(result)
        print(f"WAV file size: {size} bytes")
        print("SUCCESS")
    else:
        print("FAILED: no output file")
else:
    print("Engine not initialized")
