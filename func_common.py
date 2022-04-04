import re
from collections import defaultdict, deque
from datetime import datetime
from functools import partial

import pandas as pd
from playwright.sync_api import Page

from display import DynLog
from func_other import UserVars, update_display_info, auto_fight_on
from map import CityMap


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


def login(page: Page, conf: dict):
    DynLog.record_log("正在自动登录")
    while True:
        try:
            page.reload()
            page.wait_for_selector("input[placeholder=\"请输入密码\"]", timeout=10000)
            page.fill("input[placeholder=\"请输入用户名\"]", conf.get("login").get("username"))
            page.wait_for_timeout(timeout=300)
            page.fill("input[placeholder=\"请输入密码\"]", conf.get("login").get("password"))
            page.wait_for_timeout(timeout=300)
            page.check("input[type=\"checkbox\"]")
            page.wait_for_timeout(timeout=300)

            with page.expect_navigation(url="https://game.nimingxx.com/home", timeout=5000):
                page.click("button:has-text(\"立即登陆\")")
            page.wait_for_selector("text=日志记录", timeout=2000)
            break
        except Exception:
            DynLog.record_log("连接失败", error=True)
            page.wait_for_timeout(timeout=10000)
            continue
    DynLog.record_log("登录成功")

    # 初始化队伍和战斗
    DynLog.record_log("正在初始化界面")
    for tab in ("储物戒", "地图场景", "活动", "修行", "地图场景"):
        page.click(f"text={tab}")
        page.wait_for_timeout(timeout=500)
        if tab == "活动":
            # 领取奖励
            page.wait_for_selector("button:has-text(\"领取维护补偿\")", timeout=2000)
            if page.locator("button:has-text(\"签到\")").count() == 1:
                page.locator("button:has-text(\"签到\")").click()
                page.wait_for_timeout(timeout=300)
            page.locator("button:has-text(\"领取维护补偿\")").click()

    DynLog.record_log("正在关闭耗费资源的配置")
    # 关闭日志记录
    if (off_log_switch := page.locator("div[role=\"switch\"]")).get_attribute('aria-checked') != 'true':
        off_log_switch.locator("span").click()
        page.wait_for_timeout(timeout=300)

    page.locator("svg[data-icon=\"setting\"]").first.click()
    # 关闭自动跳转战斗
    if page.locator("label[class=\"el-checkbox is-checked\"]").count() > 0:
        page.click("text=自动跳转战斗日志")
        page.wait_for_timeout(timeout=300)

    # 关闭战斗动画
    if (fight_animation := page.locator("text=自动跳转战斗日志 是否显示战斗动画效果 清空聊天框记录 >> div[role=\"switch\"]")).get_attribute(
            'aria-checked') == 'true':
        fight_animation.locator("span").click()
        page.wait_for_timeout(timeout=300)

    page.click("button:has-text(\"保 存\")")
    page.wait_for_selector("text=配置已生效", timeout=2000)
    # page.wait_for_timeout(timeout=300)

    # 设置自动技能
    page.click("text=修行")
    page.wait_for_timeout(timeout=1000)
    for tab in ("技能", "炼丹", "合成", "技能"):
        page.click(f"div[role=\"tab\"]:text(\"{tab}\")")
        page.wait_for_timeout(timeout=500)
    page.locator("input[type=\"text\"]:below(:has-text(\"已领悟技能\"))").click()
    page.wait_for_timeout(timeout=500)
    page.locator(f'div[class=\"el-scrollbar\"] div ul li:has-text(\"{conf.get("fight").get("skill")}\")').click()
    page.wait_for_timeout(timeout=500)
    page.locator("button[type=button]:has-text(\"保存\")").click()
    page.wait_for_timeout(timeout=500)
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=500)


def mission_yaoling(page: Page, user_config, person_vars: UserVars):
    start_city = "丹城"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    for i in range(10):
        if page.url.endswith('login'):
            login(page, user_config)
        DynLog.record_log("开始做药灵任务")
        update_display_info(page, info_deque,  person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        CityMap.move_to_map(page, start_city)

        DynLog.record_log("接取药灵任务")
        page.wait_for_selector("button:has-text(\"旭日药师\")", timeout=3000)
        while (person := page.locator("button:has-text(\"旭日药师\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[采药]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    DynLog.record_log("今日任务已做完")
                    return
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
        page.wait_for_selector("span[class=\"task-brief\"]:has-text(\"地区击败\")", timeout=2000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        # 战斗
        while True:
            for tab in ("战斗日志", "地图场景"):
                page.click(f"text={tab}")
                page.wait_for_timeout(timeout=1000)
            monster_list = [s.strip() for s in page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
            monster_id = monster_list.index(mission_monster)
            page.locator(f"img[title=\"挑战\"]:above(:has-text(\"附近NPC\"))").nth(monster_id).click()

            # 自动战斗
            if not auto_fight:
                auto_fight_on(page,  cycle=False)
                auto_fight = True

            while True:
                for tab in ("战斗日志", "地图场景"):
                    page.click(f"text={tab}")
                    page.wait_for_timeout(timeout=1000)
                if page.locator(f"span[class=\"scene-name\"]:has-text(\"{mission_monster}\")").count() == 0:
                    break
                else:
                    continue

            update_display_info(page, info_deque,  person_vars)
            if mission.count() == 0:
                DynLog.record_log(f"完成今日第{i + 1}次药灵任务")
                break
    DynLog.record_log("任务完成，请手动退出")


def mission_xiangyao(page: Page, user_config,  person_vars: UserVars):
    start_city = "林中栈道"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    for i in range(3):
        if page.url.endswith('login'):
            login(page, user_config)
        DynLog.record_log("开始做降妖任务")
        update_display_info(page, info_deque, person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        CityMap.move_to_map(page, start_city)

        DynLog.record_log("接取降妖任务")
        page.wait_for_selector("button:has-text(\"凌中天\")", timeout=3000)
        for tab in ("战斗日志", "地图场景"):
            page.click(f"text={tab}")
            page.wait_for_timeout(timeout=500)

        if page.locator("a:has-text(\"X\")").count() == 0:
            page.click("text=需要密令")
            page.wait_for_timeout(timeout=300)
            page.click("button:has-text(\"创建队伍\")")
            page.wait_for_selector("a:has-text(\"X\")", timeout=1000)
        while (person := page.locator("button:has-text(\"凌中天\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[降妖]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    DynLog.record_log("今日任务已做完")
                    return
                page.wait_for_timeout(timeout=1000)
            else:
                DynLog.record_log("任务对话框没弹出来", error=True)
                continue
            page.locator("i[class=\"el-icon-refresh\"]").click()
            page.wait_for_timeout(timeout=500)
            if page.locator("text=-降妖").count() == 1:
                DynLog.record_log("接到任务")
                break
            else:
                continue
        else:
            DynLog.record_log("未能正确初始化任务位置", error=True)
            continue
        mission = page.locator("text=-降妖")
        mission.hover()
        page.wait_for_selector("span[class=\"task-brief\"]:has-text(\"地区击败\")", timeout=2000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(r".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        # 这里应该是等待地图
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        for j in range(10):
            for p in CityMap.neighbor_city(mission_city):
                CityMap.move_to_map(page, p)
                for tab in ("战斗日志", "地图场景"):
                    page.click(f"text={tab}")
                    page.wait_for_timeout(timeout=1000)
                monster_list = [s.strip() for s in
                                page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
                if mission_monster in monster_list:
                    mission_city = p
                    break
                else:
                    continue
            # 战斗
            while True:
                for tab in ("战斗日志", "地图场景"):
                    page.click(f"text={tab}")
                    page.wait_for_timeout(timeout=1000)
                monster_list = [s.strip() for s in
                                page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
                monster_id = monster_list.index(mission_monster)
                page.locator(f"img[title=\"挑战\"]:above(:has-text(\"附近NPC\"))").nth(monster_id).click()

                # 自动战斗
                if not auto_fight:
                    auto_fight_on(page,  cycle=False)
                    auto_fight = True

                # 等待战斗结束
                # page.locator("text=当前第 1 轮").count()
                try:
                    if j < 9:
                        page.wait_for_selector("text=快去附近找找看!", timeout=20000)
                    else:
                        page.wait_for_selector("text=完成[降妖]", timeout=20000)
                except Exception:
                    DynLog.record_log("没打过")
                    continue

                update_display_info(page, info_deque, person_vars)
                for tab in ("战斗日志", "地图场景"):
                    page.click(f"text={tab}")
                    page.wait_for_timeout(timeout=500)

                page.locator("i[class=\"el-icon-refresh\"]").click()
                page.wait_for_timeout(timeout=500)
                DynLog.record_log(f"完成今日第{i + 1}次第{j + 1}轮降妖任务")
                break
            if (j == 9) and mission.count() == 0:
                DynLog.record_log(f"完成今日第{i + 1}次降妖任务")
    DynLog.record_log("任务完成，请手动退出")


def mission_xunbao(page: Page, user_config, person_vars: UserVars):
    start_city = "阳城"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    for i in range(10):
        if page.url.endswith('login'):
            login(page, user_config)
        DynLog.record_log("开始做寻宝任务")
        update_display_info(page, info_deque,  person_vars)
        page.click("text=地图场景")
        page.wait_for_timeout(timeout=300)
        CityMap.move_to_map(page, start_city)

        DynLog.record_log("接取寻宝任务")
        page.wait_for_selector("button:has-text(\"盗极生\")", timeout=3000)
        while (person := page.locator("button:has-text(\"盗极生\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"ant-drawer ant-drawer-bottom ant-drawer-open\"]").count() == 1:
                page.locator("text=接取[寻宝图]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    DynLog.record_log("今日任务已做完")
                    return
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
        page.wait_for_selector("span[class=\"task-brief\"]:has-text(\"地区击败\")", timeout=2000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(r".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        # 战斗
        while True:
            for tab in ("战斗日志", "地图场景"):
                page.click(f"text={tab}")
                page.wait_for_timeout(timeout=1000)
            monster_list = [s.strip() for s in page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
            monster_id = monster_list.index(mission_monster)
            page.locator(f"img[title=\"挑战\"]:above(:has-text(\"附近NPC\"))").nth(monster_id).click()

            # 自动战斗
            if not auto_fight:
                auto_fight_on(page, cycle=False)
                auto_fight = True

            # 等待战斗结束
            while True:
                for tab in ("战斗日志", "地图场景"):
                    page.click(f"text={tab}")
                    page.wait_for_timeout(timeout=1000)
                if page.locator(f"span[class=\"scene-name\"]:has-text(\"{mission_monster}\")").count() == 0:
                    break
                else:
                    continue

            update_display_info(page, info_deque, person_vars)
            mission.hover()
            page.wait_for_selector("a[class=\"tb\"]:has-text(\"完成\")", timeout=2000)
            page.locator("a[class=\"tb\"]:has-text(\"完成\")").click()
            page.wait_for_timeout(timeout=500)
            if mission.count() == 0:
                DynLog.record_log(f"完成今日第{i + 1}次寻宝任务")
                break
    DynLog.record_log("任务完成，请手动退出")


def fight(page: Page, fight_config: dict, person_vars: UserVars):
    DynLog.record_log("正在开启自动战斗")
    for tab in ("储物戒", "地图场景"):
        page.click(f"text={tab}")
        page.wait_for_timeout(timeout=1000)
    page.click("button:has-text(\"刷新列表\")")

    page.click("text=需要密令")
    page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"创建队伍\")")
    page.wait_for_selector("a:has-text(\"X\")", timeout=1000)
    person_vars.team_leader = "自己建队"
    monster_list = [s.strip() for s in page.locator(f"span[class=\"scene-name\"]:above(:has-text(\"附近NPC\"))").all_inner_texts()]
    monster_id = monster_list.index(fight_config.get("monster"))
    page.locator(f"img[title=\"挑战\"]:above(:has-text(\"附近NPC\"))").nth(monster_id).click()
    auto_fight_on(page, fight_config)
    DynLog.record_log("开始挂机")


def guaji(page: Page, user_config,  person_vars: UserVars):
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
                cond = estimate1['hm'] > 2e2
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
