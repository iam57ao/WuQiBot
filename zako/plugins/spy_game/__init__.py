import datetime
import json
from typing import Optional
from nonebot import on_request
from nonebot import CommandGroup
from nonebot.typing import T_State
from nonebot.permission import USER
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.internal.permission import Permission
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent, FriendRequestEvent

from .game import Game
from .status import GameStatus, PlayerStatus
from .identity import Identity

games: dict[int, Optional[Game]] = {}

spy_cmd = CommandGroup("卧底游戏", priority=10)
create_cmd = spy_cmd.command("创建")
delete_cmd = spy_cmd.command("删除")
join_cmd = spy_cmd.command("加入")
leave_cmd = spy_cmd.command("退出")
ban_cmd = spy_cmd.command("踢人")
change_global_word_cmd = spy_cmd.command("更改词库")
start_cmd = spy_cmd.command("开始")
notice_event = on_request()


# 通过好友请求
@notice_event.handle()
async def _(bot: Bot, event: FriendRequestEvent):
    await bot.set_friend_add_request(flag=event.flag, approve=True)


@create_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    group_id = event.group_id

    if games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏已经存在！")
        await create_cmd.finish()

    new_game = Game(user_id)
    message = "未知错误！"
    match await new_game.add_player(user_id):
        case 0:
            games[group_id] = new_game
            message = "游戏创建成功！请输入 /卧底游戏 加入 加入游戏！"
        case 4:
            message = "创建失败！请先添加机器人好友！"

    await bot.send_group_msg(group_id=group_id, message=message)


@delete_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    group_id = event.group_id

    if not games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏不存在！")
        await delete_cmd.finish()

    this_game = games[group_id]
    if this_game.get_host_user_id() != user_id and event.sender.role == "member":
        await bot.send_group_msg(group_id=group_id, message="非房主/管理员无法删除游戏！")
    else:
        del this_game
        games[group_id] = None
        await bot.send_group_msg(group_id=group_id, message="删除游戏成功！")


@join_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    group_id = event.group_id

    if not games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏不存在！请先创建游戏！")
        await join_cmd.finish()

    this_game = games[group_id]
    message = "未知错误！"
    match await this_game.add_player(user_id):
        case 0:
            message = "您已加入游戏！\n" \
                      f"人数: {this_game.get_player_total()}/{this_game.get_max_players()}\n" \
                      f"已加入玩家QQ号:\n"
            players_str = [f"-{player.get_user_id()}" for player in this_game.get_joined_players()]
            message += "\n".join(players_str)
        case 1:
            message = "加入失败！游戏已经开始！"
        case 2:
            message = "加入失败！房间人数已满！"
        case 3:
            message = "加入失败！您已被封禁！"
        case 4:
            message = "加入失败！请先添加机器人好友！"
        case 5:
            message = "加入失败！您已经在房间中了！"

    await bot.send_group_msg(group_id=group_id, message=message)


@leave_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    group_id = event.group_id

    if not games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏不存在！")
        await leave_cmd.finish()

    this_game = games[group_id]
    message = "未知错误！"
    match this_game.delete_player(user_id):
        case 0:
            message = "您已退出游戏！\n" \
                      f"人数: {this_game.get_player_total()}/{this_game.get_max_players()}\n" \
                      f"已加入玩家QQ号:\n"
            players_str = [f"-{player.get_user_id()}" for player in this_game.get_joined_players()]
            message += "\n".join(players_str)
        case 1:
            message = "无法退出！游戏已经开始！"
        case 2:
            message = "您是房主，只能删除游戏！"
        case 3:
            message = "无法退出！您未加入游戏！"

    await bot.send_group_msg(group_id=group_id, message=message)


@change_global_word_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id

    # 判断是否为管理员
    if event.sender.role == "member":
        await bot.send_group_msg(group_id=group_id, message="您不是管理员，无法更改词库！")
        await change_global_word_cmd.finish()

    words = Game.get_words().keys()
    message = "请输入要更改的词库\n" + "\n".join(words)
    await bot.send_group_msg(group_id=group_id, message=message)


@change_global_word_cmd.receive()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    new_words = event.raw_message

    message = "未知错误!"
    match Game.change_global_word(new_words):
        case 1:
            message = "不存在该词库！"
        case 0:
            message = f"已更改词库为{new_words}"

    await bot.send_group_msg(group_id=group_id, message=message)


@ban_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    user_id = event.user_id
    group_id = event.group_id

    if not games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏不存在！")
        await ban_cmd.finish()

    this_game = games[group_id]
    ban_user_id = args[0].data.get("qq", None)
    message = "未知错误！"
    match this_game.ban_player(user_id, ban_user_id):
        case 0 | 3:
            message = f"已将{ban_user_id}加入黑名单！"
        case 1:
            message = f"游戏已经开始，无法将{ban_user_id}加入黑名单！"
        case 2:
            message = f"不能将自己加入黑名单！"
        case 4:
            message = f"您不是房主，不能使用该指令！"
        case 5:
            message = f"参数不合法，参数为@用户"

    await bot.send_group_msg(group_id=group_id, message=message)


@start_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    group_id = event.group_id

    if not games.get(group_id):
        await bot.send_group_msg(group_id=group_id, message="游戏不存在！")
        await start_cmd.finish()

    this_game = games[group_id]
    message = "未知错误，开始失败！"
    match this_game.start(user_id):
        case 0:
            message = "游戏开始！词汇已经发放，接下来是自由讨论时间。房主回复: “结束讨论”进行投票！"
            await bot.send_group_msg(group_id=group_id, message=message)
            civilian_word = this_game.get_word()["平民"]
            spy_word = this_game.get_word()["卧底"]
            for player in this_game.get_joined_players():
                if player.get_identity() == Identity.SPY:
                    await bot.send_private_msg(user_id=player.get_user_id(), message=f"你的词汇: {spy_word}")
                else:
                    await bot.send_private_msg(user_id=player.get_user_id(), message=f"你的词汇: {civilian_word}")
            state["this_game"] = this_game
            state["group_id"] = group_id

            await start_cmd.skip()
        case 1:
            message = "您不是房主，无法开启游戏！"
        case 2:
            message = "游戏已经开始！"
        case 3:
            message = "人数不足3人，无法开始！"

    await bot.send_group_msg(group_id=group_id, message=message)
    await start_cmd.finish()


@start_cmd.permission_updater
async def _(matcher: Matcher, state: T_State) -> Permission:
    group_id = state["group_id"]
    this_game: Game = state["this_game"]
    ids = []
    for user in this_game.get_alive_players():
        user_id = user.get_user_id()
        ids.extend([f"group_{group_id}_{user_id}", f"{user_id}"])
    return USER(*ids, perm=matcher.permission)


@start_cmd.receive()
async def _(bot: Bot,
            event: GroupMessageEvent | PrivateMessageEvent,
            state: T_State):
    user_id = event.user_id
    group_id = state["group_id"]
    this_game: Game = state["this_game"]

    # 如果游戏被中途删除，则结束游戏
    if not this_game:
        await start_cmd.finish()

    # 游戏中删除游戏
    if this_game.get_host_user_id() == user_id and event.raw_message == "结束游戏":
        games[group_id] = None
        await bot.send_group_msg(group_id=group_id, message="游戏已结束！")
        await start_cmd.finish()

    # 群事件响应
    if event.message_type == "group":
        match this_game.get_status():
            case GameStatus.VOTING:
                await start_cmd.reject()
            case GameStatus.DISCUSSING:
                raw_message = event.raw_message

                # 是房主并且发送结束讨论，进入投票环节
                if this_game.get_host_user_id() == user_id and raw_message == "结束讨论":
                    vote = {
                        "alive_players_total": len(this_game.get_alive_players()),
                        "vote_count": 0,
                        "users": {},
                        "votes": {}
                    }
                    state["vote"] = vote
                    message = "投票环节开始！请私聊投票对应编号！\n"
                    for index, player in enumerate(this_game.get_joined_players()):
                        if player.get_status() == PlayerStatus.GAMING:
                            message += f"-{index}->" + MessageSegment.at(player.get_user_id()) + "\n"
                            vote["users"][player.get_user_id()] = False
                            vote["votes"][index] = 0

                    this_game.set_game_status(GameStatus.VOTING)
                    await bot.send_group_msg(group_id=group_id, message=message)
                    await start_cmd.reject()

                # 检测语句是否包含自己的词汇
                player = this_game.get_player(user_id)
                word = this_game.get_word()[
                    "卧底" if player.get_identity() == Identity.SPY else "平民"]

                # 如果句中包含自己的词汇，游戏直接结束
                if any(char in raw_message for char in word):
                    await bot.send_group_msg(group_id=group_id, message=MessageSegment.at(user_id) + "触发词汇！")
                    state["触发词汇"] = {"user_id": user_id, "identity": player.get_identity()}
                    this_game.set_game_status(GameStatus.FINISHED)
                    await start_cmd.skip()

                await start_cmd.reject()
            case GameStatus.FINISHED:
                await start_cmd.skip()
    else:
        # 私聊事件响应
        match this_game.get_status():
            case GameStatus.VOTING:
                # 判断投票是否合法
                raw_message = event.raw_message
                if not raw_message.isdigit():
                    await bot.send_private_msg(user_id=user_id, message="投票数据不合法，请重新投票！")
                    await start_cmd.reject()

                vote = state["vote"]

                # 判断是否投过票
                if vote["users"][user_id]:
                    await bot.send_private_msg(user_id=user_id, message="您已经投过票了！")
                    await start_cmd.reject()

                # 判断投票的目标是否存在
                vote_index = int(raw_message)
                if vote_index not in vote["votes"].keys():
                    await bot.send_private_msg(user_id=user_id, message="请投票给存活的玩家！")
                    await start_cmd.reject()

                # 判断是否给自己投票
                if user_id == this_game.get_player_with_index(vote_index).get_user_id():
                    await bot.send_private_msg(user_id=user_id, message="不能给自己投票！")
                    await start_cmd.reject()

                # 投票成功
                vote["vote_count"] += 1
                vote["users"][user_id] = True
                vote["votes"][vote_index] += 1
                await bot.send_private_msg(user_id=user_id, message="投票成功！")

                # 判断是否所有人都已经投票
                if vote["vote_count"] != vote["alive_players_total"]:
                    await start_cmd.reject()

                # 获取将要出局玩家在已加入玩家中的索引
                votes = vote["votes"].items()
                max_vote = max(votes, key=lambda x: x[1])
                same_players = [v for v in votes if v[1] == max_vote[1]]

                group_id = state["group_id"]

                # 判断是否平票
                if len(same_players) > 1:
                    this_game.set_game_status(GameStatus.DISCUSSING)
                    await bot.send_group_msg(group_id=group_id,
                                             message="出现平票！本轮没有用户出局！进入自由讨论时间！房主回复: “结束讨论”进行投票！")
                    await start_cmd.reject()

                index = max_vote[0]
                this_game.set_out(index)
                user_id = this_game.get_player_with_index(index).get_user_id()
                message = "投票结束！本轮出局用户: " + MessageSegment.at(user_id)

                # 公布淘汰消息
                await bot.send_group_msg(group_id=group_id, message=message)

                # 判断游戏是否结束
                if this_game.is_finished():
                    this_game.set_game_status(GameStatus.FINISHED)
                    await start_cmd.skip()

                # 开始自由讨论状态
                this_game.set_game_status(GameStatus.DISCUSSING)
                await bot.send_group_msg(group_id=group_id, message="自由讨论时间开始！房主回复: “结束讨论”进行投票！")
                await start_cmd.reject()

                await start_cmd.reject()
            case GameStatus.DISCUSSING:
                await start_cmd.reject()
            case GameStatus.FINISHED:
                await start_cmd.skip()


@start_cmd.handle()
async def _(bot: Bot, state: T_State):
    this_game: Game = state["this_game"]
    word = this_game.get_word()
    group_id = state["group_id"]

    # 判断是否因触发词汇导致游戏结束
    if state.get("触发词汇"):
        winner_message = f"胜利方: {'卧底' if state['触发词汇']['identity'] == Identity.CIVILIAN else '平民'}\n"
    else:
        winner_message = f"胜利方: {this_game.get_winner()}\n"

    # 拼接消息
    word_message = f"词汇:\n-平民: {word['平民']}\n-卧底: {word['卧底']}\n"
    spy_message = "卧底: "
    civilian_message = "平民: "
    for player in this_game.get_joined_players():
        if player.get_identity() == Identity.SPY:
            spy_message += MessageSegment.at(player.get_user_id())
        else:
            civilian_message += MessageSegment.at(player.get_user_id())
    message = "游戏结束！\n" + winner_message + word_message + spy_message + "\n" + civilian_message

    # 发送结束消息
    await bot.send_group_msg(group_id=group_id, message=message)

    games[group_id] = None
