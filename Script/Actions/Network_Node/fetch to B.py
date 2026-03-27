import re
import requests
import base64
import urllib.parse
import json
import hashlib
import yaml
import os
import sys
import datetime

# ==========================================
# 1. 动态加载配置文件与跨步传参
# ==========================================
try:
    with open("sources.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    CHANNELS = config.get("CHANNELS", [])
    EXTERNAL_URLS = config.get("EXTERNAL_URLS", [])
    DYNAMIC_REPOS = config.get("DYNAMIC_REPOS", [])
    # 🌟 新增：读取动态日期模板
    DATE_TEMPLATES = config.get("DATE_TEMPLATES", [])
    
    # 读取 B 仓库的目标配置，如果没有则使用默认值防崩溃
    TARGET_REPO = config.get("TARGET_REPO", "gw124/Collection")
    TARGET_DIR = config.get("TARGET_DIR", "Web/Nodes")
    
    # 🌟 新增：读取清理 Nodes 文件夹的开关 (默认开启)
    CLEAN_NODES = config.get("CLEAN_NODES", True)
    
    # 🌟 核心魔法：将配置写入 GITHUB_ENV，让工作流的后续步骤可以直接使用
    env_file = os.getenv('GITHUB_ENV')
    if env_file:
        with open(env_file, "a", encoding="utf-8") as env_f:
            env_f.write(f"TARGET_REPO={TARGET_REPO}\n")
            env_f.write(f"TARGET_DIR={TARGET_DIR}\n")
            # 🌟 新增：将开关状态转为小写字符串传给 Bash
            env_f.write(f"CLEAN_NODES={str(CLEAN_NODES).lower()}\n")
            
    print(f"✅ 成功加载 sources.yaml")
    print(f"  --> B 仓库目标: {TARGET_REPO}")
    print(f"  --> B 仓库路径: {TARGET_DIR}")
    print(f"  --> 自动清空 Nodes 开关: {'开启' if CLEAN_NODES else '关闭'}")
    print(f"  --> 日期模板数量: {len(DATE_TEMPLATES)} 个")
    
except Exception as e:
    print(f"❌ 读取 sources.yaml 失败: {e}")
    sys.exit(1)

# ==========================================
# 2. 核心探测与读取函数
# ==========================================
NODES_DIR = "Nodes"

def get_local_nodes_urls():
    print("\n" + "="*50)
    print(f"📁 阶段 0: 扫描本地 [{NODES_DIR}] 文件夹中的配置文件")
    print("="*50)
    local_urls = []
    if not os.path.exists(NODES_DIR):
        print(f"  [⚠️ 提示] 文件夹 '{NODES_DIR}' 不存在，已自动创建。")
        os.makedirs(NODES_DIR)
        return local_urls
        
    for filename in os.listdir(NODES_DIR):
        filepath = os.path.join(NODES_DIR, filename)
        if os.path.isfile(filepath):
            safe_name = urllib.parse.quote(filename)
            local_url = f"http://127.0.0.1:8000/{NODES_DIR}/{safe_name}"
            local_urls.append(local_url)
            print(f"  [✅ 发现] 抓取本地配置文件 -> {filename}")
            
    print(f"  --> 共找到 {len(local_urls)} 个本地订阅文件。")
    return local_urls

def count_nodes_in_text(text, is_yaml=False):
    if is_yaml or 'proxies:' in text:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict) and 'proxies' in data:
                return len(data['proxies'])
        except: pass
            
    try:
        matches = re.findall(r'(vmess|vless|ss|ssr|trojan|hysteria2|tuic)://', text)
        if len(matches) > 0: return len(matches)
    except: pass
        
    try:
        padded_text = text.strip() + "=" * ((4 - len(text.strip()) % 4) % 4)
        dec = base64.b64decode(padded_text).decode('utf-8', errors='ignore')
        matches = re.findall(r'(vmess|vless|ss|ssr|trojan|hysteria2|tuic)://', dec)
        if len(matches) > 0: return len(matches)
    except: pass
        
    return 0

def get_and_heal_tg_nodes():
    print("\n" + "="*50)
    print("📡 阶段 1: 抓取 Telegram 频道野生节点")
    print("="*50)
    raw_nodes = []
    raw_pattern = re.compile(r'(vmess|vless|ss|ssr|trojan|hysteria2|tuic)://[^\s\'"<>]+')
    sub_pattern = re.compile(r'https?://[^\s\'"<>]+')
    
    for url in CHANNELS:
        try:
            res = requests.get(url, timeout=10).text
            channel_count = 0
            for m in raw_pattern.finditer(res):
                raw_nodes.append(m.group(0))
                channel_count += 1
            for m in sub_pattern.finditer(res):
                sub_url = m.group(0)
                if "t.me" in sub_url: continue 
                try:
                    sub_res = requests.get(sub_url, timeout=5).text
                    decoded = base64.b64decode(sub_res).decode('utf-8', errors='ignore')
                    for rm in raw_pattern.finditer(decoded):
                        raw_nodes.append(rm.group(0))
                        channel_count += 1
                except: pass 
            print(f"  [✅ 成功] 获取 {channel_count:3} 个节点 <- {url}")
        except Exception as e:
            print(f"  [❌ 失败] 无法访问 <- {url}")

    clean_nodes = []
    seen_configs = set()
    for node in raw_nodes:
        try:
            if node.startswith("vmess://"):
                b64_str = node[8:].split('#')[0] 
                b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                v_json = json.loads(base64.b64decode(b64_str).decode('utf-8'))
                v_config = {k: v for k, v in v_json.items() if k != 'ps'}
                config_hash = hashlib.md5(str(v_config).encode()).hexdigest()
                if config_hash in seen_configs: continue
                seen_configs.add(config_hash)
                clean_node = "vmess://" + base64.b64encode(json.dumps(v_json, separators=(',', ':')).encode('utf-8')).decode('utf-8')
                clean_nodes.append(clean_node)
            else:
                parts = node.split('#', 1)
                config_part = parts[0]
                config_hash = hashlib.md5(config_part.encode()).hexdigest()
                if config_hash in seen_configs: continue
                seen_configs.add(config_hash)
                if len(parts) > 1:
                    safe_name = urllib.parse.quote(urllib.parse.unquote(parts[1]))
                    clean_nodes.append(f"{config_part}#{safe_name}")
                else:
                    clean_nodes.append(config_part)
        except: continue
        
    print(f"  --> 净化与初步去重后，TG 频道共保留 {len(clean_nodes)} 个有效节点。")
    return clean_nodes

def check_external_links(urls_to_check):
    print("\n" + "="*50)
    print("🔗 阶段 2: 探测外部订阅源")
    print("="*50)
    valid_urls = []
    
    for url in urls_to_check:
        is_yaml = url.endswith('.yaml') or url.endswith('.yml') or '/clash' in url or 'proxies' in url
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                count = count_nodes_in_text(res.text, is_yaml)
                if count > 0:
                    print(f"  [✅ 存活] 发现 {count:3} 个节点 <- {url}")
                    valid_urls.append(url)
                else:
                    print(f"  [⚠️ 空链] 未发现节点，将被自动清理 <- {url}")
            else:
                print(f"  [❌ 报错] HTTP {res.status_code}，将被自动清理 <- {url}")
        except Exception as e:
            print(f"  [❌ 超时/异常] 无法连接，将被自动清理 <- {url}")
            
    return valid_urls

# 🌟 新增：智能日期模板探测函数 (全占位符支持版)
def get_date_template_links():
    print("\n" + "="*50)
    print("📆 阶段 2.5: 智能嗅探日期动态源")
    print("="*50)
    valid_date_urls = []
    
    # 获取今天、昨天、前天的时间对象，防止时差或网站还没更新
    today = datetime.datetime.now()
    dates_to_try = [
        today,
        today - datetime.timedelta(days=1),
        today - datetime.timedelta(days=2)
    ]
    
    for template in DATE_TEMPLATES:
        found = False
        for target_date in dates_to_try:
            # 自动生成基础日期格式
            format_basic = target_date.strftime("%Y%m%d")      # 20260317
            format_hyphen = target_date.strftime("%Y-%m-%d")   # 2026-03-17
            format_under = target_date.strftime("%Y_%m_%d")    # 2026_03_17
            
            # 提取独立的年、月、日
            yyyy = target_date.strftime("%Y")                  # 2026
            mm = target_date.strftime("%m")                    # 03
            dd = target_date.strftime("%d")                    # 17
            
            # 智能替换模板中可能出现的所有格式占位符
            test_url = template.replace("{YYYYMMDD}", format_basic) \
                               .replace("{YYYY-MM-DD}", format_hyphen) \
                               .replace("{YYYY_MM_DD}", format_under) \
                               .replace("{YYYY}", yyyy) \
                               .replace("{MM}", mm) \
                               .replace("{DD}", dd)
                               
            is_yaml = test_url.endswith('.yaml') or test_url.endswith('.yml')
            try:
                res = requests.get(test_url, timeout=5)
                if res.status_code == 200:
                    count = count_nodes_in_text(res.text, is_yaml)
                    if count > 0:
                        print(f"  [✅ 命中] 日期 {format_basic} 发现 {count:3} 个节点 <- {test_url}")
                        valid_date_urls.append(test_url)
                        found = True
                        break # 命中最新的就直接跳出，不再找更旧的日期
            except:
                pass
        if not found:
            # 日期模板哪怕找不到也不会触发自动清理，因为明天它可能又活了
            print(f"  [❌ 失败] 该模板近3天日期均无效 <- {template}")
            
    return valid_date_urls

def get_dynamic_links():
    print("\n" + "="*50)
    print("📅 阶段 3: 智能嗅探动态仓库 (API & README 双引擎)")
    print("="*50)
    dynamic_urls = []
    
    for repo in DYNAMIC_REPOS:
        repo_success = False
        try:
            api_url = f"https://api.github.com/repos/{repo}/contents"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                items = res.json()
                files = [i for i in items if i['type'] == 'file' and i['name'] not in ('README.md', 'LICENSE', '.gitignore')]
                files.sort(key=lambda x: x['name'], reverse=True)
                
                hit_count = 0
                for file_info in files:
                    latest_url = file_info['download_url']
                    check_res = requests.get(latest_url, timeout=5)
                    count = count_nodes_in_text(check_res.text, latest_url.endswith(('.yaml', '.yml')))
                    if count > 0:
                        print(f"  [✅ API命中] 发现 {count:3} 个节点 <- {latest_url}")
                        dynamic_urls.append(latest_url)
                        repo_success = True
                        hit_count += 1
                        if hit_count >= 4: 
                            break 
        except Exception as e:
            pass
            
        if not repo_success:
            try:
                readme_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
                res = requests.get(readme_url, timeout=5)
                if res.status_code == 200:
                    pattern = r"https://raw\.githubusercontent\.com/" + re.escape(repo) + r"/main/[a-zA-Z0-9_.-]+"
                    matches = re.findall(pattern, res.text)
                    valid_links = []
                    for m in matches:
                        if not m.endswith('.md') and m not in valid_links:
                            valid_links.append(m)
                    
                    for link in valid_links[:2]:
                        check_res = requests.get(link, timeout=5)
                        count = count_nodes_in_text(check_res.text, link.endswith(('.yaml', '.yml')))
                        if count > 0:
                            print(f"  [✅ 文档命中] 发现 {count:3} 个节点 <- {link}")
                            dynamic_urls.append(link)
                            break
            except Exception as e:
                print(f"  [❌ 嗅探失败] 无法获取 {repo} 的节点")
                
    return dynamic_urls

if __name__ == "__main__":
    local_nodes_urls = get_local_nodes_urls()
    tg_nodes = get_and_heal_tg_nodes()
    
    valid_external_urls = check_external_links(EXTERNAL_URLS)
    
    if len(valid_external_urls) != len(EXTERNAL_URLS):
        try:
            with open("sources.yaml", "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            config_data["EXTERNAL_URLS"] = valid_external_urls
            with open("sources.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            print(f"\n  [♻️ 配置自我净化] 成功！已从 sources.yaml 中永久删除了 {len(EXTERNAL_URLS) - len(valid_external_urls)} 个失效链接！")
        except Exception as e:
            print(f"  [⚠️ 配置净化失败] {e}")

    # 🌟 调用新增的日期探测函数
    date_template_urls = get_date_template_links()

    dynamic_urls = get_dynamic_links()
    
    print("\n" + "="*50)
    print("🚀 阶段 4: 资源聚合与下发")
    print("="*50)
    
    if tg_nodes:
        final_string = "\n".join(tg_nodes)
        b64_content = base64.b64encode(final_string.encode('utf-8')).decode('utf-8')
        with open("tg_nodes.txt", "w", encoding='utf-8') as f:
            f.write(b64_content)
    else:
        with open("tg_nodes.txt", "w") as f: f.write("")
    
    all_urls = []
    if tg_nodes:
        all_urls.append("http://127.0.0.1:8000/tg_nodes.txt")
    all_urls.extend(local_nodes_urls)
    all_urls.extend(valid_external_urls)
    # 🌟 将探测成功的日期链接加进大部队
    all_urls.extend(date_template_urls) 
    all_urls.extend(dynamic_urls)
    
    encoded_url = urllib.parse.quote("|".join(all_urls))
    sub_api = f"http://127.0.0.1:25500/sub?target=clash&url={encoded_url}&insert=false"
    
    with open("sub_api_url.txt", "w") as f:
        f.write(sub_api)
        
    print(f"  --> 剔除死链并合并 Nodes 文件夹后，最终下发给 Subconverter 的有效订阅入口: {len(all_urls)} 个。")
    print("  --> 等待 check.py 进行全局底层去重与极速测速...\n")
