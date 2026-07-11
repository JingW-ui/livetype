"""LiveType 引擎 - 提供输入原语 + 预延迟/回调外壳，逐行循环委托给语言策略。

设计要点:
- 纯 Python，不依赖 Qt；异步用 stdlib threading。
- 局部管理 pyautogui.PAUSE (打字期间设置，结束恢复)，不污染调用方进程。
- random 走自带 Random 实例 (可设种子复现节奏)。
- 非 ASCII 字符走剪切板粘贴 (pyautogui.typewrite 打不出中文等)。
- pause/stop 用锁保护的标志。
"""
import random
import threading
import time

import pyautogui
import pyperclip

from .config import Config


class LiveTyper:
    """代码自动输入引擎。既是公共 API，也向语言策略提供输入原语。"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        from .strategies import STRATEGIES
        self._strategy = STRATEGIES.get(self.config.language, STRATEGIES["python"])
        self._stop_flag = False
        self._paused = False
        self._lock = threading.Lock()
        self.rnd = random.Random(self.config.random_seed)

        # 外部回调
        self.on_progress = None        # (current, total)
        self.on_status = None          # (text)
        self.on_started = None         # ()
        self.on_completed = None       # (elapsed)

    # ── 语言切换 ──────────────────────────────
    def set_language(self, language: str) -> None:
        self.config.language = language
        from .strategies import STRATEGIES
        self._strategy = STRATEGIES.get(language, STRATEGIES["python"])

    # ── 控制 ──────────────────────────────────
    def stop(self) -> None:
        with self._lock:
            self._stop_flag = True

    def stop_requested(self) -> bool:
        return self._stop_flag

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            if self.on_status:
                self.on_status("已暂停")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            if self.on_status:
                self.on_status("恢复输入")

    def wait_while_paused(self) -> None:
        while self._paused and not self._stop_flag:
            time.sleep(0.05)

    # ── 输入原语 (策略调用) ────────────────────
    def press(self, key: str) -> None:
        pyautogui.press(key)

    def typewrite(self, s: str, interval: float = 0.0) -> None:
        """输入 ASCII 字符串 (含 \\n -> enter)。非 ASCII 请用 type_char。"""
        pyautogui.typewrite(s, interval=interval)

    def type_char(self, char: str, interval: float = 0.0) -> None:
        """单字符输入，自动路由: ASCII 走 pyautogui，非 ASCII 走剪切板粘贴。"""
        if ord(char) < 128:
            pyautogui.typewrite(char, interval=interval)
        else:
            pyperclip.copy(char)
            pyautogui.hotkey("ctrl", "v")

    def type_text_literal(self, text: str) -> None:
        """字面量输入一段文本 (不做状态机处理)，Unicode 安全。用于批量粘贴非 ASCII 段。"""
        ascii_part = []
        for ch in text:
            if ord(ch) < 128:
                ascii_part.append(ch)
            else:
                if ascii_part:
                    pyautogui.typewrite("".join(ascii_part), interval=0)
                    ascii_part.clear()
                pyperclip.copy(ch)
                pyautogui.hotkey("ctrl", "v")
        if ascii_part:
            pyautogui.typewrite("".join(ascii_part), interval=0)

    def delete_auto_close(self) -> None:
        """删除 IDE 自动补全的多余右括号: Right + Backspace。"""
        pyautogui.press("right")
        pyautogui.press("backspace")

    def gauss_delay(self) -> float:
        """类人字符间隔: 正态分布，下限 0.02s。"""
        return max(0.02, self.rnd.gauss(self.config.delay, self.config.delay * self.config.delay_variance))

    def maybe_type_error(self, char: str, delay: float) -> None:
        """按概率输入相邻错误键 + 退格 (不输入正确键)。仅 human + error_rate>0 时有效。"""
        if self.config.error_rate <= 0:
            return
        if self.rnd.random() < self.config.error_rate:
            nearby = _nearby_keys(char)
            if nearby:
                n = self.rnd.randint(1, min(3, len(nearby)))
                for wrong in self.rnd.sample(nearby, n):
                    pyautogui.typewrite(wrong, interval=delay * 0.7)
                    time.sleep(self.rnd.uniform(self.config.error_pause_min, self.config.error_pause_max))
                    pyautogui.press("backspace")
                    time.sleep(self.rnd.uniform(0.05, self.config.error_pause_max * 0.5))

    # ── 主入口 ────────────────────────────────
    def type(self, code: str) -> float:
        """同步输入一段代码，返回耗时 (秒)。"""
        lines = code.splitlines(keepends=True)
        return self._run(lines)

    def type_lines(self, lines: list) -> float:
        """按行列表输入 (已过滤 Markdown 标记等)。"""
        return self._run(lines)

    def type_async(self, code: str) -> threading.Thread:
        """异步输入，返回后台线程。用 stop()/pause()/resume() 控制。"""
        lines = code.splitlines(keepends=True)
        t = threading.Thread(target=self._run, args=(lines,), daemon=True)
        t.start()
        return t

    def _run(self, lines) -> float:
        if self.on_started:
            self.on_started()
        if self.on_status:
            self.on_status("请在数秒内切换到目标编辑器...")
        # 局部 pyautogui.PAUSE (不污染调用方)
        old_pause = pyautogui.PAUSE
        pyautogui.PAUSE = self.config.pyautogui_pause
        try:
            time.sleep(self.rnd.uniform(self.config.pre_delay_min, self.config.pre_delay_max))
            if self.on_status:
                self.on_status("正在输入代码...")
            start = time.time()
            self._strategy.type_code(lines, self)
            elapsed = time.time() - start
            if self.on_status:
                self.on_status("写入完成")
            if self.config.copy_to_clipboard:
                try:
                    pyperclip.copy("".join(lines))
                except Exception:
                    pass
            if self.on_completed:
                self.on_completed(elapsed)
            return elapsed
        finally:
            pyautogui.PAUSE = old_pause


# ── 键盘相邻键 (出错模拟) ───────────────────
_KEYBOARD_LAYOUT = {
    'q': ['w', 'a', 's'], 'w': ['q', 'e', 'a', 's', 'd'], 'e': ['w', 'r', 's', 'd', 'f'],
    'r': ['e', 't', 'd', 'f', 'g'], 't': ['r', 'y', 'f', 'g', 'h'], 'y': ['t', 'u', 'g', 'h', 'j'],
    'u': ['y', 'i', 'h', 'j', 'k'], 'i': ['y', 'o', 'j', 'k', 'l'], 'o': ['i', 'p', 'k', 'l'],
    'p': ['o', 'l'], 'a': ['q', 'w', 's', 'z', 'x'], 's': ['q', 'w', 'e', 'a', 'd', 'z', 'x', 'c'],
    'd': ['w', 'e', 'r', 's', 'f', 'x', 'c', 'v'], 'f': ['e', 'r', 't', 'd', 'g', 'c', 'v', 'b'],
    'g': ['r', 't', 'y', 'f', 'h', 'v', 'b', 'n'], 'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n', 'm'],
    'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'], 'k': ['u', 'i', 'o', 'j', 'l', 'm'],
    'l': ['i', 'o', 'p', 'k'], 'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'],
    'c': ['x', 'd', 'f', 'v'], 'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'],
    'n': ['b', 'h', 'j', 'm'], 'm': ['n', 'j', 'k'],
}


def _nearby_keys(char: str):
    lower = char.lower()
    nearby = _KEYBOARD_LAYOUT.get(lower)
    if not nearby:
        return []
    return [c.upper() if char.isupper() else c for c in nearby]
