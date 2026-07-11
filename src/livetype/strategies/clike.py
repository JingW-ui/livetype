"""C 系策略 (C / C++ / Java / Go) - 括号状态机 + IDE 自动补全处理。

行级逻辑:
- 过滤空行
- 首行: 直接输入 lstrip 内容
- content == '}': press('down') (IDE 已自动补全 '}'，下移光标)
- content 以 '}' 开头: press('down') 后输入剩余
- 其他: press('return')，缩进回退时 press('home') + 输入缩进空格，再输入 lstrip 内容

typing_mode:
- "human": 类人 (错字模拟 + 正态延迟 + 行末思考)
- "fast": 快速 (interval=config.fast_interval，无错字)
"""
import time

from .base import LanguageStrategy


class _CLikeStrategyBase(LanguageStrategy):
    _human = False

    def type_code(self, lines, engine):
        self._human = engine.config.typing_mode != "fast"
        lines = [l.rstrip('\r\n') for l in lines if l.strip() != '']
        prev_indent = 0
        for i, line in enumerate(lines):
            if engine.stop_requested():
                if engine.on_status:
                    engine.on_status("输入已中断")
                return
            engine.wait_while_paused()
            if engine.stop_requested():
                return
            if engine.on_progress:
                engine.on_progress(i + 1, len(lines))
            current_indent = len(line) - len(line.lstrip())
            content = line.lstrip()
            if i == 0:
                self._type_content_with_states(content, engine)
            elif content == '}':
                engine.press('down')
                if self._human:
                    time.sleep(engine.rnd.uniform(engine.config.think_time_min, engine.config.think_time_max))
            elif content.startswith('}') and content != '}':
                engine.press('down')
                if self._human:
                    time.sleep(engine.rnd.uniform(engine.config.think_time_min, engine.config.think_time_max))
                self._type_content_with_states(content[1:], engine)
            else:
                engine.press('return')
                if self._human:
                    time.sleep(engine.rnd.uniform(engine.config.think_time_min, engine.config.think_time_max))
                if current_indent < prev_indent:
                    engine.press('home')
                    engine.typewrite(' ' * current_indent, interval=0.01)
                self._type_content_with_states(content, engine)
            prev_indent = current_indent
            if (i + 1) % 10 == 0 or i == len(lines) - 1:
                if engine.on_status:
                    engine.on_status(f"已输入 {i + 1}/{len(lines)} 行")

    def _type_char(self, char, engine):
        """单字符输入: 模拟版 (错字+正态延迟) / 快速版 (fast_interval)。Unicode 安全。"""
        if self._human:
            delay = engine.gauss_delay()
            engine.maybe_type_error(char, delay)
            engine.type_char(char, interval=delay)
        else:
            engine.type_char(char, interval=engine.config.fast_interval)

    def _type_content_with_states(self, text, engine):
        state = 'NORMAL'
        i = 0
        n = len(text)
        while i < n:
            if engine.stop_requested():
                return
            char = text[i]
            if state == 'NORMAL':
                if char == "'":
                    self._type_char(char, engine)
                    state = 'IN_CHAR'
                    i += 1
                    continue
                elif char == '"':
                    self._type_char(char, engine)
                    state = 'IN_STRING'
                    i += 1
                    continue
                elif char == '{':
                    self._type_char('{', engine)
                    brace_depth = 1
                    j = i + 1
                    while j < n and brace_depth > 0:
                        if text[j] == '{':
                            brace_depth += 1
                        elif text[j] == '}':
                            brace_depth -= 1
                        j += 1
                    if brace_depth == 0:
                        middle = text[i + 1:j - 1]
                        if middle:
                            self._type_content_with_states(middle, engine)
                        engine.press('right')
                        i = j
                        continue
                elif char == '}':
                    pass   # IDE 已自动补全，跳过
                else:
                    self._type_char(char, engine)
            elif state == 'IN_CHAR':
                self._type_char(char, engine)
                if char == '\\':
                    state = 'IN_CHAR_ESCAPE'
                elif char == "'":
                    state = 'NORMAL'
                elif char in '({[':
                    engine.delete_auto_close()
            elif state == 'IN_CHAR_ESCAPE':
                self._type_char(char, engine)
                state = 'IN_CHAR'
            elif state == 'IN_STRING':
                self._type_char(char, engine)
                if char == '\\':
                    state = 'IN_STRING_ESCAPE'
                elif char == '"':
                    state = 'NORMAL'
                elif char in '({[':
                    engine.delete_auto_close()
            elif state == 'IN_STRING_ESCAPE':
                self._type_char(char, engine)
                state = 'IN_STRING'
            i += 1


class CStrategy(_CLikeStrategyBase):
    """C 语言。"""


class CppStrategy(_CLikeStrategyBase):
    """C++。"""


class JavaStrategy(_CLikeStrategyBase):
    """Java。"""


class GoStrategy(_CLikeStrategyBase):
    """Go - 在 C 基础上增加 IN_RAW_STRING (反引号原始字符串)。"""

    def _type_content_with_states(self, text, engine):
        state = 'NORMAL'
        i = 0
        n = len(text)
        while i < n:
            if engine.stop_requested():
                return
            char = text[i]
            if state == 'NORMAL':
                if char == "'":
                    self._type_char(char, engine)
                    state = 'IN_CHAR'
                    i += 1
                    continue
                elif char == '"':
                    self._type_char(char, engine)
                    state = 'IN_STRING'
                    i += 1
                    continue
                elif char == '`':
                    self._type_char(char, engine)
                    state = 'IN_RAW_STRING'
                    i += 1
                    continue
                elif char == '{':
                    self._type_char('{', engine)
                    brace_depth = 1
                    j = i + 1
                    while j < n and brace_depth > 0:
                        if text[j] == '{':
                            brace_depth += 1
                        elif text[j] == '}':
                            brace_depth -= 1
                        j += 1
                    if brace_depth == 0:
                        middle = text[i + 1:j - 1]
                        if middle:
                            self._type_content_with_states(middle, engine)
                        engine.press('right')
                        i = j
                        continue
                elif char == '}':
                    pass
                else:
                    self._type_char(char, engine)
            elif state == 'IN_CHAR':
                self._type_char(char, engine)
                if char == '\\':
                    state = 'IN_CHAR_ESCAPE'
                elif char == "'":
                    state = 'NORMAL'
                elif char in '({[':
                    engine.delete_auto_close()
            elif state == 'IN_CHAR_ESCAPE':
                self._type_char(char, engine)
                state = 'IN_CHAR'
            elif state == 'IN_STRING':
                self._type_char(char, engine)
                if char == '\\':
                    state = 'IN_STRING_ESCAPE'
                elif char == '"':
                    state = 'NORMAL'
                elif char in '({[':
                    engine.delete_auto_close()
            elif state == 'IN_STRING_ESCAPE':
                self._type_char(char, engine)
                state = 'IN_STRING'
            elif state == 'IN_RAW_STRING':
                self._type_char(char, engine)
                if char == '`':
                    state = 'NORMAL'
            i += 1

