"""C 系策略单测 - 验证 () [] 与收尾引号的自动闭合跳过（与 Python 策略一致）。

不依赖 pyautogui / 显示器，纯逻辑验证。
"""
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from livetype.config import Config
from livetype.strategies.clike import CStrategy, GoStrategy


class FakeEngine:
    """记录所有按键动作的假引擎。"""

    def __init__(self, language="c", mode="fast"):
        self.config = Config(language=language, typing_mode=mode)
        self.config.pre_delay_min = 0
        self.config.pre_delay_max = 0
        self.config.think_time_min = 0
        self.config.think_time_max = 0
        self.rnd = random.Random(0)
        self.actions = []
        self.on_progress = None
        self.on_status = None
        self.on_started = None
        self.on_completed = None

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
        pass

    def typed(self):
        """仅返回实际输入的字符 (忽略 press/delete)。"""
        return "".join(c for kind, c in self.actions if kind == "char")

    def presses(self):
        return [k for kind, k in self.actions if kind == "press"]


def run(code, strategy, language="c", mode="fast"):
    e = FakeEngine(language, mode)
    strategy.type_code(code.splitlines(keepends=True), e)
    return e


def test_paren_bracket_auto_close_skipped():
    # '(' '[' 输入的闭括号应被 Right 跳过，而不是重复输入
    e = run("int f(int a[2]) { return a[0]; }\n", CStrategy(), "c")
    t = e.typed()
    assert "right" in e.presses(), "闭括号/闭中括号应按 Right 跳过"
    assert ")" not in t, "闭圆括号不应被重复输入"
    assert "]" not in t, "闭方括号不应被重复输入"
    assert "}" not in t, "闭花括号不应被重复输入"


def test_closing_quote_skipped():
    # 收尾引号应被 Right 跳过，避免与 IDE 自动闭合的引号重复
    e = run('char *s = "hi";\n', CStrategy(), "c")
    assert "right" in e.presses(), "收尾引号应按 Right 跳过"
    assert e.typed().count('"') == 1, "字符串引号应恰好输入一次（开引号）"


def test_go_raw_string_literal():
    # Go 原始串内的括号/引号应原样输入，不触发跳过
    e = run("s := `raw (str [ing] {brace})`\n", GoStrategy(), "go")
    t = e.typed()
    assert "raw (str [ing] {brace})" in t
    assert "right" not in e.presses(), "原始串内的括号不应触发 Right 跳过"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("ALL_TESTS_OK")
