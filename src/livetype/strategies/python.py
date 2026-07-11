"""Python 策略 - 括号/引号状态机 + IDE 自动补全处理。

相对原版的修复:
- 三引号字符串单独状态，不再被当普通引号序列错乱
- 行内注释 (#) 进入 IN_COMMENT，注释内的括号/引号不再触发自动补全
- 非 ASCII 字符走 engine.type_char (剪切板兜底)
- 节奏随机走 engine.rnd (可设种子复现)
"""
import time

from .base import LanguageStrategy


class PythonStrategy(LanguageStrategy):
    OPEN_CLOSE = {'(': ')', '[': ']', '{': '}'}
    CLOSE_CHARS = {')', ']', '}'}

    def __init__(self):
        self._human = False
        self._reset_state()

    def _reset_state(self):
        self.state = "NORMAL"
        self.brace_stack = []

    # ── 主循环 ────────────────────────────────
    def type_code(self, lines, engine):
        self._human = engine.config.typing_mode != "fast"
        self._reset_state()
        last_leading = None
        need_home = False
        lines = [l for l in lines if not l.strip().startswith("```")]
        for idx, line in enumerate(lines):
            if engine.stop_requested():
                if engine.on_status:
                    engine.on_status("输入已中断")
                return
            engine.wait_while_paused()
            if engine.stop_requested():
                return
            if engine.on_progress:
                engine.on_progress(idx + 1, len(lines))
            if not line.strip():
                engine.press('enter')
                continue
            expanded = line.expandtabs(4)
            leading = len(expanded) - len(expanded.lstrip(" "))
            if last_leading is not None and leading < last_leading:
                need_home = True
            self._type_line(line, need_home, engine)
            need_home = False
            if self._human:
                time.sleep(engine.rnd.uniform(engine.config.think_time_min, engine.config.think_time_max))
            content = line.strip()
            if (self._human and len(content) > engine.config.long_line_threshold
                    and engine.rnd.random() < engine.config.line_break_rate):
                engine.press('enter')
                time.sleep(engine.rnd.uniform(engine.config.break_pause_min, engine.config.break_pause_max))
            if (idx + 1) % 10 == 0 or idx == len(lines) - 1:
                if engine.on_status:
                    engine.on_status(f"已输入 {idx + 1}/{len(lines)} 行")
            last_leading = leading

    def _type_line(self, line, need_home, engine):
        if need_home:
            engine.press('home')
            self._type_text(line, engine, handle_newline=True, line=line)
            if line.strip():
                engine.typewrite('\n', interval=0.01)
        else:
            content = line.strip()
            self._type_text(content, engine, handle_newline=False)
            if content:
                engine.typewrite(' ', interval=0.01)
            engine.typewrite('\n', interval=0.01)
        # 注释止于行尾
        if self.state == "IN_COMMENT":
            self.state = "NORMAL"

    def _type_text(self, text, engine, handle_newline, line=None):
        i = 0
        n = len(text)
        while i < n:
            if engine.stop_requested():
                return
            ch = text[i]
            if handle_newline and ch == '\n' and line.strip():
                engine.typewrite(' ', interval=0.01)
                i += 1
                continue
            st = self.state
            if st == "NORMAL":
                if ch == '"' and text[i:i + 3] == '"""':
                    self._type_raw('"""', engine)
                    self.state = "IN_TRIPLE_STRING"
                    i += 3
                    continue
                if ch == "'" and text[i:i + 3] == "'''":
                    self._type_raw("'''", engine)
                    self.state = "IN_TRIPLE_CHAR"
                    i += 3
                    continue
                if ch == '#':
                    self._type_raw('#', engine)
                    self.state = "IN_COMMENT"
                    i += 1
                    continue
            elif st == "IN_TRIPLE_STRING":
                if ch == '"' and text[i:i + 3] == '"""':
                    self._type_raw('"""', engine)
                    self.state = "NORMAL"
                    i += 3
                    continue
                self._type_raw(ch, engine)
                i += 1
                continue
            elif st == "IN_TRIPLE_CHAR":
                if ch == "'" and text[i:i + 3] == "'''":
                    self._type_raw("'''", engine)
                    self.state = "NORMAL"
                    i += 3
                    continue
                self._type_raw(ch, engine)
                i += 1
                continue
            elif st == "IN_COMMENT":
                self._type_raw(ch, engine)
                i += 1
                continue
            # NORMAL(普通引号/括号) / IN_STRING / IN_CHAR / 转义 -> 状态机
            delay = engine.gauss_delay() if self._human else 0.0
            self._handle(ch, engine, delay)
            i += 1

    def _type(self, char, engine, delay):
        if self._human:
            engine.maybe_type_error(char, delay)
            engine.type_char(char, interval=delay)
        else:
            engine.type_char(char, interval=engine.config.fast_interval)

    def _type_raw(self, text, engine):
        """字面量输入 (三引号/注释内): 不做错字模拟，Unicode 安全。"""
        delay = engine.gauss_delay() if self._human else 0.0
        for ch in text:
            engine.type_char(ch, interval=delay)

    def _handle(self, char, engine, delay):
        st = self.state
        if st == "NORMAL":
            if char == '"':
                self._type(char, engine, delay)
                self.state = "IN_STRING"
            elif char == "'":
                self._type(char, engine, delay)
                self.state = "IN_CHAR"
            elif char in self.OPEN_CLOSE:
                self._type(char, engine, delay)
                self.brace_stack.append(self.OPEN_CLOSE[char])
            elif char in self.CLOSE_CHARS:
                if self.brace_stack and self.brace_stack[-1] == char:
                    self.brace_stack.pop()
                    engine.press("right")
                else:
                    self._type(char, engine, delay)
            else:
                self._type(char, engine, delay)
        elif st == "IN_STRING":
            if char == '\\':
                self._type(char, engine, delay)
                self.state = "IN_STRING_ESCAPE"
            elif char == '"':
                engine.press("right")
                self.state = "NORMAL"
            elif char in self.OPEN_CLOSE:
                self._type(char, engine, delay)
                engine.delete_auto_close()
            else:
                self._type(char, engine, delay)
        elif st == "IN_STRING_ESCAPE":
            self._type(char, engine, delay)
            self.state = "IN_STRING"
        elif st == "IN_CHAR":
            if char == '\\':
                self._type(char, engine, delay)
                self.state = "IN_CHAR_ESCAPE"
            elif char == "'":
                engine.press("right")
                self.state = "NORMAL"
            elif char in self.OPEN_CLOSE:
                self._type(char, engine, delay)
                engine.delete_auto_close()
            else:
                self._type(char, engine, delay)
        elif st == "IN_CHAR_ESCAPE":
            self._type(char, engine, delay)
            self.state = "IN_CHAR"



