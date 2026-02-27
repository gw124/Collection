#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cron: 0 9 * * *
new Env('ChmlFrp自动签到');

# =================================================================
# 环境变量配置说明 (Environment Variables):
#
# 变量名称: ACCOUNTS_JSON
# 变量值格式: JSON 数组字符串 (注意必须是英文双引号)
#
# 示例:
# [{"username": "你的账号1", "password": "密码1"}, {"username": "你的账号2", "password": "密码2"}]
#
# 在青龙面板 -> 环境变量 -> 新建变量 中添加即可
# =================================================================
"""

import requests
import json
import os
import time
import random
import re

# 尝试导入青龙的通知模块
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"【通知预览】\n标题：{title}\n内容：{content}")

# ================= 核心逻辑 =================

# 获取环境变量
ACCOUNTS_ENV = os.environ.get('ACCOUNTS_JSON')

# 伪装成 macOS Chrome，防止被 WAF 拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://panel.chmlfrp.net",
    "Referer": "https://panel.chmlfrp.net/"
}

# 用于汇总推送消息
msg_list = []

def log(info):
    """打印日志并添加到推送列表"""
    print(info)
    msg_list.append(info)

def mask_account(username):
    """简单的脱敏，显示前2位和后2位"""
    if not username:
        return "未知账号"
    if len(username) > 4:
        return f"{username[:2]}***{username[-2:]}"
    return username

def run_signin(index, username, password):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    label = mask_account(username)
    print(f"\n👤 [账号{index+1}] 开始处理: {label}")

    # --- 1. 登录 (Login) ---
    login_url = "https://cf-v2.uapis.cn/login"
    login_payload = {
        "username": username,
        "password": password
    }
    
    try:
        login_res = session.post(login_url, json=login_payload, timeout=30)
        try:
            login_data = login_res.json()
        except:
            log(f"❌ {label}: 登录失败 (接口返回非JSON，可能是IP被拦截)")
            return

        if login_data.get("code") != 200:
            msg = login_data.get('msg', '未知错误')
            log(f"❌ {label}: 登录失败 - {msg}")
            return
            
        token = login_data["data"]["usertoken"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        # print(f"    登录成功，获取Token...") 

    except Exception as e:
        log(f"❌ {label}: 登录网络异常 - {e}")
        return

    time.sleep(random.uniform(1, 3))

    # --- 2. 检查积分 (可选) ---
    current_points = "未知"
    try:
        info_res = session.get("https://cf-v2.uapis.cn/qiandao_info", timeout=30)
        if info_res.status_code == 200:
            info_data = info_res.json()
            if info_data.get("code") == 200:
                current_points = info_data.get("data", {}).get("total_points", 0)
    except:
        pass

    # --- 3. 执行签到 (Sign In) ---
    sign_url = "https://cf-v2.uapis.cn/qiandao"
    
    # 极验参数留空，依赖 IP 白名单或宽松验证
    sign_payload = {
        "lot_number": "", 
        "captcha_output": "",
        "pass_token": "",
        "gen_time": str(int(time.time()))
    }

    try:
        sign_res = session.post(sign_url, json=sign_payload, timeout=30)
        try:
            sign_data = sign_res.json()
        except:
            log(f"❌ {label}: 签到失败 (接口被WAF拦截，状态码:{sign_res.status_code})")
            return

        code = sign_data.get("code")
        msg = sign_data.get("msg")

        if code == 200:
            # 尝试提取积分变动数字
            points_match = re.search(r"获得(\d+)", str(msg))
            added = points_match.group(1) if points_match else "?"
            # 计算新的总积分（如果之前获取到了的话）
            new_total = int(current_points) + int(added) if isinstance(current_points, int) and added.isdigit() else current_points
            
            log(f"✅ {label}: 签到成功 (积分+{added} | 总:{new_total})")
        
        elif code == 409:
            log(f"🔁 {label}: 今日已签过 (总:{current_points})")
        
        else:
            log(f"⚠️ {label}: 签到失败 - {msg} (Code:{code})")

    except Exception as e:
        log(f"❌ {label}: 签到请求出错 - {e}")

def main():
    if not ACCOUNTS_ENV:
        print("⛔️ 未找到环境变量 ACCOUNTS_JSON")
        print("⚠️ 请在青龙面板 -> 环境变量中添加 ACCOUNTS_JSON")
        print('⚠️ 格式示例: [{"username": "user1", "password": "pwd"}, ...]')
        return

    try:
        accounts = json.loads(ACCOUNTS_ENV)
    except json.JSONDecodeError:
        print("⛔️ 环境变量 ACCOUNTS_JSON 格式错误，请检查 JSON 语法（是否少括号或引号错误）。")
        return

    print("--- 开始 ChmlFrp 签到 ---")
    
    for i, acc in enumerate(accounts):
        run_signin(i, acc.get('username'), acc.get('password'))
        # 账号间随机等待，避免并发过高
        if i < len(accounts) - 1:
            wait_time = random.uniform(2, 5)
            print(f"⏳ 等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
            
    print("-" * 30)
    
    # 如果有日志消息，则发送推送
    if msg_list:
        send("ChmlFrp 签到结果", "\n".join(msg_list))

if __name__ == "__main__":
    main()
