"""
LocalVoice 主程序入口

串联所有模块：配置加载 → TTS 引擎 → 音频播放器 → 朗读队列 → 快捷键监听
"""

import os
import sys
import logging
import configparser
from pathlib import Path

# 将项目根目录加入 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.tts_engine import create_engine
from core.audio_player import AudioPlayer
from core.tts_queue import TTSQueue
from hotkey.hotkey_control import HotkeyController


def load_config(config_path: str) -> configparser.ConfigParser:
    """加载配置文件"""
    config = configparser.ConfigParser()

    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
        logging.info(f"配置加载完成: {config_path}")
    else:
        logging.warning(f"配置文件不存在: {config_path}，使用默认值")
        config = _create_default_config(config_path)

    return config


def _create_default_config(config_path: str) -> configparser.ConfigParser:
    """创建默认配置文件"""
    config = configparser.ConfigParser()

    config['engine'] = {
        'model': 'piper',
        'model_path': 'models/piper/zh_CN-huayan-medium.onnx',
        'config_path': 'models/piper/zh_CN-huayan-medium.onnx.json',
        'sample_rate': '22050'
    }

    config['audio'] = {
        'speed': '1.0',
        'volume': '1.0'
    }

    config['hotkeys'] = {
        'read_selected': 'ctrl+alt+r',
        'pause_resume': 'ctrl+alt+p',
        'stop': 'ctrl+alt+x',
        'toggle_auto': 'ctrl+alt+s',
        'speed_up': 'ctrl+alt+up',
        'speed_down': 'ctrl+alt+down'
    }

    config['text'] = {
        'max_sentence_length': '200',
        'min_sentence_length': '5',
        'dedup_window_ms': '3000'
    }

    config['logging'] = {
        'level': 'INFO'
    }

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)

    logging.info(f"默认配置已创建: {config_path}")
    return config


def setup_logging(config):
    """配置日志"""
    level_name = config.get('logging', 'level', fallback='INFO')
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """主函数"""
    print("=" * 50)
    print("  LocalVoice - 本地离线 TTS 文本朗读工具")
    print("  眼睛累了，让 AI 帮你读")
    print("=" * 50)

    # 加载配置
    config_path = PROJECT_ROOT / 'config' / 'settings.ini'
    config = load_config(str(config_path))

    setup_logging(config)
    logger = logging.getLogger("main")
    logger.info("LocalVoice 启动中...")

    # 创建必要的目录
    (PROJECT_ROOT / 'temp').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'models' / 'piper').mkdir(parents=True, exist_ok=True)

    # 初始化 TTS 引擎
    engine_type = config.get('engine', 'model', fallback='piper')
    model_path = config.get('engine', 'model_path', fallback='')
    config_path_str = config.get('engine', 'config_path', fallback='')
    sample_rate = config.getint('engine', 'sample_rate', fallback=22050)

    # 处理相对路径
    if model_path and not os.path.isabs(model_path):
        model_path = str(PROJECT_ROOT / model_path)
    if config_path_str and not os.path.isabs(config_path_str):
        config_path_str = str(PROJECT_ROOT / config_path_str)

    engine = create_engine(engine_type, model_path, config_path_str, sample_rate)
    if engine is None:
        logger.error("TTS 引擎创建失败，请检查模型文件和配置")
        logger.info("请下载 Piper 中文模型到 models/piper/ 目录")
        logger.info("下载地址: https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium")

    # 初始化音频播放器
    player = AudioPlayer()

    # 初始化朗读队列
    speed = config.getfloat('audio', 'speed', fallback=1.0)
    volume = config.getfloat('audio', 'volume', fallback=1.0)
    tts_queue = TTSQueue(engine, player, speed=speed, volume=volume)

    # 状态变化回调
    def on_state_change(state, info):
        if state == "start":
            print(f"\r🔊 开始朗读: {info}")
        elif state == "end":
            print(f"\r✅ {info}")
        elif state == "paused":
            print(f"\r⏸️ {info}")
        elif state == "resumed":
            print(f"\r▶️ {info}")
        elif state == "stopped":
            print(f"\r⏹️ {info}")
        elif state == "speed":
            print(f"\r⚡ {info}")
        elif state == "volume":
            print(f"\r🔊 {info}")

    tts_queue.set_on_state_change(on_state_change)

    # 初始化快捷键
    hotkeys = dict(config.items('hotkeys')) if config.has_section('hotkeys') else {}
    hotkey_ctrl = HotkeyController(tts_queue, hotkeys)

    if not hotkey_ctrl.start():
        logger.error("快捷键注册失败，程序无法正常工作")
        logger.info("请尝试以管理员权限运行")
        input("按回车键退出...")
        return

    # 打印使用说明
    print("\n📌 使用方法:")
    print("  1. 在任意软件中选中文字（网页、PDF、记事本等）")
    print("  2. 按 Ctrl+Alt+R 触发朗读")
    print("  3. Ctrl+Alt+P 暂停/继续")
    print("  4. Ctrl+Alt+X 停止朗读")
    print("  5. Ctrl+Alt+S 开关剪贴板自动监听")
    print("  6. Ctrl+Alt+↑/↓ 调速")
    print("\n💡 程序正在后台运行，关闭此窗口退出\n")

    logger.info("LocalVoice 已启动，等待快捷键操作...")

    # 主循环
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在退出...")
        hotkey_ctrl.stop()
        player.quit()
        logger.info("LocalVoice 已退出")


if __name__ == '__main__':
    main()
