from enum import Enum, unique


@unique
class GameStatus(Enum):
    """
    用于描述游戏状态的枚举类。
    """
    WAITING = 0
    INIT = 1
    DISCUSSING = 2
    VOTING = 3
    FINISHED = 4


@unique
class PlayerStatus(Enum):
    """
    用于描述玩家状态的枚举类。
    """
    GAMING = 0
    OUT = 1
