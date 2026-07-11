# LiveType

> Live-type code into any editor for screencasts, demos, and teaching videos. Multi-language, IDE auto-close aware.

LiveType takes code you've prepared (a file, a string, or your clipboard) and types it into whatever editor currently has focus — at a human-like pace or as fast as possible — correctly handling IDE auto-completion of brackets, quotes, and string literals across Python / C / C++ / Java / Go.

Built for recording tutorial videos, live coding demos, and "code-along" screencasts without the typos and fatigue of typing live.

## Install

```bash
# From GitHub
pip install git+https://github.com/JingW-ui/livetype.git

# Or from Gitee (China mirror)
pip install git+https://gitee.com/wj4/livetype.git
```

Pin a specific version with a tag:

```bash
pip install git+https://github.com/JingW-ui/livetype.git@v0.1.0
```

For local development:

```bash
git clone https://github.com/JingW-ui/livetype.git
cd livetype
pip install -e .
```

## Quick start

### As a library

```python
import livetype

# One-shot
livetype.type_file("solution.py", language="python", mode="human")
livetype.type_text("print('hi')", language="python", mode="fast")

# Controlled (callbacks + async)
typer = livetype.LiveTyper(language="python", mode="human", delay=0.08)
typer.on_progress = lambda cur, total: print(cur, "/", total)
typer.type_async(code)      # runs in a background thread
typer.pause()
typer.resume()
typer.stop()
```

### As a CLI

```bash
livetype sol.py                       # infer language from extension, human mode
livetype sol.py -l python -m fast
livetype -m fast < sol.py             # from stdin
livetype --clipboard -m human         # from clipboard
livetype sol.py --delay 0.05 --error-rate 0.03 --seed 42
```

## Modes

| Mode | Description |
|------|-------------|
| `human` (default) | Realistic typing — Gaussian inter-key delay, optional line-end "think" pauses, optional typo simulation. For tutorial videos. |
| `fast` | No delays, no typos — types as fast as the OS accepts. For quick demos. |

## Languages

`python` · `c` · `cpp` · `java` · `go`

Each language has a dedicated state machine that tracks brackets `()[]{}`, quotes `""''`, escapes, and (Python) triple-quoted strings and `#` comments, so that an IDE's auto-closed brackets are stepped over rather than doubled.

## Configuration

```python
livetype.LiveTyper(livetype.Config(
    language="python",
    typing_mode="human",
    delay=0.08,               # mean inter-key seconds (human)
    delay_variance=0.33,
    think_time_min=0.3,       # line-end pause (human)
    think_time_max=0.8,
    error_rate=0.0,           # typo probability (opt-in)
    pre_delay_min=2.0,        # window-switch wait before typing
    pre_delay_max=3.0,
    random_seed=42,           # set for reproducible pacing
    copy_to_clipboard=False,
))
```

## How it works

LiveType uses `pyautogui` to send keypresses to the focused window. For each character it consults a language-specific state machine: opening brackets are pushed onto a stack (the IDE auto-closes them), closing brackets pop the stack and press **Right** to skip the auto-inserted match, and brackets inside string/char literals delete the auto-close. Non-ASCII characters (e.g. Chinese in comments) fall back to clipboard paste, since `pyautogui.typewrite` is ASCII-only.

## Limitations

- Types into the **currently focused** window — switch to your editor during the pre-delay.
- `/* */` block comments in C-like languages are not yet specially tracked.
- Clipboard paste for non-ASCII may overwrite your clipboard contents.

## License

MIT
