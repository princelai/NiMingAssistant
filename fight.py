from collections import defaultdict, deque
from datetime import datetime
from functools import partial

import pandas as pd
from pandas import DataFrame
from playwright.sync_api import Page

from display import DynLog
from info import UserVars, update_display_info
from login import login, refresh_direct
from map import CityMap


def get_team_list(page: Page) -> DataFrame:
    page.click("div[id=\"tab-scene-tab\"]")
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"刷新列表\")")
    page.wait_for_timeout(timeout=500)
    team_list = page.locator("div[class=\"el-row team-list-row\"]")
    d = defaultdict(list)
    for i in range(team_list.count()):
        sub_div = team_list.nth(i).locator("div > div")
        d['captain'].append(sub_div.nth(1).inner_text())
        if sub_div.count() == 7:
            d['monster'].append(sub_div.nth(5).inner_text())
        else:
            d['monster'].append(sub_div.nth(6).inner_text())
        d['join_team'].append(sub_div.nth(3))
    df = pd.DataFrame(d, columns=['captain', 'monster', 'join_team'])
    return df


def auto_fight(page, fight_config, captain):
    skill_name = fight_config.get("skill")
    page.click("div[data-name=\"tab-bat\"]")
    page.wait_for_selector("text=普通攻击", timeout=10000)
    page.click("text=普通攻击")
    page.wait_for_timeout(timeout=300)
    page.locator(f"div[data-dropdown-option=\"true\"]:has-text(\"{skill_name}\")").click()
    page.wait_for_timeout(timeout=300)
    if captain:
        page.locator("text=开启循环").last.click()
        page.wait_for_timeout(timeout=300)
    page.locator("div[class=\"n-switch__unchecked\"]:has-text(\"手动\")").click()
    page.wait_for_timeout(timeout=300)
    DynLog.record_log("开启自动战斗成功")


def create_team(page):
    page.click("div[id=\"tab-scene-tab\"]")
    page.wait_for_timeout(timeout=300)
    page.click("text=自定创建")
    page.wait_for_timeout(timeout=300)
    page.locator("input[placeholder=\"入队密令(默认无)\"]").fill("3333")
    page.wait_for_timeout(timeout=300)
    page.click("div[class=\"n-popconfirm__action\"] > button:has-text(\"创建\")")
    page.wait_for_timeout(timeout=300)
    page.click("text=自定创建")
    page.wait_for_timeout(timeout=300)


def fight(page: Page, fight_config: dict):
    DynLog.record_log("准备战斗")
    page.click("div[id=\"tab-scene-tab\"]")
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"刷新列表\")")

    while True:
        if fight_config.get("captain"):
            # 加入别人队伍
            df_team = get_team_list(page)
            try:
                df_team.loc[df_team.captain == fight_config.get("captain"), "join_team"].iloc[0].click()

                page.wait_for_selector("text=请输入密令", timeout=2000)
                password_div = page.locator("div[class=\"n-card__content\"]")
                password_div.locator("input[placeholder=\"请输入\"]").fill("3333")
                page.wait_for_timeout(timeout=300)
                password_div.locator("button:has-text(\"加入\")").click()
                # 删除加入判断
                DynLog.record_log(f'加入队长{fight_config.get("captain")}队伍')
            except Exception:
                DynLog.record_log("加入队长错误，等待后重试", error=True)
                page.wait_for_timeout(timeout=10000)
                continue
            else:
                auto_fight(page, fight_config, False)
        else:
            # 自己当队长
            create_team(page)

            # 和怪物战斗
            battle_div = page.locator(f"div[class=\"n-scrollbar-content\"]:below(:has-text(\"附近兽群\")):right-of(:has-text(\"附近队伍\"))")
            battle_icon_div = battle_div.locator("svg[class=\"svg-icon icon-bat\"]")
            battle_icon = [battle_icon_div.nth(i) for i in range(battle_icon_div.count())]
            monster_list = battle_div.inner_text().split('\n')
            monster_id = monster_list.index(fight_config.get("monster"))
            battle_icon[monster_id].click()

            df_team = get_team_list(page)
            name = page.locator("div[class=\"info\"] >> span[class=\"vt\"]").nth(0).inner_text()
            if not df_team.empty and name in df_team.captain.values:
                pass
            else:
                DynLog.record_log("未能成功创建队伍，重试", error=True)
                continue
            auto_fight(page, fight_config, True)
        DynLog.record_log("开始挂机")
        break


def guaji(page: Page, user_config, person_vars: UserVars):
    while True:
        if page.url.endswith('login'):
            login(page, user_config)

        monster = CityMap.map_navigate(page, user_config.get("fight"))
        user_config["fight"]["monster"] = monster
        fight(page, user_config.get("fight"))
        info_deque = defaultdict(partial(deque, maxlen=256))
        person_vars.train_start_time = datetime.now()
        while True:
            team_members = page.locator("svg[class=\"svg-icon icon-power\"]").count()
            if (page.locator("text=链接被关闭").count() >= 1) or team_members == 0:
                DynLog.record_log("程序主动重启", error=True)
                refresh_direct(page)
                break
            update_display_info(page, info_deque, person_vars)
            page.wait_for_timeout(timeout=15000)
