# monitor.py

import psutil
import subprocess
import json
from datetime import datetime
import logging
import os
import re
import requests

class ServerMonitor:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def parse_dmidecode(self, dmi_output):
        """Phân tích đầu ra dmidecode thành JSON chuẩn"""
        dmi_data = {
            "bios": {},
            "system": {},
            "memory_devices": [],
            "processors": []
        }
        
        if not dmi_output or "No SMBIOS" in dmi_output or "Permission denied" in dmi_output:
            logging.error("dmidecode output is empty or access denied")
            return dmi_data
        
        current_section = {}
        current_type = None
        
        # Ghi log đầu ra để debug
        logging.debug(f"dmidecode output:\n{dmi_output}")
        
        lines = dmi_output.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Bắt đầu một section mới với Handle
            if line.startswith('Handle'):
                if current_section and current_type is not None:
                    if current_type == 0:
                        dmi_data["bios"] = current_section
                    elif current_type == 1:
                        dmi_data["system"] = current_section
                    elif current_type == 17:
                        dmi_data["memory_devices"].append(current_section)
                    elif current_type == 4:
                        dmi_data["processors"].append(current_section)
                current_section = {}
                match = re.search(r'type (\d+)', line, re.I)
                if match:
                    current_type = int(match.group(1))
                continue
            
            # Phân tích key-value trong section
            if ':' in line:
                key, value = [part.strip() for part in line.split(':', 1)]
                if value:  # Chỉ thêm nếu có giá trị
                    current_section[key] = value
        
        # Lưu section cuối cùng nếu có
        if current_section and current_type is not None:
            if current_type == 0:
                dmi_data["bios"] = current_section
            elif current_type == 1:
                dmi_data["system"] = current_section
            elif current_type == 17:
                dmi_data["memory_devices"].append(current_section)
            elif current_type == 4:
                dmi_data["processors"].append(current_section)
        
        # Log kết quả phân tích
        logging.info(f"Parsed dmidecode data: {json.dumps(dmi_data, indent=2)}")
        return dmi_data

    def get_system_info(self):
        """Lấy và lưu thông tin cấu hình hệ thống từ dmidecode"""
        try:
            if os.geteuid() != 0:
                logging.error("Need root privileges to run dmidecode")
                return

            dmi_info = subprocess.check_output(["dmidecode"], universal_newlines=True, stderr=subprocess.STDOUT)
            
            # Phân tích thành JSON chuẩn
            parsed_dmi = self.parse_dmidecode(dmi_info)
            
            # Tạo dữ liệu JSON
            system_info = {
                "timestamp": datetime.now().isoformat(),
                "hostname": os.uname().nodename,
                "publicip": self.get_public_ip(),
                "hardware_info": parsed_dmi
            }
            
            output_file = self.data_dir / "system_info.json"
            with open(output_file, "w") as f:
                json.dump(system_info, f, indent=2)
            logging.info(f"System info collected and saved to {output_file}")

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to run dmidecode: {e.output}")
        except PermissionError:
            logging.error(f"Permission denied when writing to {output_file}")
        except Exception as e:
            logging.error(f"Failed to get system info: {str(e)}")

    def get_resource_usage(self):
        """Lấy thông tin sử dụng tài nguyên"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            resource_info = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total / (1024*1024),  # MB
                    "available": memory.available / (1024*1024),
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total / (1024*1024*1024),  # GB
                    "used": disk.used / (1024*1024*1024),
                    "free": disk.free / (1024*1024*1024),
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent / (1024*1024),  # MB
                    "bytes_recv": net_io.bytes_recv / (1024*1024)
                }
            }

            with open(self.data_dir / "resource_usage.json", "w") as f:
                json.dump(resource_info, f, indent=2)

        except Exception as e:
            logging.error(f"Failed to get resource usage: {str(e)}")

    def get_running_services(self):
        """Lấy tất cả các service và trạng thái của chúng từ systemd"""
        try:
            result = subprocess.check_output(
                ["systemctl", "list-units", "--type=service", "--all"],
                universal_newlines=True, stderr=subprocess.STDOUT
            )
            services = []
            lines = result.splitlines()
            
            # Bỏ qua header và footer
            for line in lines[1:]:
                if ".service" in line and "loaded" in line:
                    parts = line.split()
                    service_name = parts[0].replace(".service", "")
                    load_state = parts[1]  # loaded/not-found
                    active_state = parts[2]  # active/inactive
                    sub_state = parts[3]  # running/exited/dead/failed/...
                    description = " ".join(parts[4:]) if len(parts) > 4 else "No description"
                    services.append({
                        "name": service_name,
                        "load_state": load_state,
                        "active_state": active_state,
                        "sub_state": sub_state,
                        "description": description
                    })
            
            output_file = self.data_dir / "services.json"  # Đổi tên file để rõ ràng hơn
            with open(output_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "services": services
                }, f, indent=2)
            logging.info(f"All services saved to {output_file}")
            return services
        
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get services: {e.output}")
            return []
        except Exception as e:
            logging.error(f"Error getting services: {str(e)}")
            return []

    def detect_firewall(self):
        """Phát hiện firewall và liệt kê rules chi tiết, bao gồm tất cả chain của iptables"""
        firewall_info = {
            "ufw": {"installed": False, "active": False, "rules": []},
            "iptables": {"installed": False, "chains": {}},
            "nftables": {"installed": False, "rules": ""},
            "firewalld": {"installed": False, "active": False, "rules": []}
        }
        
        # Kiểm tra UFW
        try:
            if os.path.exists("/usr/sbin/ufw"):
                firewall_info["ufw"]["installed"] = True
            status = subprocess.check_output(["ufw", "status", "verbose"], universal_newlines=True)
            if "Status: active" in status:
                firewall_info["ufw"]["active"] = True
                lines = status.splitlines()
                for line in lines:
                    if "ALLOW" in line or "DENY" in line or "REJECT" in line:
                        firewall_info["ufw"]["rules"].append(line.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Kiểm tra iptables
        try:
            if os.path.exists("/sbin/iptables"):
                firewall_info["iptables"]["installed"] = True
            rules = subprocess.check_output(["iptables", "-L", "-v", "-n", "--line-numbers"], universal_newlines=True)
            current_chain = None
            for line in rules.splitlines():
                if line.startswith("Chain"):
                    current_chain = line.split()[1]
                    firewall_info["iptables"]["chains"][current_chain] = {
                        "policy": line.split("policy")[1].strip() if "policy" in line else "unknown",
                        "rules": []
                    }
                elif line and not line.startswith("num") and current_chain:
                    parts = line.split()
                    if len(parts) >= 8:
                        rule = {
                            "num": parts[0],
                            "target": parts[1],
                            "protocol": parts[2],
                            "opt": parts[3],
                            "source": parts[4],
                            "destination": parts[5],
                            "extra": " ".join(parts[6:]) if len(parts) > 6 else ""
                        }
                        firewall_info["iptables"]["chains"][current_chain]["rules"].append(rule)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Kiểm tra nftables
        try:
            if os.path.exists("/usr/sbin/nft"):
                firewall_info["nftables"]["installed"] = True
            rules = subprocess.check_output(["nft", "list", "ruleset"], universal_newlines=True)
            firewall_info["nftables"]["rules"] = rules.strip() if rules.strip() else "No rules defined"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Kiểm tra firewalld
        try:
            if os.path.exists("/usr/sbin/firewall-cmd"):
                firewall_info["firewalld"]["installed"] = True
            status = subprocess.check_output(["firewall-cmd", "--state"], universal_newlines=True)
            if "running" in status:
                firewall_info["firewalld"]["active"] = True
                rules = subprocess.check_output(["firewall-cmd", "--list-all"], universal_newlines=True)
                lines = rules.splitlines()
                for line in lines:
                    if "services:" in line or "ports:" in line or "rules:" in line:
                        firewall_info["firewalld"]["rules"].append(line.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Xác định firewall chính đang hoạt động
        active_firewall = "unknown"
        if firewall_info["ufw"]["active"]:
            active_firewall = "ufw"
        elif firewall_info["iptables"]["chains"]:
            active_firewall = "iptables"
        elif firewall_info["nftables"]["rules"] and firewall_info["nftables"]["rules"] != "No rules defined":
            active_firewall = "nftables"
        elif firewall_info["firewalld"]["active"]:
            active_firewall = "firewalld"
        
        firewall_info["active_firewall"] = active_firewall
        
        output_file = self.data_dir / "firewall_info.json"
        with open(output_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "firewall": firewall_info
            }, f, indent=2)
        logging.info(f"Firewall info saved to {output_file}")
        return firewall_info

    def get_public_ip(self):
        """Lấy địa chỉ IP public của server"""
        try:
            response = requests.get("https://whois.inet.vn/api/ifconfig", timeout=5)
            response.raise_for_status()  # Kiểm tra lỗi HTTP
            ip = response.text.strip()
            logging.info(f"Public IP retrieved: {ip}")
            return ip
        except requests.RequestException as e:
            logging.error(f"Failed to get public IP: {str(e)}")
            return "unknown"