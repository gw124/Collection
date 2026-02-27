# pip install requests
import requests
import time
import random

# ================= 配置区域 =================
# 在这里直接填写你的账号和密码
ACCOUNTS = [
    {"username": "你的账号1", "password": "密码1"},
    {"username": "你的账号2", "password": "密码2"},
    {"username": "你的账号3", "password": "密码3"}
]
# ===========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://panel.chmlfrp.net",
    "Referer": "https://panel.chmlfrp.net/"
}

def mask_account(index):
    return f"账号 {index + 1}"

def run_signin(index, username, password):
    session = requests.Session()
    session.headers.update(HEADERS)
    account_label = mask_account(index)
    print(f"[-] 开始处理: {account_label}")

    # 1. 登录
    try:
        login_res = session.post("https://cf-v2.uapis.cn/login", 
                               json={"username": username, "password": password}, 
                               timeout=15)
        
        try:
            login_data = login_res.json()
        except:
            print(f"[!] {account_label} 登录响应解析失败 (可能是被拦截)")
            return

        if login_data.get("code") != 200:
            print(f"[x] {account_label} 登录失败: {login_data.get('msg')}")
            return
            
        token = login_data["data"]["usertoken"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"[+] {account_label} 登录成功")

    except Exception as e:
        print(f"[!] {account_label} 登录网络错误: {e}")
        return

    time.sleep(2)

    # 2. 签到
    try:
        # 本地运行时，空参数通常也能过，或者因为 IP 干净不需要验证码
        sign_payload = {
            "lot_number": "", 
            "captcha_output": "",
            "pass_token": "",
            "gen_time": str(int(time.time()))
        }
        sign_res = session.post("https://cf-v2.uapis.cn/qiandao", json=sign_payload, timeout=15)
        
        try:
            sign_data = sign_res.json()
        except:
            print(f"[!] {account_label} 签到响应解析失败")
            print(f"    内容: {sign_res.text[:100]}")
            return

        code = sign_data.get("code")
        msg = sign_data.get("msg")

        if code == 200:
            print(f"[√] {account_label} 签到成功! 消息: {msg}")
        elif code == 409:
            print(f"[-] {account_label} 今日已签到")
        else:
            print(f"[x] {account_label} 签到失败: {msg} (Code: {code})")

    except Exception as e:
        print(f"[!] {account_label} 签到请求出错: {e}")

if __name__ == "__main__":
    print("--- 开始本地签到 ---")
    for i, acc in enumerate(ACCOUNTS):
        run_signin(i, acc['username'], acc['password'])
        print("-" * 30)
        time.sleep(3)
    print("--- 结束 ---")
