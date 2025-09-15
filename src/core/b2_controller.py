
# B2控制器实现（与宇树SDK交互的核心）
# 这个文件中有AI生成的幻觉，需要继续修改
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

# 导入宇树官方SDK
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.b2.sport.sport_client import SportClient
from src.config.config import config
from src.core.controller import Controller
from src.utils.logger import logger

class B2Controller(Controller):
    """宇树B2机器狗控制器实现"""
    
    def __init__(self):
        """初始化B2控制器"""
        self.sdk = None
        self.connected = False
        self.current_mode = None
        self.last_heartbeat = 0
        self.heartbeat_interval = 0.1  # 100ms心跳间隔
        
        # 线程安全锁
        self.lock = threading.Lock()
        
        # 支持的模式列表（见b2_control_thoughts\B2_control\B2_control_cmd.md）
        self.supported_modes = [
            "FreeWalk", "Damp", "ClassicWalk", "FastWalk", "VisionWalk"
        ]
        
        # 预定义动作列表（见b2_control_thoughts\B2_control\B2_control_cmd.md）
        self.supported_actions = [
            "StandDown", "stand_up", "HandStand", "ContinuousGait", 
            "Euler"
        ]
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
    
    def connect(self) -> bool:
        """连接到B2设备
        
        Returns:
            bool: 连接是否成功
        """
        with self.lock:
            if self.connected:
                logger.info("Already connected to B2")
                return True
                
            try:
                # 初始化连接机器狗
                ChannelFactoryInitialize(0,config.NETWORK_INTERFACE )
                connect_result = True
                # 连接到B2

                
                if connect_result:
                    self.connected = True
                    self.current_mode = "idle"
                    self.last_heartbeat = time.time()
                    logger.info("Successfully connected to B2")
                    return True
                else:
                    logger.error("Failed to connect to B2")
                    return False
                    
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                return False
    
    def disconnect(self) -> bool:
        """断开与B2的连接
        
        Returns:
            bool: 断开是否成功
        """
        with self.lock:
            if not self.connected:
                logger.info("Not connected to B2")
                return True
                
            try:
                # 停止所有动作
                self.stop()
                
                # 断开连接
                if self.sdk:
                    self.sdk.disconnect()
                
                self.connected = False
                self.current_mode = None
                logger.info("Disconnected from B2")
                return True
                
            except Exception as e:
                logger.error(f"Disconnection error: {str(e)}")
                return False
    
    def is_connected(self) -> bool:
        """检查是否已连接到B2
        
        Returns:
            bool: 是否已连接
        """
        return self.connected and (time.time() - self.last_heartbeat) < 2 * self.heartbeat_interval
    
    def get_status(self) -> Dict[str, Any]:
        """获取B2状态信息
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        if not self.is_connected():
            return {
                "connected": False,
                "status": "disconnected",
                "mode": "unknown",
                "battery": 0,
                "temperature": {},
                "timestamp": time.time()
            }
        
        try:
            with self.lock:
                # 获取B2状态
                b2_state = self.sdk.get_state()
                
                return {
                    "connected": True,
                    "status": "normal" if b2_state.system_state == 0 else "error",
                    "mode": self.current_mode,
                    "battery": self.get_battery_level(),
                    "temperature": self.get_temperature(),
                    "motor_count": len(b2_state.motor_states),
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}")
            return {
                "connected": True,
                "status": "error",
                "mode": self.current_mode,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """获取传感器数据
        
        Returns:
            Dict[str, Any]: 传感器数据
        """
        if not self.is_connected():
            return {
                "connected": False,
                "sensors": {},
                "timestamp": time.time()
            }
        
        try:
            with self.lock:
                # 获取B2状态
                b2_state = self.sdk.get_state()
                
                # 提取IMU数据
                imu_data = {
                    "accelerometer": {
                        "x": b2_state.imu.accelerometer[0],
                        "y": b2_state.imu.accelerometer[1],
                        "z": b2_state.imu.accelerometer[2]
                    },
                    "gyroscope": {
                        "x": b2_state.imu.gyroscope[0],
                        "y": b2_state.imu.gyroscope[1],
                        "z": b2_state.imu.gyroscope[2]
                    },
                    "quaternion": {
                        "w": b2_state.imu.quaternion[0],
                        "x": b2_state.imu.quaternion[1],
                        "y": b2_state.imu.quaternion[2],
                        "z": b2_state.imu.quaternion[3]
                    },
                    "euler": {
                        "roll": b2_state.imu.rpy[0],
                        "pitch": b2_state.imu.rpy[1],
                        "yaw": b2_state.imu.rpy[2]
                    }
                }
                
                # 提取电机数据
                motor_data = {}
                for i, motor in enumerate(b2_state.motor_states):
                    motor_data[f"motor_{i}"] = {
                        "angle": motor.angle,
                        "speed": motor.speed,
                        "torque": motor.torque,
                        "temperature": motor.temperature
                    }
                
                # 提取其他传感器数据
                sensor_data = {
                    "connected": True,
                    "imu": imu_data,
                    "motors": motor_data,
                    "battery": {
                        "voltage": b2_state.battery.voltage,
                        "current": b2_state.battery.current,
                        "level": self.get_battery_level()
                    },
                    "timestamp": time.time()
                }
                
                return sensor_data
                
        except Exception as e:
            logger.error(f"Failed to get sensor data: {str(e)}")
            return {
                "connected": True,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def move_forward(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向前移动
        
        Args:
            speed: 移动速度 (0.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in ["walk", "trot", "gallop"]:
                self.set_mode("walk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置前进速度
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.WALK
                control.velocity = [speed, 0, 0]  # x, y, yaw
                self.sdk.send_control(control)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move forward: {str(e)}")
            return False
    
    def move_backward(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向后移动
        
        Args:
            speed: 移动速度 (0.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in ["walk", "trot", "gallop"]:
                self.set_mode("walk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置后退速度
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.WALK
                control.velocity = [-speed, 0, 0]  # x, y, yaw
                self.sdk.send_control(control)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move backward: {str(e)}")
            return False
    
    def turn_left(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向左转
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in ["walk", "trot", "gallop"]:
                self.set_mode("walk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置左转速度
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.WALK
                control.velocity = [0, 0, speed]  # x, y, yaw
                self.sdk.send_control(control)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn left: {str(e)}")
            return False
    
    def turn_right(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向右转
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in ["walk", "trot", "gallop"]:
                self.set_mode("walk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置右转速度
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.WALK
                control.velocity = [0, 0, -speed]  # x, y, yaw
                self.sdk.send_control(control)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn right: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """停止移动
        
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.IDLE
                control.velocity = [0, 0, 0]  # 停止所有运动
                self.sdk.send_control(control)
            
            # 更新当前模式
            self.current_mode = "idle"
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop: {str(e)}")
            return False
    
    def set_velocity(self, x: float, y: float, yaw: float) -> bool:
        """设置速度
        
        Args:
            x: X轴速度 (-1.0-1.0)
            y: Y轴速度 (-1.0-1.0)
            yaw: 偏航角速度 (-1.0-1.0)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in ["walk", "trot", "gallop"]:
                self.set_mode("walk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置速度
            with self.lock:
                control = B2Control()
                control.mode = B2Mode.WALK
                control.velocity = [x, y, yaw]
                self.sdk.send_control(control)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set velocity: {str(e)}")
            return False
    
    def execute_action(self, action_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """执行预定义动作
        
        Args:
            action_name: 动作名称
            params: 动作参数
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        if action_name not in self.supported_actions:
            logger.error(f"Unsupported action: {action_name}")
            return False
            
        try:
            with self.lock:
                # 根据动作名称执行不同的动作
                if action_name == "sit":
                    self.sdk.execute_action(B2Action.SIT)
                elif action_name == "stand_up":
                    self.sdk.execute_action(B2Action.STAND_UP)
                elif action_name == "lie_down":
                    self.sdk.execute_action(B2Action.LIE_DOWN)
                elif action_name == "shake_head":
                    speed = params.get("speed", 1.0) if params else 1.0
                    duration = params.get("duration", 2.0) if params else 2.0
                    self.sdk.execute_custom_action("shake_head", speed, duration)
                elif action_name == "wave_leg":
                    leg = params.get("leg", "front_left") if params else "front_left"
                    self.sdk.execute_custom_action(f"wave_{leg}")
                elif action_name == "stretch":
                    self.sdk.execute_action(B2Action.STRETCH)
                elif action_name == "push_up":
                    count = params.get("count", 3) if params else 3
                    self.sdk.execute_custom_action("push_up", count)
                elif action_name in ["back_flip", "forward_flip"]:
                    # 确保电量充足
                    battery = self.get_battery_level()
                    if battery < 80:
                        logger.warning(f"Low battery for flip action: {battery}%")
                        return False
                    
                    if action_name == "back_flip":
                        self.sdk.execute_action(B2Action.BACK_FLIP)
                    else:
                        self.sdk.execute_action(B2Action.FORWARD_FLIP)
            
            # 动作执行需要时间，等待完成
            time.sleep(3.0)  # 给动作执行留出时间
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute action {action_name}: {str(e)}")
            return False
    
    def get_battery_level(self) -> float:
        """获取电池电量
        
        Returns:
            float: 电池电量百分比 (0.0-100.0)
        """
        if not self.is_connected():
            return 0.0
            
        try:
            with self.lock:
                b2_state = self.sdk.get_state()
                # 假设SDK返回的是电压值，需要转换为百分比
                voltage = b2_state.battery.voltage
                # 宇树B2电池电压范围通常在12.0V-16.8V之间
                if voltage <= 12.0:
                    return 0.0
                elif voltage >= 16.8:
                    return 100.0
                else:
                    return ((voltage - 12.0) / (16.8 - 12.0)) * 100.0
                    
        except Exception as e:
            logger.error(f"Failed to get battery level: {str(e)}")
            return 0.0
    
    def get_temperature(self) -> Dict[str, float]:
        """获取温度信息
        
        Returns:
            Dict[str, float]: 各部件温度信息
        """
        if not self.is_connected():
            return {}
            
        try:
            with self.lock:
                b2_state = self.sdk.get_state()
                
                # 获取电机平均温度
                motor_temps = [motor.temperature for motor in b2_state.motor_states]
                avg_motor_temp = sum(motor_temps) / len(motor_temps) if motor_temps else 0
                
                # 获取控制器温度
                controller_temp = b2_state.temperature.controller
                
                return {
                    "motor_average": avg_motor_temp,
                    "controller": controller_temp,
                    "imu": b2_state.temperature.imu,
                    "battery": b2_state.temperature.battery
                }
                
        except Exception as e:
            logger.error(f"Failed to get temperature: {str(e)}")
            return {}
    
    def set_mode(self, mode: str) -> bool:
        """设置设备模式
        
        Args:
            mode: 模式名称
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        if mode not in self.supported_modes:
            logger.error(f"Unsupported mode: {mode}")
            return False
            
        try:
            with self.lock:
                # 根据模式名称设置不同的模式
                if mode == "idle":
                    self.sdk.set_mode(B2Mode.IDLE)
                elif mode == "stand":
                    self.sdk.set_mode(B2Mode.STAND)
                elif mode == "walk":
                    self.sdk.set_mode(B2Mode.WALK)
                elif mode == "trot":
                    self.sdk.set_mode(B2Mode.TROT)
                elif mode == "gallop":
                    self.sdk.set_mode(B2Mode.GALLOP)
                elif mode == "climb_stairs":
                    self.sdk.set_mode(B2Mode.CLIMB_STAIRS)
                elif mode == "避障模式":
                    self.sdk.set_mode(B2Mode.OBSTACLE_AVOIDANCE)
                elif mode == "跟随模式":
                    self.sdk.set_mode(B2Mode.FOLLOW)
                elif mode == "导航模式":
                    self.sdk.set_mode(B2Mode.NAVIGATION)
            
            # 更新当前模式
            self.current_mode = mode
            
            # 等待模式切换完成
            time.sleep(1.0)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set mode {mode}: {str(e)}")
            return False
    
    def get_supported_modes(self) -> List[str]:
        """获取支持的模式列表
        
        Returns:
            List[str]: 支持的模式列表
        """
        return self.supported_modes
    
    def reset(self) -> bool:
        """重置设备
        
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            with self.lock:
                # 重置B2
                self.sdk.reset()
            
            # 等待重置完成
            time.sleep(5.0)
            
            # 重新连接
            self.disconnect()
            time.sleep(1.0)
            return self.connect()
            
        except Exception as e:
            logger.error(f"Failed to reset: {str(e)}")
            return False
    
    def _heartbeat_loop(self):
        """心跳循环，定期检查连接状态"""
        while True:
            if self.connected:
                try:
                    with self.lock:
                        # 发送心跳包（可以是一个空的控制命令）
                        control = B2Control()
                        control.mode = B2Mode.IDLE  # 保持空闲模式
                        control.velocity = [0, 0, 0]
                        self.sdk.send_control(control)
                        
                        # 更新心跳时间
                        self.last_heartbeat = time.time()
                        
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {str(e)}")
                    # 标记为断开连接
                    self.connected = False
            
            # 等待心跳间隔
            time.sleep(self.heartbeat_interval)
