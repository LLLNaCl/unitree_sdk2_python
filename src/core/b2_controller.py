
# B2控制器实现（与宇树SDK交互的核心）
'''
实习生写python的工程代码经验有限，代码框架是AI写的，原始有很多的幻觉部分。
希望能有所用处（大概率可能看到后面的你可能不会这样写？）
一些自定义的DDS类内变量不知是否能用'.'调用，本人之前写C++会多一点，可能python这样写有点问题？

'''

import time
import threading
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

# 导入宇树官方SDK
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.b2.sport.sport_client import SportClient
from unitree_sdk2py.b2.robot_state.robot_state_client import RobotStateClient
from src.config.config import config
from src.core.controller import Controller
from src.utils.logger import logger
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_


class B2Controller(Controller):
    """宇树B2机器狗控制器实现"""
    
    def __init__(self):
        """初始化B2控制器"""
        self.sport_client = None
        self.state_client = None
        self.connected = False
        self.current_mode = None
        self.last_heartbeat = 0
        self.heartbeat_interval = 0.1  # 100ms心跳间隔

        # B2的一些信心变量
        self._LowState = None
        
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
                    self.sport_client = SportClient()
                    self.sport_client.SetTimeout(10.0)
                    self.sport_client.Init()
                    self.state_client = RobotStateClient()
                    self.state_client.Init()
                    self.connected = True
                    self.current_mode = "Damp"
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

                # 这里具体的断连方式要后人的研究了，目前sdk里暂未发觉可以直接断连的接口
                self.sport_client = None
                self.state_client = None
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
                # 这里nacl在未拿到狗本体，未测试在state_client接口下的ServiceSwitch开启对应的服务后的结果是什么，
                # 查看原码和官方的sdk描述也为发现具体的返回内容，因此笔者将自行从底层的rt/lowstate来获取数据，
                # 在sdk中也有底层数据读取的例程unitree_sdk2py\test\lowlevel
                def LowStateHandler(msg: LowState_):
                    self._LowState = msg
                sub = ChannelSubscriber("rt/lowstate", LowState_)
                sub.Init(LowStateHandler,10)

                return {
                    "connected": True,
                    "status": "normal", #这里不正常还需要用故障码，有点复杂，留给后人
                    "mode": self.current_mode,
                    "battery": self.get_battery_level(),
                    "temperature": self.get_temperature(),
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
                def LowStateHandler(msg: LowState_):
                    self._LowState = msg
                sub = ChannelSubscriber("rt/lowstate", LowState_)
                sub.Init(LowStateHandler,10)
                
                # 提取IMU数据
                imu_data = {
                    "accelerometer": {
                        "x": self._LowState.imu_state.accelerometer[0],
                        "y": self._LowState.imu.accelerometer[1],
                        "z": self._LowState.imu.accelerometer[2]
                    },
                    "gyroscope": {
                        "x": self._LowState.imu.gyroscope[0],
                        "y": self._LowState.imu.gyroscope[1],
                        "z": self._LowState.imu.gyroscope[2]
                    },
                    "quaternion": {
                        "w": self._LowState.imu.quaternion[0],
                        "x": self._LowState.imu.quaternion[1],
                        "y": self._LowState.imu.quaternion[2],
                        "z": self._LowState.imu.quaternion[3]
                    },
                    "euler": {
                        "roll": self._LowState.imu.rpy[0],
                        "pitch": self._LowState.imu.rpy[1],
                        "yaw": self._LowState.imu.rpy[2]
                    }
                }
                
                # 提取电机数据
                motor_data = {}
                for i, motor in enumerate(self._LowState.motor_state):
                    motor_data[f"motor_{i}"] = {
                        "angle": motor.q,# 关机反馈位置信息：默认为弧度值（可按照实际情况改为角度值），可按照实际数值显示（弧度值范围：-7 - +7，显示3位小数）
                        "speed": motor.dq,# 关节反馈速度
                        "torque": motor.tau_est, # 关节力矩
                        "temperature": motor.temperature # 电机温度
                    }
                
                # 提取其他传感器数据
                sensor_data = {
                    "connected": True,
                    "imu": imu_data,
                    "motors": motor_data,
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
    
    def move_forward(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向前移动
        
        Args:
            speed: 移动速度 (-1.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置前进速度
            with self.lock:
                self.sport_client.Move(0.5, 0.0, 0.0)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move forward: {str(e)}")
            return False
    
    def move_backward(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向后移动
        
        Args:
            speed: 移动速度 (-1.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置后退速度
            with self.lock:
                self.sport_client.Move(-0.5, 0.0, 0.0)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move backward: {str(e)}")
            return False
    
    def turn_left(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向左转
        
        Args:
            speed: 旋转速度 (-1.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置左转速度
            with self.lock:
                self.sport_client.Move(0.0, 0.0, 0.5)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn left: {str(e)}")
            return False
    
    def turn_right(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向右转
        
        Args:
            speed: 旋转速度 (-1.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置右转速度
            with self.lock:
                self.sport_client.Move(0.0, 0.0, -0.5)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn right: {str(e)}")
            return False
        
    def left_move(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向左平移
        
        Args:
            speed: 移动速度 (-1.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置左移速度
            with self.lock:
                self.sport_client.Move(0.0, 0.3, 0.0)
            
            # 保持指定时间
            time.sleep(duration)
            
            # 停止
            self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move left: {str(e)}")
            return False
    
    def right_move(self, speed: float = 0.5, duration: float = 0.5) -> bool:
        """向右平移
        
        Args:
            speed: 移动速度 (-1.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            if self.current_mode not in self.supported_modes:
                self.set_mode("FreeWalk")
                time.sleep(0.5)  # 等待模式切换完成
            
            # 设置右移速度
            with self.lock:
                self.sport_client.Move(0.0, -0.3, 0.0)
            
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
                self.sport_client.Damp()
            
            # 更新当前模式
            self.current_mode = "Damp"
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop: {str(e)}")
            return False
    
    def set_velocity(self, level: int) -> bool:
        """设置速度
        
        Args:
            level: 速度 (-1:低速 0:中速 1:高速)
            
        Returns:
            bool: 命令是否执行成功
        """
        if not self.is_connected():
            logger.error("Not connected to B2")
            return False
            
        try:
            # 确保在行走模式
            
            # 设置速度
            with self.lock:
                self.sport_client.SpeedLevel(level)
            
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
                # StandDown
                if action_name == self.supported_actions[0]: 
                    self.sport_client.StandDown()
                
                # stand_up
                elif action_name == "stand_up":
                    self.sport_client.StandUp()
                
                # HandStand
                elif action_name == "HandStand":
                    self.sport_client.HandStand()
                
                # ContinuousGait
                elif action_name == "ContinuousGait":
                    self.sport_client.ContinuousGait()
                # Euler
                elif action_name == "Euler":
                    self.sport_client.FreeEuler()
                #后期可供扩展的动作
                '''
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
                '''
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

               
                return self._LowState.bms_state.soc # 这里我认为C++是这样写的，python这里不知道为何关联不到。。
                
                    
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
                
                
                # 获取电机平均温度
                motor_temps = [motor.temperature for motor in self._LowState.motor_state]
                avg_motor_temp = sum(motor_temps) / len(motor_temps) if motor_temps else 0
                
                # 获取控制器温度
                controller_temp = self._LowState.temperature_ntc1
                
                return {
                    "motor_average": avg_motor_temp,
                    "controller": controller_temp,
                    "imu": self._LowState.imu_state.temperature,
                    "battery": sum(self._LowState.bms_state.bq_ntc)/2
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
                if mode == "Damp":
                    self.sport_client.Damp()
                elif mode == "FreeWalk":
                    self.sport_client.FreeWalk()
                elif mode == "ClassicWalk":
                    self.sport_client.ClassicWalk()
                elif mode == "FastWalk":
                    self.sport_client.FastWalk()
                elif mode == "VisionWalk":
                    self.sport_client.VisionWalk()

            
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
                self.sport_client.StopMove()
            
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
                        
                        
                        # 更新心跳时间
                        self.last_heartbeat = time.time()
                        
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {str(e)}")
                    # 标记为断开连接
                    self.connected = False
            
            # 等待心跳间隔
            time.sleep(self.heartbeat_interval)
