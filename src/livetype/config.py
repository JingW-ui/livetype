"""LiveType 配置 - 类人/快速打字的行为参数。

默认值面向"内容创作"场景 (教学视频 / 现场演示)，而非隐蔽模拟:
- 出错模拟默认关闭 (error_rate=0)，需要"真实打字感"时手动开启
- 行间思考停顿较短 (0.3~0.8s)，避免视频里大段空白
- 开始前预延迟 2~3s，留出切到目标编辑器的时间
- 可设 random_seed 让节奏可复现 (重录时打字一致)
"""
from dataclasses import dataclass, field, fields
from typing import Optional


@dataclass
class Config:
    """打字行为配置。human 模式使用全部参数；fast 模式忽略延迟/思考/出错。"""

    language: str = "python"
    typing_mode: str = "human"          # "human" (类人，用于视频) / "fast" (快速测试)

    delay: float = 0.08                 # 字符间隔均值 (s) - human 模式
    delay_variance: float = 0.33        # 标准差系数 (sd = delay * variance)

    think_time_min: float = 0.3         # 行末思考停顿 (human)
    think_time_max: float = 0.8

    error_rate: float = 0.0             # 错字概率 (默认关，opt-in)
    error_pause_min: float = 0.15
    error_pause_max: float = 0.40

    long_line_threshold: int = 18
    break_pause_min: float = 0.4        # 长行换行停顿 (human)
    break_pause_max: float = 1.0
    line_break_rate: float = 0.0        # 长行换行概率 (0=从不)

    pre_delay_min: float = 2.0          # 开始前等待 (切窗口)
    pre_delay_max: float = 3.0

    fast_interval: float = 0.0          # fast 模式字符间隔 (0 = 尽快，受 pyautogui.PAUSE 限制)

    random_seed: Optional[int] = None   # 设种子则节奏可复现
    copy_to_clipboard: bool = False     # 打字完成后把代码复制到剪切板
    pyautogui_pause: float = 0.0        # 打字期间的 pyautogui.PAUSE (0 = 不限速，慎用)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in names})

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}
