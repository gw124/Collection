import os
import time
import random

# ================= 配置区 =================
# 对比对：(源目录, 目标参考目录)
DIR_PAIRS = [
    ("/root/Wen/CloudDrive/115/Media/每日更新/电影/", "/root/Wen/CloudDrive/115/Media/电影/"),
    ("/root/Wen/CloudDrive/115/Media/每日更新/电视剧/", "/root/Wen/CloudDrive/115/Media/电视剧/"),
    ("/root/Wen/CloudDrive/115/Media/每日更新/动漫/", "/root/Wen/CloudDrive/115/Media/动漫/"),
]

# --- 小文件夹清理开关 ---
CLEAN_SMALL_DIRS = True           # 是否开启小文件夹清理
SMALL_DIR_THRESHOLD_MB = 10       # 体积阈值，单位 MB（小于此数值则删除整个文件夹）

# --- 风控避让设置 ---
SLEEP_MIN = 0.3
SLEEP_MAX = 1.0
# ==========================================

def get_dir_size_mb(path):
    """计算文件夹总大小 (MB)"""
    total_size = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                # 不计入软连接
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception:
        pass
    return total_size / (1024 * 1024)

def process_fast_match(source_base, target_base):
    print(f"\n{'='*50}")
    print(f"【精准匹配模式】\n源目录: {source_base}\n参考库: {target_base}")
    
    if not os.path.exists(source_base):
        print("跳过: 源目录不存在")
        return

    del_count = 0
    
    # 1. 遍历并执行文件比对删除
    for root, dirs, files in os.walk(source_base):
        for file in files:
            full_source_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_source_path, source_base)
            corresponding_target_path = os.path.join(target_base, rel_path)

            if os.path.exists(corresponding_target_path):
                try:
                    os.remove(full_source_path)
                    del_count += 1
                    print(f"  [发现重复并删除] {rel_path}")
                    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                except Exception as e:
                    print(f"  [删除失败] {rel_path}: {e}")

    # 2. 小文件夹清理逻辑
    if CLEAN_SMALL_DIRS:
        print(f"\n检查小于 {SMALL_DIR_THRESHOLD_MB}MB 的残留文件夹...")
        # 使用 topdown=False 确保先处理最深层的子目录
        for root, dirs, _ in os.walk(source_base, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                
                # 跳过源目录根路径本身
                if dir_path == source_base:
                    continue
                
                size_mb = get_dir_size_mb(dir_path)
                
                if size_mb < SMALL_DIR_THRESHOLD_MB:
                    try:
                        # 再次确认目录是否存在（可能被父级一起删了）
                        if os.path.exists(dir_path):
                            # 使用 shutil 递归删除非空的小文件夹
                            import shutil
                            shutil.rmtree(dir_path)
                            print(f"  [清理小目录] {d} (体积: {size_mb:.2f}MB)")
                            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                    except Exception as e:
                        print(f"  [清理失败] {d}: {e}")

    print(f"\n任务结束。本次清理了 {del_count} 个重复文件。")

def main():
    start_time = time.time()
    for src, tgt in DIR_PAIRS:
        process_fast_match(src, tgt)
    print(f"\n{'='*50}")
    print(f"全部任务运行结束，总耗时: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
