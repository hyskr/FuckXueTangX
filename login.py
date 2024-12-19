import asyncio
import io
import json
import os
import threading
import tkinter as tk
from dataclasses import dataclass
from queue import Queue
from tkinter import messagebox  # 添加这行
from typing import Optional, Tuple

import requests
import websockets
from PIL import Image, ImageTk


@dataclass
class WebSocketMessage:
    op: str = "requestlogin"
    role: str = "web"
    version: str = "1.4"
    purpose: str = "login"
    xtbz: str = "xt"
    x_client: str = "web"

    def to_json(self) -> str:
        return json.dumps(self.__dict__)


class LoginSession:
    def __init__(self):
        self.stop_flag: bool = False
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
        self.result_queue: Queue = Queue()

    def _safe_stop(self) -> None:
        """安全停止窗口和线程"""
        self.stop_flag = True
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()  # 确保窗口被销毁
            except tk.TclError:
                pass  # 忽略已关闭窗口的错误

    def _on_closing(self) -> None:
        """窗口关闭事件处理"""
        if not self.stop_flag:
            if messagebox.askokcancel("退出", "确定要取消登录吗?"):
                self._safe_stop()

    def show_qr_code(self, img_data: bytes) -> None:
        try:
            img = Image.open(io.BytesIO(img_data))
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda: self._update_image(photo))
            print("\n二维码已显示，请扫描登录...")
        except Exception as e:
            print(f"显示二维码出错: {e}")

    def _update_image(self, photo: ImageTk.PhotoImage) -> None:
        self.label.config(image=photo)
        self.label.image = photo

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    async def _periodic_message(self, ws: websockets.WebSocketClientProtocol) -> None:
        """每60秒发送一次保活消息"""
        while not self.stop_flag:
            try:
                await asyncio.sleep(60)  # 等待60秒
                message = WebSocketMessage()
                await ws.send(message.to_json())
                print("发送保活消息...")
            except websockets.ConnectionClosed:
                break

    async def _websocket_handler(self) -> None:
        async with websockets.connect("wss://www.xuetangx.com/wsapp/") as ws:
            # 发送初始消息
            message = WebSocketMessage()
            await ws.send(message.to_json())
            print("正在获取二维码...")

            # 启动定期消息任务
            periodic_task = asyncio.create_task(self._periodic_message(ws))

            try:
                while not self.stop_flag:
                    # 原有的消息处理逻辑
                    response = await ws.recv()
                    data = json.loads(response)

                    if data.get("op") == "requestlogin":
                        if img_url := data.get("ticket"):
                            self.show_qr_code(requests.get(img_url).content)

                    elif data.get("op") == "loginsuccess":
                        print(f"登录成功！用户ID: {data.get('UserID')}")
                        result = self._process_login(data.get("token"))
                        self.result_queue.put(result)
                        self.stop_flag = True
                        break

            finally:
                # 确保清理定期任务
                periodic_task.cancel()
                try:
                    await periodic_task
                except asyncio.CancelledError:
                    pass

    def _process_login(self, token: str) -> Tuple[str, str]:
        response = requests.post(
            "https://www.xuetangx.com/api/v1/u/login/wx/",
            headers={
                "content-type": "application/json",
                "x-client": "web",
                "xtbz": "xt",
            },
            json={"s_s": token},
        )
        cookies = response.cookies.get_dict()
        print(cookies)
        return cookies.get("csrftoken"), cookies.get("sessionid")

    def _check_stop_flag(self) -> None:
        """定期检查停止标志并关闭窗口"""
        if self.stop_flag and self.root:
            self.root.quit()
        else:
            # 每100ms检查一次
            self.root.after(100, self._check_stop_flag)

    def run(self) -> Tuple[str, str]:
        if os.path.exists("cookies.json"):
            with open("cookies.json", "r") as f:
                cookies = json.loads(f.read())
                return cookies.get("csrftoken"), cookies.get("sessionid")

        self.root = tk.Tk()
        self.root.title("登录二维码")
        self.label = tk.Label(self.root)
        self.label.pack()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)  # 处理窗口关闭事件

        tk.Label(self.root, text="请使用手机扫描二维码登录", font=("Arial", 12)).pack(
            pady=5
        )
        self._center_window()

        threading.Thread(
            target=lambda: asyncio.run(self._websocket_handler()), daemon=True
        ).start()

        # 启动停止标志检查
        self._check_stop_flag()

        try:
            self.root.mainloop()
        finally:
            self._safe_stop()  # 确保清理资源

        if self.result_queue.empty():
            raise RuntimeError("登录已取消")

        csrftoken, sessionid = self.result_queue.get()
        with open("cookies.json", "w") as f:
            f.write(json.dumps({"csrftoken": csrftoken, "sessionid": sessionid}))
        return csrftoken, sessionid
