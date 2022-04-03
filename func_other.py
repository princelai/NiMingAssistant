import re
from datetime import datetime, timedelta
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
from playwright.sync_api import Page

from display import DynLog, DisplayLayout


class UserVars:
    def __init__(self):
        self.train_start_time: datetime = datetime.now()
        self.team_leader: str = ""


def valid_config(c: dict) -> dict:
    new_c = {}
    if bool(c.get('login', {}).get("username")) & bool(c.get('login', {}).get("password")):
        new_c['login'] = c.get('login')
    else:
        DynLog.record_log("未正确配置登录信息", error=True)
        exit(1)
    new_c['fight'] = {}
    new_c['mission'] = {}
    if (v1 := c.get('fight', {}).get("skill")) is not None:
        new_c['fight'].update({"skill": v1})
    else:
        DynLog.record_log("未正确配置技能信息", error=True)
        exit(1)
    if (v2 := c.get('fight', {}).get("monster")) is None:
        new_c['fight'].update({"monster": '陆地兽群'})
    else:
        new_c['fight'].update({"monster": v2})
    new_c['mission'].update({"name": c.get('mission', {}).get("name")})
    return new_c


def get_user_info(page: Page) -> dict:
    d = dict()
    page.click("div[id=\"tab-1\"]:has-text(\"装备\")")
    page.wait_for_timeout(timeout=500)
    page.click("div[id=\"tab-0\"]:has-text(\"信息\")")
    page.wait_for_timeout(timeout=500)
    d['经验条'] = page.locator("[class=\"exp\"]").inner_text()
    d['名称'] = page.locator("span[class=\"info-v\"]:right-of(:has-text(\"名称\"))").first.inner_text()
    d['修为'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"修为\"))").first.inner_text())
    d['气血储备'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"气血储备\"))").first.inner_text())
    d['魔法储备'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"魔法储备\"))").first.inner_text())
    d['心魔'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"心魔\"))").first.inner_text())
    d['速力'] = int(page.locator("span[class=\"info-v\"]:right-of(:has-text(\"速力\"))").first.inner_text())
    # TODO(kevin):灵力
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
    # df = pd.DataFrame(joblib.load("user_deque.joblib"))
    df = pd.DataFrame(deq)
    df['time'] = pd.to_datetime(df.time)
    df.set_index('time', inplace=True)
    df = df.loc[datetime.now() - timedelta(minutes=15):datetime.now()]
    if df.shape[0] < 10:
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


def update_display_info(page: Page, info_deque, person_vars: UserVars) -> dict:
    user_info = get_user_info(page)
    info_deque['time'].append(datetime.now())
    info_deque['exp'].append(user_info['修为'])
    info_deque['hp'].append(user_info['气血储备'])
    info_deque['mp'].append(user_info['魔法储备'])
    info_deque['hm'].append(user_info['心魔'])
    stats, reward = get_fight_result(page)
    joblib.dump(info_deque, f"user_deque.joblib")
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

    DisplayLayout.update_user_info(value=dd)
    return estimate1


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
