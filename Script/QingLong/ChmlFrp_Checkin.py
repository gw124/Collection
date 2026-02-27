#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cron: 10 9 * * *
new Env('ChmlFrp自动签到');

# =================================================================
# 📋 依赖安装说明 (必看!)
# 
# 脚本依赖第三方库 `cloudscraper` 来绕过 Cloudflare 验证。
# 请在青龙面板 -> [依赖管理] -> [Python3] 中添加以下依赖：
# 
# 1. requests
# 2. cloudscraper
# 
# (安装失败尝试：安装时如果报错，尝试重启面板或在 Linux 依赖中添加 gcc, python3-dev)
# =================================================================

# =================================================================
# ⚙️ 环境变量配置 (Environment Variables)
#
# 变量名称: ACCOUNTS_JSON
# 变量值: JSON 数组字符串
# 示例: [{"username": "账号1", "password": "密码1"}, {"username": "账号2", "password": "密码2"}]
# =================================================================
"""

import os
import json
import time
import random
import sys

# 尝试导入 cloudscraper，如果没有安装则报错提示
try:
    import cloudscraper
except ImportError:
    print("❌ 错误：未安装 cloudscraper 依赖！")
    print("请在青龙面板 -> 依赖管理 -> Python3 中添加：cloudscraper")
    sys.exit(1)

# 尝试导入青龙通知
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"【通知预览】\n标题：{title}\n内容：{content}")

# ================= 配置与工具 =================

ACCOUNTS_ENV = os.environ.get('ACCOUNTS_JSON')
MSG_LIST = []

def log(info):
    """日志记录"""
    print(info)
    MSG_LIST.append(info)

def mask_account(index, username):
    """账号脱敏"""
    if not username: return f"账号{index+1}"
    if len(username) > 4:
        return f"{username[:2]}***{username[-2:]}"
    return f"账号{index+1}"

def create_scraper():
    """创建抗指纹的浏览器Session"""
    # 模拟 Windows Chrome 桌面版，这是目前过 CF 最稳的配置
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def run_signin(index, username, password):
    label = mask_account(index, username)
    print(f"\n👤 [{label}] 开始处理...")

    scraper = create_scraper()
    max_retries = 5  # 最大重试次数
    
    # --- 1. 登录 (带重试) ---
    token = None
    for attempt in range(max_retries):
        try:
            # 登录接口
            login_url = "https://cf-v2.uapis.cn/login"
            login_payload = {"username": username, "password": password}
            
            res = scraper.post(login_url, json=login_payload, timeout=20)
            
            # 检测 Cloudflare 拦截 (5xx 错误)
            if res.status_code in [520, 522, 525, 503]:
                raise Exception(f"CF拦截(Code:{res.status_code})")

            # 检测 WAF 拦截 (返回 HTML 而不是 JSON)
            try:
                data = res.json()
            except:
                raise Exception(f"响应非JSON(Code:{res.status_code})")

            # 业务逻辑判断
            if data.get("code") == 200:
                token = data["data"]["usertoken"]
                scraper.headers.update({"Authorization": f"Bearer {token}"})
                # print(f"    ✅ 登录成功 (第{attempt+1}次尝试)")
                break # 成功，跳出循环
            else:
                log(f"❌ {label}: 登录失败 - {data.get('msg')}")
                return # 账号密码错误，不重试

        except Exception as e:
            print(f"    ⚠️ 登录尝试 {attempt+1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                wait = random.uniform(3, 8)
                time.sleep(wait)
            else:
                log(f"❌ {label}: 登录最终失败 (网络/WAF拦截)")
                return

    # 随机延迟，防止被判定为脚本连击
    time.sleep(random.uniform(2, 5))

    # --- 2. 签到 (带重试) ---
    # 极验参数留空，依赖 IP 白名单或 cloudscraper 的自动处理
    sign_payload = {
        "lot_number": "", "captcha_output": "", "pass_token": "", 
        "gen_time": str(int(time.time()))
    }
    
    for attempt in range(max_retries):
        try:
            res = scraper.post("https://cf-v2.uapis.cn/qiandao", json=sign_payload, timeout=20)
            
            if res.status_code in [520, 522, 525]:
                raise Exception(f"CF拦截(Code:{res.status_code})")

            try:
                data = res.json()
            except:
                raise Exception(f"响应非JSON(Code:{res.status_code})")

            code = data.get("code")
            msg = data.get("msg")

            if code == 200:
                # 提取积分
                import re
                points = re.search(r"获得(\d+)", str(msg))
                added = points.group(1) if points else "?"
                log(f"✅ {label}: 签到成功 (积分+{added})")
                return
            elif code == 409:
                log(f"🔁 {label}: 今日已签过")
                return
            else:
                log(f"❌ {label}: 签到失败 - {msg} (Code:{code})")
                return

        except Exception as e:
            print(f"    ⚠️ 签到尝试 {attempt+1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                wait = random.uniform(3, 8)
                time.sleep(wait)
            else:
                log(f"❌ {label}: 签到最终失败")

def main():
    if not ACCOUNTS_ENV:
        print("⛔️ 未找到环境变量 ACCOUNTS_JSON，请配置后再运行。")
        return

    try:
        accounts = json.loads(ACCOUNTS_ENV)
    except json.JSONDecodeError:
        print("⛔️ 环境变量格式错误，请检查 JSON。")
        return

    print("--- 开始 ChmlFrp 签到 (Cloudscraper版) ---")
    
    for i, acc in enumerate(accounts):
        run_signin(i, acc.get('username'), acc.get('password'))
        # 账号间延迟
        if i < len(accounts) - 1:
            time.sleep(random.uniform(3, 6))

    print("-" * 30)
    if MSG_LIST:
        send("ChmlFrp 签到结果", "\n".join(MSG_LIST))

if __name__ == "__main__":
    main()
