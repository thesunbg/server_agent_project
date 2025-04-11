# config.py

class Config:
    VERSION = "1.0.0"
    UPDATE_URL = "https://raw.githubusercontent.com/thesunbg/server_agent_project/refs/heads/master/latest_version.json"
    CHECK_INTERVAL = 300  # 5 phút (giây)
    DATA_DIR = "/var/log/server_agent"
    LOG_FILE = "/var/log/server_agent.log"
    MONITOR_URL = "nguyenvando.comss"
    MONITOR_TOKEN = "xxx"