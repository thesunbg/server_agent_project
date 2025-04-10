#!/bin/bash

# URL của file project nén
PROJECT_URL="https://github.com/thesunbg/server_agent_project/raw/refs/heads/master/server_agent_project.tar.gz"
# Thư mục đích
DEST_DIR="/opt/server_agent"
# File tạm
TEMP_FILE="/tmp/server_agent_project.tar.gz"

# Tải file nén
wget "$PROJECT_URL" -O "$TEMP_FILE"
if [ $? -ne 0 ]; then
    echo "Failed to download project archive"
    exit 1
fi

# Dừng service
systemctl stop server-agent
if [ $? -ne 0 ]; then
    echo "Failed to stop server-agent service"
    rm "$TEMP_FILE"
    exit 1
fi

# Xóa thư mục cũ (nếu có)
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# Giải nén file mới
tar -xzvf "$TEMP_FILE" -C "$DEST_DIR" --strip-components=1
if [ $? -ne 0 ]; then
    echo "Failed to extract project archive"
    rm "$TEMP_FILE"
    exit 1
fi

# Cấp quyền thực thi cho main.py
chmod +x "$DEST_DIR/main.py"
if [ $? -ne 0 ]; then
    echo "Failed to set executable permissions"
    exit 1
fi

# Khởi động lại service
systemctl start server-agent
if [ $? -ne 0 ]; then
    echo "Failed to start server-agent service"
    exit 1
fi

# Dọn dẹp
rm "$TEMP_FILE"
rm -f "/tmp/update.sh"

echo "Update completed successfully"
exit 0