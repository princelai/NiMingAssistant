import re
from datetime import datetime, timedelta
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from playwright.sync_api import Page

from display import DynLog, DisplayLayout


class UserVars:
    def __init__(self):
        self.train_start_time: datetime = datetime.now()
        self.team_leader: str = ""


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
    d['灵力'] = int(re.search(r"总灵力\((\d+)\)", page.locator("text=总灵力").inner_text()).group(1))
    if d['气血储备'] < 70000:
        exchange_hp(page)
    if d['魔法储备'] < 70000:
        exchange_mp(page)
    if d['速力'] < 65:
        exchange_sl(page)
    return d


def get_fight_result(page: Page):
    page.click("text=结算日志")
    page.wait_for_timeout(timeout=300)
    page.locator("div:has-text(\"累计胜利\")").last.inner_text()
    log_result_frame = page.locator("div[role=\"tabpanel\"]:has-text(\"累计胜利\") div div")
    fight_stats = {k: int(v) for k, v in re.findall(r"(.+?):(\d+)", log_result_frame.nth(2).inner_text())}
    reward_items = {k: int(v) for k, v in re.findall(r"(\w+)\s*?x(\d+)", log_result_frame.nth(1).inner_text())}
    return fight_stats, reward_items


def format_string_num(s: str) -> str:
    sign = np.sign(int(s))
    num = abs(int(s))
    if num >= 1e4:
        return f'{sign * num / 1e4:.1f}万/小时'
    else:
        return f'{sign * num:.1f}/小时'


def estimate_info(deq) -> Tuple[dict, dict]:
    # df = pd.DataFrame(joblib.load("user_deque.joblib"))
    df = pd.DataFrame(deq)
    df.drop(columns="sl", inplace=True)
    df['time'] = pd.to_datetime(df.time)
    df.set_index('time', inplace=True)
    df = df.loc[datetime.now() - timedelta(minutes=20):datetime.now()]
    if df.shape[0] < 10:
        return {}, {}
    df_diff = df.diff(axis=0).dropna(how='all')
    df_diff["exp"] = df_diff.exp.where(df_diff.exp >= 0, df_diff.exp.median())
    df_diff["hm"] = df_diff.hm.where(df_diff.hm >= 0, df_diff.hm.mean())
    df_diff["hp"] = df_diff.hp.where(df_diff.hp <= 0, df_diff.hp.median())
    df_diff["mp"] = df_diff.mp.where(df_diff.mp <= 0, df_diff.mp.median())
    df_diff["ll"].fillna(df_diff.ll.mean(), inplace=True)
    deque_sec = (df_diff.index[-1] - df_diff.index[0]).total_seconds()
    estimate_result = (df_diff.sum() / deque_sec * 3600)
    estimate = estimate_result.apply(format_string_num)
    return estimate_result.to_dict(), estimate.to_dict()


def exchange_hp(page: Page, ling=10000):
    DynLog.record_log("兑换一次气血")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[max=\"100000\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"聚灵\")").click()
    DynLog.record_log("继续挂机中")


def exchange_mp(page: Page, ling=10000):
    DynLog.record_log("兑换一次魔法")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[max=\"100000\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"凝元\")").click()
    DynLog.record_log("继续挂机中")


def exchange_sl(page: Page, ling=10000):
    DynLog.record_log("兑换一次速力")
    page.locator("text=总灵力").hover()
    page.wait_for_timeout(timeout=300)
    page.locator("input[max=\"100000\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.locator("a:has-text(\"炼神\")").click()
    DynLog.record_log("继续挂机中")


def update_display_info(page: Page, info_deque, person_vars: UserVars) -> dict:
    user_info = get_user_info(page)
    info_deque['time'].append(datetime.now())
    info_deque['exp'].append(user_info['修为'])
    info_deque['hp'].append(user_info['气血储备'])
    info_deque['mp'].append(user_info['魔法储备'])
    info_deque['ll'].append(user_info['灵力'])
    info_deque['hm'].append(user_info['心魔'])
    info_deque['sl'].append(user_info['速力'])
    stats, reward = get_fight_result(page)
    joblib.dump(info_deque, f"user_deque.joblib")
    estimate1, estimate2 = estimate_info(info_deque)

    train_time = pd.to_timedelta(datetime.now() - person_vars.train_start_time).ceil('T')
    match_time2 = re.search(r"(\d+)\sdays\s(\d+):(\d+)", str(train_time))
    time2_str = f"{int(match_time2.group(1))}天{int(match_time2.group(2))}小时{int(match_time2.group(3))}分"

    dd = {"team_info": {"leader": person_vars.team_leader, "num": page.locator("a:has-text(\"X\")").count(), "time": time2_str},
          "user_info": user_info,
          "fight_info": stats,
          "reward_info": reward,
          "estimate_info": estimate2}

    DisplayLayout.update_user_info(value=dd)
    return estimate1
