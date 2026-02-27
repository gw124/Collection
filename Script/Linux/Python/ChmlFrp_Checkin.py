# -*- coding: utf-8 -*-

# ==============================================================================
# 📋 环境准备与依赖安装 (必读!)
#
# 本脚本需要使用 `cloudscraper` 库来绕过 Cloudflare 的 5秒盾/WAF 拦截。
# 请在终端/命令行中执行以下命令安装依赖：
#
# pip install requests cloudscraper
#
# (如果提示 pip 命令不存在，尝试使用: python3 -m pip install requests cloudscraper)
# ==============================================================================

# ==============================================================================
# ⚙️ 账号配置区域 (直接修改这里)
#
# 格式: {"username": "你的账号", "password": "你的密码"}
# ==============================================================================
ACCOUNTS = [
    {"username": "你的账号1", "password": "密码1"},
    {"username": "你的账号2", "password": "密码2"},
    # {"username": "你的账号3", "password": "密码3"},  # 可以继续添加
]
# ==============================================================================

import time
import random
import sys

# 尝试导入 cloudscraper
try:
    import cloudscraper
except ImportError:
    print("❌ 错误: 未安装 cloudscraper 库!")
    print("请执行命令安装: pip install cloudscraper")
    sys.exit(1)

def mask_account(index, username):
    """账号脱敏显示"""
    if not username: return f"账号{index+1}"
    if len(username) > 4:
        return f"{username[:2]}***{username[-2:]}"
    return f"账号{index+1}"

def create_scraper():
    """创建一个模拟 Windows Chrome 的浏览器实例"""
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def run_signin(index, username, password):
    label = mask_account(index, username)
    print(f"\n[-] 开始处理: {label}")

    scraper = create_scraper()
    max_retries = 5  # 最大重试次数 (针对 525/520 错误)
    
    # --- 1. 登录 (带重试机制) ---
    token = None
    for attempt in range(max_retries):
        try:
            login_url = "https://cf-v2.uapis.cn/login"
            login_payload = {"username": username, "password": password}
            
            # 发送请求
            res = scraper.post(login_url, json=login_payload, timeout=20)
            
            # 检查 Cloudflare 网络层拦截
            if res.status_code in [520, 522, 525, 503]:
                raise Exception(f"Cloudflare 拦截 (状态码 {res.status_code})")

            # 检查响应是否为 JSON
            try:
                data = res.json()
            except:
                raise Exception(f"响应内容非 JSON (状态码 {res.status_code})")

            # 业务逻辑判断
            if data.get("code") == 200:
                token = data["data"]["usertoken"]
                scraper.headers.update({"Authorization": f"Bearer {token}"})
                print(f"[+] 登录成功 (第 {attempt+1} 次尝试)")
                break # 成功，跳出重试循环
            else:
                print(f"[x] 登录失败: {data.get('msg')}")
                return # 账号密码错误，不需要重试

        except Exception as e:
            print(f"    [!] 第 {attempt+1} 次登录尝试失败: {e}")
            if attempt < max_retries - 1:
                wait = random.uniform(3, 8)
                print(f"        -> 等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)
            else:
                print(f"[x] {label} 登录最终失败 (网络/WAF拦截)")
                return

    # 随机延迟，防止连击被封
    time.sleep(random.uniform(2, 5))

    # --- 2. 签到 (带重试机制) ---
    sign_url = "https://cf-v2.uapis.cn/qiandao"
    # 极验参数留空，依赖 cloudscraper 的指纹绕过
    sign_payload = {
        "lot_number": "", 
        "captcha_output": "", 
        "pass_token": "", 
        "gen_time": str(int(time.time()))
    }

    for attempt in range(max_retries):
        try:
            res = scraper.post(sign_url, json=sign_payload, timeout=20)
            
            if res.status_code in [520, 522, 525]:
                raise Exception(f"Cloudflare 拦截 (状态码 {res.status_code})")

            try:
                data = res.json()
            except:
                raise Exception(f"响应非 JSON (状态码 {res.status_code})")

            code = data.get("code")
            msg = data.get("msg")

            if code == 200:
                print(f"[√] 签到成功! 消息: {msg}")
                return
            elif code == 409:
                print(f"[-] 今日已签到 (提示: {msg})")
                return
            else:
                print(f"[x] 签到失败: {msg} (Code: {code})")
                return

        except Exception as e:
            print(f"    [!] 第 {attempt+1} 次签到尝试失败: {e}")
            if attempt < max_retries - 1:
                wait = random.uniform(3, 8)
                print(f"        -> 等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)
            else:
                print(f"[x] {label} 签到最终失败")

if __name__ == "__main__":
    print("--- 开始 ChmlFrp 本地签到 (Cloudscraper版) ---")
    
    if not ACCOUNTS:
        print("请先在脚本顶部的 ACCOUNTS 列表中填入账号密码！")
    else:
        for i, acc in enumerate(ACCOUNTS):
            run_signin(i, acc.get('username'), acc.get('password'))
            # 账号间延迟
            if i < len(ACCOUNTS) - 1:
                wait_time = random.uniform(3, 6)
                print(f"⏳ 等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)

    print("-" * 30)
    print("任务结束")
