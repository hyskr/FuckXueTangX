import json

import requests

from login import LoginSession

sign = "bjtu07101004723"
classroom_id = 21560530

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

url = f"https://www.xuetangx.com/api/v1/lms/learn/course/chapter?cid={classroom_id}&sign={sign}"
response = requests.request("GET", url, headers=headers)

r = response.json()
print(r)
with open("chapter.json", "w") as f:
    f.write(json.dumps(r, indent=4))
