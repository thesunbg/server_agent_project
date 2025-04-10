#!/bin/bash

# URL của file project nén
PROJECT_URL="https://github.com/thesunbg/server_agent_project/raw/refs/heads/master/server_agent_project.tar.gz"
#!/bin/bash

# Thư mục đích
DEST_DIR="/opt/server_agent"
# File tạm
TEMP_FILE="/tmp/server_agent_project.tar.gz"
# File service
SERVICE_FILE="/etc/systemd/system/server-agent.service"

# Hàm cài đặt dependencies
install_dependencies() {
    echo "Installing dependencies..."
    apt-get update
    apt-get install -y python3 python3-pip dmidecode
    pip3 install psutil requests
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies"
        exit 1
    fi
}

# Tải project nén
wget "$PROJECT_URL" -O "$TEMP_FILE"
if [ $? -ne 0 ]; then
    echo "Failed to download project archive"
    exit 1
fi

# Kiểm tra xem agent đã cài chưa
if [ ! -d "$DEST_DIR" ] || [ ! -f "$SERVICE_FILE" ]; then
    echo "Performing initial installation..."

    # Cài đặt dependencies nếu chưa có
    if ! command -v python3 &> /dev/null || ! python3 -c "import psutil, requests" &> /dev/null; then
        install_dependencies
    fi

    # Tạo thư mục đích
    mkdir -p "$DEST_DIR"

    # Giải nén project
    tar -xzvf "$TEMP_FILE" -C "$DEST_DIR" --strip-components=1
    if [ $? -ne 0 ]; then
        echo "Failed to extract project archive"
        rm "$TEMP_FILE"
        exit 1
    fi

    # Cấp quyền thực thi
    chmod +x "$DEST_DIR/main.py"

    # Tạo file service
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

    # Kích hoạt service
    systemctl daemon-reload
    systemctl enable server-agent
    systemctl start server-agent
    if [ $? -ne 0 ]; then
        echo "Failed to start server-agent service"
        rm "$TEMP_FILE"
        exit 1
    fi

    echo "Initial installation completed successfully"
else
    echo "Updating existing installation..."

    # Dừng service
    systemctl stop server-agent
    if [ $? -ne 0 ]; then
        echo "Failed to stop server-agent service"
        rm "$TEMP_FILE"
        exit 1
    fi

    # Xóa thư mục cũ
    rm -rf "$DEST_DIR"
    mkdir -p "$DEST_DIR"

    # Giải nén project mới
    tar -xzvf "$TEMP_FILE" -C "$DEST_DIR" --strip-components=1
    if [ $? -ne 0 ]; then
        echo "Failed to extract project archive"
        rm "$TEMP_FILE"
        exit 1
    fi

    # Cấp quyền thực thi
    chmod +x "$DEST_DIR/main.py"

    # Khởi động lại service
    systemctl start server-agent
    if [ $? -ne 0 ]; then
        echo "Failed to start server-agent service"
        rm "$TEMP_FILE"
        exit 1
    fi

    echo "Update completed successfully"
fi

# Dọn dẹp
rm "$TEMP_FILE"
rm -f "/tmp/update.sh"

exit 0