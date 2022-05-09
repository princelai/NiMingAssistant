from datetime import datetime, timedelta
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from playwright.sync_api import Page

from display import DynLog, DisplayLayout


def format_string_num(s: str) -> str:
    sign = np.sign(int(s))
    num = abs(int(s))
    if num >= 1e4:
        return f'{sign * num / 1e4:.1f}万/小时'
    else:
        return f'{sign * num:.1f}/小时'


def string2num(s: str):
    if s.endswith('w'):
        return int(float(s[:-1]) * 1e4)
    elif s.endswith('e'):
        return int(float(s[:-1]) * 1e8)
    else:
        return int(s)


def get_user_info(page: Page) -> dict:
    info_div = page.locator("div[class=\"info\"]")
    info_key = info_div.locator("span[class=\"k\"]")
    info_value = info_div.locator("span[class=\"vt\"]")
    info_dict = {info_key.nth(i).inner_text().strip()[:-1]: info_value.nth(i).inner_text().strip() for i in range(info_key.count() - 2)}
    d = dict()
    d['名称'] = info_dict.get("名称")
    d['修为'] = string2num(info_dict.get("修为"))
    d['气血储备'] = string2num(info_dict.get("气血储备"))
    d['魔法储备'] = string2num(info_dict.get("魔法储备"))
    d['心魔'] = string2num(info_dict.get("心魔"))
    d['速力'] = string2num(info_dict.get("速力"))
    d['灵力'] = string2num(info_key.last.inner_text().split("：")[1])
    if d['气血储备'] < 70000:
        exchange_hp(page)
    if d['魔法储备'] < 70000:
        exchange_mp(page)
    if d['速力'] < 65:
        exchange_sl(page)
    return d


def get_fight_result(page: Page):
    page.click("text=累计奖励")
    page.wait_for_selector("text=败北", timeout=2000)
    log_fight_frame = page.locator("span[class=\"bat-log-p\"]")
    fight_stats = {(tmp := log_fight_frame.nth(i).inner_text().split(":"))[0]: int(tmp[1]) for i in range(log_fight_frame.count())}
    log_reward_frame = page.locator("span[class=\"bat-log-p goods\"]")
    reward_items = {(tmp := log_reward_frame.nth(i).inner_text().split(" x"))[0]: int(tmp[1]) for i in range(log_reward_frame.count())}
    return fight_stats, reward_items


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
    page.click("button:has-text(\"聚灵\")")
    page.wait_for_timeout(timeout=300)
    page.locator("input[placeholder=\"请输入灵力\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"转换\")")
    DynLog.record_log("继续")


def exchange_mp(page: Page, ling=10000):
    DynLog.record_log("兑换一次魔法")
    page.click("button:has-text(\"凝元\")")
    page.wait_for_timeout(timeout=300)
    page.locator("input[placeholder=\"请输入灵力\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"转换\")")
    DynLog.record_log("继续")


def exchange_sl(page: Page, ling=10000):
    DynLog.record_log("兑换一次速力")
    page.click("button:has-text(\"炼神\")")
    page.wait_for_timeout(timeout=300)
    page.locator("input[placeholder=\"请输入灵力\"]").fill(str(ling))
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"转换\")")
    DynLog.record_log("继续")


def update_display_info(page: Page, info_deque):
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

    # train_time = pd.to_timedelta(datetime.now() - train_start_time).ceil('T')
    # match_time2 = re.search(r"(\d+)\sdays\s(\d+):(\d+)", str(train_time))
    # time2_str = f"{int(match_time2.group(1))}天{int(match_time2.group(2))}小时{int(match_time2.group(3))}分"

    dd = {"team_info": {"num": page.locator("svg[class=\"svg-icon icon-power\"]").count()},
          "user_info": user_info,
          "fight_info": stats,
          "reward_info": reward,
          "estimate_info": estimate2}

    DisplayLayout.update_user_info(value=dd)
