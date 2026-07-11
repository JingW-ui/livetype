"""语言策略注册。"""
from .base import LanguageStrategy, strip_markdown_fence
from .python import PythonStrategy
from .clike import CStrategy, CppStrategy, JavaStrategy, GoStrategy

STRATEGIES = {
    "python": PythonStrategy(),
    "c": CStrategy(),
    "cpp": CppStrategy(),
    "java": JavaStrategy(),
    "go": GoStrategy(),
}

SUPPORTED_LANGUAGES = list(STRATEGIES.keys())
