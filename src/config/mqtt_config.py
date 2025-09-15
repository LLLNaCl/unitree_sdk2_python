
# MQTT配置文件

import os
import json
from typing import Dict, Any

class MQTTConfig:
    """MQTT配置管理类"""
    
    def __init__(self, device_id: str):
        # MQTT Broker配置
        self.BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "mqtt.example.com")
        self.BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 1883))
        self.BROKER_USERNAME = os.environ.get("MQTT_BROKER_USERNAME", "")
        self.BROKER_PASSWORD = os.environ.get("MQTT_BROKER_PASSWORD", "")
        
        # 设备ID（用于主题生成）
        self.DEVICE_ID = device_id
        
        # MQTT协议版本（支持5.0）
        self.PROTOCOL_VERSION = int(os.environ.get("MQTT_PROTOCOL_VERSION", 5))
        
        # 连接参数
        self.KEEPALIVE = int(os.environ.get("MQTT_KEEPALIVE", 60))
        self.CLEAN_SESSION = os.environ.get("MQTT_CLEAN_SESSION", "true").lower() == "true"
        self.CONNECT_TIMEOUT = int(os.environ.get("MQTT_CONNECT_TIMEOUT", 10))
        
        # TLS配置
        self.USE_TLS = os.environ.get("MQTT_USE_TLS", "true").lower() == "true"
        self.CA_CERTS = os.environ.get("MQTT_CA_CERTS", "")
        self.CERTFILE = os.environ.get("MQTT_CERTFILE", "")
        self.KEYFILE = os.environ.get("MQTT_KEYFILE", "")
        
        # 主题配置（按设备ID区分）
        self.TOPICS = {
            # 上行主题（设备→云端）
            "status": f"unitree/b2/{self.DEVICE_ID}/status",
            "sensor_data": f"unitree/b2/{self.DEVICE_ID}/sensor/data",
            "video_stream": f"unitree/b2/{self.DEVICE_ID}/video/stream",
            "error": f"unitree/b2/{self.DEVICE_ID}/error",
            "log": f"unitree/b2/{self.DEVICE_ID}/log",
            
            # 下行主题（云端→设备）
            "command": f"unitree/b2/{self.DEVICE_ID}/command",
            "control": f"unitree/b2/{self.DEVICE_ID}/control",
            "config": f"unitree/b2/{self.DEVICE_ID}/config"
        }
        
        # QoS配置
        self.QOS = {
            "status": 1,
            "sensor_data": 0,
            "video_stream": 0,
            "error": 2,
            "log": 1,
            "command": 1,
            "control": 1,
            "config": 1
        }
    
    def get_connection_params(self) -> Dict[str, Any]:
        """获取MQTT连接参数"""
        params = {
            "host": self.BROKER_HOST,
            "port": self.BROKER_PORT,
            "keepalive": self.KEEPALIVE,
            "clean_session": self.CLEAN_SESSION,
            "protocol": self.PROTOCOL_VERSION,
            "connect_timeout": self.CONNECT_TIMEOUT
        }
        
        if self.BROKER_USERNAME and self.BROKER_PASSWORD:
            params["username"] = self.BROKER_USERNAME
            params["password"] = self.BROKER_PASSWORD
            
        if self.USE_TLS:
            tls_params = {}
            if self.CA_CERTS:
                tls_params["ca_certs"] = self.CA_CERTS
            if self.CERTFILE:
                tls_params["certfile"] = self.CERTFILE
            if self.KEYFILE:
                tls_params["keyfile"] = self.KEYFILE
            params["tls"] = tls_params
            
        return params
    
    def get_topic(self, topic_type: str) -> str:
        """获取指定类型的主题"""
        if topic_type not in self.TOPICS:
            raise ValueError(f"Invalid topic type: {topic_type}")
        return self.TOPICS[topic_type]
    
    def get_qos(self, topic_type: str) -> int:
        """获取指定主题的QoS级别"""
        if topic_type not in self.QOS:
            raise ValueError(f"Invalid topic type: {topic_type}")
        return self.QOS[topic_type]
    
    def __str__(self):
        return json.dumps({
            "broker_host": self.BROKER_HOST,
            "broker_port": self.BROKER_PORT,
            "device_id": self.DEVICE_ID,
            "protocol_version": self.PROTOCOL_VERSION,
            "use_tls": self.USE_TLS,
            "topics": self.TOPICS
        }, indent=2)
