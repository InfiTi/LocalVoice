"""测试所有模型"""
import sys
import os
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    sys.path.insert(0, os.path.dirname(__file__))

    from core.tts_engine import create_engine

    models = [
        ("zh_CN-huayan", "models/piper/zh_CN-huayan-medium.onnx", "models/piper/zh_CN-huayan-medium.onnx.json"),
        ("zh_CN-chaowen", "models/piper/zh_CN-chaowen-medium.onnx", "models/piper/zh_CN-chaowen-medium.onnx.json"),
        ("zh_CN-xiao_ya", "models/piper/zh_CN-xiao_ya-medium.onnx", "models/piper/zh_CN-xiao_ya-medium.onnx.json"),
    ]

    for name, mp, cp in models:
        print(f"\n=== {name} ===")
        if not os.path.exists(mp):
            print(f"  onnx missing")
            continue
        try:
            engine = create_engine("piper", mp, cp, 22050)
            if not engine or not engine._initialized:
                print(f"  FAILED: engine not initialized")
                continue
            result = engine.synthesize("你好，这是测试。", speed=1.0, volume=1.0)
            if result and os.path.exists(result):
                size = os.path.getsize(result)
                print(f"  OK: {result} ({size} bytes)")
            else:
                print(f"  FAILED: no output")
        except Exception as e:
            print(f"  ERROR: {e}")
