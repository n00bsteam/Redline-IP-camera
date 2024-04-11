import requests
import threading
import time
from datetime import datetime
import json
import os

# Переменные
USERNAME = "admin"
PASSWORD = "123456"
CAMERA_URL = "http://cameraIP"
CHAT_ID = "TELEGRAM CHAT ID"  #TELEGRAM CHAT ID 
TOKEN = "TELEGRAM BOT TOKEN - https://t.me/BotFather" #TELEGRAM BOT TOKEN - https://t.me/BotFather
DB_FILE = "history.json"


class Redline:
    def __init__(self, username, password, camera_url, chat_id, token, db_file):
        self.username = username
        self.password = password
        self.camera_url = camera_url
        self.chat_id = chat_id
        self.token = token
        self.db_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), db_file)
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json; charset=utf-8",
                               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'})

    def login(self):
        url = f"{self.camera_url}/API/Web/Login"
        auth = requests.auth.HTTPDigestAuth(self.username, self.password)
        response = self.session.post(url, auth=auth)
        if response.ok:
            session_token = response.headers.get('X-csrftoken')
            self.session.headers.update({'X-csrftoken': session_token})
            print("Авторизация прошла успешно")
            return True
        else:
            print("Не удалось авторизоваться", response.status_code, response.reason, response.content)
            return False

    def send_heartbeat(self):
        t = threading.current_thread()
        while getattr(t, "heartbeat", True):
            url = f"{self.camera_url}/API/Login/Heartbeat"
            response = self.session.post(url)
            if response.ok:
                print("Heartbeat отправлен", response.status_code, response.reason, response.content)
                time.sleep(10)
            else:
                print("csrftoken протух, инициируем авторизацию")
                self.login()

    def get_records(self):
        url = f"{self.camera_url}/API/Playback/SearchRecord/Search"
        today = datetime.today().strftime("%m/%d/%Y")
        data = {
            "version": "1.0",
            "data": {
                "channel": [
                    "CH1"
                ],
                "start_date": today,
                "start_time": "00:00:00",
                "end_date": today,
                "end_time": "23:59:59",
                "record_type": 498666,
                "smart_region": [],
                "enable_smart_search": 0,
                "stream_mode": "Substream"
            }
        }
        response = self.session.post(url, json=data)
        if response.ok:
            records = response.json()['data']['record'][0]
            try:
                with open(self.db_file, 'r') as file:
                    data = json.load(file)
            except FileNotFoundError:
                data = {}

            if today not in data:
                data[today] = []

            for record in records:
                print("Запись за {} с {} по {} уже была отправлена, пропускаем".format(record["start_date"], record["start_time"], record["end_time"]))
                if not record["start_time"] in data[today]:
                    if self.download_video(record):
                        data[today].append(record["start_time"])
                        with open(self.db_file, 'w') as file:
                            json.dump(data, file, indent=4, ensure_ascii=False)
        else:
            print("Не удалось получить список записей, или их нет", response.status_code, response.reason)
            return False

    def download_video(self, record):
        t = threading.Thread(target=self.send_heartbeat)
        t.start()
        url = f"{self.camera_url}/download.mp4"
        start_date = record["start_date"].split("/")
        start_date = start_date[2] + start_date[0] + start_date[1] + record["start_time"].replace(":", '')
        end_date = record["end_date"].split("/")
        end_date = end_date[2] + end_date[0] + end_date[1] + record["end_time"].replace(":", '')
        params = {"start_time": start_date,
                    "end_time": end_date,
                    "channel": "0",
                    "record_type": record["record_type"],
                    "stream_type": "1",
                    "record_id": record["record_id"],
                    "disk_event_id": record["disk_event_id"]}

        response = self.session.post(url, params=params)
        if response.ok:
            t.heartbeat = False
            print("Видеозапись скачена, отправляем в телегу")
            msg = "Обнаружено движение {} \nв период с {} до {}".format(record["start_date"], record["start_time"], record["end_time"])
            self.send_video(response.content, msg)
            return True
        else:
            print("Не удалось получить список записей или их нет", response.status_code, response.reason)
            return False

    def send_video(self, video_file, description, max_retries=3):
        url = f"https://api.telegram.org/bot{self.token}/sendVideo"
        retries = 0

        while retries < max_retries:
            try:
                data = {'chat_id': self.chat_id, 'caption': description}
                response = requests.post(url, files={'video': video_file}, data=data)
                if response.ok:
                    print("Видеозапись успешно отправлена!")
                    return True
            except Exception as e:
                print(f"Ошибка отправки видеозаписи в Telegram: {e}")

            retries += 1
            time.sleep(15)

        if retries == max_retries:
            print("Не удалось отправить видео в Telegram", response.status_code, response.reason)

    def main(self):
        if self.login():
            self.get_records()

if __name__ == "__main__":
    video_downloader = Redline(USERNAME, PASSWORD, CAMERA_URL, CHAT_ID, TOKEN, DB_FILE)
    video_downloader.main()
