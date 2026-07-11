"""LiveType 命令行入口。

用法:
    livetype sol.py                       # 按扩展名推断语言，human 模式
    livetype sol.py -l python -m fast
    livetype -m fast < sol.py             # stdin
    livetype --clipboard -m human         # 剪切板内容
    livetype sol.py --delay 0.05 --error-rate 0.03 --seed 42
"""
import argparse
import sys

from . import Config, LiveTyper


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="livetype",
        description="把代码自动打进当前焦点编辑器，用于录屏教学 / 现场演示。",
    )
    p.add_argument("file", nargs="?", help="代码文件路径 (省略则读 stdin 或 --clipboard)")
    p.add_argument("-l", "--language", default=None,
                   help="语言: python/c/cpp/java/go (省略则按扩展名推断)")
    p.add_argument("-m", "--mode", choices=["human", "fast"], default="human",
                   help="输入模式 (默认 human)")
    p.add_argument("--clipboard", action="store_true", help="输入剪切板内容")
    p.add_argument("--delay", type=float, default=None, help="字符间隔均值 (s)")
    p.add_argument("--error-rate", type=float, default=None, help="错字概率 (0~1)")
    p.add_argument("--think-min", type=float, default=None, help="行间思考停顿下限 (s)")
    p.add_argument("--think-max", type=float, default=None, help="行间思考停顿上限 (s)")
    p.add_argument("--pre-delay", type=float, default=None, help="开始前等待 (s，切窗口)")
    p.add_argument("--seed", type=int, default=None, help="随机种子 (节奏可复现)")
    p.add_argument("--copy", action="store_true", help="完成后把代码复制到剪切板")
    return p


def _load_code(args) -> str:
    if args.clipboard:
        import pyperclip
        return pyperclip.paste()
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("错误: 未提供代码。指定文件、通过管道传入或加 --clipboard。")


def _infer_language(args) -> str:
    if args.language:
        return args.language
    if args.file:
        from . import _infer_language as infer
        return infer(args.file)
    return "python"


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    code = _load_code(args)
    if not code.strip():
        print("内容为空，已退出。")
        return 0

    language = _infer_language(args)
    overrides = {}
    if args.delay is not None: overrides["delay"] = args.delay
    if args.error_rate is not None: overrides["error_rate"] = args.error_rate
    if args.think_min is not None: overrides["think_time_min"] = args.think_min
    if args.think_max is not None: overrides["think_time_max"] = args.think_max
    if args.pre_delay is not None:
        overrides["pre_delay_min"] = args.pre_delay
        overrides["pre_delay_max"] = args.pre_delay
    if args.seed is not None: overrides["random_seed"] = args.seed
    if args.copy: overrides["copy_to_clipboard"] = True

    cfg = Config(language=language, typing_mode=args.mode, **overrides)
    typer = LiveTyper(cfg)
    typer.on_progress = lambda cur, total: print(f"\r已输入 {cur}/{total} 行", end="", flush=True)
    typer.on_status = lambda t: print(f"\n{t}", flush=True)
    elapsed = typer.type(code)
    print(f"\n完成，耗时 {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
