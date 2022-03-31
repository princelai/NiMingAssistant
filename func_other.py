import re
from datetime import datetime, timedelta
from math import ceil
from typing import List, Tuple

import joblib
import networkx as nx
import numpy as np
import pandas as pd
from playwright.sync_api import Page

from display import DynLog, DisplayLayout


class GlobalVars:
    program_start_time: datetime = datetime.now()
    team_passwd: str = ""

    def __init__(self):
        self.train_start_time: datetime = datetime.now()
        self.team_leader: str = ""


def valid_config(confs: List[dict]) -> List[dict]:
    new_configs = []
    for c in confs:
        new_c = {}
        if bool(c.get('login', {}).get("username")) & bool(c.get('login', {}).get("password")):
            new_c['login'] = c.get('login')
        else:
            DynLog.record_log("未正确配置登录信息", error=True)
            exit(1)
        new_c['fight'] = {}
        new_c['mission'] = {}
        if (v1 := c.get('fight', {}).get("alone")) is None:
            new_c['fight'].update({"alone": True})
        else:
            new_c['fight'].update({"alone": v1})
        if (v2 := c.get('fight', {}).get("passwd")) is None:
            new_c['fight'].update({"passwd": False})
        else:
            new_c['fight'].update({"passwd": v2})
        if (v3 := c.get('fight', {}).get("monster")) is None:
            new_c['fight'].update({"monster": '冰莲灵兽群'})
        else:
            new_c['fight'].update({"monster": v3})
        new_c['fight'].update({"captain": c.get('fight', {}).get("captain")})
        new_c['fight'].update({"skill": c.get('fight', {}).get("skill")})
        new_c['mission'].update({"name": c.get('mission', {}).get("name")})
        new_configs.append(new_c)
    return new_configs


def get_user_info(page: Page) -> dict:
    d = dict()
    d['经验条'] = page.locator("[class=\"exp\"]").inner_text()
    d['名称'] = page.locator("span[class=\"info-v\"]:right-of(:has-text(\"名称\"))").first.inner_text()
    d['修为'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"修为\"))").first.inner_text())
    d['气血储备'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"气血储备\"))").first.inner_text())
    d['魔法储备'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"魔法储备\"))").first.inner_text())
    d['心魔'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"心魔\"))").first.inner_text())
    d['速力'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"速力\"))").first.inner_text())
    if d['气血储备'] < 50000:
        exchange_hp(page)
    if d['魔法储备'] < 50000:
        exchange_mp(page)
    if d['速力'] < 40:
        exchange_sl(page, ling=10000)
    return d


def get_fight_result(page: Page):
    page.click("text=结算日志")
    page.wait_for_timeout(timeout=300)
    page.locator("div:has-text(\"累计胜利\")").last.inner_text()
    log_result_frame = page.locator("div[role=\"tabpanel\"]:has-text(\"累计胜利\") div div")
    fight_stats = {k: int(v) for k, v in re.findall(r"(.+?):(\d+)", log_result_frame.nth(2).inner_text())}
    reward_items = {k: int(v) for k, v in re.findall(r"(\w+)\s*?x(\d+)", log_result_frame.nth(1).inner_text())}
    return fight_stats, reward_items


def estimate_info(deq) -> Tuple[dict, dict]:
    # df = pd.DataFrame(joblib.load("user0_deque.joblib"))
    df = pd.DataFrame(deq)
    df['time'] = pd.to_datetime(df.time)
    df.set_index('time', inplace=True)
    df = df.loc[datetime.now() - timedelta(minutes=30):datetime.now()]
    if df.shape[0] < 20:
        return {}, {}
    df_diff = df.diff(axis=0).dropna(how='all')
    df_diff["exp"] *= -1
    df_diff["hm"] *= -1
    df_diff = df_diff.apply(lambda x: np.where(x <= 0, x, x.median()))
    df_diff["exp"] *= -1
    df_diff["hm"] *= -1
    deque_sec = (df_diff.index[-1] - df_diff.index[0]).total_seconds()
    estimate_result = (df_diff.sum() / deque_sec * 3600)
    estimate = estimate_result.abs().apply(lambda x: f'{x / 1e4:.1f}万/小时' if x >= 1e4 else f'{x:.1f}/小时')
    return estimate_result.to_dict(), estimate.to_dict()


def exchange_hp(page: Page, ling=5000):
    DynLog.record_log("兑换一次气血")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[role=\"spinbutton\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"聚灵\")").click()
    DynLog.record_log("继续挂机中")


def exchange_mp(page: Page, ling=5000):
    DynLog.record_log("兑换一次魔法")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[role=\"spinbutton\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"凝元\")").click()
    DynLog.record_log("继续挂机中")


def exchange_sl(page: Page, ling=5000):
    DynLog.record_log("兑换一次速力")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[role=\"spinbutton\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"炼神\")").click()
    DynLog.record_log("继续挂机中")


def move_to_map(page: Page, target_map: str) -> None:
    g = nx.read_gpickle('map_luofan.pkl')
    # g = nx.read_gml('map_luofan.gml')
    curr_map = page.locator("text=当前地图").inner_text()
    curr_map = curr_map.split(":")[1]
    map_step = 20
    if curr_map != target_map:
        DynLog.record_log(f"正在寻路去往{target_map}")
        walk_path = nx.shortest_path(g, curr_map, target_map)[1:]
        for p in walk_path:
            city_loc_idx = 0
            svg_frame_text = page.locator("svg[class=\"svg\"] >> text")
            if (city_loc := svg_frame_text.locator(f"text={p}")).count() == 1:
                x = int(city_loc.get_attribute('x'))
                y = int(city_loc.get_attribute('y'))
            else:
                city_loc_txt = city_loc.all_text_contents()
                city_loc_txt = list(map(lambda z: z.strip(), city_loc_txt))
                city_loc_idx = city_loc_txt.index(p)
                x = int(city_loc.nth(city_loc_idx).get_attribute('x'))
                y = int(city_loc.nth(city_loc_idx).get_attribute('y'))

            if x <= (x_min := 40):
                move_left = page.locator("div[class=\"move-d move-left\"]")
                for _ in range(ceil(abs((x - x_min) / map_step))):
                    move_left.click()
                    page.wait_for_timeout(timeout=500)

            if x >= (x_max := 400):
                move_right = page.locator("div[class=\"move-d move-right\"]")
                for _ in range(ceil(abs((x - x_max) / map_step))):
                    move_right.click()
                    page.wait_for_timeout(timeout=500)

            if y <= (y_min := 60):
                move_top = page.locator("div[class=\"move-d move-top\"]")
                for _ in range(ceil(abs((y - y_min) / map_step))):
                    move_top.click()
                    page.wait_for_timeout(timeout=500)

            if y >= (y_max := 230):
                move_bottom = page.locator("div[class=\"move-d move-bottom\"]")
                for _ in range(ceil(abs((y - y_max) / map_step))):
                    move_bottom.click()
                    page.wait_for_timeout(timeout=500)

            svg_frame_text.locator(f"text={p}").nth(city_loc_idx).click()
            DynLog.record_log(f"路过{p}")
            page.wait_for_timeout(timeout=2000)
        DynLog.record_log("已到达指定地图")


def map_navigate(page: Page, fight_config: dict):
    monster_map = {"无极峰": {"无极峰兽群(70)", "凤爪雪狼群(70)"},
                   "云天山峰": {"珍珠妖鹿群(65)", "开灵兽群(50)", "云峰灵兽群(55)", "赤地魔蝎群(60)"},
                   "落樱山脉": {"落樱灵兽群(45)", "飞羽兽群(40)"},
                   "通天道": {"钻地兽群(35)", "陆地兽群(35)", "通天灵兽群(30)"},
                   "碧炎山脉": {"焱炎兽群(21)"},
                   "炽焰火山": {"山火灵兽群(25)"},
                   "冰莲青湖": {"冰莲灵兽群(31)"}}
    target_map = ""
    for k, v in monster_map.items():
        for m in v:
            if m.startswith(fight_config.get('monster')):
                target_map = k
    if not bool(target_map):
        DynLog.record_log("配置的怪物未能找到", error=True)
        exit(1)
    move_to_map(page, target_map)


def update_display_info(page: Page, info_deque, user_idx, person_vars: GlobalVars) -> dict:
    user_info = get_user_info(page)
    info_deque['time'].append(datetime.now())
    info_deque['exp'].append(user_info['修为'])
    info_deque['hp'].append(user_info['气血储备'])
    info_deque['mp'].append(user_info['魔法储备'])
    info_deque['hm'].append(user_info['心魔'])
    stats, reward = get_fight_result(page)
    joblib.dump(info_deque, f"user{user_idx}_deque.joblib")
    estimate1, estimate2 = estimate_info(info_deque)

    train_time = pd.to_timedelta(datetime.now() - person_vars.train_start_time).ceil('T')
    match_time2 = re.search(r"(\d+)\sdays\s(\d+):(\d+)", str(train_time))
    time2_str = f"{int(match_time2.group(1))}天{int(match_time2.group(2))}小时{int(match_time2.group(3))}分"

    if person_vars.team_leader == "自己建队":
        person_vars.team_leader = user_info.get("名称", "")
    dd = {"team_info": {"leader": person_vars.team_leader, "num": page.locator("a:has-text(\"X\")").count(), "time": time2_str},
          "user_info": user_info,
          "fight_info": stats,
          "reward_info": reward,
          "estimate_info": estimate2}

    DisplayLayout.update_user_info(block=f"user{user_idx}", value=dd)
    return estimate1


def auto_fight_on(page: Page, fight_config: dict, cycle=True):
    page.click("text=战斗日志")
    page.wait_for_timeout(timeout=500)
    if fight_config.get("skill") is None:
        # last skill
        page.wait_for_selector("div[class=\"skill-bar\"] > div > img", timeout=10000)
        skill = page.locator("div[class=\"skill-bar\"] > div > img").last
        skill_name = skill.get_attribute("alt")
        skill.click()
    else:
        # point skill
        skill_name = fight_config.get("skill")
        page.wait_for_selector(f"img[alt=\"{skill_name}\"]", timeout=10000)
        skill = page.locator(f"img[alt=\"{skill_name}\"]")
        if skill.count() == 1:
            skill.click()
        else:
            DynLog.record_log("你还没学会配置的技能", error=True)
            exit(1)

    if cycle:
        page.click("text=循环挑战")

    auto_fight_box = page.locator(f"text=请操作 自动 ↓技能↓ {skill_name} ↓目标↓ >> input[type=\"checkbox\"]")
    while auto_fight_box.count() == 0:
        page.wait_for_timeout(timeout=600)
        continue
    else:
        auto_fight_box.check()
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)
    DynLog.record_log("开启自动战斗成功")
