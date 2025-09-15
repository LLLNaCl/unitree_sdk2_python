
# MQTT客户端实现

import json
import time
import threading
from typing import Dict, Any, Callable, Optional, List
import paho.mqtt.client as mqtt

from src.config.mqtt_config import MQTTConfig
from src.utils.logger import logger

class MQTTClient:
    """MQTT客户端，用于与云端服务器通信"""
    
    def __init__(self, config: MQTTConfig):
        """初始化MQTT客户端
        
        Args:
            config: MQTT配置
        """
        self.config = config
        self.client = None
        self.connected = False
        self.connecting = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        
        # 消息回调函数
        self.message_callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        
        # 连接状态回调
        self.connect_callback: Optional[Callable[[bool], None]] = None
        
        # 重连线程
        self.reconnect_thread = None
        self.reconnect_flag = False
    
    def connect(self) -> bool:
        """连接到MQTT服务器
        
        Returns:
            bool: 连接是否成功
        """
        if self.connected:
            logger.info("Already connected to MQTT broker")
            return True
            
        if self.connecting:
            logger.info("Already connecting to MQTT broker")
            return False
            
        try:
            self.connecting = True
            
            # 创建MQTT客户端
            client_id = f"b2_{self.config.DEVICE_ID}_{int(time.time())}"
            self.client = mqtt.Client(client_id=client_id, protocol=self.config.PROTOCOL_VERSION)
            
            # 设置用户名和密码
            if self.config.BROKER_USERNAME and self.config.BROKER_PASSWORD:
                self.client.username_pw_set(
                    username=self.config.BROKER_USERNAME,
                    password=self.config.BROKER_PASSWORD
                )
            
            # 设置TLS
            if self.config.USE_TLS:
                tls_params = {}
                if self.config.CA_CERTS:
                    tls_params["ca_certs"] = self.config.CA_CERTS
                if self.config.CERTFILE:
                    tls_params["certfile"] = self.config.CERTFILE
                if self.config.KEYFILE:
                    tls_params["keyfile"] = self.config.KEYFILE
                
                self.client.tls_set(**tls_params)
            
            # 设置回调函数
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_log = self._on_log
            
            # 连接到MQTT服务器
            logger.info(f"Connecting to MQTT broker: {self.config.BROKER_HOST}:{self.config.BROKER_PORT}")
            connection_params = self.config.get_connection_params()
            self.client.connect(**connection_params)
            
            # 启动网络循环线程
            self.client.loop_start()
            
            # 等待连接成功
            timeout = 10
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                logger.error("Failed to connect to MQTT broker (timeout)")
                self.client.loop_stop()
                self.client = None
                return False
                
            logger.info("Connected to MQTT broker successfully")
            
            # 订阅下行主题
            self._subscribe_topics()
            
            # 启动重连线程
            self._start_reconnect_thread()
            
            return True
            
        except Exception as e:
            logger.error(f"MQTT connection error: {str(e)}")
            self.client = None
            return False
        finally:
            self.connecting = False
    
    def disconnect(self) -> bool:
        """断开与MQTT服务器的连接
        
        Returns:
            bool: 断开是否成功
        """
        if not self.connected:
            logger.info("Not connected to MQTT broker")
            return True
            
        try:
            # 停止重连线程
            self.reconnect_flag = False
            if self.reconnect_thread and self.reconnect_thread.is_alive():
                self.reconnect_thread.join()
            
            # 断开连接
            self.client.disconnect()
            self.client.loop_stop()
            
            self.connected = False
            logger.info("Disconnected from MQTT broker")
            
            return True
            
        except Exception as e:
            logger.error(f"MQTT disconnection error: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        """检查是否已连接到MQTT服务器
        
        Returns:
            bool: 是否已连接
        """
        return self.connected
    
    def publish(self, topic_type: str, payload: Dict[str, Any]) -> bool:
        """发布消息到指定主题
        
        Args:
            topic_type: 主题类型
            payload: 消息 payload（字典格式）
            
        Returns:
            bool: 发布是否成功
        """
        if not self.connected:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            # 获取主题和QoS
            topic = self.config.get_topic(topic_type)
            qos = self.config.get_qos(topic_type)
            
            # 添加设备信息和时间戳
            message = {
                "device_id": self.config.DEVICE_ID,
                "timestamp": time.time(),
                "data": payload
            }
            
            # 转换为JSON字符串
            message_str = json.dumps(message)
            
            # 发布消息
            result = self.client.publish(topic, message_str, qos=qos)
            status = result[0]
            
            if status == 0:
                logger.debug(f"Published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish message to {topic}")
                return False
                
        except Exception as e:
            logger.error(f"MQTT publish error: {str(e)}")
            return False
    
    def publish_status(self, status: Dict[str, Any]) -> bool:
        """发布设备状态
        
        Args:
            status: 设备状态信息
            
        Returns:
            bool: 发布是否成功
        """
        return self.publish("status", status)
    
    def publish_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """发布传感器数据
        
        Args:
            sensor_data: 传感器数据
            
        Returns:
            bool: 发布是否成功
        """
        return self.publish("sensor_data", sensor_data)
    
    def publish_video_stream(self, stream_info: Dict[str, Any]) -> bool:
        """发布视频流信息
        
        Args:
            stream_info: 视频流信息
            
        Returns:
            bool: 发布是否成功
        """
        return self.publish("video_stream", stream_info)
    
    def publish_error(self, error_info: Dict[str, Any]) -> bool:
        """发布错误信息
        
        Args:
            error_info: 错误信息
            
        Returns:
            bool: 发布是否成功
        """
        return self.publish("error", error_info)
    
    def publish_log(self, log_info: Dict[str, Any]) -> bool:
        """发布日志信息
        
        Args:
            log_info: 日志信息
            
        Returns:
            bool: 发布是否成功
        """
        return self.publish("log", log_info)
    
    def register_callback(self, topic_type: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """注册消息回调函数
        
        Args:
            topic_type: 主题类型
            callback: 回调函数，参数为 (topic, payload)
        """
        if topic_type not in self.message_callbacks:
            self.message_callbacks[topic_type] = []
        
        self.message_callbacks[topic_type].append(callback)
    
    def set_connect_callback(self, callback: Callable[[bool], None]) -> None:
        """设置连接状态回调函数
        
        Args:
            callback: 回调函数，参数为 (connected)
        """
        self.connect_callback = callback
    
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
        """连接回调函数"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker with result code 0")
            
            # 订阅下行主题
            self._subscribe_topics()
            
            # 调用连接回调
            if self.connect_callback:
                try:
                    self.connect_callback(True)
                except Exception as e:
                    logger.error(f"Connect callback error: {str(e)}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")
            
            # 调用连接回调
            if self.connect_callback:
                try:
                    self.connect_callback(False)
                except Exception as e:
                    logger.error(f"Connect callback error: {str(e)}")
    
    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """断开连接回调函数"""
        self.connected = False
        
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with result code {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
        
        # 调用连接回调
        if self.connect_callback:
            try:
                self.connect_callback(False)
            except Exception as e:
                logger.error(f"Disconnect callback error: {str(e)}")
        
        # 设置重连标志
        self.reconnect_flag = True
    
    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """消息接收回调函数"""
        try:
            # 解析消息
            payload_str = msg.payload.decode()
            payload = json.loads(payload_str)
            
            logger.debug(f"Received message on {msg.topic}: {payload_str}")
            
            # 查找对应的主题类型
            topic_type = None
            for key, topic in self.config.TOPICS.items():
                if topic == msg.topic:
                    topic_type = key
                    break
            
            if topic_type is None:
                logger.warning(f"Received message on unknown topic: {msg.topic}")
                return
            
            # 调用回调函数
            if topic_type in self.message_callbacks:
                for callback in self.message_callbacks[topic_type]:
                    try:
                        callback(msg.topic, payload)
                    except Exception as e:
                        logger.error(f"Message callback error: {str(e)}")
        
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message: {msg.payload.decode()}")
        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
    
    def _on_log(self, client: mqtt.Client, userdata: Any, level: int, buf: str) -> None:
        """日志回调函数"""
        if level == mqtt.MQTT_LOG_DEBUG:
            logger.debug(f"MQTT log: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            logger.info(f"MQTT log: {buf}")
        elif level == mqtt.MQTT_LOG_NOTICE:
            logger.info(f"MQTT log: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            logger.warning(f"MQTT log: {buf}")
        elif level == mqtt.MQTT_LOG_ERR:
            logger.error(f"MQTT log: {buf}")
    
    def _subscribe_topics(self) -> None:
        """订阅下行主题"""
        if not self.connected:
            return
            
        # 需要订阅的下行主题类型
        downlink_topics = ["command", "control", "config"]
        
        for topic_type in downlink_topics:
            try:
                topic = self.config.get_topic(topic_type)
                qos = self.config.get_qos(topic_type)
                
                result, mid = self.client.subscribe(topic, qos=qos)
                if result == 0:
                    logger.info(f"Subscribed to topic: {topic}")
                else:
                    logger.error(f"Failed to subscribe to topic: {topic}")
            except Exception as e:
                logger.error(f"Failed to subscribe to topic {topic_type}: {str(e)}")
    
    def _start_reconnect_thread(self) -> None:
        """启动重连线程"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
            
        self.reconnect_flag = True
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()
    
    def _reconnect_loop(self) -> None:
        """重连循环"""
        while self.reconnect_flag:
            if not self.connected and not self.connecting:
                logger.info(f"Attempting to reconnect to MQTT broker in {self.reconnect_interval} seconds")
                time.sleep(self.reconnect_interval)
                
                try:
                    self.connect()
                except Exception as e:
                    logger.error(f"Reconnection failed: {str(e)}")
            
            time.sleep(1)
