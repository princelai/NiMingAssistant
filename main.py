from pathlib import Path

import fire
import yaml
from playwright.sync_api import Playwright, sync_playwright
from rich.live import Live

from display import DisplayLayout
from func_common import mission_yaoling, mission_xunbao, mission_xiangyao, guaji
from func_other import valid_config, UserVars


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
    page.wait_for_selector("input[placeholder=\"请输入密码\"]", timeout=5000)

    if user_config['mission']['name'] == "药灵":
        mission_yaoling(page, user_config, UserVars())
    elif user_config['mission']['name'] == "寻宝":
        mission_xunbao(page, user_config, UserVars())
    elif user_config['mission']['name'] == "降妖":
        mission_xiangyao(page, user_config, UserVars())
    else:
        guaji(page, user_config, UserVars())

    try:
        page.pause()
    except Exception:
        pass
    context.close()


def run(playwright: Playwright) -> None:
    with open(args_conf, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)
    user_config = valid_config(conf)

    for f in Path('.').glob("*.joblib"):
        f.unlink()

    # TODO(kevin):无头设置，记得每次检查一下是否为True
    browser = playwright.chromium.launch(headless=False)

    with Live(DisplayLayout.my_layout, refresh_per_second=8, screen=True):
        dispatcher(browser, user_config)
    browser.close()


if __name__ == "__main__":
    # playwright = sync_playwright().start()
    # playwright codegen game.nimingxx.com
    # args_conf = "config1.yml"
    args_conf = fire.Fire(cmd_args)
    with sync_playwright() as pw:
        run(pw)
