import requests
import os
import re
import shutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import traceback


def read_config(config_path="./config/media_category.yaml"):
    if not os.path.exists(config_path):
        print(f"未找到配置文件，正在初始化配置文件::: {config_path}")
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(
                {
                    "tmdb_api_key": "",
                    "config_list": [
                        {
                            "source_dir": "",
                            "dest_dir": "",
                            "move_type": "move",
                            "media_type": "anime",
                            "category_list": {
                                "国漫": ["zh", "cn", "bo", "za"],
                                "日漫": ["ja", "ko"],
                                "美漫": [""],
                            },
                        }
                    ],
                },
                file,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return data
    except Exception as e:
        print(f"配置文件出现问题: {e}")
        return {}


class MediaCategory:
    def __init__(
        self, source_dir, dest_dir, media_type, move_type, category_list
    ) -> None:
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.media_type = media_type
        self.move_type = move_type
        self.category_list = category_list

    def run(self):
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                self.tv_show_category(file_path)

    def tv_show_category(self, source_file):
        try:
            if "tmdb" in source_file:
                tmdbid = re.findall(r"tmdb.*?(\d+)", source_file)
                if tmdbid:
                    tmdbid = tmdbid[0]
                else:
                    return
                original_language, genre_ids = self.get_media_info(tmdbid)
                category_name = None
                if self.media_type == "movie":
                    if 16 in genre_ids:
                        category_name = "动画电影"
                elif self.media_type == "tv show":
                    if 99 in genre_ids:
                        category_name = "纪录片"
                    if 10764 in genre_ids or 10767 in genre_ids:
                        category_name = "综艺"
                if not category_name:
                    last_name = ""
                    for name, language in self.category_list.items():
                        if len(language) == 0:
                            last_name = name
                        if original_language in language:
                            category_name = name
                            break
                    if not category_name:
                        category_name = last_name
                dest_dir = os.path.join(self.dest_dir, category_name)
                dest_file = source_file.replace(self.source_dir, dest_dir)
                if not os.path.exists(os.path.dirname(dest_file)):
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                if not os.path.exists(dest_file):
                    shutil.move(source_file, dest_file)
                    print(f"#媒体分类# 成功转移文件 ::: {source_file} => {dest_file}")
                else:
                    print(f"#媒体分类# 目标目录已经存在文件 ::: {dest_file}")
                time.sleep(0.3)
        except:
            print(traceback.format_exc())
            pass

    def get_media_info(self, tmdb_id):
        """
        根据 TMDB ID 获取剧集的原始语言

        参数:
        tmdb_id (str): TMDB 剧集 ID

        返回:
        str: 剧集的原始语言代码
        """
        api_key = "896c4c7d5af3899b0f56be6824560848"
        match self.media_type:
            case "tv show":
                url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}"
            case "anime":
                url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}"
            case "movie":
                url = url = (
                    f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
                )

        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            original_language = data["original_language"]
            genre_ids = [genre["id"] for genre in data["genres"]]
            return original_language, genre_ids
        else:
            return "Error: Unable to retrieve original language"

    def get_tv_show_id(self, title, year, times=0):
        if times > 10:
            return None
        """
        根据电视剧名称和年份获取 TMDb ID

        Args:
            title (str): 电视剧名称
            year (int): 电视剧发布年份

        Returns:
            int: 电视剧的 TMDb ID，如果没找到则返回 None
        """
        api_key = "896c4c7d5af3899b0f56be6824560848"
        base_url = "https://api.themoviedb.org/3"

        # 构建搜索电视剧的 API 请求
        search_url = f"{base_url}/search/tv?api_key={api_key}&query={title}&year={year}"

        try:
            # 发送 API 请求并获取响应
            response = requests.get(search_url)
            response.raise_for_status()

            # 解析响应中的结果
            data = response.json()
            if data["results"]:
                # 返回第一个匹配的电视剧的 TMDb ID
                return data["results"][0]["id"]
            else:
                time.sleep(1)
                # 如果没有找到匹配的电视剧,则递归调用自身并增加尝试次数
                return self.get_tv_show_id(title, year, times + 1)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            # 如果没有找到匹配的电视剧,则递归调用自身并增加尝试次数
            time.sleep(1)
            return self.get_tv_show_id(title, year, times + 1)


# 剧集分类
source_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/SGNB"
dest_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/Completed"
media_type = "movie"
move_type = "move"
category_list = {
    "国产剧": ["CN", "TW", "HK", "SG"],
    "欧美剧": ["US", "FR", "GB", "DE", "ES", "IT", "NL", "PT", "RU", "UK"],
    "日剧": ["JP"],
    "韩剧": ["KP", "KR"],
    "未分类": [""],
}
m = MediaCategory(source_dir, dest_dir, media_type, move_type, category_list)
m.run()

# 电影分类
source_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/SGNB"
dest_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/Completed"
media_type = "movie"
move_type = "move"
category_list = {
    "华语电影": ["zh", "cn", "bo", "za"],
    "日韩电影": ["ja", "ko", "th"],
    "欧美电影": [],
}
m = MediaCategory(source_dir, dest_dir, media_type, move_type, category_list)
m.run()

# 动漫分类
source_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/SGNB"
dest_dir = "/Users/shenxian/CloudNAS/CloudDrive2/115/Completed"
media_type = "movie"
move_type = "move"
category_list = {
    "国漫": ["zh", "cn", "bo", "za"],
    "日漫": ["ja", "ko"],
    "美漫": [],
}
m = MediaCategory(source_dir, dest_dir, media_type, move_type, category_list)
m.run()
