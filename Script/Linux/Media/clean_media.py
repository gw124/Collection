import os
import time
import random

# 配置对比对
DIR_PAIRS = [
    ("/root/Wen/CloudDrive/115/Media/每日更新/电影/", "/root/Wen/CloudDrive/115/Media/电影/"),
    ("/root/Wen/CloudDrive/115/Media/每日更新/电视剧/", "/root/Wen/CloudDrive/115/Media/电视剧/"),
    ("/root/Wen/CloudDrive/115/Media/每日更新/动漫/", "/root/Wen/CloudDrive/115/Media/动漫/"),
]

# 规避风控
SLEEP_MIN = 0.3
SLEEP_MAX = 1.0

def process_fast_match(source_base, target_base):
    print(f"\n{'='*50}")
    print(f"【精准匹配模式】\n源目录: {source_base}\n参考库: {target_base}")
    
    if not os.path.exists(source_base):
        print("跳过: 源目录不存在")
        return

    del_count = 0
    
    # 遍历“每日更新”目录（这里文件通常较少，扫描很快）
    for root, dirs, files in os.walk(source_base):
        for file in files:
            # 获取文件在源目录下的相对路径（包含子文件夹）
            # 例如: "动画电影/哪吒.mp4"
            full_source_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_source_path, source_base)
            
            # 构建它在目标参考库中对应的绝对路径
            # 例如: "/root/.../电影/动画电影/哪吒.mp4"
            corresponding_target_path = os.path.join(target_base, rel_path)

            # --- 核心改进：直接询问系统该路径是否存在 ---
            # 这不会触发全库扫描，只会触发对单个文件的元数据查询
            if os.path.exists(corresponding_target_path):
                try:
                    os.remove(full_source_path)
                    del_count += 1
                    print(f"  [发现重复并删除] {rel_path}")
                    # 稍微停顿，保护网盘 API
                    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
                except Exception as e:
                    print(f"  [删除失败] {rel_path}: {e}")
            else:
                # 目标库没有，保留，不打印信息以保持屏幕清爽
                pass

    # 清理空文件夹
    if del_count > 0:
        print("清理空文件夹...")
        for _ in range(2):
            for r, ds, _ in os.walk(source_base, topdown=False):
                for d in ds:
                    dp = os.path.join(r, d)
                    if not os.listdir(dp):
                        try: os.rmdir(dp)
                        except: pass

    print(f"任务结束。本次清理了 {del_count} 个重复文件。")

def main():
    start_time = time.time()
    for src, tgt in DIR_PAIRS:
        process_fast_match(src, tgt)
    print(f"\n全部耗时: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main()
