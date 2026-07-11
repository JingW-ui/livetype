"""LiveType - 把代码"打"进任意编辑器的库，用于录屏教学 / 现场演示。

快速上手:
    import livetype
    livetype.type_file("sol.py", language="python", mode="human")

    typer = livetype.LiveTyper(language="python", mode="human")
    typer.on_progress = lambda cur, total: print(cur, "/", total)
    typer.type_async(code)          # 后台输入
    typer.pause(); typer.resume(); typer.stop()
"""
from .config import Config
from .engine import LiveTyper
from .strategies import SUPPORTED_LANGUAGES

__version__ = "0.1.0"

__all__ = ["Config", "LiveTyper", "SUPPORTED_LANGUAGES",
           "type_text", "type_file", "type_clipboard", "__version__"]


def type_text(code: str, language: str = "python", mode: str = "human", **kwargs) -> float:
    """同步输入一段代码字符串，返回耗时 (秒)。

    kwargs 透传给 Config (delay / error_rate / random_seed 等)。
    """
    cfg = Config(language=language, typing_mode=mode, **kwargs)
    return LiveTyper(cfg).type(code)


def type_file(path: str, language: str = None, mode: str = "human", **kwargs) -> float:
    """读取文件并输入。language 为 None 时按扩展名推断。"""
    if language is None:
        language = _infer_language(path)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    return type_text(code, language=language, mode=mode, **kwargs)


def type_clipboard(language: str = "python", mode: str = "human", **kwargs) -> float:
    """输入当前剪切板内容。"""
    import pyperclip
    code = pyperclip.paste()
    return type_text(code, language=language, mode=mode, **kwargs)


_EXT_MAP = {
    ".py": "python", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".java": "java", ".go": "go",
}


def _infer_language(path: str) -> str:
    import os
    ext = os.path.splitext(path)[1].lower()
    return _EXT_MAP.get(ext, "python")
