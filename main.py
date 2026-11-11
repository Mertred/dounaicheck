# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import os
import pickle
import random
import re
import sys
import time
import requests
import ddddocr
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 动态定位当前运行目录（兼容 .py 运行和打包后的 .exe 运行）
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
COOKIE_CACHE_FILE = os.path.join(BASE_DIR, "session_cookies.pkl")

BASE_URL = "https://dounai.pro"
LOGIN_PAGE = "/auth/login"
LOGIN_API = "/auth/login"
CAPTCHA_API = "/auth/captcha"
USER_PANEL = "/user/panel"
SIGN_API = "/user/checkin"

TIMEOUT = (10, 30)
COOKIE_EXPIRE_SECONDS = 24 * 3600


def load_config() -> tuple[str, str]:
    """读取 config.json，若不存在则自动生成模板"""
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {"email": "your_email@qq.com", "passwd": "your_password"}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=4, ensure_ascii=False)
        print(f"⚠️ 未检测到配置文件，已为您生成默认模板：{CONFIG_FILE}")
        print("请打开 config.json 填入正确的邮箱和密码后重新运行程序！")
        input("\n按回车键退出...")
        sys.exit(0)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        email = data.get("email", "").strip()
        passwd = data.get("passwd", "").strip()

        if not email or not passwd or "your_email" in email:
            print("⚠️ config.json 中的账号或密码未配置正确，请修改后重试！")
            input("\n按回车键退出...")
            sys.exit(0)

        return email, passwd
    except Exception as e:
        print(f"❌ 读取 config.json 失败: {e}")
        input("\n按回车键退出...")
        sys.exit(1)


# 初始化账号密码
USERNAME, PASSWORD = load_config()

ocr = ddddocr.DdddOcr(show_ad=False)
session = requests.Session()

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }
)

CN_NUM_MAP = {
    "零": "0",
    "一": "1",
    "壹": "1",
    "二": "2",
    "贰": "2",
    "两": "2",
    "三": "3",
    "叁": "3",
    "参": "3",
    "四": "4",
    "肆": "4",
    "五": "5",
    "伍": "5",
    "六": "6",
    "陆": "6",
    "七": "7",
    "柒": "7",
    "八": "8",
    "捌": "8",
    "九": "9",
    "玖": "9",
}

CN_OP_MAP = {
    "加": "+",
    "十": "+",
    "拾": "+",
    "减": "-",
    "乘": "*",
    "除": "/",
    "以": "",
}


def save_session_cookies():
    cache_data = {
        "saved_at": time.time(),
        "cookies": session.cookies.get_dict(),
    }
    try:
        with open(COOKIE_CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
        print("✅ Session Cookies 已缓存至本地")
    except Exception as e:
        print(f"⚠️ 保存 Session 失败: {e}")


def load_session_cookies() -> bool:
    if not os.path.exists(COOKIE_CACHE_FILE):
        return False
    try:
        with open(COOKIE_CACHE_FILE, "rb") as f:
            cache_data = pickle.load(f)

        saved_at = cache_data.get("saved_at", 0)
        if time.time() - saved_at > COOKIE_EXPIRE_SECONDS:
            print("🕒 本地 Session 已超时 24 小时")
            return False

        cookies = cache_data.get("cookies", {})
        session.cookies.update(cookies)
        print(
            f"🔄 读取本地 Session 成功（已保存 {int((time.time() - saved_at) / 3600)} 小时）"
        )
        return True
    except Exception as e:
        print(f"⚠️ 读取本地 Session 失败: {e}")
        return False


def is_session_valid() -> bool:
    try:
        resp = session.get(
            BASE_URL + USER_PANEL, timeout=TIMEOUT, allow_redirects=False
        )
        if resp.status_code == 200 and "/auth/login" not in resp.text:
            return True
    except Exception:
        pass
    return False


def calculate_expression(expr_str: str) -> str:
    clean = expr_str.strip()
    clean = re.sub(r"[=_\?ie言-]+$", "", clean).strip()

    for cn_op, sym in CN_OP_MAP.items():
        clean = clean.replace(cn_op, sym)

    for cn_char, num_str in CN_NUM_MAP.items():
        clean = clean.replace(cn_char, num_str)

    clean = clean.replace("x", "*").replace("X", "*").replace("×", "*")
    clean = clean.replace("t", "+").replace("T", "+")
    clean = clean.replace("÷", "/").replace(":", "/").replace("\\", "/")
    clean = (
        clean.replace("—", "-").replace("–", "-").replace("s", "-").replace("S", "-")
    )

    match = re.search(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", clean)
    if not match:
        raise ValueError(f"无法解析算式: 原文='{expr_str}', 清理后='{clean}'")

    num1 = int(match.group(1))
    op = match.group(2)
    num2 = int(match.group(3))

    if op == "+":
        return str(num1 + num2)
    elif op == "-":
        return str(num1 - num2)
    elif op == "*":
        return str(num1 * num2)
    elif op == "/":
        return str(num1 // num2) if num2 != 0 else "0"

    raise ValueError(f"未知运算符: {op}")


def get_captcha_code(
    captcha_type: str = "login", referer: str = BASE_URL + LOGIN_PAGE, max_retries=6
) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            if captcha_type == "checkin":
                url = (
                    f"{BASE_URL}{CAPTCHA_API}?type=checkin&_={int(time.time() * 1000)}"
                )
            else:
                url = f"{BASE_URL}{CAPTCHA_API}?t={int(time.time() * 1000)}"

            headers = {"Referer": referer}
            resp = session.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()

            data = resp.json()
            raw_content = data.get("svg") or data.get("img") or data.get("data") or ""
            match = re.search(r"base64,([A-Za-z0-9+/=]+)", raw_content)
            if not match:
                raise ValueError("未匹配到 Base64 图片数据")

            img_bytes = base64.b64decode(match.group(1))
            text = ocr.classification(img_bytes)
            print(f"[{captcha_type}] 验证码第 {attempt} 次 OCR 识别: '{text}'")

            result = calculate_expression(text)
            print(f"[{captcha_type}] 算式计算结果: {result}")
            return result

        except Exception as e:
            print(f"第 {attempt} 次解析失败 ({e})，正在自动换一张...")
            time.sleep(1.2)

    raise RuntimeError("连续多次验证码识别失败")


def login():
    print(f"当前登录账号: {USERNAME}")
    print("访问登录页面建立 Session...")
    session.get(BASE_URL + LOGIN_PAGE, timeout=TIMEOUT)
    time.sleep(random.uniform(1.5, 3.0))

    captcha_val = get_captcha_code(captcha_type="login", referer=BASE_URL + LOGIN_PAGE)
    time.sleep(random.uniform(2.0, 3.5))

    login_url = BASE_URL + LOGIN_API
    headers = {
        "Referer": BASE_URL + LOGIN_PAGE,
        "Origin": BASE_URL,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    payload = {
        "email": USERNAME,
        "passwd": PASSWORD,
        "captcha_code": captcha_val,
    }

    try:
        resp = session.post(login_url, data=payload, headers=headers, timeout=TIMEOUT)
        data = resp.json()
    except Exception as e:
        print("登录请求失败:", e)
        input("\n按回车键退出...")
        sys.exit(1)

    print("登录响应:", data)
    if data.get("ret") != 1:
        print(f"登录失败: {data.get('msg')}")
        input("\n按回车键退出...")
        sys.exit(1)

    print("登录成功！")
    save_session_cookies()


def extract_ticket(html: str) -> str:
    match = re.search(r'var\s+checkinTicket\s*=\s*["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)

    meta_match = re.search(
        r'<meta[^>]+name=["\']checkin-ticket["\'][^>]+content=["\']([^"\']+)["\']', html
    )
    if meta_match:
        return meta_match.group(1)
    return ""


def calc_checkin_token(ticket: str, code: str) -> str:
    raw_str = f"{ticket}_{code}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def sign():
    user_page = BASE_URL + USER_PANEL
    sign_api = BASE_URL + SIGN_API

    headers = {
        "Referer": user_page,
        "Origin": BASE_URL,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    print("访问用户面板刷新页面凭证...")
    resp_panel = session.get(user_page, timeout=TIMEOUT)

    panel_browse_delay = random.uniform(2.5, 4.5)
    print(f"模拟用户停留在面板页面 {panel_browse_delay:.1f} 秒...")
    time.sleep(panel_browse_delay)

    ticket = extract_ticket(resp_panel.text)
    if not ticket:
        print("❌ 未在用户面板中提取到 checkinTicket")
        return
    print(f"成功提取到 checkinTicket: {ticket[:25]}...")

    print("弹出签到框，正在获取验证码 (type=checkin)...")
    sign_captcha_val = get_captcha_code(captcha_type="checkin", referer=user_page)

    human_thinking_time = random.uniform(3.5, 6.0)
    print(f"模拟真人计算与输入延迟: {human_thinking_time:.2f} 秒...")
    time.sleep(human_thinking_time)

    checkin_token = calc_checkin_token(ticket, sign_captcha_val)
    print(f"已根据 ticket+code 计算 checkin_token: {checkin_token}")

    sign_payload = {
        "captcha_code": sign_captcha_val,
        "checkin_secret": "",
        "checkin_ticket": ticket,
        "checkin_token": checkin_token,
    }

    print("正在提交签到请求...")
    try:
        resp = session.post(
            sign_api,
            headers=headers,
            data=sign_payload,
            timeout=TIMEOUT,
            allow_redirects=False,
        )
        data = resp.json()
        print("签到响应:", data)
    except requests.RequestException as e:
        print("签到请求失败:", e)
    except Exception:
        print("签到返回非 JSON 数据:", resp.text[:500])


def main():
    print("==== 启动自动签到流程 ====")
    if load_session_cookies() and is_session_valid():
        print("✅ 复用本地有效的 Session，跳过登录步骤！")
    else:
        print("⚠️ 本地 Session 不存在或已失效，执行登录...")
        login()

    delay = random.uniform(3.0, 5.0)
    print(f"等待 {delay:.1f} 秒后发起签到...")
    time.sleep(delay)
    sign()

    print("\n==== 运行结束 ====")
    # 增加等待输入，防止直接闪退导致用户看不到日志
    input("按回车键退出窗口...")


if __name__ == "__main__":
    main()
