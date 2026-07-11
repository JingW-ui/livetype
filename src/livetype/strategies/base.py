"""语言策略基类 - 各语言实现完整逐行输入循环。"""
from abc import ABC, abstractmethod


class LanguageStrategy(ABC):
    """语言策略基类。"""

    @abstractmethod
    def type_code(self, lines, engine) -> None:
        """输入全部代码行 (含尾部换行)。"""
        ...


def strip_markdown_fence(lines):
    """过滤 Markdown 代码块围栏 (``` 开头的行)。"""
    return [l for l in lines if not l.strip().startswith("```")]
