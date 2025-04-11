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

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo or run as root."
    exit 1
fi

detect_os() {
    if [ -f /etc/os-release ]; then
        # CentOS 7 và Ubuntu có /etc/os-release
        . /etc/os-release
        OS=$ID
        VERSION_ID=$VERSION_ID
    elif [ -f /etc/redhat-release ]; then
        # CentOS 6 dùng /etc/redhat-release
        OS="centos"
        VERSION_ID=$(cat /etc/redhat-release | grep -oP 'CentOS release \K[0-9]+')
        if [ -z "$VERSION_ID" ]; then
            echo "Cannot determine CentOS version from /etc/redhat-release."
            exit 1
        fi
    else
        echo "Cannot detect OS. Neither /etc/os-release nor /etc/redhat-release found."
        exit 1
    fi
}

install_pip() {
    echo "Checking for pip3..."
    if ! command -v pip3 &> /dev/null; then
        echo "pip3 not found. Installing pip..."
        case $OS in
            ubuntu)
                apt-get update
                apt-get install -y python3-pip
                ;;
            centos)
                if [ "$VERSION_ID" = "6" ]; then
                    # CentOS 6 cần cài Python 3 trước, sau đó dùng get-pip.py
                    echo "Installing Python 3 on CentOS 6..."
                    yum install -y centos-release-scl 2>/dev/null || true
                    yum install -y python36 2>/dev/null || true
                    if ! command -v python3 &> /dev/null; then
                        echo "Python 3 not found. Please install Python 3 manually on CentOS 6."
                        exit 1
                    fi
                    curl -O https://bootstrap.pypa.io/pip/2.6/get-pip.py
                    python3 get-pip.py
                    rm get-pip.py
                else
                    # CentOS 7
                    yum install -y epel-release
                    yum install -y python3-pip
                fi
                ;;
            *)
                echo "Cannot install pip on unsupported OS: $OS"
                exit 1
                ;;
        esac
    fi
    echo "pip3 is installed: $(pip3 --version)"
}

# Hàm cài đặt các thư viện Python
install_python_libraries() {
    echo "Installing required Python libraries..."
    pip3 install psutil requests distro
    if [ $? -eq 0 ]; then
        echo "Python libraries installed successfully:"
        echo "- psutil: $(pip3 show psutil | grep Version)"
        echo "- requests: $(pip3 show requests | grep Version)"
        echo "- distro: $(pip3 show distro | grep Version)"
    else
        echo "Failed to install Python libraries."
        exit 1
    fi
}

# Hàm cập nhật cho Ubuntu
update_ubuntu() {
    echo "Detected Ubuntu. Using apt-get to update..."
    apt-get update
    apt-get upgrade -y
    apt-get autoremove -y
    echo "Ubuntu update completed."
}

# Hàm cập nhật cho CentOS
update_centos() {
    echo "Detected CentOS. Using yum to update..."
    
    # Kiểm tra phiên bản CentOS
    if [ -z "$VERSION_ID" ]; then
        echo "Cannot determine CentOS version."
        exit 1
    fi

    # CentOS 6 và 7 đã EOL, cần chuyển sang kho vault
    if [ "$VERSION_ID" = "6" ] || [ "$VERSION_ID" = "7" ]; then
        echo "CentOS $VERSION_ID is EOL. Switching to vault repository..."
        
        # Sao lưu file repo hiện tại
        if [ -d /etc/yum.repos.d ]; then
            mkdir -p /etc/yum.repos.d/backup
            mv /etc/yum.repos.d/*.repo /etc/yum.repos.d/backup/ 2>/dev/null
        fi

        # Tạo file repo mới cho vault
        if [ "$VERSION_ID" = "6" ]; then
            cat > /etc/yum.repos.d/CentOS-Vault.repo << EOL
[base]
name=CentOS-6 - Base
baseurl=http://vault.centos.org/6.10/os/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-6
enabled=1

[updates]
name=CentOS-6 - Updates
baseurl=http://vault.centos.org/6.10/updates/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-6
enabled=1
EOL
        elif [ "$VERSION_ID" = "7" ]; then
            cat > /etc/yum.repos.d/CentOS-Vault.repo << EOL
[base]
name=CentOS-7 - Base
baseurl=http://vault.centos.org/7.9.2009/os/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
enabled=1

[updates]
name=CentOS-7 - Updates
baseurl=http://vault.centos.org/7.9.2009/updates/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
enabled=1
EOL
        fi
    fi

    # Xóa cache yum và cập nhật
    yum clean all
    yum update -y
    yum autoremove -y 2>/dev/null || true  # CentOS 6 không có autoremove, bỏ qua lỗi nếu có
    echo "CentOS update completed."
}

# Main script
echo "Starting system update and library installation..."

# Phát hiện hệ điều hành
detect_os

# Cập nhật hệ thống
case $OS in
    ubuntu)
        update_ubuntu
        ;;
    centos)
        update_centos
        ;;
    *)
        echo "Unsupported OS: $OS. This script supports Ubuntu and CentOS only."
        exit 1
        ;;
esac

# Cài đặt pip và các thư viện Python
install_pip
install_python_libraries

# Kiểm tra xem agent đã cài chưa
if [ ! -d "$DEST_DIR" ] || [ ! -f "$SERVICE_FILE" ]; then
    echo "Performing initial installation..."
    # apt-get update
    # apt-get install -y python3 python3-pip dmidecode
    # pip3 install psutil requests distro
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