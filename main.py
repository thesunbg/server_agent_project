#!/usr/bin/env python3
# main.py

import time
import logging
import os
import sys
import json
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
        # Logic cập nhật giữ nguyên, sẽ gọi update.sh
        try:
            response = requests.get(self.update_url)
            update_info = response.json()
            # if update_info['version'] > self.version:
            #     logging.info(f"New version found: {update_info['version']}")
            #     subprocess.run(["wget", update_info['update_script'], "-O", "/tmp/update.sh"])
            #     subprocess.run(["bash", "/tmp/update.sh"])
        except Exception as e:
            logging.error(f"Update failed: {str(e)}")

    def run(self):
        last_day_check = 0
        while self.running:
            current_day = time.localtime().tm_mday
            if current_day != last_day_check:
                self.check_update()
                self.monitor.get_system_info()
                self.monitor.detect_firewall()
                last_day_check = current_day
            self.monitor.get_resource_usage()
            self.monitor.get_running_services()
            self.send_to_server()
            time.sleep(300)

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def stop(self):
        self.running = False
        logging.info("Agent stopped")

    def send_to_server(self):
        """Gửi dữ liệu monitor đến server"""
        # Tập hợp dữ liệu từ các file
        files_to_send = [
            "system_info.json",
            "resource_usage.json",
            "services.json",
            "firewall_info.json"
        ]
        
        monitor_data = {}
        for file_name in files_to_send:
            file_path = self.data_dir / file_name
            if file_path.exists():
                with open(file_path, 'r') as f:
                    monitor_data[file_name] = json.load(f)
            else:
                logging.warning(f"File {file_path} not found, skipping")
        
        if not monitor_data:
            logging.warning("No monitor data to send")
            return
        
        # Gửi dữ liệu đến server
        try:
            headers = {"Authorization": f"Bearer {Config.MONITOR_TOKEN}"}
            response = self.session.post(
                f"{Config.MONITOR_URL}",
                json=monitor_data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            logging.info(f"Successfully sent monitor data to server: {response.json()}")
        except requests.RequestException as e:
            logging.error(f"Failed to send monitor data to server: {str(e)}")

if __name__ == "__main__":
    agent = ServerAgent()
    agent.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()