from .status import PlayerStatus
from .identity import Identity


class Player:
    def __init__(self, user_id):
        self.__user_id = user_id
        self.__status = PlayerStatus.GAMING
        self.__identity = Identity.CIVILIAN

    def get_user_id(self):
        return self.__user_id

    def get_status(self):
        return self.__status

    def get_identity(self):
        return self.__identity

    def set_status(self, status: PlayerStatus):
        self.__status = status

    def set_identity(self, identity: Identity):
        self.__identity = identity
