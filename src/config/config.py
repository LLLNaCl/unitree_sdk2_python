
# 配置文件 - 基础配置

import os
import json
from pathlib import Path

class Config:
    """配置管理类"""
    
    def __init__(self):
        # 项目根目录
        self.ROOT_DIR = Path(__file__).parent.parent.parent
        
        # 设备信息
        self.NETWORK_INTERFACE = os.environ.get("NETWORK_INTERFACE", "eth0")
        self.DEVICE_ID = os.environ.get("B2_DEVICE_ID", "b2_default_001")
        self.DEVICE_NAME = os.environ.get("B2_DEVICE_NAME", "Unitree B2 Robot Dog")
        self.FIRMWARE_VERSION = "1.0.0"
        
        # 网络配置
        self.NETWORK_TYPE = os.environ.get("NETWORK_TYPE", "wifi")  # wifi or 4g
        self.WIFI_SSID = os.environ.get("WIFI_SSID", "")
        self.WIFI_PASSWORD = os.environ.get("WIFI_PASSWORD", "")
        
        # 日志配置
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
        self.LOG_DIR = self.ROOT_DIR / "logs"
        
        # 视频流配置
        self.RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/b2_stream")
        self.VIDEO_DEVICE = os.environ.get("VIDEO_DEVICE", "/dev/video0")
        self.VIDEO_RESOLUTION = os.environ.get("VIDEO_RESOLUTION", "640x360")
        self.VIDEO_FPS = int(os.environ.get("VIDEO_FPS", 30))
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.LOG_DIR.mkdir(exist_ok=True)
    
    def to_dict(self):
        """将配置转换为字典"""
        return {
            "network_interface": self.NETWORK_INTERFACE,
            "device_id": self.DEVICE_ID,
            "device_name": self.DEVICE_NAME,
            "firmware_version": self.FIRMWARE_VERSION,
            "network_type": self.NETWORK_TYPE,
            "log_level": self.LOG_LEVEL,
            "rtsp_url": self.RTSP_URL,
            "video_resolution": self.VIDEO_RESOLUTION,
            "video_fps": self.VIDEO_FPS
        }
    
    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

# 全局配置实例
config = Config()
