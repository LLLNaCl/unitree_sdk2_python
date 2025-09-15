# 一些想法
控制台对机器狗的交互，无非是下发指令，接收上报状态
总的话题结构应该由`dog/001/……`开始,表示第一条狗
- 假设目前要完成控制功能的话题结构设计，笔者想到两种方案
    1. 设立一个总话题`dog/001/cmd`
    - 当中通过MQTT消息队列传输各种如`balanced_walk`这种消息
    - 实现**初始时一个订阅**，在接收该订阅消息之后判断是`balanced_walk`或者是`damp`等其他命令
    2. 在总话题下分设
    - 有各种`dog/001/cmd/balanced_walk`、`dog/001/cmd/damp`……
    - 实现**初始时多个订阅**，接收到对应话题的`bool`类型时再做出动作

笔者认为第一种比较合适，当然无论哪种，都需要对整个机器狗的所有交互做出统一的梳理。
# 话题的尝试整理
- dog/001/cmd
    - dog/001/cmd/remote_movement
    - dog/001/cmd/switch_spped
    - dog/001/cmd/switch_walk_mode
    ……还有很多诸如巡检启动等……
- dog/001/resp
    - dog/001/resp/photo
    - dog/001/resp/video
    - dog/001/resp/status
        - dog/001/resp/status/imu
        - dog/001/resp/status/battry