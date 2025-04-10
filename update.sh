#!/bin/bash

# URL của file project nén
PROJECT_URL="https://github.com/thesunbg/server_agent_project/raw/refs/heads/master/server_agent_project.tar.gz"
#!/bin/bash

DEST_DIR="/opt/server_agent"
TEMP_FILE="/tmp/server_agent_project.tar.gz"
SERVICE_FILE="/etc/systemd/system/server-agent.service"

# Tải project nén
wget "$PROJECT_URL" -O "$TEMP_FILE"
if [ $? -ne 0 ]; then
    echo "Failed to download project archive" >&2
    exit 1
fi

# Kiểm tra xem agent đã cài chưa
if [ ! -d "$DEST_DIR" ] || [ ! -f "$SERVICE_FILE" ]; then
    echo "Performing initial installation..."
    apt-get update
    apt-get install -y python3 python3-pip dmidecode
    pip3 install psutil requests
    mkdir -p "$DEST_DIR"
    tar -xzvf "$TEMP_FILE" -C "$DEST_DIR" --strip-components=1
    chmod +x "$DEST_DIR/main.py"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Server Monitoring Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/server_agent/main.py
Restart=always
User=root
WorkingDirectory=/opt/server_agent

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable server-agent
else
    echo "Updating existing installation..."
    systemctl stop server-agent
    rm -rf "$DEST_DIR"
    mkdir -p "$DEST_DIR"
    tar -xzvf "$TEMP_FILE" -C "$DEST_DIR" --strip-components=1
    chmod +x "$DEST_DIR/main.py"
fi

# Khởi động lại service
systemctl start server-agent
if [ $? -ne 0 ]; then
    echo "Failed to start server-agent service" >&2
    exit 1
fi

# Dọn dẹp
rm "$TEMP_FILE"
rm -f "/tmp/update.sh"

echo "Update completed successfully"
exit 0