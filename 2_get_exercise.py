import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from requests.exceptions import RequestException

from login import LoginSession


@dataclass
class ExerciseConfig:
    sign: str
    classroom_id: int
    base_url: str = "https://www.xuetangx.com"
    retry_times: int = 3
    retry_delay: int = 5


class ExerciseCollector:
    def __init__(self, config: ExerciseConfig):
        self.config = config
        self.session = LoginSession()
        self.csrf_token, self.session_id = self.session.run()
        self.headers = self._get_headers()
        self.results = pd.DataFrame(
            columns=[
                "exercise_id",
                "leaf_id",
                "problem_id",
                "name",
                "problem_index",
                "problem_body",
                "problem_type",
                "problem_options",
                "answer",
                "answers",
            ]
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh",
            "app-name": "xtzx",
            "django-language": "zh",
            "content-type": "application/json",
            "x-csrftoken": self.csrf_token,
            "x-client": "web",
            "Cookie": f"provider=xuetang; django_language=zh; csrftoken={self.csrf_token}; sessionid={self.session_id};",
        }

    def _make_request(
        self, method: str, url: str, data: Optional[Dict] = None, retry: int = 0
    ) -> Dict[str, Any]:
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                json=data if data else None,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if retry < self.config.retry_times:
                return self._make_request(method, url, data, retry + 1)
            raise Exception(f"请求失败: {str(e)}")

    def get_exercises_from_chapter(self, chapter_file: str) -> List[Tuple[str, int]]:
        with open(chapter_file, "r") as f:
            chapter_data = json.load(f)

        exercises = []
        for chapter in chapter_data["data"]["course_chapter"]:
            for lessons in chapter["section_leaf_list"]:
                for lesson in lessons.get("leaf_list", []):
                    if lesson.get("leaf_type") == 6:
                        exercises.append((lesson["name"], lesson["id"]))
        return exercises

    def get_exercise_leaf_type_id(self, exercise_id: int) -> Optional[int]:
        url = f"{self.config.base_url}/api/v1/lms/learn/leaf_info/{self.config.classroom_id}/{exercise_id}/?sign={self.config.sign}"
        response = self._make_request("GET", url)
        return response.get("data", {}).get("content_info", {}).get("leaf_type_id")

    def get_exercise_content(self, leaf_type_id: int) -> List[Dict]:
        url = f"{self.config.base_url}/api/v1/lms/exercise/get_exercise_list/{leaf_type_id}/10605589/"
        response = self._make_request("GET", url)
        return response.get("data", {}).get("problems", [])

    def submit_problem_answer(
        self, leaf_id: int, exercise_id: int, problem_id: int
    ) -> List[str]:
        url = f"{self.config.base_url}/api/v1/lms/exercise/problem_apply/"
        payload = {
            "leaf_id": leaf_id,
            "classroom_id": self.config.classroom_id,
            "exercise_id": exercise_id,
            "problem_id": problem_id,
            "sign": self.config.sign,
            "answers": {},
            "answer": ["B"],
        }
        response = self._make_request("POST", url, payload)
        return response.get("data", {}).get("answer", [])

    def get_problem_answer(
        self, question: Dict, exercise_id: int, leaf_id: int, problem_id: int
    ) -> List[str]:
        ans = question.get("user", {}).get("answer")
        if ans is not None:
            return ans
        return self.submit_problem_answer(leaf_id, exercise_id, problem_id)

    def process_exercise(self, name: str, leaf_id: int) -> None:
        try:
            print(f"开始处理习题: {name}")
            exercise_id = self.get_exercise_leaf_type_id(leaf_id)
            if not exercise_id:
                raise Exception(f"无法获取习题ID: {leaf_id}")

            content = self.get_exercise_content(exercise_id)
            for question in content:
                self._process_question(question, exercise_id, leaf_id, name)

        except Exception as e:
            print(f"处理习题失败 {name}: {str(e)}")

    def _process_question(
        self, question: Dict, exercise_id: int, leaf_id: int, name: str
    ) -> None:
        problem_id = question.get("problem_id")
        if not problem_id:
            return

        print(f"\t处理问题: {problem_id}")

        answer = self.get_problem_answer(question, exercise_id, leaf_id, problem_id)
        if not answer:
            raise Exception(f"获取答案失败: {problem_id}")

        answers = [
            option.get("value")
            for option in question.get("content", {}).get("Options", [])
            if option.get("key") in answer
        ]

        new_row = pd.DataFrame(
            [
                {
                    "exercise_id": exercise_id,
                    "leaf_id": leaf_id,
                    "problem_id": problem_id,
                    "name": name,
                    "problem_index": question.get("index"),
                    "problem_body": question.get("content", {}).get("Body"),
                    "problem_type": question.get("content", {}).get("TypeText"),
                    "problem_options": question.get("content", {}).get("Options"),
                    "answer": answer,
                    "answers": answers,
                }
            ]
        )

        self.results = pd.concat([self.results, new_row], ignore_index=True)

    def run(self, chapter_file: str, output_file: str) -> None:
        exercises = self.get_exercises_from_chapter(chapter_file)

        for name, leaf_id in exercises:
            self.process_exercise(name, leaf_id)
            self.results.to_json(output_file, orient="records", force_ascii=False)


def main():
    config = ExerciseConfig(sign="bjtu07121003092", classroom_id=21558295)

    collector = ExerciseCollector(config)
    collector.run("chapter.json", "results_with_run.json")


if __name__ == "__main__":
    main()
