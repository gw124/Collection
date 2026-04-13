import os
import re
import time
import sys
import requests
import shutil

# ================= 使用CloudDrive2前安装相关依赖，本地不需要。 =================

# 1. 进入你存放脚本的目录
# cd /volume1/docker/CloudDrive/Script/

# 2. 安装 Python 的 gRPC 依赖库
# pip3 install grpcio grpcio-tools

# 3. 下载 CloudDrive 官方的 proto 接口定义文件
# wget https://www.clouddrive2.com/api/clouddrive.proto

# 4. 编译生成 Python 接口文件
# python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clouddrive.proto

# ============================================

# ================= 基础配置区域 =================

# 【扫描路径配置】
# 脚本会遍历这些路径。它会自动提取最后一个文件夹名作为你的“媒体库分类”（如“电视剧”、“动漫”）。
BASE_PATHS = [
    "/volume1/CloudNAS/CloudDrive/115/Media/电视剧",
    "/volume1/CloudNAS/CloudDrive/115/Media/动漫"
]

# =====================================================================
# 🌟 【CloudDrive2 原生 API 执行配置】 🌟 (终极提速与防止网盘风控)
# =====================================================================
# === CloudDrive gRPC API 设置 ===
USE_CLOUDDRIVE_API = True              # API 执行开关：True 为调用 API 删除，False 为本地 OS 删除默认关闭

CD_SERVER_ADDRESS = "localhost:19798"   # CloudDrive 服务地址及端口
CD_USERNAME = ""                        # 方式 1: 你的 CloudDrive 登录账号
CD_PASSWORD = ""                        # 方式 1: 你的 CloudDrive 登录密码
CD_API_TOKEN = ""                       # 方式 2: API Token（优先。若填写此项，将忽略账号密码）

# 本地挂载根目录：用于将本地路径(如 /volume1/CloudNAS/CloudDrive/115/Media) 转换为 API 识别的云端绝对路径(/115/Media)
CD_LOCAL_MOUNT_ROOT = "/volume1/CloudNAS/CloudDrive" 
# -------------------------

# 🌟【模拟测试模式】🌟 
# True = 开启测试。脚本会正常扫描并输出报告，但【绝对不会】执行任何真实的删除或移动操作，仅打印预期行为。
# False = 关闭测试。脚本会真实执行物理删除和文件转移（高危操作，请确认后再关闭测试！）。
DRY_RUN = False

# 🌟【豁免/排除路径池 (按绝对路径)】🌟
# 填入你【绝对不想被扫描、去重或删除】的文件夹路径。支持填写多个。
# 智能匹配：填入整剧路径，则整剧被忽略；填入具体的 Season 路径，则仅忽略该季。
EXCLUDE_PATHS = [
    # 示例用法 (把不想碰的路径用双引号包起来，逗号分隔，不用的话可以留空)：
    # "/volume1/CloudNAS/CloudDrive/115/Media/动漫/航海王 (1999) {tmdb-37854}",
]

# 🌟【全局文件夹名称排除 (按文件夹名)】🌟
# 只要文件夹名字包含在这里，不管在哪个剧集下都会被直接跳过（不区分大小写）。
# 专用于一键全局排除剧场版、特别篇、花絮等。
EXCLUDE_FOLDER_NAMES = [
    "Season 0", 
    "Specials"
]

# 【自动去重开关】
# True = 开启。当发现同一个 Season 文件夹里有重复集数时，触发“两轮 PK 淘汰制”，只保留最好的一个，其余物理删除。
# False = 关闭。发现重复时只在报告里记录警告，绝不动手删文件。
AUTO_DELETE_DUPLICATES = True  

# 【去重优先级排序】(仅当 AUTO_DELETE_DUPLICATES = True 时生效)
# 作用：从左到右，越靠前的后缀优先级越高（遇到重复时优先存活）。
# 补充：如果两个文件后缀一模一样（比如都是 mp4），脚本会自动比较它们的物理体积，保留体积更大的那个。
EXT_PRIORITY = ['.mkv', '.mp4', '.ts', '.avi', '.flv', '.rmvb', '.webm', '.mov', '.iso']

# =====================================================================
# 【高危操作：缺集连坐删除/转移开关】
# ⚠️ 警告：物理删除操作极其高危！建议只有在确认刮削完美时才开启。
# =====================================================================

# 🌟 刮削错乱处理模式（默认 False）：
# 只有在发现“同一集存在重复文件，且这些重复文件的年份互不相同”时触发。
# 一旦判定为刮削彻底串台污染，仅物理删除【错乱的当前 Season 季】文件夹。
# 如果整部剧集里只有这 1 个季，为了防止留下空壳根目录，直接物理删除整部剧。
DELETE_CORRUPTED_SHOW = True

# 🌟【缺集转移补救模式】🌟 
# True = 开启。发现缺集时，将其移动到指定刮削目录进行补救。
# 智能逻辑：多季剧仅移动缺集的 Season（并在目标区自动建好剧名父级）；单季剧则整剧连锅端移动。
# 优先级说明：如果下方的 DELETE_ENTIRE_SHOW 为 True，则无视转移，直接执行整剧删除！
MOVE_MISSING_TO_SYNC = True
SYNC_TARGET_DIR = "/volume1/CloudNAS/CloudDrive/115/Sync/每日刮削"

# 灭门模式（默认 False）：如果检测到该剧集任一季有缺集，直接物理删除【整部剧集】的根目录。
# ⚠️ 优先级最高：开启此项后，上面的转移开关和下方的单季删除均自动失效。
DELETE_ENTIRE_SHOW = False  

# 精准打击模式（默认 False）：如果检测到缺集，仅物理删除【当前缺集的 Season 季】文件夹。
# 如果整部剧集里只有这 1 个季了，为了防止留下空荡荡的剧集根目录，直接物理删除整部剧。
DELETE_ONLY_SEASON = False 

# =====================================================================
# 🌟 【本地盲扫强化：单集孤岛防御】 🌟 (专门解决不开 TMDB 时的死角)
# =====================================================================
# True = 开启。既然是“剧集 (TV Show)”，一个正规的 Season 文件夹里就不可能只有 1 集（除非刚开播）。
# 如果扫描发现某个 Season 里孤零零地只躺着 1 个视频文件，且这集【大于第1集】（如只有第25集），
# 脚本将直接判定该季严重缺集，触发补救移动！(如果是第1集，则安全放行，方便追更)
DETECT_SINGLE_EPISODE_ISLAND = True

# 【本地报告生成开关】
# True = 扫描结束后，会在脚本同级目录下永久保留一份 txt 详细报告。
# False = 不保留本地文件。扫描结束后，如果下方开启了 TG 文件推送，报告会被发送到你手机上，随后瞬间把 NAS 上的文件删掉（阅后即焚）。
ENABLE_LOCAL_REPORT = False

# 【报告输出名称】
# 导出的检测报告文件名。
OUTPUT_FILE = "剧集缺集检测报告.txt"

# 【防风控延迟机制】(单位：秒)
# 每扫一个文件夹暂停一下。模拟人类操作速度，防止因为全速无缝扫描被 115 网盘风控拦截或封禁 API。
SCAN_DELAY = 0.02 

# 【识别后缀名单】
# 只有属于这些后缀的文件，才会被脚本当做视频去提取集数（防止误判字幕、海报、nfo 等文件）。
VIDEO_EXTS = {'.mp4', '.mkv', '.ts', '.avi', '.rmvb', '.flv', '.iso', '.mov', '.m4v', '.wmv', '.webm'}

# ================= Telegram 推送配置 =================

ENABLE_TG_START = True      # 🌟 新增：扫描开始时发送一条启动通知
ENABLE_TG_REALTIME = True   # 扫描过程中，只要发现缺集或重复，立刻发送告警消息
ENABLE_TG_SUMMARY = True    # 扫描结束后，发送一条包含“总耗时、总缺集数量”的汇总消息 (即结束推送)
ENABLE_TG_FILE = True       # 扫描结束后，将详细的 txt 报告作为附件文件发送给你

# 你的 Telegram Bot Token 和接收消息的 Chat ID
TG_BOT_TOKEN = ""    
TG_CHAT_ID = ""        

# 网络代理。如果你的 NAS 在国内环境无法直连 TG 接口，请在此配置代理（如无需求留空 None 即可）。
PROXIES = None 

# =====================================================================
# 🌟 【TMDB API 绝对真理校验 与 连载豁免】 🌟
# =====================================================================
TMDB_API_KEY = "" # 强烈建议填入，但是有可能某些剧集因版本问题无法与TMDB对应！例如 "a1b2c3d4e5f6g7h8i9j0"

# 🌟【连载中剧集：尾部缺集豁免开关】🌟
# True = 开启。如果 TMDB 识别到该剧正在“连载中 (Returning Series)”，且你本地只缺最新还没播/没下的集数（中间没断档），则【不视为缺集】，不执行删除或转移。
# False = 关闭。不管连不连载，只要本地集数少于 TMDB 的总集数，一律视为缺集处理。
IGNORE_ONGOING_TRAILING_MISSING = True

TMDB_CACHE = {} 

# ================= gRPC 模块导入检测 =================
GRPC_AVAILABLE = False
try:
    import grpc
    import clouddrive_pb2
    import clouddrive_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    pass

# ================= CD2 原生 API 客户端类 =================
class CloudDrive2Client:
    def __init__(self):
        self.channel = grpc.insecure_channel(CD_SERVER_ADDRESS)
        self.stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(self.channel)
        self.jwt_token = None

        if CD_API_TOKEN.strip():
            self.jwt_token = CD_API_TOKEN
        else:
            self._login(CD_USERNAME, CD_PASSWORD)

    def _login(self, username, password):
        req = clouddrive_pb2.GetTokenRequest(userName=username, password=password)
        resp = self.stub.GetToken(req)
        if resp.success:
            self.jwt_token = resp.token
        else:
            raise Exception(f"CD2 登录失败: {resp.errorMessage}")

    def _meta(self):
        return [('authorization', f'Bearer {self.jwt_token}')] if self.jwt_token else []

    def delete_file(self, path):
        req = clouddrive_pb2.FileRequest(path=path)
        res = self.stub.DeleteFile(req, metadata=self._meta())
        if not res.success: raise Exception(res.errorMessage)

    def rename_file(self, path, new_name):
        req = clouddrive_pb2.RenameFileRequest(theFilePath=path, newName=new_name)
        res = self.stub.RenameFile(req, metadata=self._meta())
        if not res.success: raise Exception(res.errorMessage)

    def ensure_folder(self, parent_path, folder_name):
        req = clouddrive_pb2.CreateFolderRequest(parentPath=parent_path, folderName=folder_name)
        self.stub.CreateFolder(req, metadata=self._meta()) # 如果已存在会自动忽略

    def move_file(self, src_path, dest_path):
        req = clouddrive_pb2.MoveFileRequest(
            theFilePaths=[src_path],
            destPath=dest_path,
            conflictPolicy=1 # 1 = Rename (冲突时自动重命名保留)
        )
        res = self.stub.MoveFile(req, metadata=self._meta())
        if not res.success: raise Exception(res.errorMessage)

    def close(self):
        self.channel.close()

def to_cd2_path(local_path):
    """将本地 OS 挂载路径转换为 CD2 内部虚拟路径"""
    local_path = local_path.replace('\\', '/')
    mount_path = CD_LOCAL_MOUNT_ROOT.replace('\\', '/')
    if local_path.startswith(mount_path):
        return local_path.replace(mount_path, "", 1)
    return local_path

# ================= 正则预编译 =================
RE_RULES = [
    re.compile(r'[Ss]\d+[Ee](\d+)', re.IGNORECASE), 
    re.compile(r'第(\d+)集'),                       
    re.compile(r'[Ee][Pp]\s*(\d+)', re.IGNORECASE)  
]

# ================= 核心功能函数 =================
def is_excluded(check_path):
    if not EXCLUDE_PATHS: return False
    check_path = os.path.normpath(check_path)
    for ex_path in EXCLUDE_PATHS:
        if not ex_path.strip(): continue
        ex_path = os.path.normpath(ex_path.strip())
        if check_path == ex_path or check_path.startswith(ex_path + os.sep):
            return True
    return False

def count_seasons_in_show(show_path):
    count = 0
    try:
        with os.scandir(show_path) as it:
            for entry in it:
                if entry.is_dir() and ("Season" in entry.name or "Specials" in entry.name):
                    count += 1
    except OSError:
        pass
    return count

def extract_episode_number(filename):
    for regex in RE_RULES:
        match = regex.search(filename)
        if match: return int(match.group(1))
    return None

def get_tmdb_info(tmdb_id):
    if not TMDB_API_KEY.strip():
        return None
    if tmdb_id in TMDB_CACHE:
        return TMDB_CACHE[tmdb_id]

    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=zh-CN"
    try:
        response = requests.get(url, proxies=PROXIES, timeout=5)
        if response.status_code == 200:
            data = response.json()
            info = {
                "status": data.get("status", ""),
                "seasons": {s["season_number"]: s.get("episode_count", 0) for s in data.get("seasons", [])}
            }
            TMDB_CACHE[tmdb_id] = info
            return info
    except Exception:
        pass
    
    TMDB_CACHE[tmdb_id] = None
    return None

def analyze_season_folder(season_path, show_name):
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
    
    expected_start = 1
    expected_end = max_ep
    is_ongoing = False
    ongoing_skipped = False
    true_ep_count = None
    
    tmdb_match = re.search(r'\{tmdb-(\d+)\}', show_name, re.IGNORECASE)
    season_match = re.search(r'Season\s+(\d+)', os.path.basename(season_path), re.IGNORECASE)
    
    if tmdb_match and season_match:
        tmdb_id = tmdb_match.group(1)
        season_num = int(season_match.group(1))
        tmdb_info = get_tmdb_info(tmdb_id)
        
        if tmdb_info is not None:
            is_ongoing = (tmdb_info["status"] == "Returning Series")
            true_ep_count = tmdb_info["seasons"].get(season_num)
            
            if true_ep_count is not None and true_ep_count > 0:
                expected_end = max(max_ep, true_ep_count)
            else:
                expected_start = 1 if min_ep < 20 else min_ep
        else:
            expected_start = 1 if min_ep < 20 else min_ep
    else:
        expected_start = 1 if min_ep < 20 else min_ep

    missing_eps = [i for i in range(expected_start, expected_end + 1) if i not in episodes]
    
    # 🌟 核心升级：单集孤岛防御 (带有 TMDB 互斥锁 与 首集豁免)
    if DETECT_SINGLE_EPISODE_ISLAND and len(episodes) == 1 and true_ep_count is None:
        if min_ep > 1: # 只有一集，且这一集不是第1集（比如只有第25集），报警缺集！
            missing_eps = [f"? (本地孤岛防御：该季仅存第 {min_ep} 集，判定缺集)"]
    
    if IGNORE_ONGOING_TRAILING_MISSING and is_ongoing and missing_eps and len(episodes) > 1:
        middle_missing = [ep for ep in missing_eps if isinstance(ep, int) and ep < max_ep]
        if not middle_missing:
            missing_eps = []
            ongoing_skipped = True
            
    duplicate_eps = {ep: files for ep, files in episodes_map.items() if len(files) > 1}
            
    return {
        "min": min_ep, "max": max_ep, 
        "missing": missing_eps,
        "duplicates": duplicate_eps,
        "expected_start": expected_start, 
        "total_files": sum(len(f) for f in episodes_map.values()),
        "ongoing_skipped": ongoing_skipped
    }

def get_best_file_to_keep(filepaths):
    def score_file(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        ext_score = EXT_PRIORITY.index(ext) if ext in EXT_PRIORITY else 999
        try: size = os.path.getsize(filepath)
        except OSError: size = 0
        return (ext_score, -size)
    sorted_files = sorted(filepaths, key=score_file)
    return sorted_files[0], sorted_files[1:]

def send_tg_message(text):
    if not TG_BOT_TOKEN.strip() or TG_BOT_TOKEN == "YOUR_BOT_TOKEN": return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text}, proxies=PROXIES, timeout=10)
    except Exception as e:
        sys.stdout.write(f"\r[TG推送失败] {e} ".ljust(60) + "\n")

def send_tg_document(filepath, caption=""):
    if not ENABLE_TG_FILE or not TG_BOT_TOKEN.strip() or TG_BOT_TOKEN == "YOUR_BOT_TOKEN": return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    try:
        with open(filepath, 'rb') as f:
            sys.stdout.write("\n正在向 Telegram 发送报告文件...")
            requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": caption}, files={"document": f}, proxies=PROXIES, timeout=30)
    except Exception:
        pass

def fast_scan(base_paths, output_filepath):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    final_output_path = os.path.join(script_dir, output_filepath)
    
    # 🌟 发送开始推送通知
    if ENABLE_TG_START:
        start_msg = (
            f"▶️ **剧集缺集与去重检测任务已启动...**\n"
            f"🚀 引擎: {'⚡️ CloudDrive2 原生 API' if USE_CLOUDDRIVE_API else '💽 本地文件系统'}\n"
            f"🛡️ 模式: {'🟢 模拟测试 (未修改任何文件)' if DRY_RUN else '🔴 真实执行 (物理读写)'}"
        )
        send_tg_message(start_msg)
    
    # 🌟 初始化 CD2 API 客户端
    cd2 = None
    if USE_CLOUDDRIVE_API and not DRY_RUN:
        if not GRPC_AVAILABLE:
            sys.exit("\n❌ 错误: 启用了 USE_CLOUDDRIVE_API，但缺少 grpcio 依赖库或 clouddrive.proto 接口文件。\n"
                     "请执行 'pip3 install grpcio grpcio-tools' 并在本目录下编译接口文件。")
        try:
            print("⏳ 正在初始化 CloudDrive2 API 连接...")
            cd2 = CloudDrive2Client()
        except Exception as e:
            sys.exit(f"\n❌ CloudDrive2 API 初始化失败: {e}\n请检查 CD_SERVER_ADDRESS 和认证信息是否正确。")
            
    need_to_write_file = ENABLE_LOCAL_REPORT or ENABLE_TG_FILE
    if need_to_write_file:
        with open(final_output_path, 'w', encoding='utf-8') as f:
            f.write("================ 媒体库缺集与去重检测报告 =================\n")
            f.write(f"执行引擎: {'⚡️ CloudDrive2 原生 API' if USE_CLOUDDRIVE_API else '💽 本地文件系统'}\n")
            f.write(f"运行模式: {'🟢 模拟测试 (不修改文件)' if DRY_RUN else '🔴 真实执行 (物理读写)'}\n\n")

    print(f"🚀 开始扫描... (引擎: {'CD2-API' if USE_CLOUDDRIVE_API else '本地OS'} | 测试模式: {'✅模拟' if DRY_RUN else '❌实装'} | 去重: {'开启' if AUTO_DELETE_DUPLICATES else '关闭'})")
    
    start_time = time.time()
    missing_summary = {} 
    
    def scan_directory(current_path, current_category_set, auto_strip_prefix):
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if not entry.is_dir(): continue
                    if is_excluded(entry.path): continue
                    if entry.name.lower() in [n.lower() for n in EXCLUDE_FOLDER_NAMES]: continue
                        
                    sys.stdout.write(f"\r🔍 正在扫: {entry.name[:40].ljust(40)}")
                    sys.stdout.flush()
                    time.sleep(SCAN_DELAY) 
                    
                    if "Season" in entry.name or "Specials" in entry.name:
                        show_name = os.path.basename(current_path)
                        report = analyze_season_folder(entry.path, show_name)
                        
                        if report and (report["missing"] or report["duplicates"] or report.get("ongoing_skipped")):
                            if report["missing"]: 
                                current_category_set.add(show_name)
                            
                            friendly_path = entry.path 
                            if auto_strip_prefix and entry.path.startswith(auto_strip_prefix):
                                friendly_path = entry.path[len(auto_strip_prefix):]
                                friendly_path = friendly_path if friendly_path else "/"
                            
                            log_text = f"📺 剧集: {show_name} -> {entry.name}\n"
                            log_text += f"📁 位置: {friendly_path}\n"  
                            log_text += f"📊 统计: 共 {report['total_files']} 个视频。最大至 {report['max']}。\n"

                            if report.get("ongoing_skipped"):
                                log_text += f"ℹ️ 豁免: 识别为连载中剧集，无中间断档，尾部待更新集数已安全忽略\n"

                            # ================= 刮削致命错乱检测 =================
                            is_corrupted = False
                            corrupt_del_status = ""
                            if DELETE_CORRUPTED_SHOW and report["duplicates"]:
                                for ep, files in report["duplicates"].items():
                                    years = set()
                                    for f in files:
                                        m = re.search(r'\((\d{4})\)', os.path.basename(f))
                                        if m: years.add(m.group(1))
                                    
                                    if len(years) > 1:
                                        is_corrupted = True
                                        log_text += f"🚨 致命错乱: 第 {ep} 集的重复文件中存在不同年份 {years}，刮削已严重污染！\n"
                                        
                                        season_count = count_seasons_in_show(current_path)
                                        if season_count <= 1:
                                            if DRY_RUN:
                                                corrupt_del_status = "🛡️ [模拟] 准备物理删除错乱的整部剧集 (因其只包含这一季)"
                                            else:
                                                try:
                                                    if USE_CLOUDDRIVE_API:
                                                        cd2.delete_file(to_cd2_path(current_path))
                                                    else:
                                                        shutil.rmtree(current_path)
                                                    corrupt_del_status = "🧨 已执行：物理删除错乱的整部剧集 (因其只包含这一季)"
                                                except Exception as e:
                                                    corrupt_del_status = f"❌ 删除错乱整剧失败: {str(e)}"
                                        else:
                                            if DRY_RUN:
                                                corrupt_del_status = "🛡️ [模拟] 准备物理删除错乱的当前季"
                                            else:
                                                try:
                                                    if USE_CLOUDDRIVE_API:
                                                        cd2.delete_file(to_cd2_path(entry.path))
                                                    else:
                                                        shutil.rmtree(entry.path)
                                                    corrupt_del_status = "🧨 已执行：物理删除错乱的当前季"
                                                except Exception as e:
                                                    corrupt_del_status = f"❌ 删除错乱当前季失败: {str(e)}"
                                                
                                        log_text += f"🛡 操作: {corrupt_del_status}\n"
                                        break 
                            
                            if is_corrupted:
                                sys.stdout.write("\r" + " " * 60 + "\r")
                                print(log_text)
                                if need_to_write_file:
                                    with open(final_output_path, 'a', encoding='utf-8') as f:
                                        f.write(log_text + "\n")
                                if ENABLE_TG_REALTIME: send_tg_message(log_text)
                                
                                if "整部剧集" in corrupt_del_status:
                                    return False 
                                else:
                                    continue 

                            # ================= 缺集与去重逻辑 =================
                            if report["missing"]:
                                log_text += f"❌ 缺失: {', '.join(map(str, report['missing']))}\n"
                            
                            if report["duplicates"]:
                                log_text += f"⚠️ 重复: 发现 {len(report['duplicates'])} 集存在重复文件\n"
                                for ep, files in report["duplicates"].items():
                                    if AUTO_DELETE_DUPLICATES:
                                        keep_file, trash_files = get_best_file_to_keep(files)
                                        
                                        stems = [os.path.splitext(os.path.basename(f))[0] for f in files]
                                        cleanest_stem = min(stems, key=len)
                                        kept_ext = os.path.splitext(keep_file)[1]
                                        target_filename = cleanest_stem + kept_ext
                                        target_filepath = os.path.join(os.path.dirname(keep_file), target_filename)
                                        
                                        log_text += f"   ├── 第 {ep} 集 -> ✅保留: {os.path.basename(keep_file)}\n"
                                        
                                        for trash in trash_files:
                                            if DRY_RUN:
                                                log_text += f"   │             -> 🛡️ [模拟] 准备删除: {os.path.basename(trash)}\n"
                                            else:
                                                try:
                                                    if USE_CLOUDDRIVE_API:
                                                        cd2.delete_file(to_cd2_path(trash))
                                                    else:
                                                        os.remove(trash) 
                                                    log_text += f"   │             -> 🗑️已删除: {os.path.basename(trash)}\n"
                                                except Exception as e:
                                                    log_text += f"   │             -> ❌删除失败: {os.path.basename(trash)} ({e})\n"
                                                    
                                        if os.path.basename(keep_file) != target_filename:
                                            if DRY_RUN:
                                                log_text += f"   │             -> 🛡️ [模拟] 准备净化命名: {os.path.basename(keep_file)} -> {target_filename}\n"
                                            else:
                                                try:
                                                    if USE_CLOUDDRIVE_API:
                                                        cd2.rename_file(to_cd2_path(keep_file), target_filename)
                                                        log_text += f"   │             -> 🏷️已净化命名: {target_filename}\n"
                                                    else:
                                                        if not os.path.exists(target_filepath) or target_filepath == keep_file:
                                                            os.rename(keep_file, target_filepath)
                                                            log_text += f"   │             -> 🏷️已净化命名: {target_filename}\n"
                                                        else:
                                                            log_text += f"   │             -> ⚠️命名净化跳过: {target_filename} 仍被占用\n"
                                                except Exception as e:
                                                    log_text += f"   │             -> ❌命名净化失败: {str(e)}\n"
                                    else:
                                        log_text += f"   ├── 第 {ep} 集: 共有 {len(files)} 个重复版本\n"

                            del_status = ""
                            if report["missing"]:
                                season_count = count_seasons_in_show(current_path)
                                
                                if DELETE_ENTIRE_SHOW:
                                    if DRY_RUN:
                                        del_status = "🛡️ [模拟] 准备物理删除整部剧集"
                                    else:
                                        try:
                                            if USE_CLOUDDRIVE_API:
                                                cd2.delete_file(to_cd2_path(current_path))
                                            else:
                                                shutil.rmtree(current_path)
                                            del_status = "🧨 已执行：物理删除整部剧集"
                                        except Exception as e: del_status = f"❌ 删除失败：{str(e)}"
                                    
                                elif MOVE_MISSING_TO_SYNC:
                                    if DRY_RUN:
                                        if season_count <= 1:
                                            del_status = "🛡️ [模拟] 准备移动整部剧集至刮削补救区 (因其只包含这一季)"
                                        else:
                                            del_status = "🛡️ [模拟] 准备移动当前缺集的季至刮削补救区 (已保留剧名父目录)"
                                    else:
                                        try:
                                            if USE_CLOUDDRIVE_API:
                                                if season_count <= 1:
                                                    cd2.move_file(to_cd2_path(current_path), to_cd2_path(SYNC_TARGET_DIR))
                                                    del_status = "🚚 已执行(API)：移动整部剧集至刮削补救区 (因其只包含这一季)"
                                                else:
                                                    cd2.ensure_folder(to_cd2_path(SYNC_TARGET_DIR), show_name)
                                                    dest_dir = os.path.join(SYNC_TARGET_DIR, show_name).replace('\\', '/')
                                                    cd2.move_file(to_cd2_path(entry.path), to_cd2_path(dest_dir))
                                                    del_status = "🚚 已执行(API)：移动当前缺集的季至刮削补救区"
                                            else:
                                                os.makedirs(SYNC_TARGET_DIR, exist_ok=True)
                                                if season_count <= 1:
                                                    dest_path = os.path.join(SYNC_TARGET_DIR, show_name)
                                                    if os.path.exists(dest_path):
                                                        dest_path += f"_{int(time.time())}"
                                                    shutil.move(current_path, dest_path)
                                                    del_status = "🚚 已执行：移动整部剧集至刮削补救区 (因其只包含这一季)"
                                                else:
                                                    dest_show_dir = os.path.join(SYNC_TARGET_DIR, show_name)
                                                    os.makedirs(dest_show_dir, exist_ok=True)
                                                    dest_season_dir = os.path.join(dest_show_dir, entry.name)
                                                    if os.path.exists(dest_season_dir):
                                                        dest_season_dir += f"_{int(time.time())}"
                                                    shutil.move(entry.path, dest_season_dir)
                                                    del_status = "🚚 已执行：移动当前缺集的季至刮削补救区 (已保留剧名父目录)"
                                        except Exception as e:
                                            del_status = f"❌ 移动至刮削补救区失败：{str(e)}"
                                        
                                elif DELETE_ONLY_SEASON:
                                    if season_count <= 1:
                                        if DRY_RUN:
                                            del_status = "🛡️ [模拟] 准备物理删除整部剧集 (因其只包含这一季)"
                                        else:
                                            try:
                                                if USE_CLOUDDRIVE_API:
                                                    cd2.delete_file(to_cd2_path(current_path))
                                                else:
                                                    shutil.rmtree(current_path)
                                                del_status = "🧨 已执行：物理删除整部剧集 (因其只包含这一季)"
                                            except Exception as e: del_status = f"❌ 删除整部剧集失败：{str(e)}"
                                    else:
                                        if DRY_RUN:
                                            del_status = "🛡️ [模拟] 准备物理删除当前季"
                                        else:
                                            try:
                                                if USE_CLOUDDRIVE_API:
                                                    cd2.delete_file(to_cd2_path(entry.path))
                                                else:
                                                    shutil.rmtree(entry.path)
                                                del_status = "🧨 已执行：物理删除当前季"
                                            except Exception as e: del_status = f"❌ 删除当前季失败：{str(e)}"
                            
                            if del_status or report["missing"] or report["duplicates"] or report.get("ongoing_skipped"):
                                if del_status: log_text += f"🛡 操作: {del_status}\n"
                                sys.stdout.write("\r" + " " * 60 + "\r")
                                print(log_text)
                                
                                if need_to_write_file:
                                    with open(final_output_path, 'a', encoding='utf-8') as f:
                                        f.write(log_text + "\n")
                                    
                                if ENABLE_TG_REALTIME: send_tg_message(log_text)
                            
                            if report["missing"] and ("整部剧集" in del_status or DELETE_ENTIRE_SHOW): 
                                return False 
                    else:
                        scan_directory(entry.path, current_category_set, auto_strip_prefix)
        except OSError:
            pass 
        return False

    for path in base_paths:
        if os.path.exists(path):
            clean_path = path.rstrip('/\\')
            category_name = os.path.basename(clean_path)
            
            auto_strip_prefix = os.path.dirname(clean_path)
            
            if category_name not in missing_summary: 
                missing_summary[category_name] = set()
                
            scan_directory(clean_path, missing_summary[category_name], auto_strip_prefix)

    # 🌟 任务结束，断开 CD2 API 连接
    if cd2: cd2.close()

    # ================= 最终统计汇总 =================
    total_seconds = int(time.time() - start_time)
    time_str = f"{total_seconds}秒" if total_seconds < 60 else f"{total_seconds // 60}分{total_seconds % 60}秒"
    total_missing = sum(len(shows) for shows in missing_summary.values())
    
    category_text = ""
    for cat, shows in missing_summary.items():
        category_text += f"   ├─ 📁 {cat}: {len(shows)} 部\n"

    # 🌟 生成结束报告
    summary_text = (
        f"🏁 任务完成！\n"
        f"🚀 执行引擎：{'⚡️ CloudDrive2 原生 API' if USE_CLOUDDRIVE_API else '💽 本地文件系统'}\n"
        f"🛡️ 运行模式：{'模拟测试 (未修改任何文件)' if DRY_RUN else '真实执行 (物理读写)'}\n"
        f"⏱ 用时：{time_str}\n"
        f"⚠️ 缺集总计：{total_missing} 部\n"
        f"{category_text.rstrip()}\n"
        f"🧹 自动去重：{'已执行' if AUTO_DELETE_DUPLICATES else '未开启'}\n"
        f"📅 完成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("\n" + "="*30)
    print(summary_text)
    print("="*30)

    # 🌟 发送结束推送通知
    if ENABLE_TG_SUMMARY: send_tg_message(summary_text)
    
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