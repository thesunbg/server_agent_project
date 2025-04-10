# monitor.py

import psutil
import subprocess
import json
from datetime import datetime
import logging
import os

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
        current_section = None
        current_type = None
        
        # Chia nhỏ đầu ra thành các dòng
        lines = dmi_output.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Phát hiện section mới
            if line.startswith('Handle'):
                match = re.search(r'DMI type (\d+)', line)
                if match:
                    current_type = int(match.group(1))
                    current_section = {}
                continue
            
            # Phân tích key-value
            if ':' in line and current_section is not None:
                key, value = [part.strip() for part in line.split(':', 1)]
                current_section[key] = value
                
                # Khi gặp dòng cuối của section, lưu vào đúng loại
                if key == "Type" and "Handle" in line:
                    if current_type == 0:  # BIOS
                        dmi_data["bios"] = current_section
                    elif current_type == 1:  # System
                        dmi_data["system"] = current_section
                    elif current_type == 17:  # Memory Device
                        dmi_data["memory_devices"].append(current_section)
                    elif current_type == 4:  # Processor
                        dmi_data["processors"].append(current_section)
                    current_section = None
        
        return dmi_data

    def get_system_info(self):
        """Lấy và lưu thông tin cấu hình hệ thống từ dmidecode"""
        try:
            if os.geteuid() != 0:
                logging.error("Need root privileges to run dmidecode")
                return

            dmi_info = subprocess.check_output(["dmidecode"], universal_newlines=True, stderr=subprocess.STDOUT)
            parsed_dmi = self.parse_dmidecode(dmi_info)
            
            # Phân tích thành JSON chuẩn
            parsed_dmi = self.parse_dmidecode(dmi_info)
            
            # Tạo dữ liệu JSON
            system_info = {
                "timestamp": datetime.now().isoformat(),
                "hostname": os.uname().nodename,
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