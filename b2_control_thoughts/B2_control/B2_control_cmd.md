# 概念说明
![alt text](image.png)

# 控制面板划分
## 步态模式
1. 灵动模式
2. 阻尼模式
3. 经典模式
4. 跑步模式
5. 视觉辅助模式
## 速度控制
1. 低速
2. 中速
3. 高速
## 移动控制
| 左转 | 前进 | 右转 |
| :--: | :--: | :--: |
|左移 | 恢复站立|右移|
|左后|右后|后退|


ps：这里相当于一个触屏控制的工具

## 动作指令
1. 踏步
2. 倒立
3. 摆姿势
### 特殊按键
1. 停止动作（急停）
2. 趴下
3. 站起

# 实现
所有的运动控制接口可以在
`unitree_sdk2_python\unitree_sdk2py\b2\sport`
文件夹内找到
以下为B2机器狗所有的动作指令
```python
"""
" api id
"""
ROBOT_SPORT_API_ID_DAMP              = 1001
ROBOT_SPORT_API_ID_BALANCESTAND      = 1002
ROBOT_SPORT_API_ID_STOPMOVE          = 1003
ROBOT_SPORT_API_ID_STANDUP           = 1004
ROBOT_SPORT_API_ID_STANDDOWN         = 1005
ROBOT_SPORT_API_ID_RECOVERYSTAND     = 1006
ROBOT_SPORT_API_ID_MOVE              = 1008
ROBOT_SPORT_API_ID_SWITCHGAIT        = 1011
ROBOT_SPORT_API_ID_BODYHEIGHT        = 1013
ROBOT_SPORT_API_ID_SPEEDLEVEL        = 1015
ROBOT_SPORT_API_ID_TRAJECTORYFOLLOW  = 1018
ROBOT_SPORT_API_ID_CONTINUOUSGAIT    = 1019
ROBOT_SPORT_API_ID_MOVETOPOS         = 1036
ROBOT_SPORT_API_ID_SWITCHMOVEMODE    = 1038
ROBOT_SPORT_API_ID_VISIONWALK        = 1101
ROBOT_SPORT_API_ID_HANDSTAND         = 1039
ROBOT_SPORT_API_ID_AUTORECOVERY_SET  = 1040
ROBOT_SPORT_API_ID_FREEWALK          = 1045
ROBOT_SPORT_API_ID_CLASSICWALK       = 1049
ROBOT_SPORT_API_ID_FASTWALK          = 1050
ROBOT_SPORT_API_ID_FREEEULER         = 1051
```
所有的动作实现均需要以下初始化
```python
    sport_client = SportClient()  
    sport_client.SetTimeout(10.0) #这里设置的超时时间可以更改
    sport_client.Init()
```
## 步态模式切换
### 灵动模式FreeWalk
![alt text](image-1.png)
代码应用
```python
    sport_client.FreeWalk()
```
### 阻尼模式Damp
![alt text](image-2.png)
代码应用
```python
    sport_client.Damp()
```
### 经典模式ClassicWalk
![alt text](image-3.png)
代码应用
```python
    sport_client.ClassicWalk(True)
```
### 跑步模式FastWalk
![alt text](image-4.png)
代码应用
```python
    sport_client.FastWalk(True)
```
### 视觉辅助模式VisionWalk
![alt text](image-5.png)
代码应用
```python
    sport_client.VisionWalk(True)
```

- **PS** ：宇树SDK中也提供了切换步态的函数
![alt text](image-6.png)
```python
    sport_client.SwitchGait(1)  # 0:锁定站立 1:盲走模式 2:持续踏步模式 3:视觉辅助行走模式 4:平面行走模式
```
但比较奇怪的是其枚举的步态：
- 锁定站立不知是否是指阻尼模式
- 盲走模式如果是不带任何传感器避障等的话，在演示场景中容易出问题
- 持续踏步模式可以直接调用函数实现
- 视觉辅助行走模式也可以直接调用函数实现
- 平面行走模式称对地面倾角有要求

**感觉每个模式都不太适合通过这个函数调用，当然如果另有其意在后续可再谈**
## 速度控制SpeedLevel
![alt text](image-7.png)
代码应用
- 低速
```python
    sport_client.SpeedLevel(-1)  # -1:低速 0:中速 1:高速
```
- 中速
```python
    sport_client.SpeedLevel(0)  # -1:低速 0:中速 1:高速
```
- 高速
```python
    sport_client.SpeedLevel(1)  # -1:低速 0:中速 1:高速
```

## 移动控制Move
![alt text](image-8.png)
这三个参数分别代表机器人的运动速度：

- vx：前后方向的线速度，单位为米/秒 (m/s)。

    - 正值表示向前运动，负值表示向后运动。
    - 取值范围：[-0.6, 0.6]
- vy：左右方向的线速度，单位为米/秒 (m/s)。

    - 正值表示向左平移，负值表示向右平移。
    - 取值范围：[-0.4, 0.4]
- vyaw：自转角速度，单位为弧度/秒 (rad/s)。

    - 正值表示逆时针旋转（左转），负值表示顺时针旋转（右转）。
    - 取值范围：[-0.8, 0.8]

**根据SDK提供的说明，这个函数应该在被调用之后会一直持续运动，因此需要实时监听控制板的方向按键是否被按下，如果被松开则需要调用停止运动的函数为止**
ps:这里的动作可以根据实际再修改，比如下方代码中的左转是指原地左转，如果场景需求为左前方斜走则需要将前进和左转的参数同时设置
- 左转
```python
    sport_client.Move(0.0, 0.0, 0.5)  # 左转
```
- 右转
```python
    sport_client.Move(0.0, 0.0, -0.5)  # 右转
```
- 前进
```python
    sport_client.Move(0.5, 0.0, 0.0)  # 前进
```
- 后退
```python
    sport_client.Move(-0.5, 0.0, 0.0)  # 后退
```
- 左移
```python
    sport_client.Move(0.0, 0.3, 0.0)  # 左移
```
- 右移
```python
    sport_client.Move(0.0, -0.3, 0.0)  # 右移
```

- 左后
```python
    sport_client.Move(-0.3, 0.3, 0.0)  # 左后
```
- 右后
```python
    sport_client.Move(-0.3, -0.3, 0.0)  # 右后
```
- 恢复站立（只在翻倒时有效）
```python
    sport_client.RecoveryStand()  # 恢复站立
```
**开启实时控制函数**
![alt text](image-14.png)
这个函数非常适合控制板上进行各种移动操作，但是官方建议谨慎开启，但在py版本的SDK中没有发现这个函数

## 动作指令
### 踏步ContinuousGait
![alt text](image-9.png)
代码应用
```python
    sport_client.ContinuousGait(True)  # True:开始踏步 False:停止踏步
```
### 倒立HandStand
![alt text](image-10.png)
代码应用
```python
    sport_client.HandStand(True)  # True:开始倒立 False:停止倒立
```
### 摆姿势Euler
![alt text](image-11.png)
这里有点问题，在py版本SDK中查看各种动作函数时，并没有发现这个函数
**只有**
```python
    def FreeEuler(self, flag: bool):
        p = {}
        p["data"] = flag
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_SPORT_API_ID_FREEEULER, parameter)
        return code
```
**但这个函数的功能并不清楚，网上也暂无解释**
代码应用
```python
    sport_client.FreeEuler(True)  # True:开始摆姿势 False:停止摆姿势
```
## 特殊按键
### 停止动作StopMove
**这里的初步想法是直接调用[Damp](###阻尼模式Damp)函数来实现急停**，因为该模式具有最高的优先级，用于突发情况下的急停
或者也有`StopMove()`
![alt text](image-12.png)
具体用哪个，得看实际效果
代码应用
```python
    sport_client.Damp()
    # or
    sport_client.StopMove()  # 急停
```

### 趴下StandDown
![alt text](image-13.png)
代码应用
```python
    sport_client.StandDown()  # 趴下
```
### 站起StandUp
这个函数SDK文档未提及，但笔者在原码仓库中发现
```python
    def StandUp(self):
        p = {}
        parameter = json.dumps(p)
        code, data = self._Call(ROBOT_SPORT_API_ID_STANDUP, parameter)
        return code
```
代码应用
```python
    sport_client.StandUp()  # 站起
```