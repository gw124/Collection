import os
import requests
import base64
import json
import re
import time
import yaml
from urllib.parse import unquote

# ---------------- 配置区域 ----------------
GIST_ID = os.environ.get("GIST_ID")
TOKEN = os.environ.get("REPO_TOKEN")
SUBS_URLS = os.environ.get("SUBS_URLS", "").split(",")

# ⚠️ 自定义配置
SAVE_FILENAME = "GLaDOS.txt"   # 最终输出的文件名
AIRPORT_PREFIX = "红叶"        # 自定义前缀
SEPARATOR = " | "              # 分隔符 (红叶 | 日本...)
# ----------------------------------------

# 地区映射表 (包含关键词匹配兜底)
COUNTRY_CONFIG = {
    'HK': {'flag': '🇭🇰', 'name': '香港', 'keywords': ['HK', 'HONGKONG', '港', '香港']},
    'TW': {'flag': '🇹🇼', 'name': '台湾', 'keywords': ['TW', 'TAIWAN', '台', '台湾', '台北', '新北']},
    'MO': {'flag': '🇲🇴', 'name': '澳门', 'keywords': ['MO', 'MACAU', 'MACAO', '澳', '澳门']},
    'JP': {'flag': '🇯🇵', 'name': '日本', 'keywords': ['JP', 'JAPAN', 'TOKYO', 'OSAKA', '日', '日本', '东京', '大阪']},
    'KR': {'flag': '🇰🇷', 'name': '韩国', 'keywords': ['KR', 'KOREA', 'SEOUL', '韩', '韩国', '首尔']},
    'SG': {'flag': '🇸🇬', 'name': '新加坡', 'keywords': ['SG', 'SINGAPORE', '狮城', '新', '新加坡']},
    'US': {'flag': '🇺🇸', 'name': '美国', 'keywords': ['US', 'USA', 'AMERICA', '美', '美国', '洛杉矶', '波特兰', '西雅图']},
    'GB': {'flag': '🇬🇧', 'name': '英国', 'keywords': ['GB', 'UK', 'LONDON', '英', '英国', '伦敦']},
    'DE': {'flag': '🇩🇪', 'name': '德国', 'keywords': ['DE', 'GERMANY', 'FRANKFURT', '德', '德国', '法兰克福']},
    'CA': {'flag': '🇨🇦', 'name': '加拿大', 'keywords': ['CA', 'CANADA', '加', '加拿大']},
    'AU': {'flag': '🇦🇺', 'name': '澳洲', 'keywords': ['AU', 'AUSTRALIA', 'SYDNEY', '澳洲', '澳大利亚']},
    'FR': {'flag': '🇫🇷', 'name': '法国', 'keywords': ['FR', 'FRANCE', 'PARIS', '法', '法国', '巴黎']},
    'RU': {'flag': '🇷🇺', 'name': '俄罗斯', 'keywords': ['RU', 'RUSSIA', '俄', '俄罗斯']},
    'IN': {'flag': '🇮🇳', 'name': '印度', 'keywords': ['IN', 'INDIA', '印', '印度']},
    'TH': {'flag': '🇹🇭', 'name': '泰国', 'keywords': ['TH', 'THAILAND', '泰', '泰国', '曼谷']},
    'VN': {'flag': '🇻🇳', 'name': '越南', 'keywords': ['VN', 'VIETNAM', '越', '越南']},
    'MY': {'flag': '🇲🇾', 'name': '马来', 'keywords': ['MY', 'MALAYSIA', '马', '马来西亚']},
    'ID': {'flag': '🇮🇩', 'name': '印尼', 'keywords': ['ID', 'INDONESIA', '印尼', '印度尼西亚']},
    'PH': {'flag': '🇵🇭', 'name': '菲律宾', 'keywords': ['PH', 'PHILIPPINES', '菲', '菲律宾']},
    'TR': {'flag': '🇹🇷', 'name': '土耳其', 'keywords': ['TR', 'TURKEY', '土耳其']},
    'NL': {'flag': '🇳🇱', 'name': '荷兰', 'keywords': ['NL', 'NETHERLANDS', '荷', '荷兰']},
    'CN': {'flag': '🇨🇳', 'name': '中国', 'keywords': ['CN', 'CHINA', 'SHANGHAI', 'BEIJING', '中', '中国', '上海', '北京', '广州', '深圳']},
}

# 💡 复刻你 JS 脚本里的 blkey 标签规则
TAG_DICT = {
    "Zx": "专线", "专线": "专线", "Fam": "家宽", "家宽": "家宽", 
    "直连": "直连", "Direct": "直连", "中转": "中转", "Transit": "中转", 
    "中继": "中转", "Relay": "中转", "动态": "动态", "IPV6": "IPV6", 
    "流媒体": "流媒体", "Netflix": "Netflix", "Disney": "Disney", 
    "chatGPT": "OpenAI", "IPLC": "IPLC", "IEPL": "IEPL", 
    "BGP": "BGP", "CN2": "CN2", "GIA": "GIA", "CMI": "CMI", 
    "CMIN": "CMIN", "AIG": "AIG", "PCCW": "PCCW", "HKT": "HKT",
    "EIP": "EIP" # 补充了你截图里的 EIP
}

def decode_base64(s):
    s = s.strip()
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4)).decode('utf-8', errors='ignore')

def get_proxies(urls):
    combined_proxies = []
    print(f"[*] 正在下载 {len(urls)} 个订阅源...")
    headers = {'User-Agent': 'ClashVerge/1.3.5'} 
    for url in urls:
        url = url.strip()
        if not url: continue
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                content = resp.text.strip()
                try:
                    yaml_data = yaml.safe_load(content)
                    if isinstance(yaml_data, dict) and 'proxies' in yaml_data:
                        for p in yaml_data['proxies']:
                            combined_proxies.append({'type': 'yaml', 'server': p.get('server'), 'raw_obj': p})
                        continue 
                except: pass
                try:
                    lines = decode_base64(content).split('\n')
                    for line in lines:
                        if line.strip(): combined_proxies.append({'type': 'uri', 'raw_str': line.strip()})
                except: pass
        except Exception as e:
            print(f"[-] 下载异常: {e}")
    return combined_proxies

def extract_server_info(proxy_item):
    if proxy_item['type'] == 'yaml': return proxy_item['raw_obj'].get('server')
    raw = proxy_item.get('raw_str', '')
    if raw.startswith("vmess://"):
        try: return json.loads(decode_base64(raw[8:])).get("add")
        except: return None
    if "://" in raw and "@" in raw:
        try: return re.search(r'@([^:/#?]+)', raw).group(1)
        except: return None
    return None

def get_original_name(proxy_item):
    if proxy_item['type'] == 'yaml': return str(proxy_item['raw_obj'].get('name', 'Unknown'))
    raw = proxy_item.get('raw_str', '')
    if raw.startswith("vmess://"):
        try: return str(json.loads(decode_base64(raw[8:])).get("ps", "Unknown"))
        except: return "Unknown"
    if '#' in raw:
        try: return unquote(raw.split('#')[-1]).strip()
        except: pass
    return "Unknown"

def guess_country_from_name(name):
    words = re.findall(r'[A-Z0-9\u4e00-\u9fa5]+', name.upper())
    for code, data in COUNTRY_CONFIG.items():
        for keyword in data['keywords']:
            if keyword in words or keyword in name.upper():
                return code
    return 'UN'

def extract_tags(name):
    """💡 复刻 JS: 提取标签和倍率"""
    matched_tags = []
    
    # 1. 匹配标签 (去重)
    for search_key, replace_val in TAG_DICT.items():
        if re.search(search_key, name, re.IGNORECASE):
            if replace_val not in matched_tags:
                matched_tags.append(replace_val)
    
    # 2. 匹配倍率 (例如: 1.5x, 2倍)
    multiplier = ""
    # 匹配: 倍率/x/X 前后的数字
    match = re.search(r'(?:[xX×倍]\s*)(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)(?:\s*[xX×倍])', name)
    if match:
        val = match.group(1) or match.group(2)
        if val and float(val) != 1.0: # 排除 1x
            multiplier = f"{val}x"
            
    if multiplier:
        matched_tags.append(multiplier)
        
    return matched_tags

def batch_query_ip(ips):
    if not ips: return {}
    url = "http://ip-api.com/batch?fields=query,countryCode,country"
    results = []
    print(f"[*] 正在查询 {len(ips)} 个 IP 的地理位置...")
    try:
        unique_ips = list(set(ips))
        for i in range(0, len(unique_ips), 100):
            batch = unique_ips[i:i+100]
            resp = requests.post(url, json=batch, timeout=20)
            if resp.status_code == 200: results.extend(resp.json())
            time.sleep(1.5)
        ip_map = {item['query']: item for item in results if 'query' in item}
        return ip_map
    except: return {}

def process_and_rename(proxy_list):
    hosts = []
    for p in proxy_list:
        h = extract_server_info(p)
        if h:
            p['parsed_host'] = h
            hosts.append(h)
    
    if not hosts: return ""

    ip_info = batch_query_ip(hosts)
    grouped_proxies = {}
    
    for p in proxy_list:
        host = p.get('parsed_host')
        original_name = get_original_name(p)
        
        country_code = 'UN'
        country_name = '未知'
        
        info = ip_info.get(host)
        if info and info.get('countryCode'):
            country_code = info['countryCode']
            country_name = info.get('country', country_code)
            
        if country_code == 'UN' or country_code not in COUNTRY_CONFIG:
            guess = guess_country_from_name(original_name)
            if guess != 'UN':
                country_code = guess
        
        if country_code not in grouped_proxies: grouped_proxies[country_code] = []
        
        # 预先提取标签，为了后面的排序
        tags = extract_tags(original_name)
        grouped_proxies[country_code].append({
            'proxy': p, 
            'code': country_code, 
            'name_en': country_name,
            'tags': tags
        })

    final_proxies_yaml = []
    final_proxies_uri = []
    
    sort_order = ['HK', 'TW', 'MO', 'JP', 'KR', 'SG', 'US', 'GB', 'DE', 'CN']
    sorted_keys = sorted(grouped_proxies.keys(), key=lambda x: sort_order.index(x) if x in sort_order else 999)

    for code in sorted_keys:
        proxies = grouped_proxies[code]
        
        # 💡 复刻 JS: 智能排序，纯净节点在前，带标签节点在后
        # tags 为空的排前面(0)，有标签的排后面(1)
        proxies.sort(key=lambda x: (1 if x['tags'] else 0, " ".join(x['tags'])))
        
        if code in COUNTRY_CONFIG:
            c_flag = COUNTRY_CONFIG[code]['flag']
            c_name = COUNTRY_CONFIG[code]['name']
        else:
            c_flag = '🏴'
            c_name = '未知'
        
        for index, item in enumerate(proxies):
            p = item['proxy']
            tags = item['tags']
            
            seq = str(index + 1).zfill(2)
            
            # 基础名字: 红叶 | 🇯🇵 日本 01
            base_name = f"{AIRPORT_PREFIX}{SEPARATOR}{c_flag} {c_name} {seq}"
            
            # 如果有标签，格式化为 [BGP | EIP | 1.5x] 并追加到后面
            if tags:
                tags_str = " | ".join(tags)
                new_name = f"{base_name} [{tags_str}]"
            else:
                new_name = base_name
            
            if p['type'] == 'yaml':
                p['raw_obj']['name'] = new_name
                final_proxies_yaml.append(p['raw_obj'])
            elif p['type'] == 'uri':
                raw = p['raw_str']
                if raw.startswith("vmess://"):
                    try:
                        b64 = raw[8:]
                        conf = json.loads(decode_base64(b64))
                        conf['ps'] = new_name
                        final_proxies_uri.append("vmess://" + base64.b64encode(json.dumps(conf, ensure_ascii=False).encode()).decode())
                    except: pass
                elif '#' in raw:
                    from urllib.parse import quote
                    final_proxies_uri.append(f"{raw.split('#')[0]}#{quote(new_name)}")
                else:
                    from urllib.parse import quote
                    final_proxies_uri.append(f"{raw}#{quote(new_name)}")

    if final_proxies_yaml:
        return yaml.dump({'proxies': final_proxies_yaml}, allow_unicode=True, sort_keys=False)
    if final_proxies_uri:
        return base64.b64encode("\n".join(final_proxies_uri).encode()).decode()
    return ""

def update_gist(content_str):
    if not content_str: return

    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 强行覆盖 GLaDOS.txt 并且自动删除多余的 nodes.txt
    data = {
        "files": {
            SAVE_FILENAME: {"content": content_str},
            "nodes.txt": None  
        }
    }
    
    try:
        r = requests.patch(f"https://api.github.com/gists/{GIST_ID}", json=data, headers=headers)
        if r.status_code == 200:
            print(f"[+] 成功更新文件: {SAVE_FILENAME} ✅")
        else:
            print(f"[-] Gist 更新失败: {r.status_code}")
    except Exception as e:
        print(f"[-] 网络请求异常: {e}")

if __name__ == "__main__":
    if not SUBS_URLS or not GIST_ID or not TOKEN: exit(1)
    proxy_list = get_proxies(SUBS_URLS)
    result_content = process_and_rename(proxy_list)
    update_gist(result_content)
