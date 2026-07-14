"""
全局快捷键控制模块

基于 keyboard 库实现全局热键。
支持朗读选中文本、暂停/继续、停止、调速、开关自动监听。
"""

import logging
import threading
import subprocess

logger = logging.getLogger(__name__)


class HotkeyController:
    """全局快捷键控制器"""

    def __init__(self, tts_queue, hotkey_config: dict):
        """
        Args:
            tts_queue: TTSQueue 实例
            hotkey_config: 快捷键配置字典
        """
        self.tts_queue = tts_queue
        self.hotkey_config = hotkey_config
        self._auto_monitor = False  # 自动监听开关
        self._keyboard_hook = None
        self._clipboard_monitor_thread = None

    def start(self):
        """注册所有全局快捷键"""
        try:
            import keyboard
        except ImportError:
            logger.error("keyboard 库未安装，请运行 pip install keyboard")
            return False

        # 注册快捷键
        keys = self.hotkey_config

        # Ctrl+Alt+R: 朗读选中文本
        if 'read_selected' in keys:
            keyboard.add_hotkey(keys['read_selected'], self._on_read_selected)
            logger.info(f"注册快捷键: {keys['read_selected']} → 朗读选中文本")

        # Ctrl+Alt+P: 暂停/继续
        if 'pause_resume' in keys:
            keyboard.add_hotkey(keys['pause_resume'], self._on_pause_resume)
            logger.info(f"注册快捷键: {keys['pause_resume']} → 暂停/继续")

        # Ctrl+Alt+X: 停止
        if 'stop' in keys:
            keyboard.add_hotkey(keys['stop'], self._on_stop)
            logger.info(f"注册快捷键: {keys['stop']} → 停止朗读")

        # Ctrl+Alt+S: 开关自动监听（阶段2）
        if 'toggle_auto' in keys:
            keyboard.add_hotkey(keys['toggle_auto'], self._on_toggle_auto)
            logger.info(f"注册快捷键: {keys['toggle_auto']} → 开关自动监听")

        # Ctrl+Alt+↑: 语速加快
        if 'speed_up' in keys:
            keyboard.add_hotkey(keys['speed_up'], self._on_speed_up)
            logger.info(f"注册快捷键: {keys['speed_up']} → 语速加快")

        # Ctrl+Alt+↓: 语速减慢
        if 'speed_down' in keys:
            keyboard.add_hotkey(keys['speed_down'], self._on_speed_down)
            logger.info(f"注册快捷键: {keys['speed_down']} → 语速减慢")

        logger.info("快捷键注册完成，等待操作...")
        return True

    def _get_selected_text(self) -> str:
        """
        获取当前选中的文本

        通过模拟 Ctrl+C 复制选中文本到剪贴板，然后读取。
        保存原始剪贴板内容并恢复。
        """
        try:
            import pyperclip
        except ImportError:
            logger.error("pyperclip 未安装")
            return ""

        # 保存原始剪贴板
        try:
            original_clipboard = pyperclip.paste()
        except:
            original_clipboard = ""

        try:
            import keyboard
            # 模拟 Ctrl+C 复制选中文本
            keyboard.send('ctrl+c', do_press=True, do_release=True)
            time.sleep(0.1)  # 等待剪贴板更新

            # 读取新剪贴板内容
            try:
                text = pyperclip.paste()
            except:
                text = ""

            # 恢复原始剪贴板
            try:
                pyperclip.copy(original_clipboard)
            except:
                pass

            return text.strip() if text else ""

        except Exception as e:
            logger.error(f"获取选中文本失败: {e}")
            # 恢复剪贴板
            try:
                pyperclip.copy(original_clipboard)
            except:
                pass
            return ""

    def _on_read_selected(self):
        """朗读选中文本"""
        text = self._get_selected_text()
        if text:
            logger.info(f"触发朗读: {text[:50]}{'...' if len(text)>50 else ''}")
            self.tts_queue.enqueue_text(text)
        else:
            logger.warning("未获取到选中的文本")

    def _on_pause_resume(self):
        """暂停/继续"""
        if self.tts_queue.is_paused():
            self.tts_queue.resume()
        else:
            self.tts_queue.pause()

    def _on_stop(self):
        """停止朗读"""
        self.tts_queue.stop_reading()

    def _on_toggle_auto(self):
        """开关自动监听（阶段2实现）"""
        self._auto_monitor = not self._auto_monitor
        if self._auto_monitor:
            self._start_clipboard_monitor()
            logger.info("自动监听已开启")
        else:
            self._auto_monitor = False
            logger.info("自动监听已关闭")

    def _on_speed_up(self):
        """语速加快"""
        self.tts_queue.set_speed(self.tts_queue.speed + 0.1)

    def _on_speed_down(self):
        """语速减慢"""
        self.tts_queue.set_speed(self.tts_queue.speed - 0.1)

    def _start_clipboard_monitor(self):
        """启动剪贴板监听（阶段2实现）"""
        if self._clipboard_monitor_thread and self._clipboard_monitor_thread.is_alive():
            return

        self._clipboard_monitor_thread = threading.Thread(
            target=self._clipboard_monitor_loop, daemon=True
        )
        self._clipboard_monitor_thread.start()

    def _clipboard_monitor_loop(self):
        """剪贴板监听循环（阶段2实现）"""
        import pyperclip
        last_clipboard = ""
        import time

        while self._auto_monitor:
            try:
                current = pyperclip.paste()
                if current and current != last_clipboard:
                    last_clipboard = current
                    if len(current.strip()) > 0:
                        logger.info(f"剪贴板捕获: {current[:50]}{'...' if len(current)>50 else ''}")
                        self.tts_queue.enqueue_text(current)
            except:
                pass
            time.sleep(0.5)

    def stop(self):
        """停止监听"""
        self._auto_monitor = False
        try:
            import keyboard
            keyboard.unhook_all()
        except:
            pass


# 需要 time 模块
import time
