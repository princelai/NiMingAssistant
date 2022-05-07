from random import choices

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

    new_c['fight'].update({"material": c.get('fight', {}).get("material")})
    new_c['fight'].update({"captain": c.get('fight', {}).get("captain")})
    new_c['fight'].update({"fallback": c.get('fight', {}).get("fallback")})
    new_c['mission'].update({"id": c.get('mission', {}).get("id")})
    return new_c


def refresh_direct(page: Page):
    while True:
        try:
            with page.expect_navigation(url="https://nimingxx.com/login"):
                page.reload(timeout=5000)
        except Exception:
            DynLog.record_log("页面重载失败，继续重试", error=True)
            continue
        else:
            DynLog.record_log("页面重载成功")
            break


def check_in(page):
    page.locator("text=当前活动").click()
    page.wait_for_timeout(timeout=300)
    if page.locator("button:has-text(\"日日签\")").count() == 1:
        page.click("button:has-text(\"日日签\")")
        page.wait_for_timeout(timeout=300)
    page.click("button:has-text(\"领取维护补偿\")")
    page.wait_for_timeout(timeout=300)
    page.keyboard.press(key='Escape')


def auto_fight(page, fight_conf):
    skill_name = fight_conf.get("skill")
    page.click("div[data-name=\"tab-bat\"]")
    page.wait_for_selector("text=普通攻击", timeout=10000)
    page.click("text=普通攻击")
    page.wait_for_timeout(timeout=300)
    page.click(f"text={skill_name}")
    page.wait_for_timeout(timeout=300)
    page.locator("text=手动").last.click()
    page.locator("text=开启循环").last.click()
    page.wait_for_timeout(timeout=300)
    DynLog.record_log("开启自动战斗成功")


def disable_animation(page):
    page.click("svg[class=\"svg-icon icon-setting\"]")
    page.wait_for_timeout(timeout=500)
    page.uncheck("text=自动跳转战斗")
    page.wait_for_timeout(timeout=300)
    page.uncheck("text=播放战斗动画")
    page.wait_for_timeout(timeout=300)

    page.locator("button:has-text(\"保存\")").last.click()
    page.wait_for_selector("text=配置已生效", timeout=2000)
    page.keyboard.press(key='Escape')
    page.wait_for_timeout(timeout=300)


def login(page: Page, conf: dict):
    DynLog.record_log("正在自动登录")
    while True:
        try:
            page.reload()
            page.wait_for_selector("input[placeholder=\"密码\"]", timeout=10000)
            page.fill("input[placeholder=\"用户名\"]", conf.get("login").get("username"))
            page.wait_for_timeout(timeout=300)
            page.fill("input[placeholder=\"密码\"]", conf.get("login").get("password"))
            page.wait_for_timeout(timeout=300)

            with page.expect_navigation(url="https://nimingxx.com/home/index", timeout=6000):
                page.click("button[type=\"button\"]")
            page.wait_for_selector("text=当前任务", timeout=4000)
            break
        except Exception:
            DynLog.record_log("连接失败", error=True)
            page.wait_for_timeout(timeout=10000)
            continue
    DynLog.record_log("登录成功")

    DynLog.record_log("正在关闭耗费资源的配置")
    # 省流
    page.locator("text=开启省流").nth(1).click()
    page.wait_for_timeout(timeout=300)

    disable_animation(page)
    auto_fight(page, conf.get('fight'))
    check_in(page)
