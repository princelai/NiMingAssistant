import networkx as nx
from playwright.sync_api import Page

from display import DynLog


class CityMap:
    g = nx.read_gml('map_luofan.gml')

    @classmethod
    def neighbor_city(cls, center) -> list:
        return [center] + list(cls.g.neighbors(center))

    @classmethod
    def move_to_map(cls, page: Page, target_map: str) -> None:
        curr_map = page.locator("text=当前地图").inner_text()
        curr_map = curr_map.split(":")[1].strip()
        if curr_map != target_map:
            DynLog.record_log(f"正在寻路去往{target_map}")
            walk_path = nx.shortest_path(cls.g, curr_map, target_map)[1:]
            for p in walk_path:
                near_city = page.locator("div[class=\"can-move-map\"] > span")
                for i in range(near_city.count()):
                    if near_city.nth(i).inner_text() == p:
                        near_city.nth(i).click()
                        break

                DynLog.record_log(f"路过{p}")
                page.wait_for_selector(f"text=\"当前地图:{p}\"", timeout=10000)
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
