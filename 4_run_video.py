import json
import random
import time
from typing import Any, Dict, Tuple

import requests
from requests.exceptions import RequestException
from tqdm import tqdm

from login import LoginSession


class VideoPlayer:
    def __init__(self, sign: str, classroom_id: int):
        self.sign = sign
        self.classroom_id = classroom_id
        self.session = LoginSession()
        self.csrf_token, self.session_id = self.session.run()

    def _get_headers(self, heart_beat=False) -> Dict[str, str]:
        tmp_header = {"content-type": "application/json"} if heart_beat else {}
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh",
            "app-name": "xtzx",
            "django-language": "zh",
            "x-csrftoken": self.csrf_token,
            "Cookie": f"provider=xuetang; django_language=zh; csrftoken={self.csrf_token}; sessionid={self.session_id};",
        } | tmp_header

    def get_video_info(self, video_id: str) -> Tuple[str, str, str, str, str]:
        try:
            url = f"https://www.xuetangx.com/api/v1/lms/learn/leaf_info/{self.classroom_id}/{video_id}/?sign={self.sign}"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()["data"]
            return (
                data["sku_id"],
                data["content_info"]["media"]["ccid"],
                data["name"],
                data["course_id"],
                data["user_id"],
            )
        except (RequestException, KeyError) as e:
            raise Exception(f"获取视频信息失败: {str(e)}")

    def get_video_duration(self, cc: str) -> float:
        try:
            url = (
                f"https://www.xuetangx.com/api/v1/lms/service/playurl/{cc}/?appid=10000"
            )
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json().get("data", {}).get("duration", 0)
        except (RequestException, KeyError) as e:
            raise Exception(f"获取视频时长失败: {str(e)}")

    def send_heartbeat(self, heart_data: list) -> None:
        try:
            url = "https://www.xuetangx.com/video-log/heartbeat/"
            response = requests.post(
                url,
                headers=self._get_headers(heart_beat=True),
                json={"heart_data": heart_data},
                timeout=10,
            )
            response.raise_for_status()
        except RequestException as e:
            raise Exception(f"发送心跳包失败: {str(e)}")

    def get_watch_progress(
        self, video_id: str, course_id: str, user_id: str
    ) -> Dict[str, Any]:
        try:
            url = f"https://www.xuetangx.com/video-log/get_video_watch_progress/?cid={course_id}&user_id={user_id}&classroom_id={self.classroom_id}&video_type=video&vtype=rate&video_id={video_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            raise Exception(f"获取观看进度失败: {str(e)}")

    def play_video(self, video_id: str) -> None:
        try:
            sku_id, cc, video_name, course_id, user_id = self.get_video_info(video_id)
            duration = self.get_video_duration(cc) + 0.1

            with tqdm(total=duration, desc=f"观看进度 - {video_name}") as pbar:
                progress = self.get_watch_progress(video_id, course_id, user_id)
                if progress.get(str(video_id), {}).get("completed", False):
                    print(f"视频<{video_name}>已看完")
                    return

                # 发送初始心跳包
                template = self._create_heartbeat_template(
                    video_id, sku_id, cc, course_id, user_id, duration
                )
                self._send_initial_heartbeats(template)

                # 发送进度心跳包
                self._send_progress_heartbeats(
                    template, video_id, course_id, user_id, duration, pbar
                )

        except Exception as e:
            print(f"播放视频失败: {str(e)}")

    def _create_heartbeat_template(
        self,
        video_id: str,
        sku_id: str,
        cc: str,
        course_id: str,
        user_id: str,
        duration: float,
    ) -> Dict[str, Any]:
        return {
            "c": course_id,
            "cc": cc,
            "classroomid": self.classroom_id,
            "d": duration,
            "i": 5,
            "p": "web",
            "pg": f"{video_id}_{random.sample('zyxwvutsrqponmlkjihgfedcba1234567890', 4)}",
            "skuid": sku_id,
            "u": user_id,
            "v": video_id,
            "cards_id": 0,
            "cp": 0,  # 当前播放时长
            "et": "",  # 心跳包类型
            "n": "ali-cdn.xuetangx.com",  # 固定设置为”ali-cdn.xuetangx.com“
            "lob": "plat2",  # 固定设置为”cloud4“
            "fp": 0,  # 视频起始播放位置
            "slide": 0,  # 固定设置为0
            "sp": 1,  # 播放速度
            "sq": 0,  # 心跳包序列号
            "t": "video",  # 固定设置为”video“
            "tp": 0,  # 上一次看视频的播放位置
            "ts": int(time.time() * 1000),  # 时间戳，标识事件发生的时间戳
            "uip": "",  # 固定设置为”“
            "v_url": "",  # 固定设置为”“
        }

    def _create_progress_heartbeat(
        self, template: Dict[str, Any], watched_time: float, sq: int
    ) -> Dict[str, Any]:
        data = template.copy()
        data.update(
            {
                "et": "heartbeat",
                "cp": watched_time,
                "sq": sq,
                "tp": max(0, watched_time - 5),
                "ts": int(time.time() * 1000),
            }
        )
        return data

    def _update_progress_bar(
        self, progress: Dict[str, Any], video_id: str, pbar: tqdm
    ) -> None:
        if str(video_id) in progress:
            video_progress = progress[str(video_id)]
            watched_length = video_progress.get("watch_length", 0)
            completion_rate = video_progress.get("rate", 0) * 100

            pbar.n = watched_length
            pbar.set_postfix({"完成度": f"{completion_rate:.2f}%"})
            pbar.refresh()

    def _send_initial_heartbeats(self, template: Dict[str, Any]) -> None:
        heart_data = []
        for etype, sq in [
            ("loadstart", 1),
            ("seeking", 2),
            ("loadeddata", 3),
            ("play", 4),
            ("playing", 5),
        ]:
            data = template.copy()
            data.update({"et": etype, "sq": sq})
            heart_data.append(data)
        self.send_heartbeat(heart_data)

    def _send_progress_heartbeats(
        self,
        template: Dict[str, Any],
        video_id: str,
        course_id: str,
        user_id: str,
        duration: float,
        pbar: tqdm,
    ) -> None:
        watched_time = 0
        sq = 6

        while watched_time < int(duration):
            watched_time += 5
            time.sleep(2)

            heart_data = [self._create_progress_heartbeat(template, watched_time, sq)]
            self.send_heartbeat(heart_data)
            sq += 1

            progress = self.get_watch_progress(video_id, course_id, user_id)
            self._update_progress_bar(progress, video_id, pbar)


if __name__ == "__main__":
    player = VideoPlayer(sign="bjtu07121003092", classroom_id=21558295)

    with open("chapter.json", "r") as f:
        chapter_data = json.load(f)

    chapters = chapter_data["data"]["course_chapter"]
    videos = []

    for chapter in chapters:
        for lessons in chapter["section_leaf_list"]:
            for lesson in lessons.get("leaf_list", []):
                if lesson.get("leaf_type", None) == 0:
                    videos.append(lesson["id"])

    for video in videos:
        player.play_video(video)
