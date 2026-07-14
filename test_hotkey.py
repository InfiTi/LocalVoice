"""快捷键诊断测试"""
import sys
import time

print("=== 快捷键诊断测试 ===\n")

# 1. 检查 keyboard 库
try:
    import keyboard
    print("[1] keyboard 库导入成功")
except ImportError:
    print("[1] keyboard 库导入失败！请运行: pip install keyboard")
    sys.exit(1)

# 2. 检查管理员权限
try:
    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"[2] 管理员权限: {'是' if is_admin else '否'}")
    if not is_admin:
        print("    ⚠️  没有管理员权限！keyboard 库需要管理员权限才能注册全局快捷键")
        print("    请右键 CMD/PowerShell -> 以管理员身份运行，再执行此脚本")
except Exception as e:
    print(f"[2] 权限检查失败: {e}")

# 3. 注册快捷键
def on_hotkey():
    print("\n    ★★★ 快捷键触发了！★★★\n")

try:
    keyboard.add_hotkey('ctrl+alt+r', on_hotkey)
    print("[3] 快捷键 ctrl+alt+r 注册成功")
except Exception as e:
    print(f"[3] 快捷键注册失败: {e}")
    sys.exit(1)

# 4. 等待测试
print("\n现在请按 Ctrl+Alt+R 测试快捷键是否生效")
print("等待 30 秒...\n")

start = time.time()
while time.time() - start < 30:
    time.sleep(0.1)

print("\n测试结束。如果你看到了 ★★★ 快捷键触发了 ★★★，说明正常工作")
print("如果没看到，说明权限不足或快捷键被其他软件占用")

keyboard.unhook_all()
