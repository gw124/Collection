import os
import shutil
import traceback


def get_video_files(folder_path):
    video_extensions = [
        ".mkv",
        ".iso",
        ".ts",
        ".mp4",
        ".avi",
        ".rmvb",
        ".wmv",
        ".m2ts",
        ".mpg",
        ".flv",
        ".rm",
        ".mov",
    ]
    video_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in video_extensions:
                if "720p" in file:
                    os.remove(os.path.join(root, file))
                    continue
                video_files.append(os.path.join(root, file))
    return video_files


def process_video_files(video_files, resolution):
    if len(video_files) == 1:
        return
    try:
        files_with_2160p = [file for file in video_files if resolution in file]
        if len(files_with_2160p) > 0:
            if len(files_with_2160p) == 1:
                max_file = files_with_2160p[0]
            elif len(files_with_2160p) > 1:
                max_file = max(files_with_2160p, key=os.path.getsize)
            for file in video_files:
                # 只删除当前分辨率的电影文件
                if file != max_file and resolution in file:
                    os.remove(file)
                    print(f"Deleted file: {file}")
                    nfo_file = os.path.splitext(file)[0] + ".nfo"
                    if os.path.exists(nfo_file):
                        os.remove(nfo_file)
                        print(f"Deleted nfo file: {file}")
    except:
        print(traceback.format_exc())
        print(video_files)


# 指定要遍历的文件夹路径
folder_list = [
    "/volume1/CloudNAS/CloudDrive/115/Media/Movie/华语电影",
    "/volume1/CloudNAS/CloudDrive/115/Media/Movie/欧美电影",
    "/volume1/CloudNAS/CloudDrive/115/Media/Movie/日韩电影",
    "/volume1/CloudNAS/CloudDrive/115/Media/Movie/动画电影",
]
folder_num = 0
resolution_list = ["2160p", "1080p"]
for folder_path in folder_list:
    # 遍历文件夹的子文件夹并获取视频文件
    subfolders = [f.path for f in os.scandir(folder_path) if f.is_dir()]
    for subfolder in subfolders:
        for resolution in resolution_list:
            video_files = get_video_files(subfolder)
            if len(video_files) == 0:
                shutil.rmtree(subfolder)
            process_video_files(video_files, resolution)
        folder_num += 1
        print(f"已处理{folder_num}个文件夹.\n")
