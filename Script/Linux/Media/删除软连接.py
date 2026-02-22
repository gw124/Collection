import os
import pathlib

# 指定要删除文件的目录
directory = "/volume2/Meida/AutoSymlink"

# 遍历目录下的所有文件
for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)
    if os.path.islink(file_path):
        # 删除文件
        os.remove(file_path)
        print(f"Deleted file: {file_path}")

for root, dirs, files in os.walk(directory):
    for file in files:
        file_path = os.path.join(root, file)
        if os.path.islink(file_path) or file_path.endswith(".strm"):
            # 删除文件
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
