import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


class ExerciseSubmitter:
    def __init__(self, config: ExerciseConfig):
        self.config = config
        self.session = LoginSession()
        self.csrf_token, self.session_id = self.session.run()
        self.headers = self._get_headers()
        self.exercise_state: Dict[int, Dict[int, bool]] = {}

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
            result = response.json()

            if "请求超过了限速" in result.get("detail", ""):
                if retry < self.config.retry_times:
                    time.sleep(self.config.retry_delay)
                    return self._make_request(method, url, data, retry + 1)
                raise Exception("请求达到限速上限")

            return result
        except RequestException as e:
            if retry < self.config.retry_times:
                time.sleep(self.config.retry_delay)
                return self._make_request(method, url, data, retry + 1)
            raise Exception(f"请求失败: {str(e)}")

    def submit_answer(
        self, leaf_id: int, exercise_id: int, problem_id: int, answer: List
    ) -> bool:
        url = f"{self.config.base_url}/api/v1/lms/exercise/problem_apply/"
        payload = {
            "leaf_id": leaf_id,
            "classroom_id": self.config.classroom_id,
            "exercise_id": exercise_id,
            "problem_id": problem_id,
            "sign": self.config.sign,
            "answers": {},
            "answer": answer,
        }

        result = self._make_request("POST", url, payload)
        print(result.json())
        if result.get("error_code") == "80001":
            return True
        return result.get("data", {}).get("is_correct", False)

    def get_sku_id(self, exercise_id: int) -> Optional[str]:
        url = f"{self.config.base_url}/api/v1/lms/learn/leaf_info/{self.config.classroom_id}/{exercise_id}/?sign={self.config.sign}"
        result = self._make_request("GET", url)
        return result.get("data", {}).get("sku_id")

    def get_exercise_state(self, exercise_id: int, sku_id: int) -> Dict[int, bool]:
        url = f"{self.config.base_url}/api/v1/lms/exercise/get_exercise_list/{exercise_id}/{sku_id}/"
        result = self._make_request("GET", url)

        return {
            problem["problem_id"]: bool(problem.get("user", {}).get("my_answer"))
            for problem in result.get("data", {}).get("problems", [])
        }

    def process_exercises(self, results_file: str) -> None:
        with open(results_file, "r", encoding="utf-8") as f:
            exercises = json.load(f)

        for result in exercises:
            try:
                self._process_single_exercise(result)
            except Exception as e:
                print(f"处理习题失败: {str(e)}")
                continue

    def _process_single_exercise(self, result: Dict) -> None:
        answer = result.get("answer", [])
        leaf_id = int(result.get("leaf_id", 0))
        exercise_id = int(result.get("exercise_id", 0))
        problem_id = int(result.get("problem_id", 0))

        if not all([answer, leaf_id, exercise_id, problem_id]):
            print(f"无效的习题数据: {result}")
            return

        sku_id = self.get_sku_id(leaf_id)
        if not sku_id:
            print(f"获取SKU ID失败: {leaf_id}")
            return

        if exercise_id not in self.exercise_state:
            self.exercise_state[exercise_id] = self.get_exercise_state(
                exercise_id, int(sku_id)
            )

        if self.exercise_state[exercise_id].get(problem_id, False):
            print(f"习题已完成: {problem_id}")
            return

        print(f"正在提交习题: {problem_id}")
        is_correct = self.submit_answer(leaf_id, exercise_id, problem_id, answer)
        print(f"\t{'回答正确' if is_correct else '回答错误'}")

        time.sleep(3)


def main():
    config = ExerciseConfig(sign="bjtu07121003092", classroom_id=21558295)

    submitter = ExerciseSubmitter(config)
    submitter.process_exercises("results_with_run.json")


if __name__ == "__main__":
    main()
