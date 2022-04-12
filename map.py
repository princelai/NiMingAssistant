from typing import Optional

import networkx as nx
import pandas as pd
from playwright.sync_api import Page

from display import DynLog


class CityMap:
    g = nx.read_gml('map_luofan.gml')
    df = pd.read_csv("material_map.csv")
    df.sort_values("等级", inplace=True)

    @classmethod
    def neighbor_city(cls, center) -> list:
        return [center] + list(cls.g.neighbors(center))

    @classmethod
    def move_to_map(cls, page: Page, target_map: str) -> None:
        page.wait_for_timeout(timeout=1000)
        curr_map = page.locator("text=当前地图").inner_text()
        curr_map = curr_map.split(":")[1].strip()
        if curr_map != target_map:
            DynLog.record_log(f"正在寻路去往{target_map}")
            walk_path = nx.shortest_path(cls.g, curr_map, target_map)[1:]
            for p in walk_path:
                near_city = page.locator("div[class=\"can-move-map\"] > span")
                for i in range(near_city.count()):
                    if near_city.nth(i).inner_text().strip() == p:
                        near_city.nth(i).click()
                        break

                DynLog.record_log(f"路过{p}")
                for _ in range(6):
                    near_city = page.locator("div[class=\"can-move-map\"] > span")
                    if set(cls.g.neighbors(p)) == set(near_city.all_inner_texts()):
                        break
                    else:
                        page.wait_for_timeout(timeout=500)
                        continue
            DynLog.record_log("已到达指定地图")

    @classmethod
    def map_navigate(cls, page: Page, fight_config: dict) -> Optional[str]:
        monster = None
        target_map = None
        if fight_config.get('material'):
            select = cls.df.loc[cls.df["掉落"] == fight_config.get('material')].tail(1)
            if select.empty:
                monster = None
                target_map = None
            else:
                monster = select["怪物名"].to_list()[0]
                target_map = select["地点"].to_list()[0]

        if not monster and fight_config.get('monster'):
            select = cls.df.loc[cls.df["怪物名"] == fight_config.get('monster')].tail(1)
            monster = select["怪物名"].to_list()[0]
            target_map = select["地点"].to_list()[0]
            if fight_config.get('monster') != monster:
                DynLog.record_log("配置的怪物和物品表中的怪物未匹配，请检查，本次以物品表为准", error=True)

        cls.move_to_map(page, target_map)
        return monster
