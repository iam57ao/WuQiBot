import json
from typing import Optional
from random import sample, choice, randint
from nonebot import get_bot
from .player import Player
from .status import GameStatus, PlayerStatus
from .identity import Identity


class Game:
    __word_category = "默认"

    def __init__(self, host_user_id: int):
        self.__status: GameStatus = GameStatus.WAITING
        self.__spy_players = 1
        self.__min_players = 3
        self.__max_players = 10
        self.__host_user_id = host_user_id
        self.__ban_list = []
        self.__player_list = []
        self.__civilian_list = []
        self.__spy_list = []
        self.__word = {"平民": None, "卧底": None}

    @classmethod
    def change_global_word(cls, word):
        words = Game.get_words()
        words = words.keys()

        if word not in words:
            return 1

        cls.__word_category = word
        return 0

    @staticmethod
    def get_words() -> dict:
        with open("data/words.json", "r", encoding="utf-8") as file:
            words = json.load(file)
        return words

    def get_host_user_id(self):
        return self.__host_user_id

    def get_alive_players(self) -> list[Player]:
        return self.__civilian_list + self.__spy_list

    def get_player_total(self):
        return len(self.__player_list)

    def get_joined_players(self) -> list[Player]:
        return self.__player_list

    def get_max_players(self):
        return self.__max_players

    def get_player(self, user_id) -> Optional[Player]:
        for player in self.__player_list:
            if player.get_user_id() == user_id:
                return player
        else:
            return None

    def get_winner(self):
        if not self.__spy_list:
            return "平民"
        elif len(self.get_alive_players()) <= 2:
            return "间谍"

    def get_player_with_index(self, index) -> Player:
        return self.__player_list[index]

    def get_status(self):
        return self.__status

    def get_word(self):
        return self.__word

    def is_finished(self):
        if not self.__spy_list:
            return True
        if len(self.get_alive_players()) <= 2:
            return True

        return False

    def __is_full(self):
        return len(self.__player_list) >= self.__max_players

    def __set_spy_players(self):
        self.__spy_list = sample(self.__player_list, self.__spy_players)
        for player in self.__spy_list:
            player.set_identity(Identity.SPY)
        self.__civilian_list = list(set(self.__player_list) - set(self.__spy_list))

    def __set_word(self):
        with open("data/words.json", "r", encoding="utf-8") as file:
            words: dict = json.load(file)
        category_words = words.get(self.__word_category)
        word: list = choice(category_words)
        self.__word["平民"] = word.pop(randint(0, 1))
        self.__word["卧底"] = word.pop()

    def change_word(self):
        ...

    def set_game_status(self, status: GameStatus):
        self.__status = status

    def set_max_players(self, user_id, max_players):
        # 如果游戏已经开始，返回1
        if self.__status != GameStatus.WAITING:
            return 1

        # 如果用户不是房主，返回2
        if self.__host_user_id != user_id:
            return 2

        # 如果数值有误，返回3
        if self.__min_players > max_players:
            return 3

        # 成功返回0
        self.__max_players = max_players
        return 0

    def set_out(self, index):
        player = self.__player_list[index]
        player.set_status(PlayerStatus.OUT)
        if player in self.__spy_list:
            self.__spy_list.remove(player)
        else:
            self.__civilian_list.remove(player)

    async def add_player(self, user_id):
        # 判断游戏是否已经开始
        if self.__status != GameStatus.WAITING:
            return 1
        # 判断是否满人
        if self.__is_full():
            return 2
        # 判断玩家是否被踢
        for player in self.__ban_list:
            if player == user_id:
                return 3
        # 判断是否有机器人好友
        bot = get_bot()
        friends = await bot.get_friend_list()
        for friend in friends:
            if friend["user_id"] == user_id:
                break
        else:
            return 4
        # 判断玩家是否加入
        for player in self.__player_list:
            if player.get_user_id() == user_id:
                return 5

        self.__player_list.append(Player(user_id))
        return 0

    def delete_player(self, user_id):
        # 判断游戏是否已经开始
        if self.__status != GameStatus.WAITING:
            return 1
        # 判断是否为房主
        if user_id == self.__host_user_id:
            return 2
        # 判断玩家是否加入
        for player in self.__player_list:
            if player.get_user_id() == user_id:
                self.__player_list.remove(player)
                return 0
        return 3

    def ban_player(self, user_id, ban_user_id):
        # 判断执行指令的用户是否为房主
        if self.__host_user_id != user_id:
            return 4
        # 判断数据是否合法
        if ban_user_id is None or not ban_user_id.isdigit():
            return 5
        self.__ban_list.append(int(ban_user_id))
        return self.delete_player(ban_user_id)

    def start(self, user_id):
        # 判断是否为房主
        if user_id != self.__host_user_id:
            return 1

        # 判断游戏是否已经开始
        if self.__status != GameStatus.WAITING:
            return 2

        # 判断人数是否足够
        if self.get_player_total() < self.__min_players:
            return 3

        self.__status = GameStatus.DISCUSSING
        self.__set_spy_players()
        self.__set_word()

        return 0
