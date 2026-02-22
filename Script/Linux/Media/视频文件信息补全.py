import os
import re
import json
import subprocess


def get_video_metadata(file_path):
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_data",
        "-show_format",
        file_path,
    ]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    return json.loads(result.stdout)


def get_title(filename):
    title = re.findall(r"(.*?)\(", filename)
    if title:
        title = title[0].strip()
        return title
    else:
        return ""
    # symbol_list = [".", "-", "("]
    # final = 0
    # for idx, string in enumerate(filename):
    #     if string in symbol_list:
    #         final = idx
    #         break
    # return filename if final == 0 else filename[:final].strip()


def __complete_rev_title(file_path, extra_text=""):
    """
    根据输入的路径和文件名称完善视频的分辨率、视频编码、音频编码等信息
    """
    # print(f"添加额外信息为:{extra_text}")
    basename = os.path.basename(file_path)
    # print(f"当前文件名为:{basename}")
    filename, ext = os.path.splitext(basename)
    movie_name = get_title(filename)
    year = re.findall(r"19\d\d|20[012]\d", filename)
    if year:
        year = f" ({year[0]})"
    else:
        year = ""

    # if not os.path.exists(filePath):
    #     log.info(f"【Meta】输入的视频路径不存在")
    #     return title

    # 获取文件元数据
    video_meta = get_video_metadata(file_path)
    # if not video_meta:
    #     log.info("【Meta】未能获取到视频元信息")
    #     return title

    # 视频分辨率(144p/288p/360p/480p/720p/1080p/2K/4K)
    resolution = __get_resolution(video_meta)
    # 色彩空间(SDR/HDR)
    color_space = __get_color_space(video_meta)
    # 杜比视界
    dolby_vision = __get_dolby_vision(video_meta)
    # 视频编码
    video_codec = __get_video_codec(video_meta)
    # 音频编码
    audio_codec = __get_audio_codec(video_meta)

    video_meta_title_list = []
    if resolution:
        video_meta_title_list.append(f" - {resolution}")
    if len(extra_text) > 0:
        video_meta_title_list.append(f".{extra_text}")
    if dolby_vision:
        video_meta_title_list.append(f".{dolby_vision}")
    if color_space:
        video_meta_title_list.append(f".{color_space}")
    if video_codec:
        video_meta_title_list.append(f".{video_codec}")
    if audio_codec:
        video_meta_title_list.append(f".{audio_codec}")

    video_meta_title = "".join(video_meta_title_list)
    completed_video_meta_title = movie_name + year + video_meta_title + ext
    # completed_video_meta_title = completed_video_meta_title.replace(" .", "").replace(
    #     "(side)", ""
    # )
    # print(f"新文件名为:{completed_video_meta_title}\n")
    return completed_video_meta_title


def __get_resolution(video_meta):
    """
    根据ffprobe获取到的视频信息，生成分辨率信息，480p/720p/1080p/4K
    """
    for stream in video_meta.get("streams", []):
        if stream.get("codec_type") == "video":
            height = stream.get("height")
            if isinstance(height, int):
                return __calculate_resolution(height)
    return None


def __calculate_resolution(height):
    """
    根据视频分辨率的高信息，输出144p/288p/360p/480p/576p/720p/960p/1080p/2K/4K
    """
    if height <= 144:
        return "144p"
    elif 144 < height <= 288:
        return "288p"
    elif 288 < height <= 360:
        return "360p"
    elif 360 < height <= 480:
        return "480p"
    elif 480 < height <= 576:
        return "576p"
    elif 576 < height <= 720:
        return "720p"
    elif 720 < height < 1080:
        return "960p"
    elif 1080 <= height < 1440:
        return "1080p"
    elif 1400 <= height < 2160:
        return "2K"
    elif 2160 <= height < 4320:
        return "2160p"
    elif height >= 4320:
        return "4K+"
    else:
        return None


def __get_color_space(video_meta):
    """
    根据ffprobe获取到的视频信息，获取色彩空间(SDR/HDR)
    """
    for stream in video_meta.get("streams", []):
        if stream.get("codec_type") == "video":
            color_space = stream.get("color_space")
            # if StringUtils.is_string_and_not_empty(color_space):
            if color_space:
                color_space_lower = color_space.lower().replace(".", "")
                if "bt709" in color_space_lower or "rec709" in color_space_lower:
                    return ""  # 默认不输出SDR
                elif "bt2020" in color_space_lower or "rec2020" in color_space_lower:
                    return "HDR"
    return None


def __get_dolby_vision(video_meta):
    """
    根据ffprobe获取到的视频信息，判断是否是杜比视界, 输出DV
    """
    for stream in video_meta.get("streams", []):
        if stream.get("codec_type") == "video":
            side_data_list = stream.get("side_data_list")
            if side_data_list:
                for side_data in side_data_list:
                    if "DOVI" in side_data.get("side_data_type"):
                        return "DV"
    return None


def __get_video_codec(video_meta):
    """
    根据ffprobe获取到的视频信息，生成视频编码信息，HEVC/H264/H265
    """
    codec_name = None
    for stream in video_meta.get("streams", []):
        if stream.get("codec_type") == "video":
            codec_name = stream.get("codec_long_name")
            if "264" in codec_name:
                codec_name = "x264"
            elif "265" in codec_name:
                codec_name = "x265"
            elif "MPEG-2" in codec_name:
                codec_name = "MPEG-2"
            else:
                codec_name = ""
            return codec_name
    #         if StringUtils.is_string_and_not_empty(codec_name):
    #             return codec_name.upper()
    return None


def __get_audio_codec(video_meta):
    """
    根据ffprobe获取到的视频信息，生成音频编码信息，AAC/FLAC/APE
    """
    codec_name = None
    channel_layout = None
    channels = None
    channel_name = ""
    profile_name = None
    audio_codec = []
    for stream in video_meta.get("streams", []):
        if stream.get("codec_type") == "audio":
            codec_name = stream.get("codec_name")
            channel_layout = stream.get("channel_layout")
            channels = stream.get("channels")
            profile_name = stream.get("profile")
            if "pcm" in codec_name:
                codec_name = "PCM"
            if channel_layout:
                if "mono" in channel_layout:
                    channel_name = "1.0"
                elif "stereo" in channel_layout:
                    channel_name = "2.0"
            if channels == 8:
                channel_name = "7.1"
            elif channels == 6:
                channel_name = "5.1"
            elif channels == 2:
                channel_name = "2.0"
            if profile_name:
                if "atmos" in profile_name.lower():
                    profile_name = "Atmos"
                else:
                    profile_name = ""
            if codec_name:
                audio_codec.append(codec_name.upper().replace("TRUEHD", "TrueHD"))
            if channel_name:
                audio_codec.append(re.sub(r"\s*\(.*\)$", "", channel_name))
            if profile_name:
                audio_codec.append(profile_name)
            return " ".join(audio_codec)
            # if StringUtils.is_string_and_not_empty(codec_name):
            #     return codec_name.upper()
    return None


num = 0
for root, dirs, files in os.walk(
    "/Users/shenxian/CloudNAS/CloudDrive2/115/我的接收/已刮削"
):
    try:
        for file in files:
            if file.endswith(("mkv", "mp4", "ts", "m2ts", "iso")):
                # if "HDR" in file:
                #     continue
                _, ext = os.path.splitext(file)
                file_path = os.path.join(root, file)
                new_file_path = os.path.join(
                    root,
                    __complete_rev_title(file_path, "BluRay REMUX"),  # BluRay REMUX
                )
                try:
                    os.rename(file_path, new_file_path)
                    num += 1
                    print(f"重命名成功::: {file_path} => {new_file_path} {num}\n")
                    nfo_file_path = file_path.replace(ext, ".nfo")
                    srt_file_path = file_path.replace(ext, ".srt")
                    if os.path.exists(nfo_file_path):
                        new_nfo_file_path = new_file_path.replace(ext, ".nfo")
                        os.rename(nfo_file_path, new_nfo_file_path)
                        print(f"重命名成功::: {nfo_file_path} => {new_nfo_file_path}\n")
                    elif os.path.exists(srt_file_path):
                        new_srt_file_path = new_file_path.replace(ext, ".srt")
                        os.rename(srt_file_path, new_srt_file_path)
                        print(f"重命名成功::: {srt_file_path} => {new_srt_file_path}\n")
                except:
                    print(f"error ::: {file}")
    except:
        pass
