import re
from collections import defaultdict, deque
from datetime import datetime
from functools import partial
from pathlib import Path

import joblib
import pandas as pd
from pandas import DataFrame
from playwright.sync_api import Page

from display import DynLog
from info import UserVars, update_display_info
from login import login, refresh_direct
from map import CityMap


def get_team_list(page: Page) -> DataFrame:
    page.click("button:has-text(\"刷新列表\")")
    page.wait_for_timeout(timeout=1000)
    team_list = page.locator("[class=\"team-list-row el-row\"]")
    d = defaultdict(list)
    for i in range(team_list.count()):
        s = team_list.nth(i).text_content()
        team_info = re.split(r"\s+", s.strip())[:3]
        d['captain'].append(team_info[0])
        d['monster'].append(team_info[1])
        d['team_size'].append(team_info[2])
        d['encryption'].append(team_list.nth(i).locator("svg[data-icon=\"lock\"]"))
        d['join_team'].append(team_list.nth(i).locator("a:has-text(\"+\")"))
    df = pd.DataFrame(d, columns=['captain', 'monster', 'team_size', 'encryption', 'join_team'])
    return df


def auto_fight_on(page: Page, cycle=True):
    page.click("text=战斗日志")
    page.wait_for_selector(f"div[class=\"skill-bar\"] > div > img[alt=\"普通攻击\"]", timeout=15000)

    if cycle:
        page.click("text=循环挑战")
        page.wait_for_timeout(timeout=300)

    auto_fight_box = page.locator(f"text=自动 ↓技能↓ >> input[type=\"checkbox\"]")
    auto_fight_box.check()
    page.wait_for_timeout(timeout=300)
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)
    DynLog.record_log("开启自动战斗成功")


def fight(page: Page, fight_config: dict, person_vars: UserVars):
    DynLog.record_log("正在开启战斗")
    for tab in ("储物戒", "地图场景"):
        page.click(f"text={tab}")
        page.wait_for_timeout(timeout=1000)
    page.click("button:has-text(\"刷新列表\")")

    while True:
        if fight_config.get("captain"):
            df_team = get_team_list(page)
            if fight_config.get("captain") in df_team.captain.values:
                try:
                    df_team.loc[df_team.captain == fight_config.get("captain"), "join_team"].iloc[0].click()
                    passwd_loc = "div[class=\"ant-modal-content\"] >> input[role=\"spinbutton\"]"
                    page.wait_for_selector(passwd_loc, timeout=1000)
                    page.locator(passwd_loc).fill(joblib.load("password.bin"))
                    page.wait_for_timeout(timeout=300)
                    page.locator("button[type=\"button\"]:has-text(\"确认加入\")").click()
                    page.wait_for_selector(f'div[class=\"ant-card-body\"]:has-text(\"{fight_config.get("captain")}\")', timeout=1000)
                    DynLog.record_log(f'加入队长{fight_config.get("captain")}队伍')
                    person_vars.team_leader = fight_config.get("captain")
                    auto_fight_on(page, cycle=False)
                except Exception:
                    if fight_config.get("fallback"):
                        fight_config["captain"] = None
                        DynLog.record_log("加入队长模式错误，进入回落模式", error=True)
                    else:
                        DynLog.record_log("加入队长模式错误，等待后重试", error=True)
                        page.wait_for_timeout(timeout=10000)
                    continue
            else:
                if fight_config.get("fallback"):
                    fight_config["captain"] = None
                    DynLog.record_log("队长不在地图中，进入回落模式", error=True)
                else:
                    DynLog.record_log("队长不在地图中，等待后重试", error=True)
                    page.wait_for_timeout(timeout=10000)
                continue
        else:
            page.click("text=需要密令")
            page.wait_for_timeout(timeout=300)
            page.click("button:has-text(\"创建队伍\")")
            page.wait_for_selector("a:has-text(\"X\")", timeout=1000)
            person_vars.team_leader = "自己建队"
            monster_list = [s.strip() for s in page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
            monster_id = monster_list.index(fight_config.get("monster"))
            page.locator(f"img[title=\"挑战\"]:above(:has-text(\"附近NPC\"))").nth(monster_id).click()
            auto_fight_on(page)
            df_team = get_team_list(page)
            name = page.locator("span[class=\"info-v\"]:right-of(:has-text(\"名称\"))").first.inner_text()
            person_vars.team_leader = name
            if not df_team.empty and name in df_team.captain.values:
                f = Path("password.bin")
                if f.exists():
                    f.unlink()
                df_team.loc[df_team.captain == name, "encryption"].iloc[0].hover()
                page.wait_for_selector("text=队伍密令", timeout=1000)
                joblib.dump(page.locator("text=队伍密令").inner_text().split(":")[1], f.as_posix())
            else:
                DynLog.record_log("未能成功创建队伍，重试", error=True)
                continue
        DynLog.record_log("开始挂机")
        break


def guaji(page: Page, user_config, person_vars: UserVars):
    while True:
        if page.url.endswith('login'):
            login(page, user_config)

        CityMap.map_navigate(page, user_config.get("fight"))
        fight(page, user_config.get("fight"), person_vars)
        info_deque = defaultdict(partial(deque, maxlen=128))
        person_vars.train_start_time = datetime.now()
        estimate1 = {}
        while True:
            if estimate1:
                # cond = (estimate1['exp'] < 5e5) + (estimate1['hp'] < -3e5) + (estimate1['hm'] > 2e2)
                cond = estimate1['hm'] > 2e2 or estimate1['ll'] < -1e4
            else:
                cond = 0
            # page.locator("img[height=\"10px\"]").count()
            if (page.locator("div[role=\"alert\"]:has-text(\"你已掉线...\")").count() >= 1) or (
                    page.locator("a:has-text(\"X\")").count() == 0) or cond:
                DynLog.record_log("程序主动重启", error=True)
                refresh_direct(page)
                break
            estimate1 = update_display_info(page, info_deque, person_vars)
            page.wait_for_timeout(timeout=15000)
