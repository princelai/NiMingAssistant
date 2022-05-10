import re
from collections import defaultdict, deque
from functools import partial
from typing import Optional

from playwright.sync_api import Page, TimeoutError

from display import DynLog
from info import update_display_info
from login import login
from map import CityMap
from fight import auto_fight, get_monster_list, create_team


class YaoLing:
    start_city = "丹城"
    info_deque = defaultdict(partial(deque, maxlen=128))

    @classmethod
    def mission_take(cls, page: Page) -> Optional[bool]:
        CityMap.move_to_map(page, cls.start_city)

        DynLog.record_log("接取药灵任务")
        page.wait_for_selector("div[class=\"npc-d\"]:has-text(\"旭日药师\")", timeout=3000)
        while (person := page.locator("div[class=\"npc-d\"]:has-text(\"旭日药师\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"n-card__content\"] >> div[role=\"separator\"]").count() == 1:
                page.locator("text=接取[采药]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    #
                    DynLog.record_log("今日任务已做完")
                    return None
                page.wait_for_timeout(timeout=500)
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
        return True

    @classmethod
    def mission_do(cls, page: Page, i):
        mission = page.locator("text=-寻找药灵")
        mission.hover()
        page.wait_for_selector("text=地区击败", timeout=2000)
        task_info = page.locator("div[class=\"task-info\"]")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", task_info.inner_text())
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=500)
        page.hover("text=累计奖励")
        page.wait_for_timeout(timeout=500)
        page.click("div[id=\"tab-scene-tab\"]")
        page.wait_for_timeout(timeout=500)
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        DynLog.record_log("任务传送成功")
        # 战斗
        while True:
            battle_icon, monster_list = get_monster_list(page)
            monster_id = monster_list.index(mission_monster)
            battle_icon[monster_id].click()

            try:
                page.wait_for_selector("text=完成任务", timeout=30000)
            except TimeoutError:
                continue
            else:
                page.click("div[id=\"tab-scene-tab\"]")
                page.wait_for_timeout(timeout=500)

            battle_div = page.locator(f"div[class=\"n-scrollbar-content\"]:below(:has-text(\"附近兽群\")):right-of(:has-text(\"附近队伍\"))")
            if battle_div.locator(f"text={mission_monster}").count() != 0:
                continue
            update_display_info(page, cls.info_deque)
            DynLog.record_log(f"完成今日第{i + 1}次药灵任务")
            break

    @classmethod
    def run(cls, page: Page, user_config: dict):
        for i in range(10):
            if page.url.endswith('login'):
                login(page, user_config)
                create_team(page)
                auto_fight(page, user_config.get("fight"), False)
            DynLog.record_log("开始做药灵任务")
            update_display_info(page, cls.info_deque)
            page.click("div[id=\"tab-scene-tab\"]")
            page.wait_for_timeout(timeout=500)

            if page.locator("text=-寻找药灵").count() == 0:
                success = cls.mission_take(page)
                if success is False:
                    continue
                elif success is None:
                    break
                cls.mission_do(page, i)
            else:
                cls.mission_do(page, i)
        DynLog.record_log("任务完成，请手动退出")


class XiangYao:
    start_city = "林中栈道"
    info_deque = defaultdict(partial(deque, maxlen=128))

    @classmethod
    def mission_take(cls, page: Page):
        CityMap.move_to_map(page, cls.start_city)

        DynLog.record_log("接取降妖任务")
        page.wait_for_selector("div[class=\"npc-d\"]:has-text(\"凌中天\")", timeout=3000)
        while (person := page.locator("div[class=\"npc-d\"]:has-text(\"凌中天\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"n-card__content\"] >> div[role=\"separator\"]").count() == 1:
                page.locator("text=接取[降妖]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    DynLog.record_log("今日任务已做完")
                    return None
                page.wait_for_timeout(timeout=500)
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
            return False
        return True

    @classmethod
    def mission_do(cls, page: Page, i):
        mission = page.locator("text=-降妖")
        mission.hover()
        page.wait_for_selector("text=地区击败", timeout=2000)
        task_info = page.locator("div[class=\"task-info\"]")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", task_info.inner_text())
        mission_city = pattern_mission.group(1).strip()
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=500)
        page.hover("text=累计奖励")
        page.wait_for_timeout(timeout=500)
        page.click("div[id=\"tab-scene-tab\"]")
        page.wait_for_timeout(timeout=500)
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        DynLog.record_log("任务传送成功")
        for j in range(10):
            for p in CityMap.neighbor_city(mission_city):
                CityMap.move_to_map(page, p)
                battle_icon, monster_list = get_monster_list(page)
                if mission_monster in monster_list:
                    mission_city = p
                    DynLog.record_log(f"妖兽在{p}")
                    break
                else:
                    DynLog.record_log(f"妖兽不在{p}，继续寻找", error=True)
                    continue
            else:
                return False
            # 战斗
            while True:
                monster_id = monster_list.index(mission_monster)
                battle_icon[monster_id].click()

                try:
                    if j < 9:
                        page.wait_for_selector("text=快去附近找找看!", timeout=45000)
                    else:
                        page.wait_for_selector("text=完成[降妖]", timeout=45000)
                except TimeoutError:
                    DynLog.record_log("没打过")
                    continue
                else:
                    page.click("div[id=\"tab-scene-tab\"]")
                    page.wait_for_timeout(timeout=500)

                battle_div = page.locator(f"div[class=\"n-scrollbar-content\"]:below(:has-text(\"附近兽群\")):right-of(:has-text(\"附近队伍\"))")
                if battle_div.locator(f"text={mission_monster}").count() != 0:
                    continue
                update_display_info(page, cls.info_deque)
                DynLog.record_log(f"完成今日第{i + 1}次第{j + 1}轮降妖任务")
                break

    @classmethod
    def run(cls, page: Page, user_config: dict):
        for i in range(3):
            if page.url.endswith('login'):
                login(page, user_config)
                create_team(page)
                auto_fight(page, user_config.get("fight"), False)
            DynLog.record_log("开始做降妖任务")
            update_display_info(page, cls.info_deque)
            page.click("div[id=\"tab-scene-tab\"]")
            page.wait_for_timeout(timeout=500)

            if page.locator("text=-降妖").count() == 0:
                success = cls.mission_take(page)
                if success is False:
                    continue
                elif success is None:
                    break
                cls.mission_do(page, i)
            else:
                cls.mission_do(page, i)
        DynLog.record_log("任务完成，请手动退出")


class XunBao:
    start_city = "阳城"
    info_deque = defaultdict(partial(deque, maxlen=128))

    @classmethod
    def mission_take(cls, page: Page) -> Optional[bool]:
        CityMap.move_to_map(page, cls.start_city)

        DynLog.record_log("接取寻宝任务")
        page.wait_for_selector("div[class=\"npc-d\"]:has-text(\"盗极生\")", timeout=3000)
        while (person := page.locator("div[class=\"npc-d\"]:has-text(\"盗极生\")")).count() == 1:
            person.click()
            page.wait_for_timeout(timeout=500)
            if page.locator("div[class=\"n-card__content\"] >> div[role=\"separator\"]").count() == 1:
                page.locator("text=接取[寻宝图]任务").click()
                page.wait_for_timeout(timeout=500)
                if page.locator("text=领取上限").count() == 1:
                    DynLog.record_log("今日任务已做完")
                    return None
                page.wait_for_timeout(timeout=500)
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
            return False
        return True

    @classmethod
    def mission_do(cls, page: Page, i):
        mission = page.locator("text=-寻宝")
        mission.hover()
        page.wait_for_selector("text=地区击败", timeout=2000)
        task_info = page.locator("div[class=\"task-info\"]")
        pattern_mission = re.search(".+【(.+)】.*地区击败(.+)", task_info.inner_text())
        mission_monster = pattern_mission.group(2).strip()

        mission.click()
        DynLog.record_log("飞过去")
        page.wait_for_timeout(timeout=500)
        page.hover("text=累计奖励")
        page.wait_for_timeout(timeout=500)
        page.click("div[id=\"tab-scene-tab\"]")
        page.wait_for_timeout(timeout=500)
        page.wait_for_selector(f"text={mission_monster}", timeout=3000)
        DynLog.record_log("任务传送成功")
        # 战斗
        while True:
            battle_icon, monster_list = get_monster_list(page)
            monster_id = monster_list.index(mission_monster)
            battle_icon[monster_id].click()

            try:
                page.wait_for_selector("text=完成任务", timeout=30000)
            except TimeoutError:
                continue
            else:
                page.click("div[id=\"tab-scene-tab\"]")
                page.wait_for_timeout(timeout=500)

            battle_div = page.locator(f"div[class=\"n-scrollbar-content\"]:below(:has-text(\"附近兽群\")):right-of(:has-text(\"附近队伍\"))")
            if battle_div.locator(f"text={mission_monster}").count() != 0:
                continue
            update_display_info(page, cls.info_deque)
            DynLog.record_log(f"完成今日第{i + 1}次寻宝任务")
            break

    @classmethod
    def run(cls, page: Page, user_config: dict):
        for i in range(10):
            if page.url.endswith('login'):
                login(page, user_config)
                create_team(page)
                auto_fight(page, user_config.get("fight"), False)
            DynLog.record_log("开始做寻宝任务")
            update_display_info(page, cls.info_deque)
            page.click("div[id=\"tab-scene-tab\"]")
            page.wait_for_timeout(timeout=1000)

            if page.locator("text=-寻宝").count() == 0:
                success = cls.mission_take(page)
                if success is False:
                    continue
                elif success is None:
                    break
                cls.mission_do(page, i)
            else:
                cls.mission_do(page, i)
        DynLog.record_log("任务完成，请手动退出")
