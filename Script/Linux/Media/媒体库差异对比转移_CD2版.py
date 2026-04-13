import os
import shutil
import re
import urllib.request
import urllib.parse
import json
import time
import random
import uuid
from datetime import datetime

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

# =====================================================================
# 🌟 【CloudDrive2 原生 API 执行配置】 🌟 (终极提速与防止网盘风控)
# =====================================================================
# === CloudDrive gRPC API 设置 ===
USE_CLOUDDRIVE_API = True               # API 执行开关：True 为调用 API 执行移动/复制，False 为本地 OS 执行(默认关闭)

CD_SERVER_ADDRESS = "localhost:19798"   # CloudDrive 服务地址及端口
CD_USERNAME = ""                        # 方式 1: 你的 CloudDrive 登录账号
CD_PASSWORD = ""                        # 方式 1: 你的 CloudDrive 登录密码
CD_API_TOKEN = ""   # 方式 2: API Token（优先。若填写此项，将忽略账号密码）

# 本地挂载根目录：用于将本地路径(如 /volume1/CloudNAS/CloudDrive/115/Media) 转换为 API 识别的云端绝对路径(/115/Media)
CD_LOCAL_MOUNT_ROOT = "/volume1/CloudNAS/CloudDrive" 
# -------------------------

REPORT_FILE_NAME = "媒体对比同步报告.txt" 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = os.path.join(SCRIPT_DIR, REPORT_FILE_NAME)

# ==================== 工具函数 ====================

results_log = [] 

class CloudDrive2GRPC:
    """CloudDrive 2 官方 gRPC API 引擎封装"""
    def __init__(self, address, username, password, token):
        try:
            import grpc
            import clouddrive_pb2_grpc
            import clouddrive_pb2
            self.pb2 = clouddrive_pb2
            self.pb2_grpc = clouddrive_pb2_grpc
            self.grpc = grpc
        except ImportError:
            raise Exception("缺少 gRPC 模块或 pb2 协议文件！请仔细阅读执行指引，先编译 clouddrive.proto")

        self.channel = self.grpc.insecure_channel(address)
        self.stub = self.pb2_grpc.CloudDriveFileSrvStub(self.channel)
        self.jwt_token = None

        # 智能鉴权：Token 优先，其次账号密码
        if token and str(token).strip():
            self.jwt_token = str(token).strip()
        elif username and password:
            req = self.pb2.GetTokenRequest(userName=username, password=password)
            resp = self.stub.GetToken(req)
            if resp.success:
                self.jwt_token = resp.token
            else:
                raise Exception(f"CD2 API 账密登录失败: {resp.errorMessage}")
        else:
            raise Exception("CD2 API 认证配置错误：请提供 API Token 或 账号密码")

    def _meta(self):
        return [('authorization', f'Bearer {self.jwt_token}')]

    def process_file(self, src_path, dest_parent_path, is_move):
        """执行复制或移动"""
        if is_move:
            req = self.pb2.MoveFileRequest(
                theFilePaths=[src_path], 
                destPath=dest_parent_path, 
                conflictPolicy=0 # 0=Overwrite，交由外部防撞名逻辑保障安全
            )
            resp = self.stub.MoveFile(req, metadata=self._meta())
        else:
            req = self.pb2.CopyFileRequest(
                theFilePaths=[src_path], 
                destPath=dest_parent_path, 
                conflictPolicy=0
            )
            resp = self.stub.CopyFile(req, metadata=self._meta())

        if not resp.success:
            raise Exception(resp.errorMessage)

    def rename_file(self, target_path, new_name):
        """执行重命名"""
        req = self.pb2.RenameFileRequest(
            theFilePath=target_path, 
            newName=new_name
        )
        resp = self.stub.RenameFile(req, metadata=self._meta())
        if not resp.success:
            raise Exception(resp.errorMessage)


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
    mode_text = "🟢 [模拟演习]" if DRY_RUN else "🔴 [实弹执行]"
    api_text = "🌐 [云端 API 引擎]" if USE_CLOUDDRIVE_API else "💻 [本地 NAS 引擎]"
    log_and_print(f"🚀 媒体库差异对比与转移脚本启动 {mode_text} {api_text}...", write_to_report=True)
    send_tg_msg(f"🔔 *媒体库差异对比与转移脚本启动 {mode_text} {api_text}*")

    success_count = 0
    skip_count = 0

    # 预初始化 API 引擎
    cd2_api = None
    if USE_CLOUDDRIVE_API and not DRY_RUN:
        try:
            cd2_api = CloudDrive2GRPC(CD_SERVER_ADDRESS, CD_USERNAME, CD_PASSWORD, CD_API_TOKEN)
            log_and_print("✅ 成功连接至 CloudDrive 2 gRPC 服务器！", write_to_report=False)
        except Exception as e:
            log_and_print(f"❌ 严重错误: API引擎启动失败 ({e})\n请检查配置或 pb2 协议文件。脚本中止！", write_to_report=True)
            return

    def execute_transfer(src_local, dest_local_target, is_move, op_text, item_name):
        """核心执行中转器：负责分发给 API 或 本地执行，并处理防撞名重命名"""
        nonlocal success_count
        
        # 无论 API 还是本地，先在本地创建父目录，确保 NAS 挂载路径正常连通
        parent_dir_local = os.path.dirname(dest_local_target)
        os.makedirs(parent_dir_local, exist_ok=True)

        if USE_CLOUDDRIVE_API:
            # 路径翻译：去除挂载根目录前缀，转换为内部路径 (如 "/115/Media/xxx")
            src_cd2 = src_local.replace(CD_LOCAL_MOUNT_ROOT, "", 1).replace("\\", "/")
            if not src_cd2.startswith("/"): src_cd2 = "/" + src_cd2
            
            dest_target_cd2 = dest_local_target.replace(CD_LOCAL_MOUNT_ROOT, "", 1).replace("\\", "/")
            if not dest_target_cd2.startswith("/"): dest_target_cd2 = "/" + dest_target_cd2
            
            dest_parent_cd2 = os.path.dirname(dest_target_cd2).replace("\\", "/")
            dest_basename_target = os.path.basename(dest_target_cd2)
            src_basename = os.path.basename(src_cd2)

            try:
                if src_basename == dest_basename_target:
                    # 名字一致无冲突，直接调用 API 移入目标父目录
                    cd2_api.process_file(src_cd2, dest_parent_cd2, is_move)
                else:
                    # 发生本地重命名防撞名 (如 Movie 变成了 Movie-1)
                    # 由于 API Move/Copy 只能指定目标父目录，我们需要使用“缓存目录中转法”来安全改名
                    temp_dir_cd2 = f"{dest_parent_cd2}/_api_temp_{uuid.uuid4().hex[:8]}"
                    # 先通过本地确保 temp 存在
                    os.makedirs(CD_LOCAL_MOUNT_ROOT + temp_dir_cd2, exist_ok=True)
                    
                    # 1. 移入临时目录
                    cd2_api.process_file(src_cd2, temp_dir_cd2, is_move)
                    # 2. 在临时目录内重命名为目标防撞名字 (如 Movie-1)
                    cd2_api.rename_file(f"{temp_dir_cd2}/{src_basename}", dest_basename_target)
                    # 3. 将改名后的文件从临时目录移回真正的父目录 (这一步必须是移动)
                    cd2_api.process_file(f"{temp_dir_cd2}/{dest_basename_target}", dest_parent_cd2, is_move=True)
                    # 4. 删除临时目录
                    try: os.rmdir(CD_LOCAL_MOUNT_ROOT + temp_dir_cd2)
                    except: pass

                log_and_print(f"✅ {op_text}成功 (API): {item_name}", write_to_report=True)
                success_count += 1
                if ENABLE_REALTIME_PUSH: send_tg_msg(f"✅ *完成 ({op_text})*\nAPI模式: `{item_name}`")
            except Exception as e:
                log_and_print(f"❌ API {op_text}失败 ({item_name}): {e}", write_to_report=True)
        else:
            # 原生本地执行
            try:
                if is_move: shutil.move(src_local, dest_local_target)
                else: 
                    if os.path.isdir(src_local):
                        shutil.copytree(src_local, dest_local_target, dirs_exist_ok=True, copy_function=shutil.copyfile)
                    else:
                        shutil.copyfile(src_local, dest_local_target)
                log_and_print(f"✅ {op_text}成功 (本地): {item_name}", write_to_report=True)
                success_count += 1
                if ENABLE_REALTIME_PUSH: send_tg_msg(f"✅ *完成 ({op_text})*\n本地模式: `{item_name}`")
            except Exception as e:
                log_and_print(f"❌ 本地 {op_text}失败 ({item_name}): {e}", write_to_report=True)


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
            missing_items = set() 

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
                        
                        a_season_dirs = set(d for d in a_items if os.path.isdir(os.path.join(a_dir, d)) and re.search(r'(?i)^(season|specials|第.*季|sp)', d.strip()))
                        
                        if a_season_dirs:
                            b_dirs = set(d for d in b_items if os.path.isdir(os.path.join(b_dir, d)))
                            missing_items = a_season_dirs - b_dirs
                        else:
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

            # 【第三步：执行转移 (应用防撞名与双引擎调度)】
            op_text = "移动" if IS_MOVE_MODE else "复制"
            
            if is_new_entirely:
                final_c_dir = get_unique_path(c_dir_initial)
                if final_c_dir != c_dir_initial:
                    log_and_print(f"⚠️ 发现同名残留！已自动重命名为: {os.path.basename(final_c_dir)}")

                if DRY_RUN:
                    log_and_print(f"✅ [模拟] 准备{op_text}至: {final_c_dir}", write_to_report=True)
                    success_count += 1
                else:
                    log_and_print(f"⏳ 正在执行{op_text} (整体)... 请稍候: {rel_path}", write_to_report=False)
                    execute_transfer(a_dir, final_c_dir, IS_MOVE_MODE, op_text, folder_name)
            else:
                for item in missing_items:
                    a_item = os.path.join(a_dir, item)
                    c_item_initial = os.path.join(c_dir_initial, item)
                    final_c_item = get_unique_path(c_item_initial)

                    if DRY_RUN:
                        log_and_print(f"✅ [模拟] 准备{op_text}增量内容至: {final_c_item}", write_to_report=True)
                        success_count += 1
                    else:
                        log_and_print(f"⏳ 正在执行{op_text} (增量)... 请稍候: {item}", write_to_report=False)
                        execute_transfer(a_item, final_c_item, IS_MOVE_MODE, op_text, f"{folder_name} - {item}")

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
            f"执行引擎: {'CD2 官方 API' if USE_CLOUDDRIVE_API else 'NAS 本地 IO'}\n"
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