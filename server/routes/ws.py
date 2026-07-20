"""
WebSocket 事件处理。

客户端事件：join_room, reconnect_session, start_game,
            play_cards, pass_turn,
            respond_cha, respond_dian,
            tribute_select, tribute_swap_respond, tribute_confirm,
            tribute_return_submit,
            respond_ligun
"""
import threading
from flask_socketio import emit, join_room as sio_join, leave_room as sio_leave
from flask import request
from .. import socketio
from ..store import rooms, sessions, player_room, register_session, remove_session
from ..models.player import Player
from ..models.room import Room
from ..models.game import GameState
from ..models.tribute import TributeState, TributeSelectionState, determine_tribute, validate_return_card
from ..models.ligun import LigunState
import uuid

# 倒计时时长（秒）
LIGUN_TIMEOUT = 15      # 每个玩家回答立棍的时间
TRIBUTE_TIMEOUT = 30    # 赢家确认进贡牌的时间
TRIBUTE_BACK_TIMEOUT = 30  # 赢家提交还贡的时间


# ------------------------------------------------------------------
# 广播工具
# ------------------------------------------------------------------

def _broadcast_game_state(room: Room):
    for p in room.players:
        sid = sessions.get(p.id)
        if sid:
            socketio.emit("game_state", room.game.state_for_seat(p.seat), to=sid)


def _emit_room_state(room: Room):
    socketio.emit("room_state", room.to_dict(), to=room.id)


# ------------------------------------------------------------------
# 倒计时工具
# ------------------------------------------------------------------

def _cancel_timer(room: Room, attr: str):
    t: threading.Timer = getattr(room, attr, None)
    if t:
        t.cancel()
        setattr(room, attr, None)


def _set_timer(room: Room, attr: str, seconds: float, fn, *args):
    _cancel_timer(room, attr)
    t = threading.Timer(seconds, fn, args=args)
    t.daemon = True
    t.start()
    setattr(room, attr, t)


# ------------------------------------------------------------------
# 房间加入 / 断线处理
# ------------------------------------------------------------------

@socketio.on("join_room")
def on_join_room(data):
    room_id = data.get("room_id", "").upper()
    name = data.get("name", "玩家")

    room = rooms.get(room_id)
    if not room:
        emit("error", {"msg": "房间不存在"})
        return
    if room.is_full():
        emit("error", {"msg": "房间已满"})
        return

    player_id = uuid.uuid4().hex
    seat = len(room.players)
    player = Player(player_id, name, seat)
    room.add_player(player)
    register_session(player_id, request.sid, room_id)
    sio_join(room_id)
    room.touch()

    emit("joined", {"player_id": player_id, "seat": seat, "room_id": room_id})
    _emit_room_state(room)


@socketio.on("reconnect_session")
def on_reconnect_session(data):
    """断线重连：玩家重新建立 WS 连接后发送此事件恢复会话。"""
    player_id = data.get("player_id", "")
    if not player_id:
        emit("error", {"msg": "missing player_id"})
        return

    room_id = player_room.get(player_id)
    room = rooms.get(room_id) if room_id else None
    if not room:
        emit("error", {"msg": "session expired"})
        return

    player = room.get_player_by_id(player_id)
    if not player:
        emit("error", {"msg": "player not found"})
        return

    # 更新 sid
    register_session(player_id, request.sid, room_id)
    sio_join(room_id)
    room.touch()

    emit("reconnected", {"seat": player.seat, "room_id": room_id})
    _emit_room_state(room)
    if room.game:
        emit("game_state", room.game.state_for_seat(player.seat))

    # 通知房间内其他人此玩家已重连
    socketio.emit("player_reconnected", {"player_id": player_id, "seat": player.seat},
                  to=room_id, skip_sid=request.sid)


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    player_id = remove_session(sid)
    if not player_id:
        return
    room_id = player_room.get(player_id)
    if room_id and room_id in rooms:
        socketio.emit("player_disconnected", {"player_id": player_id}, to=room_id)


# ------------------------------------------------------------------
# 开局
# ------------------------------------------------------------------

@socketio.on("start_game")
def on_start_game(data):
    player_id = _sid_to_player_id(request.sid)
    if not player_id:
        return
    room = _find_room_by_player(player_id)
    if not room or not room.is_full():
        emit("error", {"msg": "人数不足"})
        return

    if not room.round_results:
        first_seat = room.start_first_round()
    else:
        finish_order = getattr(room, "_last_finish_order", [])
        first_seat = finish_order[0] if finish_order else 0
        room.start_round(first_seat)

    room.touch()
    socketio.emit("game_started", {"first_seat": room.game.current_seat}, to=room.id)
    _broadcast_game_state(room)


# ------------------------------------------------------------------
# 出牌 / Pass
# ------------------------------------------------------------------

@socketio.on("play_cards")
def on_play_cards(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    result = room.game.play(player.seat, data.get("card_indices", []))
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    _handle_events(room, result["events"])


@socketio.on("pass_turn")
def on_pass_turn(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    result = room.game.pass_turn(player.seat)
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    _handle_events(room, result["events"])


# ------------------------------------------------------------------
# 叉 / 点
# ------------------------------------------------------------------

@socketio.on("respond_cha")
def on_respond_cha(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    result = room.game.respond_cha(player.seat, data.get("do_cha", False))
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    _handle_events(room, result["events"])


@socketio.on("respond_dian")
def on_respond_dian(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    result = room.game.respond_dian(player.seat, data.get("do_dian", False))
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    _handle_events(room, result["events"])


# ------------------------------------------------------------------
# 立棍
# ------------------------------------------------------------------

@socketio.on("respond_ligun")
def on_respond_ligun(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    ligun_state: LigunState = getattr(room, "_ligun_state", None)
    if not ligun_state:
        emit("error", {"msg": "不在立棍选择阶段"})
        return

    _cancel_timer(room, "_ligun_timer")
    _process_ligun_vote(room, player.seat, data.get("do_ligun", False))


def _process_ligun_vote(room: Room, seat: int, do_ligun: bool):
    ligun_state: LigunState = getattr(room, "_ligun_state", None)
    if not ligun_state:
        return

    result = ligun_state.submit_vote(seat, do_ligun)
    if result["status"] == "error":
        return

    room.touch()

    if result["status"] == "ligun":
        li_seat = result["li_gun_seat"]
        room.game.li_gun_mode = True
        room.game.li_gun_seat = li_seat
        teammate_seat = (li_seat + 2) % 4
        room.game.li_gun_teammate_seat = teammate_seat
        room.players[teammate_seat].locked = True
        room.game.current_seat = li_seat
        del room._ligun_state
        socketio.emit("ligun_started", {"li_gun_seat": li_seat}, to=room.id)
        _broadcast_game_state(room)

    elif result["status"] == "no_ligun":
        del room._ligun_state
        finish_order = getattr(room, "_last_finish_order", [])
        _tribute_or_start(room, finish_order)

    else:
        next_seat = result["next_seat"]
        socketio.emit("ligun_ask", {"asking_seat": next_seat}, to=room.id)
        # 为下一位玩家启动倒计时
        _set_timer(room, "_ligun_timer", LIGUN_TIMEOUT,
                   _ligun_timeout, room.id, next_seat)


def _ligun_timeout(room_id: str, seat: int):
    """立棍倒计时超时：自动视为不立棍。"""
    room = rooms.get(room_id)
    if not room:
        return
    ligun_state: LigunState = getattr(room, "_ligun_state", None)
    if not ligun_state or ligun_state.current_ask_seat != seat:
        return
    socketio.emit("ligun_timeout", {"seat": seat}, to=room_id)
    _process_ligun_vote(room, seat, False)


# ------------------------------------------------------------------
# 进贡 / 还贡  —— 统一选牌协议
# ------------------------------------------------------------------
# 流程：
#   phase="tribute_select" → 赢家(反贡时输家)从进贡牌池中选牌 → 全部确认
#   → _execute_tribute → phase="return_submit" → 赢家各自提交还贡牌
#   → phase="return_select" → 输家(反贡时赢家)从还贡牌池中选牌 → 全部确认
#   → _execute_tribute_back → _start_next_round
#
# 三个 WS 事件在两个选牌 phase 中复用：
#   tribute_select { giver_seat }      —— 预选/更换预选
#   tribute_swap_respond { accept }    —— 响应交换请求
#   tribute_confirm {}                 —— 确认当前预选


@socketio.on("tribute_select")
def on_tribute_select(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    phase = getattr(room, "_tribute_phase", None)
    if phase not in ("tribute_select", "return_select"):
        emit("error", {"msg": "不在选牌阶段"})
        return

    sel: TributeSelectionState = getattr(room, "_selection_state", None)
    if not sel:
        return

    giver_seat = data.get("giver_seat")
    if not isinstance(giver_seat, int):
        emit("error", {"msg": "参数错误"})
        return

    result = sel.select(player.seat, giver_seat)
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()

    if result["status"] == "swap_request":
        target_seat = result["target_seat"]
        target_player = next((p for p in room.players if p.seat == target_seat), None)
        if target_player:
            target_sid = sessions.get(target_player.id)
            if target_sid:
                socketio.emit(
                    "tribute_swap_request",
                    {"requester_seat": player.seat, "giver_seat": giver_seat},
                    to=target_sid,
                )

    socketio.emit("tribute_selection_update", sel.to_dict(), to=room.id)


@socketio.on("tribute_swap_respond")
def on_tribute_swap_respond(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    phase = getattr(room, "_tribute_phase", None)
    if phase not in ("tribute_select", "return_select"):
        emit("error", {"msg": "不在选牌阶段"})
        return

    sel: TributeSelectionState = getattr(room, "_selection_state", None)
    if not sel:
        return

    result = sel.respond_swap(player.seat, data.get("accept", False))
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    socketio.emit("tribute_selection_update", sel.to_dict(), to=room.id)


@socketio.on("tribute_confirm")
def on_tribute_confirm(data):
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    phase = getattr(room, "_tribute_phase", None)
    if phase not in ("tribute_select", "return_select"):
        emit("error", {"msg": "不在选牌阶段"})
        return

    sel: TributeSelectionState = getattr(room, "_selection_state", None)
    if not sel:
        return

    result = sel.confirm(player.seat)
    if not result["ok"]:
        emit("error", {"msg": result["reason"]})
        return

    room.touch()
    socketio.emit("tribute_selection_update", sel.to_dict(), to=room.id)

    if result["complete"]:
        _cancel_timer(room, "_tribute_timer")
        tribute_state: TributeState = getattr(room, "_tribute_state", None)
        if phase == "tribute_select":
            _apply_tribute_selection(room, tribute_state, sel)
            _start_return_submit_phase(room, tribute_state)
        else:
            _apply_return_selection(room, tribute_state, sel)
            _finish_tribute(room)


@socketio.on("tribute_return_submit")
def on_tribute_return_submit(data):
    """赢家（反贡时输家）提交一张还贡牌。{ "card_index": N }"""
    player_id = _sid_to_player_id(request.sid)
    room, player = _get_room_player(player_id)
    if not room or not player:
        return

    if getattr(room, "_tribute_phase", None) != "return_submit":
        emit("error", {"msg": "不在还贡提交阶段"})
        return

    tribute_state: TributeState = getattr(room, "_tribute_state", None)
    if not tribute_state:
        return

    seat = player.seat
    if seat not in tribute_state.receiver_seats:
        emit("error", {"msg": "你不是还贡方"})
        return
    if tribute_state.return_confirmed.get(seat):
        emit("error", {"msg": "已经提交过还贡"})
        return

    card_index = data.get("card_index")
    if not isinstance(card_index, int) or not player.has_card_at([card_index]):
        emit("error", {"msg": "无效下标"})
        return

    card = player.peek_cards([card_index])[0]
    if not validate_return_card(card):
        emit("error", {"msg": "不能还贡A或4"})
        return

    tribute_state.return_cards[seat] = card
    tribute_state.return_confirmed[seat] = True
    room.touch()

    if not tribute_state.is_return_complete():
        socketio.emit("tribute_back_partial", {"seat": seat}, to=room.id)
        return

    _cancel_timer(room, "_tribute_timer")
    _start_return_select_phase(room, tribute_state)


def _tribute_selection_timeout(room_id: str, phase: str):
    """选牌超时：自动 resolve 然后推进流程。"""
    room = rooms.get(room_id)
    if not room:
        return
    if getattr(room, "_tribute_phase", None) != phase:
        return

    sel: TributeSelectionState = getattr(room, "_selection_state", None)
    if sel:
        sel.resolve_timeout()
        socketio.emit("tribute_selection_update", sel.to_dict(), to=room_id)

    tribute_state: TributeState = getattr(room, "_tribute_state", None)
    if phase == "tribute_select":
        socketio.emit("tribute_timeout", {"phase": "tribute_select"}, to=room_id)
        _apply_tribute_selection(room, tribute_state, sel)
        _start_return_submit_phase(room, tribute_state)
    else:
        socketio.emit("tribute_timeout", {"phase": "return_select"}, to=room_id)
        _apply_return_selection(room, tribute_state, sel)
        _finish_tribute(room)


def _tribute_return_submit_timeout(room_id: str):
    """还贡提交超时：自动为未提交的赢家选最小合法牌。"""
    room = rooms.get(room_id)
    if not room:
        return
    tribute_state: TributeState = getattr(room, "_tribute_state", None)
    if not tribute_state or getattr(room, "_tribute_phase", None) != "return_submit":
        return

    level = room.team_levels[room.on_stage_team]
    for seat in tribute_state.receiver_seats:
        if tribute_state.return_confirmed.get(seat):
            continue
        player = next((p for p in room.players if p.seat == seat), None)
        if player:
            eligible = [c for c in player.hand if validate_return_card(c)]
            if eligible:
                card = min(eligible, key=lambda c: c.get_value(level))
                tribute_state.return_cards[seat] = card
                tribute_state.return_confirmed[seat] = True

    socketio.emit("tribute_back_timeout", {}, to=room_id)
    _start_return_select_phase(room, tribute_state)


# ------------------------------------------------------------------
# 内部流程辅助
# ------------------------------------------------------------------

def _handle_events(room: Room, events: list):
    for ev in events:
        if ev["type"] == "round_end":
            _handle_round_end(room, ev["finish_order"])
        else:
            socketio.emit("game_action", ev, to=room.id)
    if not any(e["type"] == "round_end" for e in events):
        _broadcast_game_state(room)


def _handle_round_end(room: Room, finish_order: list):
    if room.game.li_gun_mode:
        summary = room.settle_ligun(room.game.li_gun_seat, finish_order)
    else:
        summary = room.settle_round(finish_order)

    room._last_finish_order = finish_order

    socketio.emit("round_end", summary, to=room.id)

    if summary.get("game_over"):
        socketio.emit("game_over", {"winner_team": summary.get("game_winner")}, to=room.id)
        return

    # 先立棍，再进贡
    _start_ligun_phase(room, finish_order[0])


def _tribute_or_start(room: Room, finish_order: list):
    """立棍结束后：有进贡走进贡流程，否则直接开新局。"""
    tribute_state = determine_tribute(
        finish_order,
        room.players,
        room.team_levels[room.on_stage_team],
        force_quan_dong=room.next_force_tribute,
    )
    room.next_force_tribute = False

    if tribute_state is None:
        _start_next_round(room)
        return

    room._tribute_state = tribute_state
    _start_tribute_select_phase(room, tribute_state)


def _start_tribute_select_phase(room: Room, tribute_state: TributeState):
    """进贡选牌阶段：receiver_seats 从 tribute_cards 池中选牌。"""
    cards = {
        g: tribute_state.tribute_cards[g]
        for g in tribute_state.giver_seats
        if tribute_state.tribute_cards.get(g) is not None
    }
    sel = TributeSelectionState(
        selector_seats=tribute_state.receiver_seats,
        cards=cards,
    )
    room._selection_state = sel
    room._tribute_phase = "tribute_select"

    socketio.emit(
        "tribute_start",
        {
            "type": tribute_state.tribute_type,
            "giver_seats": tribute_state.giver_seats,
            "receiver_seats": tribute_state.receiver_seats,
            "selection": sel.to_dict(),
        },
        to=room.id,
    )
    _set_timer(room, "_tribute_timer", TRIBUTE_TIMEOUT,
               _tribute_selection_timeout, room.id, "tribute_select")


def _apply_tribute_selection(room: Room, tribute_state: TributeState,
                              sel: TributeSelectionState):
    """根据选牌结果将进贡牌从输家手中转移到赢家手中。"""
    player_map = {p.seat: p for p in room.players}
    level = room.team_levels[room.on_stage_team]

    for selector_seat, giver_seat in sel.selections.items():
        if giver_seat is None:
            continue
        card = sel.cards.get(giver_seat)
        if card is None:
            continue
        giver = player_map.get(giver_seat)
        receiver = player_map.get(selector_seat)
        if not giver or not receiver:
            continue
        try:
            idx = next(j for j, c in enumerate(giver.hand) if c is card)
            giver.remove_cards([idx])
        except StopIteration:
            pass
        receiver.hand.append(card)
        from ..models.hand_type import sort_hand
        receiver.hand = sort_hand(receiver.hand, level)

    room._selection_state = None


def _start_return_submit_phase(room: Room, tribute_state: TributeState):
    """还贡提交阶段：receiver_seats 每人独立提交一张还贡牌。"""
    room._tribute_phase = "return_submit"
    socketio.emit(
        "tribute_return_request",
        {
            "receiver_seats": tribute_state.receiver_seats,
            "giver_seats": tribute_state.giver_seats,
        },
        to=room.id,
    )
    _broadcast_game_state(room)
    _set_timer(room, "_tribute_timer", TRIBUTE_BACK_TIMEOUT,
               _tribute_return_submit_timeout, room.id)


def _start_return_select_phase(room: Room, tribute_state: TributeState):
    """还贡选牌阶段：giver_seats（原输家）从 return_cards 池中选牌。"""
    cards = {
        r: tribute_state.return_cards[r]
        for r in tribute_state.receiver_seats
        if tribute_state.return_cards.get(r) is not None
    }
    sel = TributeSelectionState(
        selector_seats=tribute_state.giver_seats,
        cards=cards,
    )
    room._selection_state = sel
    room._tribute_phase = "return_select"

    socketio.emit(
        "tribute_return_select_start",
        {
            "giver_seats": tribute_state.giver_seats,
            "selection": sel.to_dict(),
        },
        to=room.id,
    )
    _set_timer(room, "_tribute_timer", TRIBUTE_BACK_TIMEOUT,
               _tribute_selection_timeout, room.id, "return_select")


def _apply_return_selection(room: Room, tribute_state: TributeState,
                             sel: TributeSelectionState):
    """根据选牌结果将还贡牌从赢家手中转移到输家手中。"""
    player_map = {p.seat: p for p in room.players}
    level = room.team_levels[room.on_stage_team]

    for selector_seat, returner_seat in sel.selections.items():
        if returner_seat is None:
            continue
        card = sel.cards.get(returner_seat)
        if card is None:
            continue
        returner = player_map.get(returner_seat)
        original_giver = player_map.get(selector_seat)
        if not returner or not original_giver:
            continue
        try:
            idx = next(j for j, c in enumerate(returner.hand) if c is card)
            returner.remove_cards([idx])
        except StopIteration:
            pass
        original_giver.hand.append(card)
        from ..models.hand_type import sort_hand
        original_giver.hand = sort_hand(original_giver.hand, level)

    room._selection_state = None


def _finish_tribute(room: Room):
    """还贡完成，清理状态，广播并开新局。"""
    if hasattr(room, "_tribute_state"):
        del room._tribute_state
    if hasattr(room, "_tribute_phase"):
        del room._tribute_phase
    socketio.emit("tribute_complete", {}, to=room.id)
    _broadcast_game_state(room)
    _start_next_round(room)


def _start_ligun_phase(room: Room, first_seat: int):
    seat_order = [(first_seat + i) % 4 for i in range(4)]
    room._ligun_state = LigunState(seat_order)
    socketio.emit("ligun_ask", {"asking_seat": seat_order[0]}, to=room.id)
    _set_timer(room, "_ligun_timer", LIGUN_TIMEOUT,
               _ligun_timeout, room.id, seat_order[0])


def _start_next_round(room: Room):
    """进贡/土皇上流程结束，开始下一局。"""
    finish_order = getattr(room, "_last_finish_order", [])
    first_seat = finish_order[0] if finish_order else 0
    room.start_round(first_seat)
    room.touch()
    socketio.emit("game_started", {"first_seat": room.game.current_seat}, to=room.id)
    _broadcast_game_state(room)


# ------------------------------------------------------------------
# 查找工具
# ------------------------------------------------------------------

def _sid_to_player_id(sid: str):
    for pid, s in sessions.items():
        if s == sid:
            return pid
    return None


def _find_room_by_player(player_id: str):
    if not player_id:
        return None
    room_id = player_room.get(player_id)
    if room_id:
        return rooms.get(room_id)
    # 兜底：遍历查找
    for room in rooms.values():
        if room.get_player_by_id(player_id):
            return room
    return None


def _get_room_player(player_id: str):
    if not player_id:
        return None, None
    room = _find_room_by_player(player_id)
    if not room:
        return None, None
    player = room.get_player_by_id(player_id)
    return room, player
