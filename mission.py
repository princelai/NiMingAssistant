import re
from collections import defaultdict, deque
from functools import partial

from playwright.sync_api import Page

from display import DynLog
from fight import auto_fight_on
from info import UserVars, update_display_info
from login import login, switch_tab_to
from map import CityMap


class YaoLing:
    start_city = "丹城"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    person_vars = UserVars()

    @classmethod
    def mission_jie(cls, page: Page):
        CityMap.move_to_map(page, cls.start_city)

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
            return False

    @classmethod
    def mission_zuo(cls, page: Page, i):
        mission = page.locator("text=-寻找药灵")
        mission.hover()
        page.wait_for_selector("span[class=\"task-brief\"]:has-text(\"地区击败\")", timeout=2000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        switch_tab_to(page, tab="地图场景", num=2)
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        DynLog.record_log("任务传送成功")
        # 战斗
        while True:
            switch_tab_to(page, tab="地图场景", num=2, timeout=1000)
            battle_div = page.locator(f"div[class=\"el-row\"]:above(:has-text(\"附近NPC\")):right-of(:has-text(\"附近灵兽\"))")
            monster_list = [s.strip() for s in battle_div.locator("span[class=\"scene-name\"]").all_inner_texts()]
            monster_id = monster_list.index(mission_monster)
            battle_div.locator("img[title=\"挑战\"]").nth(monster_id).click()

            # 自动战斗
            if not cls.auto_fight:
                auto_fight_on(page, cycle=False)
                cls.auto_fight = True

            # TODO(kevin): 更智能的判断结束
            while True:
                switch_tab_to(page, tab="地图场景", num=2, timeout=1000)
                if page.locator(f"span[class=\"scene-name\"]:has-text(\"{mission_monster}\")").count() == 0:
                    break
                else:
                    continue

            update_display_info(page, cls.info_deque, cls.person_vars)
            if mission.count() == 0:
                DynLog.record_log(f"完成今日第{i + 1}次药灵任务")
                break

    @classmethod
    def run(cls, page: Page, user_config: dict):

        for i in range(10):
            if page.url.endswith('login'):
                login(page, user_config)
            DynLog.record_log("开始做药灵任务")
            update_display_info(page, cls.info_deque, cls.person_vars)
            page.click("text=地图场景")
            page.wait_for_timeout(timeout=300)

            if page.locator("text=-寻找药灵").count() == 0:
                success = cls.mission_jie(page)
                if success is False:
                    continue
                cls.mission_zuo(page, i)
            else:
                cls.mission_zuo(page, i)
        DynLog.record_log("任务完成，请手动退出")


class XiangYao:
    start_city = "林中栈道"
    auto_fight = False
    info_deque = defaultdict(partial(deque, maxlen=128))
    person_vars = UserVars()

    @classmethod
    def mission_jie(cls, page: Page):
        CityMap.move_to_map(page, cls.start_city)

        DynLog.record_log("接取降妖任务")
        page.wait_for_selector("button:has-text(\"凌中天\")", timeout=3000)
        switch_tab_to(page, tab="地图场景", num=2)

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
            return False

    @classmethod
    def mission_zuo(cls, page: Page, i):
        mission = page.locator("text=-降妖")
        mission.hover()
        page.wait_for_selector("span[class=\"task-brief\"]:has-text(\"地区击败\")", timeout=2000)
        mission_detail = page.locator("span[class=\"task-brief\"]:has-text(\"地区击败\")")
        pattern_mission = re.search(r".+【(.+)】.*地区击败(.+)", mission_detail.inner_text())
        mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        switch_tab_to(page, tab="地图场景", num=2)
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        DynLog.record_log("任务传送成功")
        for j in range(10):
            for p in CityMap.neighbor_city(mission_city):
                CityMap.move_to_map(page, p)
                switch_tab_to(page, tab="地图场景", num=2)
                battle_div = page.locator(f"div[class=\"el-row\"]:above(:has-text(\"附近NPC\")):right-of(:has-text(\"附近灵兽\"))")
                monster_list = [s.strip() for s in battle_div.locator("span[class=\"scene-name\"]").all_inner_texts()]
                if mission_monster in monster_list:
                    mission_city = p
                    DynLog.record_log(f"妖兽在{p}")
                    break
                else:
                    DynLog.record_log(f"妖兽不在{p}，继续寻找", error=True)
                    continue
            # 战斗
            while True:
                switch_tab_to(page, tab="地图场景", num=2, timeout=1000)
                DynLog.record_log("准备和妖兽决战")
                battle_div = page.locator(f"div[class=\"el-row\"]:above(:has-text(\"附近NPC\")):right-of(:has-text(\"附近灵兽\"))")
                monster_list = [s.strip() for s in battle_div.locator("span[class=\"scene-name\"]").all_inner_texts()]
                monster_id = monster_list.index(mission_monster)
                battle_div.locator("img[title=\"挑战\"]").nth(monster_id).click()

                # 自动战斗
                if not cls.auto_fight:
                    auto_fight_on(page, cycle=False)
                    cls.auto_fight = True

                try:
                    if j < 9:
                        page.wait_for_selector("text=快去附近找找看!", timeout=40000)
                    else:
                        page.wait_for_selector("text=完成[降妖]", timeout=40000)
                except Exception:
                    DynLog.record_log("没打过")
                    continue

                update_display_info(page, cls.info_deque, cls.person_vars)
                switch_tab_to(page, tab="地图场景", num=2)

                page.locator("i[class=\"el-icon-refresh\"]").click()
                page.wait_for_timeout(timeout=500)
                DynLog.record_log(f"完成今日第{i + 1}次第{j + 1}轮降妖任务")
                break
            if (j == 9) and mission.count() == 0:
                DynLog.record_log(f"完成今日第{i + 1}次降妖任务")

    @classmethod
    def run(cls, page: Page, user_config: dict):
        for i in range(3):
            if page.url.endswith('login'):
                login(page, user_config)
            DynLog.record_log("开始做降妖任务")
            update_display_info(page, cls.info_deque, cls.person_vars)
            page.click("text=地图场景")
            page.wait_for_timeout(timeout=300)

            if page.locator("text=-降妖").count() == 0:
                success = cls.mission_jie(page)
                if success is False:
                    continue
                cls.mission_zuo(page, i)
            else:
                cls.mission_zuo(page, i)
        DynLog.record_log("任务完成，请手动退出")
