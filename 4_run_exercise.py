import json
import os
import time

import pandas as pd
import requests

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh",
    "app-name": "xtzx",
    "django-language": "zh",
    "priority": "u=1, i",
    "referer": "https://www.xuetangx.com/learn/bjtu07121003092/bjtu07121003092/21558295/exercise/50261867",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "terminal-type": "web",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "x-client": "web",
    "x-csrftoken": "0CiwdIY2mhnj9nhP5EKkXdLDTrJo5rna",
    "xtbz": "xt",
    "Cookie": "_abfpc=50f50f45869f646743edae56254250802f5dd19e_2.0; cna=01accd30e089023087480e2762443f0e; login_type=WX; csrftoken=0CiwdIY2mhnj9nhP5EKkXdLDTrJo5rna; sessionid=ykz3nbyu6zxbbl09hzemrwuk67w0cyj3; mode_type=normal; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2256758079%22%2C%22first_id%22%3A%22193c88f783bc5a-0b8eb6bf2cbd118-26011851-3686400-193c88f783c18be%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%7D%2C%22%24device_id%22%3A%22193c88f783bc5a-0b8eb6bf2cbd118-26011851-3686400-193c88f783c18be%22%7D; provider=xuetang; django_language=zh; k=56758079; JG_016f5b1907c3bc045f8f48de1_PV=1734567515088|1734567515088; point={%22point_active%22:true%2C%22platform_task_active%22:true%2C%22learn_task_active%22:true}; 56758079video_seconds=19",
}

sign = "bjtu07121003092"
classroom_id = 21558295


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


if os.path.exists("breakpoint_with_run.csv"):
    df_breakpoint = pd.read_csv("breakpoint_with_run.csv")
else:
    df_breakpoint = pd.DataFrame(columns=["leaf_id", "problem_id", "completed"])

df_result = json.load(open("results_with_run.json", "r", encoding="utf-8"))

for result in df_result:
    answer = result.get("answer", [])
    leaf_id = result.get("leaf_id", None)
    exercise_id = result.get("exercise_id", None)
    problem_id = result.get("problem_id", None)
    if len(answer) == 0 or leaf_id is None or exercise_id is None or problem_id is None:
        print("Error: ", result)
        exit()
    leaf_id = int(leaf_id)
    exercise_id = int(exercise_id)
    problem_id = int(problem_id)
    if not df_breakpoint[
        (df_breakpoint["leaf_id"] == leaf_id)
        & (df_breakpoint["problem_id"] == problem_id)
        & (df_breakpoint["completed"])
    ].empty:
        print("skip", problem_id)
        continue
    print("run", problem_id)
    res = submit_problem_answer(leaf_id, exercise_id, problem_id, answer)
    print("\t 回答正确" if res else "回答错误")
    new_breakpoint = pd.DataFrame(
        [{"leaf_id": leaf_id, "problem_id": problem_id, "completed": True}]
    )
    df_breakpoint = pd.concat([df_breakpoint, new_breakpoint], ignore_index=True)
    df_breakpoint.to_csv("breakpoint_with_run.csv", index=False)
    time.sleep(5)
