import re
from datetime import datetime

import pandas as pd
from rich import box
from rich.align import Align
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, TextColumn, SpinnerColumn, TaskID
from rich.table import Table
from rich.text import Text


class GlobalVars:
    program_start_time: datetime = datetime.now()


def make_layout():
    layout = Layout()
    layout.split_row(Layout(name="log", ratio=1), Layout(name="detail", ratio=3))
    layout["detail"].split_column(Layout(name="info", ratio=1), Layout(name="user", ratio=3))
    return layout


class ProgramInfo:
    def __rich__(self) -> Panel:
        program_time = pd.to_timedelta(datetime.now() - GlobalVars.program_start_time).ceil('T')
        match_time1 = re.search(r"(\d+)\sdays\s(\d+):(\d+)", str(program_time))
        time1_str = f"程序运行时间: {int(match_time1.group(1))}天{int(match_time1.group(2))}小时{int(match_time1.group(3))}分"
        info1 = Align.center(Text(time1_str, style="bold magenta", justify="center"))
        # TODO(kevin): 每次更新时候增加版本号
        info2 = Text(
            """Version:0.11.0  项目主页:https://github.com/princelai/NiMingAssistant""",
            justify="center",
        )

        info_panel = Panel(
            Group(info1, info2),
            box=box.ROUNDED,
            padding=(1, 1),
            title="[b]匿名修仙[/b]挂机辅助",
            border_style="bright_blue",
        )
        return info_panel


class UserMainInfo:
    def __init__(self, values):
        super().__init__()
        self.values = values

    def __rich__(self) -> Panel:
        info_panel = Panel(
            Group(self.make_user_status(), self.make_fight_info(), self.make_estimate_info(), self.make_reward_info()),
            box=box.ROUNDED,
            padding=(1, 1),
            title=self.values.get("user_info", {}).get("名称", ""),
            border_style="bright_blue",
        )
        return info_panel

    def make_user_status(self):
        message = Table.grid(expand=True)
        for _ in range(6):
            message.add_column(justify="right")
            message.add_column(justify="left")
        message.add_row("修为:", str(self.values.get("user_info", {}).get("修为", "")),
                        "气血储备:", str(self.values.get("user_info", {}).get("气血储备", "")),
                        "魔法储备:", str(self.values.get("user_info", {}).get("魔法储备", "")),
                        "灵力:", str(self.values.get("user_info", {}).get("灵力", "")),
                        "速力:", str(self.values.get("user_info", {}).get("速力", "")),
                        "心魔:", str(self.values.get("user_info", {}).get("心魔", "")))
        return Panel(message, title="角色信息")

    def make_fight_info(self):
        message = Table.grid(expand=True)
        for _ in range(4):
            message.add_column(justify="right")
            message.add_column(justify="left")
        message.add_row("胜利:", str(self.values.get("fight_info", {}).get("胜", "")),
                        "败北:", str(self.values.get("fight_info", {}).get("败", "")),
                        "修为:", str(self.values.get("fight_info", {}).get("累计修为", "")),
                        "队伍人数:", str(self.values.get("team_info", {}).get("num", "")))
        return Panel(message, title="战斗信息")

    def make_estimate_info(self):
        message = Table.grid(expand=True)
        for _ in range(5):
            message.add_column(justify="right")
            message.add_column(justify="left")
        message.add_row("经验获取:", self.values.get("estimate_info", {}).get("exp", ""),
                        "气血损伤:", self.values.get("estimate_info", {}).get("hp", ""),
                        "魔法消耗:", self.values.get("estimate_info", {}).get("mp", ""),
                        "灵力损益:", self.values.get("estimate_info", {}).get("ll", ""),
                        "心魔增长:", self.values.get("estimate_info", {}).get("hm", ""))
        return Panel(message, title="预估信息")

    def make_reward_info(self):
        message = Text.from_markup('  '.join([f"{k}:{v}" for k, v in self.values.get("reward_info", {}).items()]), justify="left")
        return Panel(message, title="奖励信息")


class DynLog:
    log_progress = Progress(SpinnerColumn(), TextColumn("[{task.fields[dt]}] {task.description}"))

    @classmethod
    def record_log(cls, s, error=False):
        task_id = cls.log_progress.add_task("")
        if error:
            cls.log_progress.update(task_id, description=f"[red]{s}", dt=datetime.now().strftime("%H:%M:%S"))
        else:
            cls.log_progress.update(task_id, description=f"[green]{s}", dt=datetime.now().strftime("%H:%M:%S"))
        if task_id >= 1:
            cls.log_progress.update(TaskID(task_id - 1), completed=100)
        if task_id >= 22:
            cls.log_progress.update(TaskID(task_id - 22), visible=False)


class DisplayLayout:
    my_layout = make_layout()
    my_layout["info"].update(ProgramInfo())
    my_layout["log"].update(Panel(DynLog.log_progress, title="运行日志"))

    @classmethod
    def update_user_info(cls, value):
        cls.my_layout["user"].update(UserMainInfo(values=value))
