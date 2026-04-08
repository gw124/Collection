import os
import time
import urllib.request
import urllib.parse
import json
import re
from pathlib import Path
from datetime import datetime

# ================= 配置区域 =================
DIR_A = "/volume1/CloudNAS/CloudDrive/115/Media" 
DIR_B = "/volume1/CloudNAS/CloudDrive/115/Media/每日更新"

# 屏蔽设置
EXCLUDE_DIRS = ["每日更新", "@eaDir", "#recycle"] 

# 安全开关 (True 为测试模式，False 为正式执行彻底删除)
DRY_RUN = False       

# --- Telegram 推送设置 ---
TG_BOT_TOKEN = ""   # 请填入你的 Token
TG_CHAT_ID = ""     # 请填入你的 Chat ID
# -------------------------

# 媒体与去重参数
MEDIA_EXTS = {'.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.wmv', '.flv', '.mov', '.m2ts', '.iso'}
DELAY_DIR_SCAN = 1.0   
DELAY_FILE_DEL = 1.5   
# ============================================

def send_tg_msg(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': TG_CHAT_ID, 'text': text}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            pass 
    except Exception as e:
        print(f"\n❌ Telegram 请求异常: {e}")

def get_media_bases(dir_path):
    bases = {}
    try:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            for f in os.listdir(dir_path):
                file_path = Path(f)
                if file_path.suffix.lower() in MEDIA_EXTS:
                    bases[file_path.stem] = f 
    except OSError:
        pass
    return bases

def get_clean_prefix(name):
    parts = name.split(" - ")
    if len(parts) > 1:
        return parts[0].replace(" ", "").lower()
    ym = re.search(r'\(\d{4}\)', name)
    if ym:
        return name[:ym.end()].replace(" ", "").lower()
    return name.replace(" ", "").lower()

def extract_ep(name):
    m = re.search(r'(?i)s\d+e\d+(?:-e\d+)?', name)
    return m.group(0).lower() if m else None

def extract_db_id(name):
    """
    智能提取 TMDB 或 IMDB ID
    支持格式: {tmdb-123}, [imdbid=tt123], tmdb_123 等一切变体
    统一返回标准化特征，如: tmdb-123 或 imdb-tt123
    """
    m = re.search(r'(?i)(tmdb|imdb).*?(tt\d+|\d+)', name)
    if m:
        return f"{m.group(1).lower()}-{m.group(2).lower()}"
    return None

def main():
    path_a = Path(DIR_A)
    path_b = Path(DIR_B)
    
    start_time = time.time()
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count_movie, count_episode, count_metadata, count_folders = 0, 0, 0, 0

    mode_label = "⚠️ 测试模式 (不删除)" if DRY_RUN else "🚀 正式清理模式"
    
    start_msg = (
        f"🔔 基准去重任务启动\n"
        f"=========================\n"
        f"模式: {mode_label}\n"
        f"时间: {start_time_str}\n"
        f"目标: {path_b.name}\n"
        f"========================="
    )
    print("\n" + start_msg + "\n")
    send_tg_msg(start_msg)

    print(">>> [步骤 1] 正在启用智能模糊匹配 (含 TMDB/IMDB 身份证核验) ...\n")
    
    for root, dirs, files in os.walk(DIR_B):
        for dname in list(dirs):
            if dname in EXCLUDE_DIRS:
                dirs.remove(dname)

        root_path = Path(root)
        rel_path = root_path.relative_to(path_b)
        target_path_a = path_a / rel_path
        
        if not target_path_a.exists():
            continue
            
        a_bases = get_media_bases(target_path_a)
        if not a_bases:
            continue
            
        path_str = str(rel_path)
        is_movie_dir = "电影" in path_str
        is_episode_dir = any(k in path_str for k in ["电视剧", "动漫", "短剧", "系列合集"])

        # 提取当前 B 目录的特征 ID (如果文件夹名里带的话)
        folder_db_id_b = extract_db_id(root_path.name)
        folder_db_id_a = extract_db_id(target_path_a.name)

        for f in files:
            file_path = Path(f)
            stem_b = file_path.stem
            clean_b = stem_b.replace(" ", "").lower()
            prefix_b = get_clean_prefix(stem_b)
            ep_code_b = extract_ep(f)
            
            # 文件的 ID 优先于文件夹的 ID
            db_id_b = extract_db_id(f) or folder_db_id_b
            
            matched_a_file = None
            
            for stem_a, original_a_name in a_bases.items():
                clean_a = stem_a.replace(" ", "").lower()
                prefix_a = get_clean_prefix(stem_a)
                ep_code_a = extract_ep(original_a_name)
                db_id_a = extract_db_id(original_a_name) or folder_db_id_a

                # 0. 撞名绝对防护：如果有 ID 且 ID 不同，立刻跳过！不管名字多像。
                if db_id_b and db_id_a and db_id_b != db_id_a:
                    continue

                # 1. 严格无空格比对
                if clean_b == clean_a:
                    matched_a_file = target_path_a / original_a_name
                    break
                
                # 2. 传统后缀匹配 (关联元数据)
                if f.startswith(f"{stem_a}-") or f.startswith(f"{stem_a}."):
                    matched_a_file = target_path_a / original_a_name
                    break
                
                # 3. 剧集特征雷达 (集数对上即可)
                if ep_code_b and ep_code_a and ep_code_b == ep_code_a:
                    matched_a_file = target_path_a / original_a_name
                    break
                
                # 4. 电影匹配逻辑
                if is_movie_dir:
                    # 4.1 终极 ID 核对：两者都有 ID 且相等
                    if db_id_b and db_id_a and db_id_b == db_id_a:
                        matched_a_file = target_path_a / original_a_name
                        break
                    # 4.2 降级使用片名前缀截断匹配
                    elif prefix_b and prefix_a and prefix_b == prefix_a:
                        matched_a_file = target_path_a / original_a_name
                        break
            
            if matched_a_file:
                full_path_b = root_path / f
                
                if file_path.suffix.lower() in MEDIA_EXTS:
                    if is_movie_dir: count_movie += 1
                    else: count_episode += 1
                else:
                    count_metadata += 1

                if DRY_RUN:
                    print(f"[测试] 智能命中 -> 拟删除: {full_path_b}")
                    print(f"               参照基准库: {matched_a_file}")
                else:
                    print(f"[*] 执行删除: {full_path_b}")
                    print(f"  参照基准库: {matched_a_file}")
                    try:
                        os.remove(full_path_b)
                        time.sleep(DELAY_FILE_DEL)
                    except Exception as e:
                        print(f"[!] 删除失败: {e}")
                        
        time.sleep(DELAY_DIR_SCAN)

    print("\n>>> [步骤 2] 正在清理空文件夹...\n")
    for root, dirs, files in os.walk(DIR_B, topdown=False):
        root_path = Path(root)
        if root_path == path_b or root_path.name in EXCLUDE_DIRS:
            continue

        try:
            if not os.listdir(root_path):
                if DRY_RUN:
                    print(f"[测试] 空目录拟删除: {root_path}")
                else:
                    os.rmdir(root_path)
                    print(f"[*] 已清理空目录: {root_path}")
                    time.sleep(DELAY_FILE_DEL)
                count_folders += 1
        except OSError:
            pass
        time.sleep(DELAY_DIR_SCAN / 2)

    end_time = time.time()
    duration = end_time - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    res_mode_str = "⚠️ 测试报告" if DRY_RUN else "✅ 清理完成"
    report_text = (
        f"🤖 基准去重结算报告\n"
        f"=========================\n"
        f"状态: {res_mode_str}\n"
        f"⏱️ 总计耗时: {minutes}分{seconds}秒\n"
        f"🎬 去重电影: {count_movie} 部\n"
        f"📺 去重剧集: {count_episode} 集\n"
        f"📄 相关元数据: {count_metadata} 个\n"
        f"🗑️ 清理空目录: {count_folders} 个\n"
        f"========================="
    )

    print("\n" + report_text + "\n")
    send_tg_msg(report_text)

if __name__ == "__main__":
    main()