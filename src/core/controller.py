
# 控制器基类

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class Controller(ABC):
    """控制器基类，定义所有控制器必须实现的接口"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到设备
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开与设备的连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查设备是否已连接
        
        Returns:
            bool: 是否已连接
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态信息
        """
        pass
    
    @abstractmethod
    def get_sensor_data(self) -> Dict[str, Any]:
        """获取传感器数据
        
        Returns:
            Dict[str, Any]: 传感器数据
        """
        pass
    
    @abstractmethod
    def move_forward(self, speed: float = 0, duration: float = 1.0) -> bool:
        """向前移动
        
        Args:
            speed: 移动速度 (-1.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def move_backward(self, speed: float = 0, duration: float = 1.0) -> bool:
        """向后移动
        
        Args:
            speed: 移动速度 (0.0-1.0)
            duration: 移动持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def turn_left(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向左转
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def turn_right(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """向右转
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass

    @abstractmethod
    def move_left(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """左移
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def move_right(self, speed: float = 0.5, duration: float = 1.0) -> bool:
        """右移
        
        Args:
            speed: 旋转速度 (0.0-1.0)
            duration: 旋转持续时间(秒)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """停止移动
        
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def set_velocity(self, x: float, y: float, yaw: float) -> bool:
        """设置速度
        
        Args:
            x: X轴速度 (-1.0-1.0)
            y: Y轴速度 (-1.0-1.0)
            yaw: 偏航角速度 (-1.0-1.0)
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def execute_action(self, action_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """执行预定义动作
        
        Args:
            action_name: 动作名称
            params: 动作参数
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def get_battery_level(self) -> float:
        """获取电池电量
        
        Returns:
            float: 电池电量百分比 (0.0-100.0)
        """
        pass
    
    @abstractmethod
    def get_temperature(self) -> Dict[str, float]:
        """获取温度信息
        
        Returns:
            Dict[str, float]: 各部件温度信息
        """
        pass
    
    @abstractmethod
    def set_mode(self, mode: str) -> bool:
        """设置设备模式
        
        Args:
            mode: 模式名称
            
        Returns:
            bool: 命令是否执行成功
        """
        pass
    
    @abstractmethod
    def get_supported_modes(self) -> List[str]:
        """获取支持的模式列表
        
        Returns:
            List[str]: 支持的模式列表
        """
        pass
    
    @abstractmethod
    def reset(self) -> bool:
        """重置设备
        
        Returns:
            bool: 命令是否执行成功
        """
        pass
