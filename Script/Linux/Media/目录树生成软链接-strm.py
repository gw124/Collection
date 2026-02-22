from posixpath import join as joinpath
from re import compile as re_compile
import os
from pathlib import Path
import urllib.parse
import traceback
import time
import shutil


class StrmFileCreator:
    def __init__(
        self,
        source_dir,
        dest_dir,
        cloud_root_path,
        strm_mode="cloud",
        cloud_type="cd2",
        cloud_url="",
    ):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.cloud_root_path = cloud_root_path
        self.strm_mode = strm_mode
        self.cloud_type = cloud_type
        self.cloud_url = cloud_url

    def create_strm_file(self, source_file):
        try:
            # 获取视频文件名和目录
            target_file = source_file.replace(self.source_dir, self.dest_dir)
            video_name = Path(target_file).name
            # 获取视频目录
            dest_path = Path(target_file).parent
            # 构造.strm文件路径
            strm_path = os.path.join(
                dest_path, f"{os.path.splitext(video_name)[0]}.strm"
            )
            if os.path.exists(strm_path):
                os.remove(strm_path)
            if self.strm_mode == "cloud":
                # 云盘模式
                if self.cloud_type:
                    # 替换路径中的\为/
                    target_file = source_file.replace("\\", "/")
                    target_file = target_file.replace(self.cloud_root_path, "")
                    # 对盘符之后的所有内容进行url转码
                    target_file = urllib.parse.quote(target_file, safe="")
                    # 考虑到会有https反代的情况
                    if not self.cloud_url.startswith(
                        "https://"
                    ) and not self.cloud_url.startswith("http://"):
                        self.cloud_url = f"http://{self.cloud_url}"
                    if str(self.cloud_type) == "cd2":
                        # 将路径的开头盘符"/mnt/user/downloads"替换为"http://localhost:19798/static/http/localhost:19798/False/"
                        target_file = f"{self.cloud_url}/static/http/{self.cloud_url}/False/{target_file}"
                    else:
                        print(f"云盘类型 {self.cloud_type} 错误")
                        return
                    target_file = target_file.replace("http/https://", "http/").replace(
                        "http/http://", "http/"
                    )
                # 写入.strm文件
                with open(strm_path, "w", encoding="utf-8") as f:
                    f.write(target_file)
            else:
                strm_content = source_file
                # 写入.strm文件
                with open(strm_path, "w", encoding="utf-8") as f:
                    f.write(strm_content)
            print(f"已经创建strm文件: {source_file} => {strm_path}")

        except Exception as e:
            print(f"创建strm文件失败: {source_file}")
            print(traceback.format_exc())

    @staticmethod
    def parse_115_export_dir_as_path_iter(path):
        cre = re_compile("^(?:\| )+\|-")
        stack = ["/"]
        for i, r in enumerate(open(path, encoding="utf-16")):
            match = cre.match(r)
            if match is None:
                continue
            prefix = match[0]
            prefix_length = len(prefix)
            depth = prefix_length // 2 - 1
            name = r.removesuffix("\n")[prefix_length:]
            try:
                stack[depth] = name
            except IndexError:
                stack.append(name)
            yield joinpath(*stack[: depth + 1])

    @staticmethod
    def measure_time(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            total_time = end_time - start_time
            print(f"总耗时: {total_time:.2f} 秒")
            return result

        return wrapper


@StrmFileCreator.measure_time
def main(
    category_path,
    source_dir,
    dest_dir,
    cloud_root_path,
    symlink_mode,
    metadata_copy,
    cloud_url,
    strm_mode,
):
    strm_creator = StrmFileCreator(
        source_dir, dest_dir, cloud_root_path, cloud_url=cloud_url, strm_mode=strm_mode
    )
    if symlink_mode == "symlink":
        symlink_name = "软链接"
    else:
        symlink_name = "Strm文件"
    symlink_num = 0
    metadata_num = 0
    for filepath in strm_creator.parse_115_export_dir_as_path_iter(category_path):
        source_file = Path(source_dir) / filepath[1:]
        dest_file = Path(dest_dir) / filepath[1:]
        try:
            if filepath.endswith((".mkv", ".mp4", ".ts")):
                if symlink_mode == "strm":
                    dir_path = dest_file.parent
                    if not dir_path.exists():
                        dir_path.mkdir(parents=True, exist_ok=True)
                    if not dest_file.exists():
                        strm_creator.create_strm_file(str(source_file))
                    symlink_num += 1
                else:
                    dir_path = dest_file.parent
                    if not dir_path.exists():
                        dir_path.mkdir(parents=True, exist_ok=True)
                    print(source_file, dest_file)
                    try:
                        if not dest_file.exists():
                            os.symlink(source_file, dest_file)
                            print(f"已经创建软链接: {source_file} => {dest_file}")
                            symlink_num += 1
                    except:
                        print(f"{symlink_name}已经存在,跳过: {dest_file}")
            elif filepath.endswith((".nfo", ".jpg", ".png", ".ass", ".srt")):
                if not metadata_copy:
                    continue
                dir_path = dest_file.parent
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                if not dest_file.exists():
                    try:
                        shutil.copy2(str(source_file), str(dest_file))
                        metadata_num += 1
                        print(f"已经复制元数据: {source_file} => {dest_file}")
                    except Exception as e:
                        print(f"复制文件失败: {source_file}")
                        print(traceback.format_exc())
        except:
            print(traceback.format_exc())
    print(f"共创建 {symlink_num} 个{symlink_name},共复制 {metadata_num} 个元数据 ")


if __name__ == "__main__":
    # 目录树的路径
    category_path = "/Users/shenxian/Downloads/影视合集_目录树.txt"
    # 目录树文件第一行的文件夹在cd2中的路径
    source_dir = "/volume1/CloudNAS/CloudDrive2/115/看剧"
    # 本地目录
    dest_dir = "/Users/shenxian/Downloads/未命名文件夹"
    # cd2根目录
    cloud_root_path = "/volume1/CloudNAS/CloudDrive2"
    # 软链接/strm
    symlink_mode = "symlink"
    # 是否复制元数据
    metadata_copy = False
    # cd2地址
    cloud_url = "http://172.17.0.1:19798"
    # Strm模式:cloud/local
    strm_mode = "cloud"
    main(
        category_path=category_path,
        source_dir=source_dir,
        dest_dir=dest_dir,
        cloud_root_path=cloud_root_path,
        symlink_mode=symlink_mode,
        metadata_copy=metadata_copy,
        cloud_url=cloud_url,
        strm_mode=strm_mode,
    )
