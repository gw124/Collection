import os
import re
import time
import sys
import requests
import shutil

# ================= 基础配置区域 =================

# 【扫描路径配置】
# 脚本会遍历这些路径。它会自动提取最后一个文件夹名作为你的“媒体库分类”（如“电视剧”、“动漫”）。
BASE_PATHS = [
    "/volume1/CloudNAS/CloudDrive/115/Media/电视剧",
    "/volume1/CloudNAS/CloudDrive/115/Media/动漫"
]

# 填入你【绝对不想被扫描、去重或删除】的文件夹路径。支持填写多个。
# 智能匹配：填入整剧路径，则整剧被忽略；填入具体的 Season 路径，则仅忽略该季。
EXCLUDE_PATHS = [
    # 示例用法 (把不想碰的路径用双引号包起来，逗号分隔，不用的话可以留空)：
    # "/volume1/CloudNAS/CloudDrive/115/Media/动漫/航海王 (1999) {tmdb-37854}",
    # "/volume1/CloudNAS/CloudDrive/115/Media/电视剧/某部珍藏老剧/Season 1"
]

# 【显示路径美化】
# 纯视觉优化：在最终的报告 txt 里，把这段冗长的网盘挂载路径隐藏掉，让路径显示更简短清爽。
PATH_PREFIX_TO_STRIP = "/volume1/CloudNAS/CloudDrive/115/Media"

# 【自动去重开关】
# True = 开启。当发现同一个 Season 文件夹里有重复集数时，触发“两轮 PK 淘汰制”，只保留最好的一个，其余物理删除。
# False = 关闭。发现重复时只在报告里记录警告，绝不动手删文件。
AUTO_DELETE_DUPLICATES = True  

# 【去重优先级排序】(仅当 AUTO_DELETE_DUPLICATES = True 时生效)
# 作用：从左到右，越靠前的后缀优先级越高（遇到重复时优先存活）。
# 补充：如果两个文件后缀一模一样（比如都是 mp4），脚本会自动比较它们的物理体积，保留体积更大的那个。
EXT_PRIORITY = ['.mkv', '.mp4', '.ts', '.avi', '.flv', '.rmvb', '.webm', '.mov', '.iso']

# =====================================================================
# 【高危操作：缺集连坐删除开关】
# ⚠️ 警告：物理删除操作极其高危！建议只有在确认刮削完美时才开启。
# 这两个开关专门对付“残缺不全”的剧集，与上方的“去重”逻辑互不干扰。
# =====================================================================

# 灭门模式（默认 False）：如果检测到该剧集任一季有缺集，直接物理删除【整部剧集】的根目录。
DELETE_ENTIRE_SHOW = False 

# 精准打击模式（默认 False）：如果检测到缺集，仅物理删除【当前缺集的那一个 Season 季】文件夹。
# 注意：如果上面的 DELETE_ENTIRE_SHOW 已经是 True，这个开关就没意义了（因为整部剧都没了）。
DELETE_ONLY_SEASON = False 

# 【本地报告生成开关】
# True = 扫描结束后，会在脚本同级目录下永久保留一份 txt 详细报告。
# False = 不保留本地文件。扫描结束后，如果下方开启了 TG 文件推送，报告会被发送到你手机上，随后瞬间把 NAS 上的文件删掉（阅后即焚）。
ENABLE_LOCAL_REPORT = False

# 【报告输出名称】
# 导出的检测报告文件名。
OUTPUT_FILE = "缺集检测报告.txt"

# 【防风控延迟机制】(单位：秒)
# 每扫一个文件夹暂停一下。模拟人类操作速度，防止因为全速无缝扫描被 115 网盘风控拦截或封禁 API。
SCAN_DELAY = 0.02 

# 【识别后缀名单】
# 只有属于这些后缀的文件，才会被脚本当做视频去提取集数（防止误判字幕、海报、nfo 等文件）。
VIDEO_EXTS = {'.mp4', '.mkv', '.ts', '.avi', '.rmvb', '.flv', '.iso', '.mov', '.m4v', '.wmv', '.webm'}

# ================= Telegram 推送配置 =================

# 扫描过程中，只要发现缺集或重复，立刻发送一条简短的实时告警消息（建议 False，免得手机一直响）。
ENABLE_TG_REALTIME = False

# 扫描结束后，发送一条包含“总耗时、总缺集数量”的汇总概览消息。
ENABLE_TG_SUMMARY = True

# 扫描结束后，将详细的 txt 报告作为附件文件发送给你。
ENABLE_TG_FILE = True

# 你的 Telegram Bot Token 和接收消息的 Chat ID
TG_BOT_TOKEN = ""    
TG_CHAT_ID = ""        

# 网络代理。如果你的 NAS 在国内环境无法直连 TG 接口，请在此配置代理（如无需求留空 None 即可）。
PROXIES = None 

# ================= 正则预编译 =================
RE_RULES = [
    re.compile(r'[Ss]\d+[Ee](\d+)', re.IGNORECASE), 
    re.compile(r'第(\d+)集'),                       
    re.compile(r'[Ee][Pp]\s*(\d+)', re.IGNORECASE)  
]

# ================= 核心功能函数 =================
def is_excluded(check_path):
    """检测当前路径是否命中排除列表（支持模糊子目录匹配）"""
    if not EXCLUDE_PATHS: return False
    check_path = os.path.normpath(check_path)
    for ex_path in EXCLUDE_PATHS:
        if not ex_path.strip(): continue
        ex_path = os.path.normpath(ex_path.strip())
        # 如果当前路径正好是排除路径，或者是它的子目录，直接触发护盾
        if check_path == ex_path or check_path.startswith(ex_path + os.sep):
            return True
    return False

def extract_episode_number(filename):
    """从文件名中利用正则提取集数"""
    for regex in RE_RULES:
        match = regex.search(filename)
        if match: return int(match.group(1))
    return None

def analyze_season_folder(season_path):
    """分析 Season 文件夹，返回缺失列表和重复的字典"""
    episodes_map = {} 
    try:
        with os.scandir(season_path) as it:
            for entry in it:
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in VIDEO_EXTS:
                    ep_num = extract_episode_number(entry.name)
                    if ep_num is not None:
                        if ep_num not in episodes_map:
                            episodes_map[ep_num] = []
                        episodes_map[ep_num].append(entry.path)
    except OSError:
        return None

    if not episodes_map: return None

    episodes = set(episodes_map.keys())
    min_ep = min(episodes)
    max_ep = max(episodes)
    
    expected_start = 1 if min_ep < 20 else min_ep
    missing_eps = [i for i in range(expected_start, max_ep + 1) if i not in episodes]
    
    duplicate_eps = {ep: files for ep, files in episodes_map.items() if len(files) > 1}
            
    return {
        "min": min_ep, "max": max_ep, 
        "missing": missing_eps,
        "duplicates": duplicate_eps,
        "expected_start": expected_start, 
        "total_files": sum(len(f) for f in episodes_map.values())
    }

def get_best_file_to_keep(filepaths):
    """智能去重决断：两轮 PK 淘汰制"""
    def score_file(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        ext_score = EXT_PRIORITY.index(ext) if ext in EXT_PRIORITY else 999
        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0
        return (ext_score, -size)

    sorted_files = sorted(filepaths, key=score_file)
    return sorted_files[0], sorted_files[1:]

def send_tg_message(text):
    """向 Telegram 发送文本"""
    if not TG_BOT_TOKEN.strip() or TG_BOT_TOKEN == "YOUR_BOT_TOKEN": return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text}, proxies=PROXIES, timeout=10)
    except Exception as e:
        sys.stdout.write(f"\r[TG推送失败] {e} ".ljust(60) + "\n")

def send_tg_document(filepath, caption=""):
    """向 Telegram 发送报告文件"""
    if not ENABLE_TG_FILE or not TG_BOT_TOKEN.strip() or TG_BOT_TOKEN == "YOUR_BOT_TOKEN": return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            sys.stdout.write("\n正在向 Telegram 发送报告文件...")
            requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": caption}, files={"document": f}, proxies=PROXIES, timeout=30)
    except Exception:
        pass

def fast_scan(base_paths, output_filepath):
    """核心扫描调度器"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    final_output_path = os.path.join(script_dir, output_filepath)
    
    # 🌟 核心逻辑：只要你需要本地报告，或者需要TG推送，就必须在运行中写文件
    need_to_write_file = ENABLE_LOCAL_REPORT or ENABLE_TG_FILE
    
    if need_to_write_file:
        with open(final_output_path, 'w', encoding='utf-8') as f:
            f.write("================ 媒体库缺集与去重检测报告 =================\n\n")

    print(f"🚀 开始扫描... (去重: {'开启' if AUTO_DELETE_DUPLICATES else '关闭'} | 本地报告: {'开启' if ENABLE_LOCAL_REPORT else '关闭(阅后即焚)'})")
    
    start_time = time.time()
    missing_summary = {} 
    
    def scan_directory(current_path, current_category_set):
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if not entry.is_dir(): continue
                    
                    # 🌟 护盾触发：如果命中排除路径，直接跳过这个文件夹
                    if is_excluded(entry.path):
                        continue
                        
                    sys.stdout.write(f"\r🔍 正在扫: {entry.name[:40].ljust(40)}")
                    sys.stdout.flush()
                    time.sleep(SCAN_DELAY) 
                    
                    if "Season" in entry.name or "Specials" in entry.name:
                        report = analyze_season_folder(entry.path)
                        if report and (report["missing"] or report["duplicates"]):
                            show_name = os.path.basename(current_path)
                            if report["missing"]: 
                                current_category_set.add(show_name)
                            
                            friendly_path = entry.path 
                            if PATH_PREFIX_TO_STRIP and entry.path.startswith(PATH_PREFIX_TO_STRIP):
                                friendly_path = entry.path[len(PATH_PREFIX_TO_STRIP):]
                                friendly_path = friendly_path if friendly_path else "/"
                            
                            log_text = f"📺 剧集: {show_name} -> {entry.name}\n"
                            log_text += f"📁 位置: {friendly_path}\n"  
                            log_text += f"📊 统计: 共 {report['total_files']} 个视频。最大至 {report['max']}。\n"
                            
                            if report["missing"]:
                                log_text += f"❌ 缺失: {', '.join(map(str, report['missing']))}\n"
                            
                            if report["duplicates"]:
                                log_text += f"⚠️ 重复: 发现 {len(report['duplicates'])} 集存在重复文件\n"
                                
                                for ep, files in report["duplicates"].items():
                                    if AUTO_DELETE_DUPLICATES:
                                        keep_file, trash_files = get_best_file_to_keep(files)
                                        log_text += f"   ├── 第 {ep} 集 -> ✅保留: {os.path.basename(keep_file)}\n"
                                        
                                        for trash in trash_files:
                                            try:
                                                os.remove(trash) 
                                                log_text += f"   │             -> 🗑️已删除: {os.path.basename(trash)}\n"
                                            except Exception as e:
                                                log_text += f"   │             -> ❌删除失败: {os.path.basename(trash)} ({e})\n"
                                    else:
                                        log_text += f"   ├── 第 {ep} 集: 共有 {len(files)} 个重复版本\n"

                            del_status = ""
                            if report["missing"]:
                                if DELETE_ENTIRE_SHOW:
                                    try:
                                        shutil.rmtree(current_path)
                                        del_status = "🧨 已执行：物理删除整部剧集"
                                    except Exception as e: del_status = f"❌ 删除失败：{str(e)}"
                                elif DELETE_ONLY_SEASON:
                                    try:
                                        shutil.rmtree(entry.path)
                                        del_status = "🧨 已执行：物理删除当前季"
                                    except Exception as e: del_status = f"❌ 删除失败：{str(e)}"
                            
                            if del_status:
                                log_text += f"🛡 操作: {del_status}\n"

                            sys.stdout.write("\r" + " " * 60 + "\r")
                            print(log_text)
                            
                            if need_to_write_file:
                                with open(final_output_path, 'a', encoding='utf-8') as f:
                                    f.write(log_text + "\n")
                                
                            if ENABLE_TG_REALTIME: send_tg_message(log_text)
                            
                            if DELETE_ENTIRE_SHOW and report["missing"]: 
                                return False 
                    else:
                        scan_directory(entry.path, current_category_set)
        except OSError:
            pass 
        return False

    for path in base_paths:
        if os.path.exists(path):
            category_name = os.path.basename(path.rstrip('/\\'))
            if category_name not in missing_summary: missing_summary[category_name] = set()
            scan_directory(path, missing_summary[category_name])

    # ================= 最终统计汇总 =================
    total_seconds = int(time.time() - start_time)
    time_str = f"{total_seconds}秒" if total_seconds < 60 else f"{total_seconds // 60}分{total_seconds % 60}秒"
    total_missing = sum(len(shows) for shows in missing_summary.values())
    
    category_text = ""
    for cat, shows in missing_summary.items():
        category_text += f"   ├─ 📁 {cat}: {len(shows)} 部\n"

    summary_text = (
        f"🏁 任务完成！\n"
        f"⏱ 用时：{time_str}\n"
        f"⚠️ 缺集总计：{total_missing} 部\n"
        f"{category_text.rstrip()}\n"
        f"🧹 自动去重：{'已执行' if AUTO_DELETE_DUPLICATES else '未开启'}\n"
        f"📅 完成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("\n" + "="*30)
    print(summary_text)
    print("="*30)

    if ENABLE_TG_SUMMARY: send_tg_message(summary_text)
    
    # 🌟 阅后即焚逻辑：发送文件，如果不需要本地保留则立刻物理删除
    if ENABLE_TG_FILE and need_to_write_file: 
        send_tg_document(final_output_path, caption="📦 缺集与去重清理报告")
        
        if not ENABLE_LOCAL_REPORT:
            try:
                os.remove(final_output_path)
                print("\n🧹 阅后即焚：已自动清理 NAS 上的临时报告文件。")
            except Exception:
                pass

if __name__ == "__main__":
    try: import requests
    except ImportError: sys.exit("❌ 缺少 requests 库，请执行 pip3 install requests")
    fast_scan(BASE_PATHS, OUTPUT_FILE)
