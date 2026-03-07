import os
import time
import requests
import subprocess
import base64
import ddddocr

# ================= 配置区 =================
# 读取账号环境变量 (支持换行符或 & 分隔)
ENV_ACCOUNTS = os.environ.get('ACCOUNTS', '')

# 匿名模式开关：如果不专门去设置 'false' 或 '关闭'，默认强制开启匿名保护
env_anon = os.environ.get('ANONYMOUS_MODE', '').strip().lower()
ANONYMOUS_MODE = env_anon not in ['false', '关闭', '0']

# API 接口定义
BASE_URL = "https://ltyun.org"
LOGIN_API = f"{BASE_URL}/api/sysAuth/login"
USER_INFO_API = f"{BASE_URL}/api/userhome/userinfo"
SIGN_API = f"{BASE_URL}/api/userhome/usersign"
CAPTCHA_API = f"{BASE_URL}/api/sysAuth/captcha" 

# ================= WARP IP 切换模块 =================
def mask_ip(ip_str):
    """智能隐藏 IP 地址中间部分"""
    if not ip_str:
        return "未知 IP"
    ip_str = ip_str.strip()
    
    if ":" in ip_str:  # 处理 IPv6
        parts = ip_str.split(":")
        if len(parts) >= 3:
            return f"{parts[0]}:{parts[1]}:***:{parts[-1]}"
        return ip_str[:4] + "***" + ip_str[-4:]
        
    elif "." in ip_str:  # 处理 IPv4
        parts = ip_str.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.{parts[3]}"
        return ip_str[:3] + "***" + ip_str[-3:]
        
    return ip_str[:4] + "***"

def rotate_warp():
    """执行系统命令重启 WARP 客户端，获取全新 IP"""
    print("\n🔄 [IP切换] 正在重启 WARP 以更换 IP...")
    try:
        subprocess.run(
            ["sudo", "warp-cli", "--accept-tos", "disconnect"], 
            check=True, 
            stdout=subprocess.DEVNULL
        )
        time.sleep(3)
        
        subprocess.run(
            ["sudo", "warp-cli", "--accept-tos", "connect"], 
            check=True, 
            stdout=subprocess.DEVNULL
        )
        
        print("    -> 等待网络连接建立 (10秒)...")
        time.sleep(10)
        
        try:
            ip_check = subprocess.check_output(
                ["curl", "-s", "--max-time", "5", "https://api.ip.sb/ip"], 
                text=True
            ).strip()
            
            masked_ip = mask_ip(ip_check)
            print(f"    -> 🌐 新 IP 地址: {masked_ip}")
        except Exception:
            print("    -> ⚠️ (IP 查询超时，但底层连接通常已建立)")
            
    except Exception as e:
        print(f"⚠️ WARP 重启失败: {e}")
        print("    -> 将使用旧 IP 继续尝试...")

# ================= 核心业务逻辑 =================
def parse_accounts(env_str):
    """解析账号配置，自动处理匿名命名"""
    accounts = []
    if not env_str:
        return accounts
    
    raw_list = env_str.replace('\n', '&').split('&')
    for index, raw in enumerate(raw_list):
        raw = raw.strip()
        if not raw:
            continue
            
        # 默认使用匿名名称
        display_name = f"账户{index + 1}"
        
        # 判断是否包含自定义名称
        if ':' in raw:
            custom_name, creds = raw.split(':', 1)
            # 如果彻底关闭了匿名模式，才使用自定义名称
            if not ANONYMOUS_MODE:
                display_name = custom_name
        else:
            creds = raw
            
        try:
            user, pwd = creds.split(',', 1)
            accounts.append({
                'name': display_name,
                'user': user.strip(),
                'pwd': pwd.strip()
            })
        except ValueError:
            print(f"⚠️ 账号格式解析失败，已跳过: {raw}")
            
    return accounts

def get_captcha(session, name):
    """获取并识别图形验证码"""
    print(f"[{name}] 正在获取并识别验证码...")
    try:
        res = session.get(CAPTCHA_API, timeout=10).json()
        if res.get('code') == 200:
            result = res.get('result', {})
            code_id = result.get('id', '')
            img_b64 = result.get('img', '')
            
            if ',' in img_b64:
                img_b64 = img_b64.split(',', 1)[1]
                
            ocr = ddddocr.DdddOcr(show_ad=False)
            img_bytes = base64.b64decode(img_b64)
            code = ocr.classification(img_bytes)
            return code_id, code
    except Exception as e:
        print(f"[{name}] ⚠️ 验证码获取/识别异常: {e}")
    return "", ""

def process_account(account):
    name = account['name']
    print(f"\n[{name}] 开始执行任务...")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_3_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/143.0.7499.151 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "Content-Type": "application/json"
    })

    # 1. 验证码与登录
    code_id, code = get_captcha(session, name)
    
    login_payload = {
        "account": account['user'],
        "password": account['pwd'],
        "codeId": code_id,
        "code": code
    }
    
    try:
        login_res = session.post(LOGIN_API, json=login_payload, timeout=10).json()
        if login_res.get("code") != 200:
            print(f"[{name}] ❌ 登录失败: {login_res.get('message', '未知原因 (可能是验证码识别错误)')}")
            return
            
        access_token = login_res["result"]["accessToken"]
        session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "X-Authorization": access_token
        })
        print(f"[{name}] ✅ 登录成功")
    except Exception as e:
        print(f"[{name}] ❌ 登录请求异常: {e}")
        return

    # 2. 查询当前状态
    try:
        info_res = session.post(USER_INFO_API, json={}, timeout=10).json()
        if info_res.get("code") != 200:
            print(f"[{name}] ❌ 获取用户信息失败")
            return
            
        user_data = info_res["result"]
        # 根据抓包逻辑：false = 已签到，true = 未签到
        is_sign = user_data.get("isSign", False) 
        current_points = user_data.get("points", 0)
        current_amount = user_data.get("amount", 0)
        
        if not is_sign:
            print(f"[{name}] 🛑 今日已签到 | 账户积分: {current_points} | 账户余额: {current_amount} CNY")
            return
            
    except Exception as e:
        print(f"[{name}] ❌ 状态查询异常: {e}")
        return

    # 3. 执行签到
    try:
        # 🎯 关键修复：签到接口是 GET 请求！
        sign_req = session.get(SIGN_API, timeout=10)
        
        # 增加防崩溃解析
        try:
            sign_res = sign_req.json()
        except Exception:
            print(f"[{name}] ❌ 签到解析失败，非预期返回内容: {sign_req.text[:150]}")
            return

        if sign_res.get("code") == 200:
            # 4. 再次查询比对收益
            new_info_res = session.post(USER_INFO_API, json={}, timeout=10).json()
            new_data = new_info_res.get("result", {})
            new_points = new_data.get("points", 0)
            
            gained = new_points - current_points
            print(f"[{name}] 🎉 签到成功 | 获得积分: {gained} | 最新积分: {new_points} | 账户余额: {new_data.get('amount', 0)} CNY")
        else:
            print(f"[{name}] ❌ 签到失败: {sign_res.get('message', '未知错误')}")
    except Exception as e:
        print(f"[{name}] ❌ 签到请求异常: {e}")

# ================= 主入口 =================
if __name__ == "__main__":
    accounts_list = parse_accounts(ENV_ACCOUNTS)
    if not accounts_list:
        print("❌ 未检测到账号配置，请在 GitHub Secrets 设置 'ACCOUNTS'")
        exit(1)
        
    print(f"🚀 共检测到 {len(accounts_list)} 个配置账号")
    print(f"🕵️ 匿名模式: {'已开启 (隐藏真实命名)' if ANONYMOUS_MODE else '已关闭'}")
    
    for i, acc in enumerate(accounts_list):
        if i > 0:
            rotate_warp()
            time.sleep(5) # 切换后增加延迟，防风控
        process_account(acc)
        
    print("\n✅ 所有任务执行完毕！")
