import json
import os

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


with open("chapter.json", "r") as f:
    chapter = json.loads(f.read())

chapters = chapter["data"]["course_chapter"]
exercise = []

for chapter in chapters:
    for lessons in chapter["section_leaf_list"]:
        for lesson in lessons.get("leaf_list", []):
            if lesson.get("leaf_type", None) == 6:
                exercise.append(
                    (
                        lesson["name"],
                        lesson["id"],
                    )
                )


def get_exercise_leaf_type_id(exercise_id):
    url = f"https://www.xuetangx.com/api/v1/lms/learn/leaf_info/21558295/{exercise_id}/?sign=bjtu07121003092"
    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    return (
        response.json()
        .get("data", {})
        .get("content_info", {})
        .get("leaf_type_id", None)
    )


def get_exercise_content(leaf_type_id):
    url = f"https://www.xuetangx.com/api/v1/lms/exercise/get_exercise_list/{leaf_type_id}/10605589/"
    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    return response.json().get("data", {}).get("problems", [])


def submit_problem_answer(leaf_id, exercise_id, problem_id):
    url = "https://www.xuetangx.com/api/v1/lms/exercise/problem_apply/"
    submit_headers = headers | (
        {
            "content-type": "application/json",
        }
    )
    payload = json.dumps(
        {
            "leaf_id": leaf_id,
            "classroom_id": 21558295,
            "exercise_id": exercise_id,
            "problem_id": problem_id,
            "sign": "bjtu07121003092",
            "answers": {},
            "answer": ["B"],
        }
    )
    response = requests.request("POST", url, headers=submit_headers, data=payload)
    print(response.json())
    return response.json().get("data", {}).get("answer", [])


def get_problem_answer(question, exercise_id, leaf_id, problem_id):
    ans = question.get("user", {}).get("answer", None)
    if ans is not None:
        return ans
    else:
        ans = submit_problem_answer(leaf_id, exercise_id, problem_id)
        return ans


if os.path.exists("breakpoint_with_run.csv"):
    df_breakpoint = pd.read_csv("breakpoint_with_run.csv")
else:
    df_breakpoint = pd.DataFrame(columns=["leaf_id", "problem_id", "completed"])


df_results = pd.DataFrame(
    columns=[
        "name",
        "problem_index",
        "problem_body",
        "problem_type",
        "problem_options",
        "answer",
    ]
)

for name, leaf_id in exercise:
    print("=" * 10)
    print(f"start {name}")
    exercise_id = get_exercise_leaf_type_id(leaf_id)
    content = get_exercise_content(exercise_id)
    for question in content:
        print(question)
        problem_id = question.get("problem_id", None)
        problem_body = question.get("content", {}).get("Body", None)
        problem_type = question.get("content", {}).get("TypeText", None)
        problem_options = question.get("content", {}).get("Options", None)
        problem_index = question.get("index", None)
        if not df_breakpoint[
            (df_breakpoint["leaf_id"] == leaf_id)
            & (df_breakpoint["problem_id"] == problem_id)
            & (df_breakpoint["completed"])
        ].empty:
            print("\t skip", problem_id)
            continue
        print("\t start", problem_id)
        answer = get_problem_answer(question, exercise_id, leaf_id, problem_id)
        answers = []
        if len(answer) == 0:
            print("Error")
            exit()
        for option in problem_options:
            if option.get("key") in answer:
                answers.append(option.get("value"))
        new_row = pd.DataFrame(
            [
                {
                    "exercise_id": exercise_id,
                    "leaf_id": leaf_id,
                    "problem_id": problem_id,
                    "name": name,
                    "problem_index": problem_index,
                    "problem_body": problem_body,
                    "problem_type": problem_type,
                    "problem_options": problem_options,
                    "answer": answer,
                    "answers": answers,
                }
            ]
        )
        df_results = pd.concat([df_results, new_row], ignore_index=True)

        new_breakpoint = pd.DataFrame(
            [{"leaf_id": leaf_id, "problem_id": problem_id, "completed": True}]
        )
        df_breakpoint = pd.concat([df_breakpoint, new_breakpoint], ignore_index=True)
        df_breakpoint.to_csv("breakpoint_with_run.csv", index=False)
    df_results.to_json("results_with_run.json", orient="records", force_ascii=False)
    print(f"end {name}")
