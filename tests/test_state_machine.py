"""状态机单测 - 用 fake engine 录制按键序列，验证 IDE 自动补全处理。

不依赖 pyautogui / 显示器，纯逻辑验证。
"""
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from livetype.config import Config
from livetype.strategies.python import PythonStrategy


class FakeEngine:
    """记录所有按键动作的假引擎。"""

    def __init__(self, mode="human"):
        self.config = Config(language="python", typing_mode=mode)
        self.config.pre_delay_min = 0
        self.config.pre_delay_max = 0
        self.config.think_time_min = 0
        self.config.think_time_max = 0
        self.rnd = random.Random(0)
        self.actions = []   # [('char', c) | ('press', k) | ('delete',)]
        self.on_progress = None
        self.on_status = None

    def stop_requested(self):
        return False

    def wait_while_paused(self):
        pass

    def press(self, key):
        self.actions.append(("press", key))

    def typewrite(self, s, interval=0.0):
        for c in s:
            self.actions.append(("char", c))

    def type_char(self, char, interval=0.0):
        self.actions.append(("char", char))

    def delete_auto_close(self):
        self.actions.append(("delete",))

    def gauss_delay(self):
        return 0.0

    def maybe_type_error(self, char, delay):
        pass  # error_rate=0 by default

    def typed(self):
        """仅返回实际输入的字符 (忽略 press/delete)。"""
        return "".join(c for kind, c in self.actions if kind == "char")

    def presses(self):
        return [k for kind, k in self.actions if kind == "press"]


def run(code, mode="human"):
    e = FakeEngine(mode)
    PythonStrategy().type_code(code.splitlines(keepends=True), e)
    return e


# ── 基本括号: IDE 自动补全的闭括号应被 Right 跳过 ──
def test_paren_auto_close_skipped():
    e = run("f(x)\n")
    # '(' 输入后 IDE 补 ')', 'x' 在括号内, ')' 处按 Right 跳过补全 -> typed 中无 ')'
    assert e.typed() == "f(x \n"
    assert "right" in e.presses(), "闭括号应按 Right 跳过 IDE 补全"


# ── 注释内的括号不应触发自动补全逻辑 ──
def test_brackets_in_comment_are_literal():
    e = run("# use ( and )\n")
    # 注释里的 ( ) 应原样输入，不应 press right
    assert e.typed().startswith("# use ( and )")
    assert "right" not in e.presses(), "注释内的括号不应触发跳过"


# ── 三引号字符串: 内容字面输入，不触发引号状态机 ──
def test_triple_quoted_string():
    code = '"""hello (world)"""\n'
    e = run(code)
    # 三引号内的 ( 应原样输入，不 press right
    assert "right" not in e.presses(), "三引号串内的括号不应触发跳过"
    assert "hello (world)" in e.typed()


# ── 字符串内的开括号应 delete_auto_close ──
def test_bracket_inside_string_deletes_autoclose():
    e = run('s = "a(b)"\n')
    # 字符串内的 '(' 后应 delete_auto_close (删除 IDE 补的 ')')
    assert any(a[0] == "delete" for a in e.actions), \
        "字符串内开括号应 delete_auto_close"


# ── 空行只按 enter ──
def test_blank_line_just_enter():
    e = run("a\n\nb\n")
    # 第二行空行 -> press enter，不输入字符
    assert e.presses().count("enter") >= 1


# ── fast 模式不思考停顿 (无 sleep 影响)、字符仍正确 ──
def test_fast_mode_types_chars():
    e = run("f(x)\n", mode="fast")
    assert "right" in e.presses(), "fast 模式仍应处理 IDE 自动补全"
    assert e.typed() == "f(x \n"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("ALL_TESTS_OK")
