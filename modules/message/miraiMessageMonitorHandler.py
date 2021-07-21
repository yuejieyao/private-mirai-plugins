from typing import List
import threading
from modules.message.messageChain import MessageChain


class MiraiMessageMonitor:
    def __init__(self, type: str,  target: int, group: int = None, filter=None, call=None) -> None:
        """一次性监听,用于等待对方回复的情况,通过传入自定义的filter来判断是否触发传入的call函数
        type (str): message类型(FriendMessage,GroupMessage)
        group (int): 群号,可以为空
        target (int): 监听对象QQ
        filter (function): 消息过滤函数
        call: (function) 监听触发的函数
        """
        self.type = type
        self.group = group
        self.target = target
        self.filter = filter
        self.call = call


class MiraiMessageMonitorHandler:

    _instance_lock = threading.Lock()
    monitors: List[MiraiMessageMonitor] = []

    def __new__(cls) -> 'MiraiMessageMonitorHandler':
        if not hasattr(MiraiMessageMonitorHandler, "_instance"):
            with MiraiMessageMonitorHandler._instance_lock:
                if not hasattr(MiraiMessageMonitorHandler, "_instance"):
                    MiraiMessageMonitorHandler._instance = object.__new__(cls)
        return MiraiMessageMonitorHandler._instance

    def __init__(self) -> None:
        pass

    def add(self, monitor: MiraiMessageMonitor):
        self.monitors.append(monitor)

    def remove(self, monitor: MiraiMessageMonitor):
        self.monitors.remove(monitor)

    def process(self, type: str, msg: MessageChain, target: int, group: int = None) -> bool:
        """遍历当前的监听列表,满足目标条件时调用监听的filter,满足后调用回调函数,后删除该监听
        Param:
            type (str): message类型(FriendMessage,GroupMessage)
            target (int): 监听目标的QQ号
            msg (MessageChain): 消息链
        Returns:
            bool: 如有监听成功执行则返回true,若遍历结束没有符合条件的监听则返回false
        """

        for monitor in self.monitors:
            if monitor.type == type:
                if monitor.target == target:
                    if group:
                        if monitor.filter(msg, target, group):
                            monitor.call(msg, target, group)
                            self.monitors.remove(monitor)
                            return True
                    else:
                        if monitor.filter(msg, target):
                            monitor.call(msg, target)
                            self.monitors.remove(monitor)
                            return True
        return False
