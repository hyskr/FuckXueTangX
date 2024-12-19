import json
import time

import pandas as pd
import requests

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
    "referer": f"https://www.xuetangx.com/learn/{sign}/{sign}/{classroom_id}/exercise/50261867?channel=learn_title",
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


def submit_problem_answer(leaf_id, exercise_id, problem_id, answer):
    url = "https://www.xuetangx.com/api/v1/lms/exercise/problem_apply/"
    submit_headers = headers | (
        {
            "content-type": "application/json",
        }
    )
    payload = json.dumps(
        {
            "leaf_id": leaf_id,
            "classroom_id": classroom_id,
            "exercise_id": exercise_id,
            "problem_id": problem_id,
            "sign": sign,
            "answers": {},
            "answer": answer,
        }
    )
    response = requests.request("POST", url, headers=submit_headers, data=payload)
    print(response.json())
    if response.json().get("error_code", None) == "80001":
        return True
    if "请求超过了限速" in response.json().get("detail", ""):
        exit()
        return False
    return response.json().get("data", {}).get("is_correct", False)


def get_exercise_sku_id(exercise_id):
    url = f"https://www.xuetangx.com/api/v1/lms/learn/leaf_info/21558295/{exercise_id}/?sign={sign}"
    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    if "user is not login" in response.text:
        print("User is not login")
        raise Exception("User is not login")
    return response.json().get("data", {}).get("sku_id", None)


def get_exercise_state(exercise_id, sku_id):
    url = f"https://www.xuetangx.com/api/v1/lms/exercise/get_exercise_list/{exercise_id}/{sku_id}/"
    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    res = {}
    for problem in response.json().get("data", {}).get("problems", []):
        problem_id = problem.get("problem_id", None)
        if problem.get("user", {}).get("my_answer", None):
            res[problem_id] = True
        else:
            res[problem_id] = False
    return res


df_result = json.load(open("results_with_run.json", "r", encoding="utf-8"))
exercise_state = {}

for result in df_result:
    answer = result.get("answer", [])
    leaf_id = int(result.get("leaf_id", None))
    exercise_id = int(result.get("exercise_id", None))
    problem_id = int(result.get("problem_id", None))
    sku_id = get_exercise_sku_id(leaf_id)
    if (
        len(answer) == 0
        or leaf_id is None
        or exercise_id is None
        or problem_id is None
        or sku_id is None
    ):
        print("Error: ", result)
        exit()
    if exercise_id not in exercise_state:
        exercise_state[exercise_id] = get_exercise_state(exercise_id, int(sku_id))
    if exercise_state[exercise_id][problem_id]:
        print("Already answered", problem_id)
        continue
    leaf_id = int(leaf_id)
    exercise_id = int(exercise_id)
    problem_id = int(problem_id)
    print("run", problem_id)
    res = submit_problem_answer(leaf_id, exercise_id, problem_id, answer)
    print("\t 回答正确" if res else "回答错误")
    new_breakpoint = pd.DataFrame(
        [{"leaf_id": leaf_id, "problem_id": problem_id, "completed": True}]
    )
    time.sleep(5)
