import requests
import os
import time

# 1. 获取 Token
USER_TOKEN = os.environ.get('USER_TOKEN')

# 2. 获取抵消开关
# 默认为 'false' (关闭)。只有当 Secrets 里填了 'true' 时才会开启。
ENABLE_OFFSET = os.environ.get('ENABLE_OFFSET', 'false')

def run_task():
    if not USER_TOKEN:
        print("❌ 错误: 未检测到 USER_TOKEN，请在 GitHub Secrets 中添加！")
        return

    # 基础配置
    api_host = "api-1209.apitutu.com"
    api_base = f"https://{api_host}/gateway/tqt/cn"
    origin_site = "https://vip.taoqitu.pro"
    
    # 伪装成 Mac 电脑 Chrome 浏览器 (匹配你的抓包环境)
    headers = {
        "Host": api_host,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": origin_site,
        "Referer": f"{origin_site}/",
        "Authorization": USER_TOKEN,
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }

    session = requests.Session()

    # 强制同步 Cookie，确保通过后端校验
    cookie_dict = {
        'auth_data': USER_TOKEN,
        'authorization': USER_TOKEN
    }
    session.cookies.update(cookie_dict)

    try:
        print("🚀 [Desktop模式] 开始执行任务...")
        
        # --- 1. 执行签到 ---
        sign_url = f"{api_base}/user/sign"
        res = session.get(sign_url, headers=headers, timeout=10)
        
        print(f"📊 签到状态码: {res.status_code}")
        try:
            data = res.json()
            msg = data.get('message', '无消息')
            print(f"🎉 签到反馈: {msg}")
        except:
            print(f"⚠️ 原始响应: {res.text[:100]}")

        # --- 2. 流量抵消逻辑 ---
        # 只有在签到正常(200) 或 提示已签到时，才检查是否需要抵消
        if res.status_code == 200 or (res.text and "已签到" in res.text):
            
            # 检查开关状态 (忽略大小写)
            if ENABLE_OFFSET.lower() != 'true':
                print(f"🛑 抵消功能未开启 (当前设置: {ENABLE_OFFSET})，任务结束。")
                return

            time.sleep(1)
            print("🔄 开关已开启，正在查询流量并执行抵消...")
            
            # 获取流量列表
            list_res = session.get(f"{api_base}/user/getSignList", headers=headers, timeout=10)
            
            try:
                list_data = list_res.json().get('data', [])
                if list_data:
                    # 获取最新的一条流量数值
                    flow_val = list_data[0].get('get_num')
                    print(f"📊 待抵消流量: {flow_val}GB")
                    
                    # 发送抵消请求
                    convert_res = session.get(f"{api_base}/user/convertSign", headers=headers, params={'convert_num': flow_val})
                    print(f"🎁 抵消结果: {convert_res.json().get('message', '完成')}")
                else:
                    print("ℹ️ 未查询到可抵消的流量记录")
            except Exception as e:
                print(f"⚠️ 获取流量列表失败: {e}")

    except Exception as e:
        print(f"💥 运行出错: {str(e)}")

if __name__ == "__main__":
    run_task()
