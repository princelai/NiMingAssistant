from math import ceil

import networkx as nx
from playwright.sync_api import Page

from display import DynLog


class CityMap:
    g = nx.read_gml('map_luofan.gml')

    @classmethod
    def neighbor_city(cls, center):
        return list(cls.g.neighbors(center))

    @classmethod
    def move_to_map(cls, page: Page, target_map: str) -> None:
        curr_map = page.locator("text=当前地图").inner_text()
        curr_map = curr_map.split(":")[1].strip()
        map_step = 20
        if curr_map != target_map:
            DynLog.record_log(f"正在寻路去往{target_map}")
            walk_path = nx.shortest_path(cls.g, curr_map, target_map)[1:]
            for p in walk_path:
                city_loc_idx = 0
                svg_frame_text = page.locator("svg[class=\"svg\"] >> text")
                if (city_loc := svg_frame_text.locator(f"text={p}")).count() == 1:
                    x = int(city_loc.get_attribute('x'))
                    y = int(city_loc.get_attribute('y'))
                else:
                    # 处理类似阳城和阳城驿站这种
                    city_loc_txt = city_loc.all_text_contents()
                    city_loc_txt = list(map(lambda z: z.strip(), city_loc_txt))
                    city_loc_idx = city_loc_txt.index(p)
                    x = int(city_loc.nth(city_loc_idx).get_attribute('x'))
                    y = int(city_loc.nth(city_loc_idx).get_attribute('y'))

                if x <= (x_min := 40):
                    move_left = page.locator("div[class=\"move-d move-left\"]")
                    for _ in range(ceil(abs((x - x_min) / map_step))):
                        move_left.click()
                        page.wait_for_timeout(timeout=300)

                if x >= (x_max := 400):
                    move_right = page.locator("div[class=\"move-d move-right\"]")
                    for _ in range(ceil(abs((x - x_max) / map_step))):
                        move_right.click()
                        page.wait_for_timeout(timeout=300)

                if y <= (y_min := 60):
                    move_top = page.locator("div[class=\"move-d move-top\"]")
                    for _ in range(ceil(abs((y - y_min) / map_step))):
                        move_top.click()
                        page.wait_for_timeout(timeout=300)

                if y >= (y_max := 230):
                    move_bottom = page.locator("div[class=\"move-d move-bottom\"]")
                    for _ in range(ceil(abs((y - y_max) / map_step))):
                        move_bottom.click()
                        page.wait_for_timeout(timeout=300)

                svg_frame_text.locator(f"text={p}").nth(city_loc_idx).click()
                DynLog.record_log(f"路过{p}")
                page.wait_for_selector(f"text=\"当前地图:{p}\"", timeout=3000)
            DynLog.record_log("已到达指定地图")

    @classmethod
    def map_navigate(cls, page: Page, fight_config: dict):
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
        cls.move_to_map(page, target_map)
