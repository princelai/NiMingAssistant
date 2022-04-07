from playwright.sync_api import Page

from display import DynLog


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

    new_c['fight'].update({"captain": c.get('fight', {}).get("captain")})
    new_c['fight'].update({"fallback": c.get('fight', {}).get("fallback")})
    new_c['mission'].update({"id": c.get('mission', {}).get("id")})
    return new_c


def refresh_direct(page: Page):
    while True:
        try:
            with page.expect_navigation(url="https://game.nimingxx.com/login"):
                page.reload(timeout=5000)
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
            if page.locator("button:has-text(\"日日签\")").count() == 1:
                page.locator("button:has-text(\"日日签\")").click()
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
    page.wait_for_timeout(timeout=500)
    for tab in ("技能", "炼丹", "合成", "技能"):
        page.click(f"div[role=\"tab\"]:text(\"{tab}\")")
        page.wait_for_timeout(timeout=300)
    page.locator("input[type=\"text\"]:below(:has-text(\"已领悟技能\"))").click()
    page.wait_for_timeout(timeout=300)
    page.locator(f'div[class=\"el-scrollbar\"] div ul li:has-text(\"{conf.get("fight").get("skill")}\")').click()
    page.wait_for_timeout(timeout=300)
    page.locator("button[type=button]:has-text(\"保存\")").click()
    page.wait_for_timeout(timeout=300)
    page.click("text=地图场景")
    page.wait_for_timeout(timeout=300)
