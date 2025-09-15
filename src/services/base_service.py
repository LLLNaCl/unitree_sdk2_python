
# 服务基类

import time
from typing import Dict, Any, Optional, Callable, List
import json

from src.utils.logger import logger

class BaseService:
    """服务基类，所有服务都继承自此类"""
    
    def __init__(self, name: str, controller, mqtt_client):
        """初始化服务
        
        Args:
            name: 服务名称
            controller: 控制器实例
            mqtt_client: MQTT客户端实例
        """
        self.name = name
        self.controller = controller
        self.mqtt_client = mqtt_client
        self.running = False
        self.initialized = False
        
        # 服务状态
        self.status = {
            "name": self.name,
            "status": "stopped",
            "last_error": None,
            "start_time": 0,
            "uptime": 0,
            "statistics": {}
        }
        
        # 订阅的命令类型
        self.command_types: List[str] = []
        
        # 统计信息
        self.statistics = {
            "commands_received": 0,
            "commands_processed": 0,
            "commands_failed": 0,
            "data_sent": 0,
            "errors": 0
        }
    
    def initialize(self) -> bool:
        """初始化服务
        
        Returns:
            bool: 初始化是否成功
        """
        if self.initialized:
            logger.info(f"Service {self.name} is already initialized")
            return True
            
        try:
            # 订阅命令主题
            self._subscribe_commands()
            
            # 初始化状态
            self.status.update({
                "status": "initialized",
                "last_error": None
            })
            
            self.initialized = True
            logger.info(f"Service {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize service {self.name}: {str(e)}")
            self.status.update({
                "status": "error",
                "last_error": str(e)
            })
            return False
    
    def start(self) -> bool:
        """启动服务
        
        Returns:
            bool: 启动是否成功
        """
        if self.running:
            logger.info(f"Service {self.name} is already running")
            return True
            
        # 如果未初始化，先初始化
        if not self.initialized and not self.initialize():
            logger.error(f"Failed to start service {self.name}: not initialized")
            return False
            
        try:
            # 启动服务特定的任务
            self._start_service()
            
            # 更新状态
            self.status.update({
                "status": "running",
                "start_time": time.time(),
                "uptime": 0
            })
            
            self.running = True
            logger.info(f"Service {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start service {self.name}: {str(e)}")
            self.status.update({
                "status": "error",
                "last_error": str(e)
            })
            return False
    
    def stop(self) -> bool:
        """停止服务
        
        Returns:
            bool: 停止是否成功
        """
        if not self.running:
            logger.info(f"Service {self.name} is not running")
            return True
            
        try:
            # 停止服务特定的任务
            self._stop_service()
            
            # 更新状态
            self.status.update({
                "status": "stopped",
                "uptime": time.time() - self.status["start_time"]
            })
            
            self.running = False
            logger.info(f"Service {self.name} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {self.name}: {str(e)}")
            self.status.update({
                "status": "error",
                "last_error": str(e)
            })
            return False
    
    def restart(self) -> bool:
        """重启服务
        
        Returns:
            bool: 重启是否成功
        """
        logger.info(f"Restarting service {self.name}")
        self.stop()
        time.sleep(1)  # 等待停止完成
        return self.start()
    
    def is_running(self) -> bool:
        """检查服务是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self.running
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态
        
        Returns:
            Dict[str, Any]: 服务状态信息
        """
        # 更新运行时间
        if self.running:
            self.status["uptime"] = time.time() - self.status["start_time"]
        
        # 更新统计信息
        self.status["statistics"] = self.statistics
        
        return self.status.copy()
    
    def _subscribe_commands(self) -> None:
        """订阅命令主题"""
        if not self.command_types:
            return
            
        for command_type in self.command_types:
            try:
                # 注册命令回调
                self.mqtt_client.register_callback(
                    "command", 
                    lambda topic, payload, ct=command_type: self._handle_command(ct, payload)
                )
                logger.info(f"Service {self.name} subscribed to command type: {command_type}")
            except Exception as e:
                logger.error(f"Failed to subscribe to command type {command_type}: {str(e)}")
    
    def _handle_command(self, command_type: str, payload: Dict[str, Any]) -> None:
        """处理接收到的命令
        
        Args:
            command_type: 命令类型
            payload: 命令负载
        """
        # 更新统计信息
        self.statistics["commands_received"] += 1
        
        try:
            # 检查命令类型是否匹配
            if "command" not in payload or payload["command"] != command_type:
                return
                
            # 检查设备ID是否匹配
            if "device_id" in payload and payload["device_id"] != self.mqtt_client.config.DEVICE_ID:
                return
                
            # 检查是否有数据
            if "data" not in payload:
                logger.warning(f"Received command {command_type} without data payload")
                return
                
            # 处理命令
            result = self._process_command(command_type, payload["data"])
            
            # 更新统计信息
            if result:
                self.statistics["commands_processed"] += 1
            else:
                self.statistics["commands_failed"] += 1
                self.statistics["errors"] += 1
                
        except Exception as e:
            logger.error(f"Error handling command {command_type}: {str(e)}")
            self.statistics["commands_failed"] += 1
            self.statistics["errors"] += 1
            self.status["last_error"] = str(e)
    
    def _process_command(self, command_type: str, data: Dict[str, Any]) -> bool:
        """处理命令的抽象方法，子类需要实现
        
        Args:
            command_type: 命令类型
            data: 命令数据
            
        Returns:
            bool: 处理是否成功
        """
        logger.warning(f"Service {self.name} does not implement command processing for {command_type}")
        return False
    
    def _start_service(self) -> None:
        """启动服务的抽象方法，子类可以重写"""
        pass
    
    def _stop_service(self) -> None:
        """停止服务的抽象方法，子类可以重写"""
        pass
    
    def _publish_response(self, command_type: str, success: bool, data: Optional[Dict[str, Any]] = None) -> None:
        """发布命令响应
        
        Args:
            command_type: 命令类型
            success: 是否成功
            data: 响应数据
        """
        response = {
            "command": command_type,
            "success": success,
            "timestamp": time.time()
        }
        
        if data is not None:
            response["data"] = data
            
        if not success and "error" not in response:
            response["error"] = "Unknown error"
            
        try:
            self.mqtt_client.publish("command_response", response)
            logger.debug(f"Published response for command {command_type}: {success}")
        except Exception as e:
            logger.error(f"Failed to publish response for command {command_type}: {str(e)}")
    
    def _publish_data(self, data_type: str, data: Dict[str, Any]) -> None:
        """发布数据
        
        Args:
            data_type: 数据类型
            data: 数据内容
        """
        try:
            # 根据数据类型选择不同的主题
            if data_type == "sensor":
                self.mqtt_client.publish_sensor_data(data)
            elif data_type == "status":
                self.mqtt_client.publish_status(data)
            elif data_type == "log":
                self.mqtt_client.publish_log(data)
            elif data_type == "error":
                self.mqtt_client.publish_error(data)
            elif data_type == "video_stream":
                self.mqtt_client.publish_video_stream(data)
            else:
                self.mqtt_client.publish(data_type, data)
                
            # 更新统计信息
            self.statistics["data_sent"] += 1
            
        except Exception as e:
            logger.error(f"Failed to publish data {data_type}: {str(e)}")
            self.statistics["errors"] += 1
            self.status["last_error"] = str(e)
