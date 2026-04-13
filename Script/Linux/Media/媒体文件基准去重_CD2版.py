import os
import sys
import time
import urllib.request
import urllib.parse
import json
import re
from pathlib import Path
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

# ================= 配置区域 =================
# 基准库
DIR_A = "/volume1/CloudNAS/CloudDrive/115/Media" 
# 去重库
DIR_B = "/volume1/CloudNAS/CloudDrive/115/Media/每日更新"

# 屏蔽设置
EXCLUDE_DIRS = ["每日更新", "@eaDir", "#recycle"] 

# 安全开关 (True 为测试模式，False 为正式执行彻底删除)
DRY_RUN = False       

# --- Telegram 推送设置 ---
TG_BOT_TOKEN = ""   # 请填入你的 Token
TG_CHAT_ID = ""     # 请填入你的 Chat ID

# 实时推送开关 (True 为开启去重明细实时推送，False 为仅推送开头和结尾的汇总报告)
TG_REALTIME_PUSH = True  

# === CloudDrive gRPC API 设置 ===
USE_CLOUDDRIVE_API = False              # API 执行开关：True 为调用 API 删除，False 为本地 OS 删除。默认关闭

CD_SERVER_ADDRESS = "localhost:19798"   # CloudDrive 服务地址及端口
CD_USERNAME = ""                        # 方式 1: 你的 CloudDrive 登录账号
CD_PASSWORD = ""                        # 方式 1: 你的 CloudDrive 登录密码
CD_API_TOKEN = ""                       # 方式 2: API Token（优先。若填写此项，将忽略账号密码）

# 本地挂载根目录：用于将本地路径(如 /volume1/CloudNAS/CloudDrive/115/Media) 转换为 API 识别的云端绝对路径(/115/Media)
CD_LOCAL_MOUNT_ROOT = "/volume1/CloudNAS/CloudDrive" 
# ============================================

# 媒体与去重参数
MEDIA_EXTS = {'.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.wmv', '.flv', '.mov', '.m2ts', '.iso'}
DELAY_DIR_SCAN = 1.0   
DELAY_FILE_DEL = 1.5   

# 全局 API 变量
cd_stub = None
cd_metadata = None

def init_clouddrive_api():
    """初始化并登录 CloudDrive gRPC API"""
    global cd_stub, cd_metadata
    try:
        import grpc
        import clouddrive_pb2
        import clouddrive_pb2_grpc
    except ImportError:
        print("\n❌ 缺少 gRPC 依赖或接口文件！")
        print("请在终端执行以下命令生成环境：")
        print("pip3 install grpcio grpcio-tools")
        print("wget https://www.clouddrive2.com/api/clouddrive.proto")
        print("python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clouddrive.proto\n")
        sys.exit(1)

    print(">>> 正在初始化 CloudDrive API 连接...")
    channel = grpc.insecure_channel(CD_SERVER_ADDRESS)
    cd_stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)

    if CD_API_TOKEN:
        print("    使用 API Token 认证...")
        token = CD_API_TOKEN
    else:
        print(f"    使用账号密码认证 ({CD_USERNAME})...")
        req = clouddrive_pb2.GetTokenRequest(userName=CD_USERNAME, password=CD_PASSWORD)
        try:
            resp = cd_stub.GetToken(req)
            if resp.success:
                token = resp.token
                print("    认证成功！")
            else:
                print(f"\n❌ CloudDrive 登录失败: {resp.errorMessage}")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ CloudDrive 连接异常: {e}")
            sys.exit(1)
            
    cd_metadata = [('authorization', f'Bearer {token}')]

def execute_delete(local_path_str, is_dir=False):
    """根据开关执行 本地删除 或 API删除"""
    if USE_CLOUDDRIVE_API:
        import clouddrive_pb2
        # 将本地路径映射为 API 认识的云端绝对路径
        api_path = local_path_str.replace(CD_LOCAL_MOUNT_ROOT, "")
        if not api_path.startswith("/"):
            api_path = "/" + api_path
            
        req = clouddrive_pb2.FileRequest(path=api_path)
        resp = cd_stub.DeleteFile(req, metadata=cd_metadata)
        if not resp.success:
            raise Exception(resp.errorMessage)
    else:
        # 本地 OS 执行模式
        if is_dir:
            os.rmdir(local_path_str)
        else:
            os.remove(local_path_str)

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
    
    if USE_CLOUDDRIVE_API:
        init_clouddrive_api()
    
    start_time = time.time()
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count_movie, count_episode, count_metadata, count_folders = 0, 0, 0, 0

    mode_label = "⚠️ 测试模式 (不删除)" if DRY_RUN else "🚀 正式清理模式"
    engine_label = "🌐 CloudDrive API 接口" if USE_CLOUDDRIVE_API else "💻 本地文件系统"
    
    start_msg = (
        f"🔔 基准去重任务启动\n"
        f"=========================\n"
        f"模式: {mode_label}\n"
        f"引擎: {engine_label}\n"
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

        folder_db_id_b = extract_db_id(root_path.name)
        folder_db_id_a = extract_db_id(target_path_a.name)

        for f in files:
            file_path = Path(f)
            stem_b = file_path.stem
            clean_b = stem_b.replace(" ", "").lower()
            prefix_b = get_clean_prefix(stem_b)
            ep_code_b = extract_ep(f)
            
            db_id_b = extract_db_id(f) or folder_db_id_b
            
            matched_a_file = None
            
            for stem_a, original_a_name in a_bases.items():
                clean_a = stem_a.replace(" ", "").lower()
                prefix_a = get_clean_prefix(stem_a)
                ep_code_a = extract_ep(original_a_name)
                db_id_a = extract_db_id(original_a_name) or folder_db_id_a

                if db_id_b and db_id_a and db_id_b != db_id_a:
                    continue

                if clean_b == clean_a:
                    matched_a_file = target_path_a / original_a_name
                    break
                
                if f.startswith(f"{stem_a}-") or f.startswith(f"{stem_a}."):
                    matched_a_file = target_path_a / original_a_name
                    break
                
                if ep_code_b and ep_code_a and ep_code_b == ep_code_a:
                    matched_a_file = target_path_a / original_a_name
                    break
                
                if is_movie_dir:
                    if db_id_b and db_id_a and db_id_b == db_id_a:
                        matched_a_file = target_path_a / original_a_name
                        break
                    elif prefix_b and prefix_a and prefix_b == prefix_a:
                        matched_a_file = target_path_a / original_a_name
                        break
            
            if matched_a_file:
                full_path_b = root_path / f
                full_path_b_str = str(full_path_b)
                
                is_main_media = file_path.suffix.lower() in MEDIA_EXTS
                
                if is_main_media:
                    if is_movie_dir: count_movie += 1
                    else: count_episode += 1
                else:
                    count_metadata += 1

                if DRY_RUN:
                    print(f"[测试] 智能命中 -> 拟删除: {full_path_b_str}")
                    print(f"               参照基准库: {matched_a_file}")
                    
                    # 实时推送 (测试模式)
                    if TG_REALTIME_PUSH and is_main_media:
                        send_tg_msg(f"👀 [测试拟删除]\n🎬 {file_path.name}")
                else:
                    print(f"[*] 执行删除: {full_path_b_str}")
                    print(f"  参照基准库: {matched_a_file}")
                    try:
                        execute_delete(full_path_b_str, is_dir=False)
                        time.sleep(DELAY_FILE_DEL)
                        
                        # 实时推送 (正式模式)
                        if TG_REALTIME_PUSH and is_main_media:
                            send_tg_msg(f"🗑️ [成功删除]\n🎬 {file_path.name}")
                    except Exception as e:
                        print(f"[!] 删除失败: {e}")
                        
                        # 失败时强制推送 (不受文件类型限制)
                        if TG_REALTIME_PUSH:
                            send_tg_msg(f"❌ [删除失败]\n📁 {file_path.name}\n⚠️ 原因: {e}")
                        
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
                    execute_delete(str(root_path), is_dir=True)
                    print(f"[*] 已清理空目录: {root_path}")
                    time.sleep(DELAY_FILE_DEL)
                count_folders += 1
        except OSError:
            pass
        except Exception as e:
            if not DRY_RUN:
                print(f"[!] 清理空目录失败 {root_path}: {e}")
                
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
        f"引擎: {engine_label}\n"
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