import json
import random
import time

import requests
from tqdm import tqdm

from login import LoginSession

sign = "bjtu07121003092"
classroom_id = 21558295

session = LoginSession()
csrf_token, session_id = session.run()


headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh",
    "app-name": "xtzx",
    "django-language": "zh",
    "priority": "u=1, i",
    "referer": "https://www.xuetangx.com/learn/bjtu07121003092/bjtu07121003092/21558295/exercise/50261867?channel=learn_title",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "terminal-type": "web",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "x-client": "web",
    "x-csrftoken": csrf_token,
    "xtbz": "xt",
    "Cookie": f"provider=xuetang; django_language=zh; sajssdk_2015_cross_new_user=1; login_type=P; csrftoken={csrf_token}; sessionid={session_id}; ",
}

with open("chapter.json", "r") as f:
    chapter = json.loads(f.read())

chapters = chapter["data"]["course_chapter"]
videos = []

for chapter in chapters:
    for lessons in chapter["section_leaf_list"]:
        for lesson in lessons.get("leaf_list", []):
            if lesson.get("leaf_type", None) == 0:
                videos.append(
                    (
                        lesson["name"],
                        lesson["id"],
                    )
                )


def get_video_info(video_id):
    video_info_url = f"https://www.xuetangx.com/api/v1/lms/learn/leaf_info/{classroom_id}/{video_id}/?sign={sign}"
    video_info = requests.get(video_info_url, headers=headers)
    video_info.encoding = video_info.apparent_encoding
    data = json.loads(video_info.text)["data"]
    sku_id = data["sku_id"]
    cc = data["content_info"]["media"]["ccid"]
    video_name = data["name"]
    course_id = data["course_id"]
    user_id = data["user_id"]
    return sku_id, cc, video_name, course_id, user_id


def get_video_len(cc):
    video_play_url = (
        f"https://www.xuetangx.com/api/v1/lms/service/playurl/{cc}/?appid=10000"
    )
    video_play = requests.get(video_play_url, headers=headers)
    video_play.encoding = video_play.apparent_encoding

    duration = video_play.json().get("data", {}).get("duration", 0)
    return duration


for name, video_id in videos[22:]:
    sku_id, cc, video_name, course_id, user_id = get_video_info(video_id)
    d = get_video_len(cc) + 0.1
    rate_url = f"https://www.xuetangx.com/video-log/get_video_watch_progress/?cid={course_id}&user_id={user_id}&classroom_id={classroom_id}&video_type=video&vtype=rate&video_id={video_id}"
    rate = requests.get(rate_url, headers=headers)
    rate.encoding = rate.apparent_encoding
    rate = rate.json()
    pbar = tqdm(total=d, desc=f"观看进度 - {video_name}")
    sd = rate.get(str(video_id), {}).get("last_point", 0)
    start_d = max(
        int(rate.get(str(video_id), {}).get("watch_length", 0) // 5 * 5) - 5, 0
    )
    rate = rate.get(str(video_id), {}).get("completed", False)
    template = {
        "c": course_id,  # 课程ID
        "cards_id": 0,
        "cc": cc,  # 每个视频的特定参数
        "classroomid": classroom_id,  # 教室ID
        "cp": 0,  # 当前播放时长
        "d": d,  # 总时长
        "et": "",  # 心跳包类型
        "i": 5,  # 固定设置为5
        "p": "web",  # 固定设置为”web“
        "n": "ali-cdn.xuetangx.com",  # 固定设置为”ali-cdn.xuetangx.com“
        "lob": "plat2",  # 固定设置为”cloud4“
        "fp": 0,  # 视频起始播放位置
        "pg": str(video_id)
        + "_"
        + "".join(
            random.sample("zyxwvutsrqponmlkjihgfedcba1234567890", 4)
        ),  # 视频id_随机字符串
        "skuid": sku_id,  # SKU ID
        "slide": 0,  # 固定设置为0
        "sp": 1,  # 播放速度
        "sq": 0,  # 心跳包序列号
        "t": "video",  # 固定设置为”video“
        "tp": 0,  # 上一次看视频的播放位置
        "ts": int(time.time() * 1000),  # 时间戳，标识事件发生的时间戳
        "u": user_id,  # 用户ID
        "uip": "",  # 固定设置为”“
        "v": video_id,  # 视频ID
        "v_url": "",  # 固定设置为”“
    }
    if rate == 1:
        pbar.close()
        print(f"视频<{video_name}>已看完")
    else:
        # 1. 发送空的心跳包
        requests.post(
            "https://www.xuetangx.com/video-log/heartbeat/",
            headers=headers | {"content-type": "application/json"},
            data={"heart_data": []},
        )
        # 2. 构建新的心跳包
        heart_data = []
        # 2.1 添加初始心跳包数据
        for etype, sq in [
            ("loadstart", 1),
            ("seeking", 2),
            ("loadeddata", 3),
            ("play", 4),
            ("playing", 5),
        ]:
            data = template.copy()
            data["et"] = etype
            data["sq"] = sq
            heart_data.append(data)
        send = requests.post(
            "https://www.xuetangx.com/video-log/heartbeat/",
            headers=headers | {"content-type": "application/json"},
            data=json.dumps({"heart_data": heart_data}),
        )
        rate = requests.get(rate_url, headers=headers)
        rate = rate.json()
        wc = rate.get(str(video_id), {}).get("watch_length", 0)
        rate = rate.get(str(video_id), {}).get("rate", 0) * 100
        i = wc
        pbar.n = wc
        pbar.set_postfix({"完成度": f"{rate:.2f}%"})
        pbar.refresh()
        heart_data.clear()
        sq = 6
        # 2.2 生成心跳包序列并发送
        while i < int(d):
            i = i + 5
            time.sleep(2)
            # 2.2.1 迭代生成心跳包
            hb = template.copy()
            hb["et"] = "heartbeat"
            hb["cp"] = i
            hb["sq"] = sq
            heart_data.append(hb)
            sq += 1
            # 2.2.2 发送心跳包
            send = requests.post(
                "https://www.xuetangx.com/video-log/heartbeat/",
                headers=headers | {"content-type": "application/json"},
                data=json.dumps({"heart_data": heart_data}),
            )
            rate = requests.get(rate_url, headers=headers)
            rate = rate.json()
            wc = rate[str(video_id)]["watch_length"]
            rate = rate[str(video_id)]["rate"] * 100
            i = wc
            pbar.n = wc
            pbar.set_postfix({"完成度": f"{rate:.2f}%"})
            pbar.refresh()
            heart_data.clear()
        # 3. 添加结束心跳包数据
        data = template.copy()
        data["et"] = "videoend"
        data["cp"] = d
        data["sq"] = sq
        heart_data.append(data)
        requests.post(
            "https://www.xuetangx.com/video-log/heartbeat/",
            headers=headers | {"content-type": "application/json"},
            data=json.dumps({"heart_data": heart_data}),
        )
        rate = requests.get(rate_url, headers=headers)
        rate = rate.json()
        pbar.n = int(rate[str(video_id)]["watch_length"])
        percentage = rate[str(video_id)]["rate"] * 100
        pbar.set_postfix({"完成度": f"{percentage:.2f}%"})
        pbar.refresh()
        pbar.close()
