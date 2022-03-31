import re
from collections import defaultdict, deque
from datetime import datetime
from functools import partial

import pandas as pd
from playwright.sync_api import Page

from display import DynLog
from func_other import GlobalVars, move_to_map, map_navigate, update_display_info, auto_fight_on


def refresh_direct(page: Page):
    while True:
        try:
            with page.expect_navigation(url="https://game.nimingxx.com/login"):
                page.reload(timeout=3000)
        except Exception:
            DynLog.record_log("页面重载失败，继续重试", error=True)
            continue
        else:
            DynLog.record_log("页面重载成功")
            break


def login(page: Page, login_conf: dict):
    DynLog.record_log("正在自动登录")
    page.fill("input[placeholder=\"请输入用户名\"]", login_conf.get("username"))
    page.fill("input[placeholder=\"请输入密码\"]", login_conf.get("password"))
    page.check("input[type=\"checkbox\"]")
    while True:
        try:
            with page.expect_navigation(url="https://game.nimingxx.com/home", timeout=5000):
                page.click("button:has-text(\"立即登陆\")")
        except Exception:
            DynLog.record_log("连接失败1", error=True)
            page.wait_for_timeout(timeout=10000)
            continue
        finally:
            page.wait_for_timeout(timeout=600)

        try:
            page.wait_for_selector("text=日志记录", timeout=2000)
            # "div[role=\"tab\"]:has-text(\"灵宠\")"
            break
        except Exception:
            DynLog.record_log("连接失败2", error=True)
            page.wait_for_timeout(timeout=10000)
            continue
        finally:
            page.wait_for_timeout(timeout=600)
    DynLog.record_log("登录成功")

    # 初始化队伍和战斗
    DynLog.record_log("正在初始化界面")
    page.click("text=储物戒")
    page.wait_for_timeout(timeout=300)
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)
    page.click("text=活动")
    page.wait_for_timeout(timeout=300)
    # 领取奖励
    if (button1 := page.locator("button:has-text(\"签到\")")).count() == 1:
        button1.click()
    page.wait_for_timeout(timeout=300)
    if (button2 := page.locator("button:has-text(\"领取维护补偿\")")).count() == 1:
        button2.click()
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)

    DynLog.record_log("正在关闭耗费资源的配置")
    # 关闭日志记录
    if (off_log_switch := page.locator("div[role=\"switch\"]")).get_attribute('aria-checked') != 'true':
        off_log_switch.locator("span").click()

    page.locator("svg[data-icon=\"setting\"]").first.click()
    # 关闭自动跳转战斗
    if page.locator("label[class=\"el-checkbox is-checked\"]").count() > 0:
        page.click("text=自动跳转战斗日志")

    # 关闭战斗动画
    if (fight_animation := page.locator("text=自动跳转战斗日志 是否显示战斗动画效果 清空聊天框记录 >> div[role=\"switch\"]")).get_attribute(
            'aria-checked') == 'true':
        fight_animation.locator("span").click()

    page.click("button:has-text(\"保 存\")")


def mission_yaoling(page: Page, user_config, user_idx: int, person_vars: object):
    start_city = "丹城"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    times = 10
    while times > 0:
        if page.url.endswith('login'):
            login(page, user_config.get("login"))
        DynLog.record_log("开始做药灵任务")
        update_display_info(page, info_deque, user_idx, person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        move_to_map(page, start_city)

        DynLog.record_log("接取药灵任务")
        page.wait_for_timeout(timeout=2000)
        while (person := page.locator("button:has-text(\"旭日药师\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=1000)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[采药]任务").click()
                page.wait_for_timeout(timeout=1000)
            else:
                DynLog.record_log("任务对话框没弹出来", error=True)
                continue
            if page.locator("text=-寻找药灵").count() == 1:
                DynLog.record_log("接到任务")
                break
            else:
                continue
        else:
            DynLog.record_log("未能正确初始化任务位置", error=True)
            continue
        mission = page.locator("text=-寻找药灵")
        mission.hover()
        page.wait_for_timeout(timeout=1000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        # move_to_map(page, mission_city)
        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=2000)
        # 战斗
        while True:
            # page.locator(f'a div img:right-of(:text("{mission_monster}"))').first.click()
            page.locator(f'img[title=\"挑战\"]:right-of(:text("{mission_monster}"))').first.click()

            # 自动战斗
            if not auto_fight:
                auto_fight_on(page, user_config.get("fight"), cycle=False)
                auto_fight = True

            page.wait_for_timeout(timeout=8000)
            update_display_info(page, info_deque, user_idx, person_vars)
            if mission.count() == 0:
                DynLog.record_log("完成一次药灵任务")
                times -= 1
                break
    DynLog.record_log("任务完成，请手动退出")


def mission_xiangyao(page: Page, user_config, user_idx: int, person_vars: object):
    start_city = "林中栈道"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    times = 3
    while times > 0:
        if page.url.endswith('login'):
            login(page, user_config.get("login"))
        DynLog.record_log("开始做降妖任务")
        update_display_info(page, info_deque, user_idx, person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        move_to_map(page, start_city)

        DynLog.record_log("接取降妖任务")
        page.wait_for_timeout(timeout=2000)
        # 组队
        page.wait_for_timeout(timeout=1000)
        while (person := page.locator("button:has-text(\"凌中天\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=1000)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[降妖]任务").click()
                page.wait_for_timeout(timeout=1000)
            else:
                DynLog.record_log("任务对话框没弹出来", error=True)
                continue
            if page.locator("text=-降妖").count() == 1:
                DynLog.record_log("接到任务")
                break
            else:
                continue
        else:
            DynLog.record_log("未能正确初始化任务位置", error=True)
            continue
        # 任务刷新
        mission = page.locator("text=-降妖")
        mission.hover()
        page.wait_for_timeout(timeout=1000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(r".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        # mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=2000)
        # 战斗
        while True:
            # page.locator(f'a div img:right-of(:text("{mission_monster}"))').first.click()
            page.locator(f'img[title=\"挑战\"]:right-of(:text("{mission_monster}"))').first.click()

            # 自动战斗
            if not auto_fight:
                auto_fight_on(page, user_config.get("fight"), cycle=False)
                auto_fight = True

            page.wait_for_timeout(timeout=8000)
            update_display_info(page, info_deque, user_idx, person_vars)

            # 任务刷新
            mission.hover()
            page.wait_for_timeout(timeout=1000)
            page.locator("a[class=\"tb\"]:has-text(\"完成\")").click()
            page.wait_for_timeout(timeout=1000)
            if mission.count() == 0:
                DynLog.record_log("完成一次降妖任务")
                times -= 1
                break
    DynLog.record_log("任务完成，请手动退出")


def mission_xunbao(page: Page, user_config, user_idx: int, person_vars: object):
    start_city = "阳城"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    times = 10
    while times > 0:
        if page.url.endswith('login'):
            login(page, user_config.get("login"))
        DynLog.record_log("开始做寻宝任务")
        update_display_info(page, info_deque, user_idx, person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        move_to_map(page, start_city)

        DynLog.record_log("接取寻宝任务")
        page.wait_for_timeout(timeout=2000)
        while (person := page.locator("button:has-text(\"盗极生\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=1000)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[寻宝图]任务").click()
                page.wait_for_timeout(timeout=1000)
            else:
                DynLog.record_log("任务对话框没弹出来", error=True)
                continue
            if page.locator("text=-寻宝").count() == 1:
                DynLog.record_log("接到任务")
                break
            else:
                continue
        else:
            DynLog.record_log("未能正确初始化任务位置", error=True)
            continue
        mission = page.locator("text=-寻宝")
        mission.hover()
        page.wait_for_timeout(timeout=1000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(r".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        # mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        # move_to_map(page, mission_city)
        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=2000)
        # 战斗
        while True:
            # page.locator(f'a div img:right-of(:text("{mission_monster}"))').first.click()
            page.locator(f'img[title=\"挑战\"]:right-of(:text("{mission_monster}"))').first.click()

            # 自动战斗
            if not auto_fight:
                auto_fight_on(page, user_config.get("fight"), cycle=False)
                auto_fight = True

            page.wait_for_timeout(timeout=8000)
            update_display_info(page, info_deque, user_idx, person_vars)
            mission.hover()
            page.wait_for_timeout(timeout=1000)
            page.locator("a[class=\"tb\"]:has-text(\"完成\")").click()
            page.wait_for_timeout(timeout=1000)
            if mission.count() == 0:
                DynLog.record_log("完成一次寻宝任务")
                times -= 1
                break
    DynLog.record_log("任务完成，请手动退出")


def fight(page: Page, fight_config: dict, person_vars: GlobalVars):
    DynLog.record_log("正在开启自动战斗")
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"刷新列表\")")

    while True:
        # TODO(kevin):增加一个fallback模式
        if fight_config.get("captain") is not None or not fight_config.get("alone"):
            page.wait_for_timeout(timeout=600)
            team_list = page.locator("[class=\"team-list-row el-row\"]")
            d = defaultdict(list)
            for i in range(team_list.count()):
                s = team_list.nth(i).text_content()
                team_info = re.split(r"\s+", s.strip())[:3]
                d['captain'].append(team_info[0])
                d['monster'].append(team_info[1])
                d['team_size'].append(team_info[2])
                d['encryption'].append(team_list.nth(i).locator("div i").count() >= 2)
                d['join_team'].append(team_list.nth(i).locator("a:has-text(\"+\")"))  # team_list.nth(i).locator("text=+")
            df = pd.DataFrame(d)

            if df.empty:
                # 降级打怪
                DynLog.record_log("当前地图内没有队伍，切换为独立建队", error=True)
                fight_config["captain"] = None
                fight_config["alone"] = True
                continue

            if fight_config.get("captain") is not None:
                DynLog.record_log("尝试加入指定队长模式")
                df_captain_team = df.loc[df.captain == fight_config.get("captain")]
                if not df_captain_team.empty:
                    df_captain_team.iloc[0, -1].click()
                    # TODO(kevin):处理加入密码
                    person_vars.team_leader = df_captain_team.captain.iloc[0]
                    break
                else:
                    DynLog.record_log("队长不在该地图内或队长还未创建队伍", error=True)
                    DynLog.record_log("切换为随机加入队伍", error=True)
                    fight_config["captain"] = None
                    fight_config["alone"] = False
                    continue
            else:
                DynLog.record_log("尝试随机加入队伍模式")
                df_can_join = df.loc[(~df.encryption) & (df.team_size.str.slice(1, 2).astype(int) < 5) & (df.monster != '未选择')]
                if not df_can_join.empty:
                    # TODO(kevin):排序
                    df_captain_team = df_can_join.sample(1)
                    df_captain_team.iloc[0, -1].click()
                    person_vars.team_leader = df_captain_team.captain.iloc[0]
                    break
                else:
                    DynLog.record_log("当前没有可加入的队伍", error=True)
                    DynLog.record_log("转换为独立建队", error=True)
                    fight_config["alone"] = True
                    continue
        elif fight_config.get("alone"):
            DynLog.record_log("尝试独立建队模式")
            if fight_config.get("passwd"):
                page.click("text=需要密令")
            page.click("button:has-text(\"创建队伍\")")
            person_vars.team_leader = "自己建队"
            # TODO(kevin):队伍密码
            page.locator(f'img:right-of(:text("{fight_config.get("monster")}"))').first.click()
            break
        else:
            DynLog.record_log("尝试独立建队模式", error=True)
            exit(1)

    auto_fight_on(page, fight_config)
    DynLog.record_log("开始挂机")


def guaji(page: Page, user_config, user_idx: int, person_vars: GlobalVars):
    while True:
        if page.url.endswith('login'):
            login(page, user_config.get("login"))

        map_navigate(page, user_config.get("fight"))
        fight(page, user_config.get("fight"), person_vars)
        info_deque = defaultdict(partial(deque, maxlen=128))
        person_vars.train_start_time = datetime.now()
        estimate1 = {}
        while True:
            if estimate1:
                cond = (estimate1['exp'] < 5e5) + (estimate1['hp'] < -3e5) + (estimate1['hm'] > 2e2)
            else:
                cond = 0
            # page.locator("img[height=\"10px\"]").count()
            if (page.locator("div[role=\"alert\"]:has-text(\"你已掉线...\")").count() >= 1) or (page.locator("a:has-text(\"X\")").count() == 0) or cond >= 2:
                refresh_direct(page)
                break
            estimate1 = update_display_info(page, info_deque, user_idx, person_vars)
            page.wait_for_timeout(timeout=29500)
