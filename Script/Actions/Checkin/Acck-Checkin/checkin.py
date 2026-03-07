import os
import time
import requests
import subprocess

# WARP 代理地址 (默认端口 40000)
WARP_PROXY = "socks5h://127.0.0.1:40000"

# =========================================
# WARP IP 切换模块
# =========================================
def mask_ip(ip_str):
    if not ip_str:
        return "未知 IP"
    ip_str = ip_str.strip()
    
    if ":" in ip_str:  # IPv6
        parts = ip_str.split(":")
        if len(parts) >= 3:
            return f"{parts[0]}:{parts[1]}:***:{parts[-1]}"
        return ip_str[:4] + "***" + ip_str[-4:]
        
    elif "." in ip_str:  # IPv4
        parts = ip_str.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.{parts[3]}"
        return ip_str[:3] + "***" + ip_str[-3:]
        
    return ip_str[:4] + "***"

def rotate_warp():
    print("\n🔄 [IP切换] 正在重启 WARP 以更换 IP...")
    try:
        subprocess.run(["sudo", "warp-cli", "--accept-tos", "disconnect"], check=True, stdout=subprocess.DEVNULL)
        time.sleep(3)
        subprocess.run(["sudo", "warp-cli", "--accept-tos", "connect"], check=True, stdout=subprocess.DEVNULL)
        
        print("    -> 等待网络连接建立 (10秒)...")
        time.sleep(10)
        
        try:
            ip_check = subprocess.check_output(
                ["curl", "-s", "-x", WARP_PROXY, "--max-time", "10", "https://api.ip.sb/ip"], 
                text=True
            ).strip()
            print(f"    -> 新出口 IP: {mask_ip(ip_check)}")
        except Exception as e:
            print(f"    -> (IP 查询超时或异常，但底层连接通常已建立: {e})")
            
    except Exception as e:
        print(f"⚠️ WARP 重启失败: {e}")

# =========================================
# 签到核心业务模块
# =========================================
class AcckSigner:
    def __init__(self, account_index, username, password):
        self.account_id = f"账号{account_index}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        self.session.proxies = {
            "http": WARP_PROXY,
            "https": WARP_PROXY
        }
        
        self.token = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_3_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/143.0.7499.151 Mobile/15E148 Safari/604.1",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9"
        }

    def login(self):
        url = "https://api.acck.io/api/v1/user/login"
        headers = self.headers.copy()
        headers.update({
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://acck.io",
            "Referer": "https://acck.io/"
        })
        
        payload = {
            "email": self.username,
            "password": self.password,
            "token": "",
            "verifyCode": ""
        }
        
        try:
            res = self.session.post(url, json=payload, headers=headers, timeout=15)
            
            try:
                data = res.json()
            except Exception:
                print(f"❌ [{self.account_id}] 登录失败: 网站未返回预期的 JSON。状态码: {res.status_code}")
                return False

            if data.get("status_code") == 0:
                self.token = data.get("data", {}).get("token")
                print(f"✅ [{self.account_id}] 登录成功！")
                return True
            else:
                msg = data.get("status_msg", "未知错误")
                print(f"❌ [{self.account_id}] 登录失败！原因: {msg}")
                return False
                
        except Exception as e:
            print(f"❌ [{self.account_id}] 登录请求网络异常: {e}")
            return False

    def check_status(self):
        if not self.token: return False
        url = "https://sign-service.acck.io/api/acLogs/signStatus"
        headers = self.headers.copy()
        headers.update({
            "Authorization": self.token,
            "Referer": f"https://sign-service.acck.io/acbShop?token={self.token}"
        })
        try:
            res = self.session.get(url, headers=headers, timeout=10)
            data = res.json()
            if data.get("code") == 200 and data.get("data") is True:
                return True
        except Exception:
            pass
        return False

    def check_in(self):
        if not self.token: return
        url = "https://sign-service.acck.io/api/acLogs/sign"
        headers = self.headers.copy()
        headers.update({
            "Authorization": self.token,
            "Origin": "https://sign-service.acck.io",
            "Referer": f"https://sign-service.acck.io/acbShop?token={self.token}"
        })
        try:
            res = self.session.get(url, headers=headers, timeout=15)
            data = res.json()
            if data.get("code") == 200:
                print(f"🎉 [{self.account_id}] 签到成功！")
            else:
                msg = data.get("msg", "未知")
                print(f"⚠️ [{self.account_id}] 签到失败或异常: {msg}")
        except Exception as e:
            print(f"⚠️ [{self.account_id}] 签到请求异常: {e}")

    def get_reward(self):
        if not self.token: return
        url = "https://sign-service.acck.io/api/users/getUserInfo"
        headers = self.headers.copy()
        headers.update({
            "Authorization": self.token,
            "Referer": f"https://sign-service.acck.io/acbShop?token={self.token}"
        })
        try:
            res = self.session.get(url, headers=headers, timeout=10)
            data = res.json()
            if data.get("code") == 200:
                jifen = data.get("data", {}).get("jifen", 0)
                print(f"💰 [{self.account_id}] 当前账户余额: {jifen} AC币")
            else:
                print(f"⚠️ [{self.account_id}] 获取余额失败: {data.get('msg')}")
        except Exception as e:
            print(f"⚠️ [{self.account_id}] 查询余额异常: {e}")

# =========================================
# 主程序
# =========================================
def main():
    accounts_env = os.environ.get("ACCOUNTS")
    if not accounts_env:
        print("❌ 未检测到 ACCOUNTS 环境变量，请配置。")
        return
        
    account_list = accounts_env.split(",")
    print(f"🚀 共检测到 {len(account_list)} 个待签到账号")
    
    for index, account_str in enumerate(account_list, start=1):
        if "----" not in account_str:
            continue
            
        username, password = account_str.split("----", 1)
        
        print(f"\n" + "="*40)
        print(f"▶️ 开始处理: 账号{index}")
        
        rotate_warp()
        
        signer = AcckSigner(index, username, password)
        if signer.login():
            time.sleep(2)
            if signer.check_status():
                print(f"ℹ️ [{signer.account_id}] 今日已签到，跳过签到步骤。")
            else:
                signer.check_in()
            time.sleep(2)
            signer.get_reward()
            
        print(f"⏹️ 账号{index} 处理完毕")
        time.sleep(5) 

if __name__ == "__main__":
    main()
