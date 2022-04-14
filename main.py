from pathlib import Path
from typing import Callable

import fire
import yaml
from playwright.sync_api import Playwright, sync_playwright, Page
from rich.live import Live

from display import DisplayLayout, DynLog
from fight import guaji
from info import UserVars
from login import valid_config
from mission import YaoLing, XiangYao, XunBao


def cmd_args(conf="config.yml"):
    f = Path(conf)
    if f.exists():
        return conf
    else:
        exit(1)


def dispatcher(browser, user_config):
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    context.clear_cookies()
    page = context.new_page()
    with page.expect_navigation(url="https://game.nimingxx.com/login", timeout=8000):
        page.goto("https://game.nimingxx.com/login", timeout=8000)
    page.wait_for_selector("input[placeholder=\"请输入密码\"]", timeout=10000)

    mission_id_map: dict[int, Callable[[Page, dict], None]] = {1: YaoLing.run, 2: XiangYao.run, 3: XunBao}
    if user_config['mission']['id']:
        mission_id_map.get(user_config['mission']['id'])(page, user_config)
    else:
        guaji(page, user_config, UserVars())

    DynLog.record_log("程序完成，10秒后自动退出")
    page.wait_for_timeout(timeout=10000)
    page.close()
    context.close()


def run(playwright: Playwright) -> None:
    with open(args_conf, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)
    user_config = valid_config(conf)

    for f in Path('.').glob("*.joblib"):
        f.unlink()

    # TODO(kevin):无头设置，记得每次检查一下是否为True
    browser = playwright.chromium.launch(headless=True)

    with Live(DisplayLayout.my_layout, refresh_per_second=6, screen=True):
        dispatcher(browser, user_config)
    browser.close()


if __name__ == "__main__":
    # playwright = sync_playwright().start()
    # playwright codegen game.nimingxx.com
    # args_conf = "config1.yml"
    args_conf = fire.Fire(cmd_args)
    with sync_playwright() as pw:
        run(pw)
