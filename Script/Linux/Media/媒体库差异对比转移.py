import os
import shutil
import re
import urllib.request
import urllib.parse
import json
import time
import random
from datetime import datetime

# ==================== 配置区域 (请仔细核对) ====================

# 1. 基础路径配置
PATH_A = "/volume1/CloudNAS/CloudDrive/115/Media/每日更新"    # 待处理/新下载资源的源路径
PATH_B = "/volume1/CloudNAS/CloudDrive/115/Media"           # 你的正式媒体库路径 (用于对比是否已存在)
PATH_C = "/volume1/CloudNAS/CloudDrive/115/Sync/待刮削"       # 达标后，最终转移存放的目标路径 (刮削目录)

# 2. 演习测试开关 (DRY_RUN)
# True = 演习模式。只做逻辑对比和打印日志，绝不进行真实的物理拷贝/移动！(测试逻辑、防止重名冲突的最佳工具)
# False = 实弹模式。脚本将真正开始搬运文件。
DRY_RUN = False           

# 3. 模式开关
# False = 复制模式 (默认推荐，安全不丢数据) 
# True = 移动模式 (注意：网盘挂载工具在移动文件时，会触发服务器端秒传，速度极快)
IS_MOVE_MODE = True        

# 4. 连载状态检测开关 (仅针对电视剧/动漫有效)
# False = 不管是否连载，只要目标库没有都转移 
# True = 仅转移官方已标记为“完结(Ended)”的剧集/动漫 (默认)
CHECK_COMPLETED = True      

# 5. 缺集防漏开关 (最后一道保险 - 放心开启，现已优化为最后一步才扫描，绝不卡死！)
# False = 不检查，直接转移
# True = 开启缺集检测。如果完结剧集的内部实际视频文件数量，少于命名的最大集数则拒绝转移
CHECK_MISSING_EPISODES = True 

# 6. 报告与风控设置
# True = 保留本地txt报告文件 | False = 仅推送到 TG 后自动删除本地文件 (默认)
SAVE_LOCAL_REPORT = False   
# 风控随机延迟 (秒)：每次独立操作后随机休眠。单线程极速查找下，0.5~1.5秒最安全，防 115 封禁。
ANTI_BAN_DELAY = (0.5, 1.5)     

# 7. Telegram 推送配置
# True = 每成功转移一个资源就推送一条消息 | False = 关闭实时推送，仅最后推送总报告
ENABLE_REALTIME_PUSH = True 
# 您的专属 TG 机器人 Token 和 Chat ID
TG_BOT_TOKEN = ""
TG_CHAT_ID = ""

# 8. 高阶配置项
# TMDB API Key：核心数据源，用于向 TMDB 直接查询剧集/动漫是否完结
TMDB_API_KEY = ""           

# 9. 电影处理开关
# False = 差异对比：目标库没有这部电影才进行移动/复制 (默认推荐)
# True  = 强制处理：只要判定是电影，无视目标库是否已存在，全部强行移动/复制
FORCE_SYNC_MOVIES = False

REPORT_FILE_NAME = "媒体对比同步报告.txt" 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = os.path.join(SCRIPT_DIR, REPORT_FILE_NAME)

# ==================== 工具函数 ====================

results_log = [] 

def get_unique_path(path):
    """
    【核心防撞名函数】
    如果目标文件夹已存在(可能是之前报错残留)，则自动生成 -1, -2 后缀的新路径，确保同步任务是干净的。
    """
    if not os.path.exists(path):
        return path
    
    # 提取基础路径（如果是文件会带后缀，目录则无）
    base, ext = os.path.splitext(path)
    counter = 1
    # 循环探测是否存在 path-1, path-2...
    while os.path.exists(f"{base}-{counter}{ext}"):
        counter += 1
    return f"{base}-{counter}{ext}"

def send_tg_msg(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
        urllib.request.urlopen(url, data=data, timeout=10)
    except: pass

def send_tg_file(file_path, caption):
    if not TG_BOT_TOKEN or not TG_CHAT_ID or not os.path.exists(file_path): return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        with open(file_path, 'rb') as f: file_content = f.read()
        part_boundary = f'--{boundary}\r\n'
        data = (f'{part_boundary}Content-Disposition: form-data; name="chat_id"\r\n\r\n{TG_CHAT_ID}\r\n'
                f'{part_boundary}Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
                f'{part_boundary}Content-Disposition: form-data; name="document"; filename="{os.path.basename(file_path)}"\r\n'
                f'Content-Type: text/plain\r\n\r\n').encode('utf-8') + file_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        urllib.request.urlopen(req, timeout=30)
    except: pass

def log_and_print(msg, write_to_report=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg, flush=True) 
    if write_to_report:
        results_log.append(full_msg) 

def get_tmdb_id(folder_name):
    match = re.search(r'\{tmdb-(\d+)\}', folder_name)
    return match.group(1) if match else None

def is_tv_show_smart(folder_path, folder_name):
    """
    【四维智能判定引擎】无惧混装目录，精准识别电影和剧集
    """
    # 1. 结构特征识别 (最快)：查里面有没有 Season 季文件夹
    try:
        for item in os.listdir(folder_path):
            if os.path.isdir(os.path.join(folder_path, item)):
                if re.search(r'(?i)^(season|specials|第.*季|sp)', item.strip()):
                    return True
    except: pass

    # 2. 命名特征识别 (较快)：查视频文件是否带 S01E01 或 EP01
    video_exts = {'.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.flv'}
    try:
        for file in os.listdir(folder_path):
            if os.path.splitext(file)[1].lower() in video_exts:
                if re.search(r'(?i)(S\d+\s*E\d+|EP\d+|E\d+|第\d+集)', file):
                    return True
    except: pass

    # 3. TMDB API 权威认证 (最准)
    tmdb_id = get_tmdb_id(folder_name)
    if tmdb_id and TMDB_API_KEY:
        try:
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=zh-CN"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                return True 
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False 
        except: pass

    # 4. 路径关键字兜底
    if any(kw in folder_path for kw in ["电视剧", "动漫", "剧集", "动画"]):
        return True
        
    return False 

def is_show_completed(folder_name):
    tmdb_id = get_tmdb_id(folder_name)
    if tmdb_id and TMDB_API_KEY:
        try:
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=zh-CN"
            with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as response:
                status = json.loads(response.read().decode()).get('status', '')
                if status in ['Ended', 'Canceled']: 
                    return True
                return False
        except: pass
    return False

def check_no_missing_episodes(folder_path):
    video_exts = {'.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.flv'}
    season_eps = {}
    has_video = False

    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in video_exts:
                    has_video = True
                    match_se = re.search(r'(?i)S(\d+)\s*E(\d+)(?:-E?(\d+))?', file)
                    if match_se:
                        s = int(match_se.group(1))
                        if s == 0: continue
                        e_start = int(match_se.group(2))
                        e_end = int(match_se.group(3)) if match_se.group(3) else e_start
                        if s not in season_eps: season_eps[s] = set()
                        for e in range(e_start, e_end + 1): season_eps[s].add(e)
                        continue
                    match_ep = re.search(r'(?i)(?:EP|E|第)\s*(\d+)\s*(?:集|)', file)
                    if match_ep:
                        if not season_eps: season_eps[1] = set()
                        season_eps[1].add(int(match_ep.group(1)))

        if not has_video: return False
        for s, eps in season_eps.items():
            if not eps: continue
            if max(eps) > len(eps): return False
        return True
    except: pass
    return True

def find_media_folders_lazy(base_path):
    try:
        with os.scandir(base_path) as it:
            for entry in it:
                if entry.is_dir():
                    if re.search(r'\{tmdb-\d+\}', entry.name): yield entry.path, entry.name
                    else: yield from find_media_folders_lazy(entry.path)
    except Exception as e: print(f"扫描异常: {e}")

# ==================== 主逻辑 ====================

def main():
    start_time = datetime.now()
    mode_text = "🟢 [模拟演习模式]" if DRY_RUN else "🔴 [实弹执行模式]"
    log_and_print(f"🚀 媒体对比同步脚本启动 {mode_text}...", write_to_report=True)
    send_tg_msg(f"🔔 *脚本启动 {mode_text}*")

    success_count = 0
    skip_count = 0

    try:
        media_tasks = list(find_media_folders_lazy(PATH_A))
        log_and_print(f"📂 扫描到待处理资源共 {len(media_tasks)} 个，开始智能识别与比对...", write_to_report=False)

        for a_dir, folder_name in media_tasks:
            time.sleep(random.uniform(*ANTI_BAN_DELAY)) 
            
            rel_path = os.path.relpath(a_dir, PATH_A)
            b_dir = os.path.join(PATH_B, rel_path)
            c_dir_initial = os.path.join(PATH_C, rel_path) 
            
            is_tv_show = is_tv_show_smart(a_dir, folder_name)

            # 【第一步：极速查异】
            is_new_entirely = not os.path.exists(b_dir)
            missing_items = set() # 改为 missing_items，因为它可能是文件夹，也可能是扁平的单集视频

            if not is_tv_show:
                # ====== 电影专用逻辑 ======
                if FORCE_SYNC_MOVIES:
                    is_new_entirely = True 
                elif not is_new_entirely:
                    log_and_print(f"跳过 (电影在媒体库已存在): {rel_path}", write_to_report=False)
                    skip_count += 1
                    continue
            else:
                # ====== 剧集专用逻辑 ======
                if not is_new_entirely:
                    try:
                        a_items = set(os.listdir(a_dir))
                        b_items = set(os.listdir(b_dir))
                        
                        # 尝试寻找规范的“季”目录
                        a_season_dirs = set(d for d in a_items if os.path.isdir(os.path.join(a_dir, d)) and re.search(r'(?i)^(season|specials|第.*季|sp)', d.strip()))
                        
                        if a_season_dirs:
                            # 模式A：规范结构。只对比季目录差异。
                            b_dirs = set(d for d in b_items if os.path.isdir(os.path.join(b_dir, d)))
                            missing_items = a_season_dirs - b_dirs
                        else:
                            # 模式B：扁平化结构(没季文件夹)。直接对比底层的视频文件差异。
                            video_exts = {'.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.flv'}
                            a_videos = set(f for f in a_items if os.path.splitext(f)[1].lower() in video_exts)
                            b_videos = set(f for f in b_items if os.path.splitext(f)[1].lower() in video_exts)
                            missing_items = a_videos - b_videos
                    except: pass
                    
                    if not missing_items:
                        log_and_print(f"跳过 (媒体库已存在该剧且无新增内容): {rel_path}", write_to_report=False)
                        skip_count += 1
                        continue

            # 【第二步：状态核查 (仅剧集参与)】
            if is_tv_show:
                if CHECK_COMPLETED and not is_show_completed(folder_name):
                    log_and_print(f"跳过 (连载中/未完结或 TMDB 查询失败): {rel_path}", write_to_report=False)
                    skip_count += 1
                    continue
                
                if CHECK_MISSING_EPISODES and not check_no_missing_episodes(a_dir):
                    log_and_print(f"🚨 跳过 (检测到缺集): {rel_path}", write_to_report=False)
                    skip_count += 1
                    continue

            # 【第三步：执行转移】
            op_text = "移动" if IS_MOVE_MODE else "复制"
            
            if is_new_entirely:
                final_c_dir = get_unique_path(c_dir_initial)
                if final_c_dir != c_dir_initial:
                    log_and_print(f"⚠️ 发现同名残留！已自动重命名为: {os.path.basename(final_c_dir)}")

                if DRY_RUN:
                    log_and_print(f"✅ [模拟] 准备{op_text}至: {final_c_dir}", write_to_report=True)
                    success_count += 1
                else:
                    os.makedirs(os.path.dirname(final_c_dir), exist_ok=True)
                    try:
                        if IS_MOVE_MODE: shutil.move(a_dir, final_c_dir)
                        else: shutil.copytree(a_dir, final_c_dir, dirs_exist_ok=True, copy_function=shutil.copyfile)
                        log_and_print(f"✅ 成功: {os.path.basename(final_c_dir)}", write_to_report=True)
                        success_count += 1
                        if ENABLE_REALTIME_PUSH: send_tg_msg(f"✅ *进度 ({op_text})*\n`{folder_name}`")
                    except Exception as e:
                        log_and_print(f"❌ 失败: {e}", write_to_report=True)
            else:
                # 增量转移 (可能是文件夹，也可能是单集视频文件)
                for item in missing_items:
                    a_item = os.path.join(a_dir, item)
                    c_item_initial = os.path.join(c_dir_initial, item)
                    final_c_item = get_unique_path(c_item_initial)

                    if DRY_RUN:
                        log_and_print(f"✅ [模拟] 准备{op_text}增量内容至: {final_c_item}", write_to_report=True)
                        success_count += 1
                    else:
                        os.makedirs(os.path.dirname(final_c_item), exist_ok=True)
                        try:
                            if IS_MOVE_MODE: shutil.move(a_item, final_c_item)
                            else: 
                                if os.path.isdir(a_item):
                                    shutil.copytree(a_item, final_c_item, dirs_exist_ok=True, copy_function=shutil.copyfile)
                                else:
                                    shutil.copyfile(a_item, final_c_item)
                                    
                            log_and_print(f"✅ 增量成功: {item}", write_to_report=True)
                            success_count += 1
                            if ENABLE_REALTIME_PUSH: send_tg_msg(f"✅ *增量 ({op_text})*\n`{folder_name} - {item}`")
                        except Exception as e:
                            log_and_print(f"❌ 增量失败: {e}", write_to_report=True)

    except KeyboardInterrupt:
        log_and_print("用户手动中断执行。", write_to_report=True)
    except Exception as e:
        log_and_print(f"致命错误: {e}", write_to_report=True)
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        summary = (
            f"📊 *执行报告汇总*\n━━━━━━━━━━━━━━\n"
            f"运行模式: {'模拟演习' if DRY_RUN else '实弹执行'}\n"
            f"处理成功: {success_count} 项\n"
            f"已入库/跳过: {skip_count} 部\n"
            f"总耗时: {str(duration).split('.')[0]}\n━━━━━━━━━━━━━━"
        )
        send_tg_msg(summary)
        
        if success_count > 0 or len(results_log) > 1:
            results_log.append("\n" + summary.replace("*", ""))
            with open(REPORT_FILE, "w", encoding="utf-8") as f: f.write("\n".join(results_log))
            send_tg_file(REPORT_FILE, f"转移记录 ({success_count}项)")
            if not SAVE_LOCAL_REPORT and os.path.exists(REPORT_FILE): os.remove(REPORT_FILE)
        else:
            print("💡 无新增资源处理，未生成报告。")

if __name__ == "__main__":
    main()
