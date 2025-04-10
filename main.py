#!/usr/bin/env python3
# main.py

import time
import logging
import os
import sys
import requests
import threading
import subprocess
from pathlib import Path
from monitor import ServerMonitor  # Import từ file monitor.py
from config import Config          # Import từ file config.py

class ServerAgent:
    def __init__(self):
        self.setup_logging()
        self.data_dir = Path("/var/log/server_agent")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = True
        self.version = Config.VERSION
        self.update_url = Config.UPDATE_URL
        self.monitor = ServerMonitor(self.data_dir)

    def setup_logging(self):
        logging.basicConfig(
            filename='/var/log/server_agent.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def check_update(self):
        """Kiểm tra và chuẩn bị cập nhật mà không dừng service từ bên trong"""
        try:
            response = requests.get(self.update_url)
            update_info = response.json()
            if update_info['version'] > self.version:
                logging.info(f"New version found: {update_info['version']}")
                # Tải update.sh nhưng không chạy ngay trong tiến trình này
                subprocess.run(["wget", update_info['update_script'], "-O", "/tmp/update.sh"])
                # Gọi một lệnh bên ngoài để chạy update.sh sau khi thoát
                subprocess.Popen(["bash", "/tmp/update.sh"], start_new_session=True)
                # Thoát tiến trình hiện tại để update.sh xử lý tiếp
                logging.info("Initiating update process, exiting current instance")
                self.stop()
                sys.exit(0)  # Thoát Python để update.sh tiếp quản
        except Exception as e:
            logging.error(f"Update failed: {str(e)}")

    def run(self):
        last_day_check = 0
        while self.running:
            current_day = time.localtime().tm_mday
            if current_day != last_day_check:
                self.check_update()
                self.monitor.get_system_info()
                last_day_check = current_day
            self.monitor.get_resource_usage()
            time.sleep(300)

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def stop(self):
        self.running = False
        logging.info("Agent stopped")

if __name__ == "__main__":
    agent = ServerAgent()
    agent.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()