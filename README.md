
# 宇树机器狗B2代码封装方案

## 目录结构

```
unitree_b2_cloud_sdk/
│
├── unitree_sdk2py/                 # 宇树官方SDK目录（保持不变）
│   ├── __init__.py
│   ├── b2_sdk.py                # 宇树B2官方SDK实现
│   └── ...                      # 其他SDK相关文件
│
├── src/                         # 自定义封装代码
│   ├── __init__.py
│   ├── main.py                  # 主程序入口
│   ├── config/                  # 配置文件
│   │   ├── __init__.py
│   │   ├── config.py            # 配置管理
│   │   └── mqtt_config.py       # MQTT配置
│   │
│   ├── core/                    # 核心功能模块
│   │   ├── __init__.py
│   │   ├── controller.py        # 控制器基类
│   │   ├── b2_controller.py     # B2控制器实现
│   │   ├── mqtt_client.py       # MQTT客户端
│   │   └── video_streamer.py    # 视频流处理
│   │
│   ├── services/                # 服务模块
│   │   ├── __init__.py
│   │   ├── base_service.py      # 服务基类
│   │   ├── motion_service.py    # 运动控制服务
│   │   ├── sensor_service.py    # 传感器服务
│   │   ├── navigation_service.py # 导航服务
│   │   ├── map_service.py       # 地图服务
│   │   └── system_service.py    # 系统服务
│   │
│   ├── utils/                   # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py            # 日志工具
│   │   ├── network.py           # 网络工具
│   │   └── data_converter.py    # 数据转换工具
│   │
│   └── web/                     # Web服务（可选）
│       ├── __init__.py
│       └── api_server.py        # HTTP API服务
│
├── examples/                    # 示例代码
│   ├── basic_control.py         # 基础控制示例
│   ├── mqtt_communication.py    # MQTT通信示例
│   └── video_streaming.py       # 视频流示例
│
├── tests/                       # 测试代码
│   ├── __init__.py
│   ├── test_controller.py       # 控制器测试
│   └── test_mqtt.py             # MQTT测试
│
├── requirements.txt             # 依赖库
└── README.md                    # 项目说明
```

## 与宇树SDK的关系说明

1. **依赖关系**：
   - 自定义封装代码完全依赖宇树官方SDK（unitree_sdk目录）
   - 通过组合而非继承的方式使用SDK功能，便于未来SDK版本升级

2. **功能映射**：
   - 运动控制：映射到宇树SDK的运动控制API
   - 传感器数据：映射到宇树SDK的传感器读取API
   - 系统管理：映射到宇树SDK的系统状态查询和设置API

3. **扩展功能**：
   - MQTT通信：新增功能，不依赖宇树SDK
   - 视频流处理：新增功能，使用FFmpeg实现
   - 导航和地图：在宇树SDK基础上实现的高级功能

4. **适配层**：
   - b2_controller.py作为适配层，将宇树SDK的API转换为统一的接口
   - 所有服务模块通过控制器间接使用宇树SDK，降低耦合度

# Installation
与宇树原始readme.md相同

# Attention
只是编写了一下框架，内容大多还有问题嗯。。。有些文件空，有些文件可能有幻觉。但是b2_controller.py基本是笔者过了一遍的