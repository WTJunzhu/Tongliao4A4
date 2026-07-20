"""
进贡/还贡/反贡/土皇上状态管理。

进贡阶段独立于 Game 状态机，由 Room 在 ROUND_END 后调用。
"""
import time as _time
from typing import Optional
from .player import Player
from .card import Card


class TributeSelectionState:
    """
    进贡/还贡统一选牌协议：预选 + 交换请求 + 确认。

    selector_seats: 选牌方（进贡=赢家，还贡=输家）
    cards: 可供选择的牌池 {giver_seat: Card}
           进贡阶段 giver_seat 是输家座位（tribute_cards 的来源）
           还贡阶段 giver_seat 是赢家座位（return_cards 的提交方）
    """

    def __init__(self, selector_seats: list, cards: dict):
        self.selector_seats: list = list(selector_seats)
        self.cards: dict = dict(cards)  # giver_seat → Card
        # 预选状态: selector_seat → giver_seat（None 表示未选）
        self.selections: dict = {s: None for s in self.selector_seats}
        # 待处理的交换请求
        self.pending_swap: Optional[dict] = None  # {requester_seat, target_seat}
        # 已点确认的选择器
        self.confirmations: set = set()
        # 时间戳用于超时争议判定
        self.selection_timestamps: dict = {}

    # ------------------------------------------------------------------
    # 预选操作
    # ------------------------------------------------------------------

    def select(self, seat: int, giver_seat: int) -> dict:
        """
        seat 预选 giver_seat 的牌。
        返回 {ok, status="selected"|"swap_request", target_seat?}
        """
        if seat not in self.selector_seats:
            return {"ok": False, "reason": "not_a_selector"}
        if giver_seat not in self.cards:
            return {"ok": False, "reason": "invalid_card"}
        if self.pending_swap:
            return {"ok": False, "reason": "pending_swap"}

        self.selection_timestamps[seat] = _time.time()

        # 检查该牌是否已被其他人预选
        current_holder = next(
            (s for s, g in self.selections.items() if g == giver_seat and s != seat),
            None,
        )

        if current_holder is None:
            self.selections[seat] = giver_seat
            return {"ok": True, "status": "selected"}
        else:
            # 发起交换请求：requester=seat，target=current_holder
            self.pending_swap = {"requester_seat": seat, "target_seat": current_holder}
            return {"ok": True, "status": "swap_request", "target_seat": current_holder}

    # ------------------------------------------------------------------
    # 交换请求响应
    # ------------------------------------------------------------------

    def respond_swap(self, seat: int, accept: bool) -> dict:
        """
        seat（交换请求的 target）响应是否同意。
        接受：requester 得到 target 原来选的牌，target 得到 requester 原来选的牌（可能 None）。
        拒绝：pending_swap 清除，selections 不变。
        """
        if not self.pending_swap:
            return {"ok": False, "reason": "no_pending_swap"}
        if seat != self.pending_swap["target_seat"]:
            return {"ok": False, "reason": "not_the_target"}

        requester = self.pending_swap["requester_seat"]
        target = self.pending_swap["target_seat"]
        contested_giver = self.selections[target]

        if accept:
            old_req = self.selections.get(requester)
            self.selections[requester] = contested_giver
            self.selections[target] = old_req

        self.pending_swap = None
        return {"ok": True, "swapped": accept}

    # ------------------------------------------------------------------
    # 确认
    # ------------------------------------------------------------------

    def can_confirm(self) -> bool:
        """所有人都已预选且没有待处理的交换请求时，可以点确认。"""
        return (
            self.pending_swap is None
            and all(v is not None for v in self.selections.values())
        )

    def confirm(self, seat: int) -> dict:
        if seat not in self.selector_seats:
            return {"ok": False, "reason": "not_a_selector"}
        if not self.can_confirm():
            return {"ok": False, "reason": "cannot_confirm_yet"}
        self.confirmations.add(seat)
        complete = len(self.confirmations) == len(self.selector_seats)
        return {"ok": True, "complete": complete}

    # ------------------------------------------------------------------
    # 超时兜底
    # ------------------------------------------------------------------

    def resolve_timeout(self) -> None:
        """
        超时处理：先到先得清除 pending_swap，然后补填所有未预选者，最后全部自动确认。
        """
        # pending_swap：target 先选（先到先得），requester 放弃，无需改变 selections
        self.pending_swap = None

        # 为未选牌者随机分配剩余牌
        selected_givers = {v for v in self.selections.values() if v is not None}
        available = [g for g in self.cards if g not in selected_givers]
        for sel in self.selector_seats:
            if self.selections[sel] is None and available:
                self.selections[sel] = available.pop(0)

        self.confirmations = set(self.selector_seats)

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "selector_seats": self.selector_seats,
            "cards": {str(k): v.to_dict() for k, v in self.cards.items()},
            "selections": {str(k): v for k, v in self.selections.items()},
            "pending_swap": self.pending_swap,
            "confirmations": list(self.confirmations),
            "can_confirm": self.can_confirm(),
        }


class TributeState:
    """记录本轮进贡/还贡的中间状态。"""

    def __init__(self, tribute_type: str, giver_seats: list[int], receiver_seats: list[int]):
        """
        tribute_type: "quan_dong" | "ban_dong" | "fan_gong"
        giver_seats:    进贡方座位列表
        receiver_seats: 接收方座位列表（与 giver_seats 一一对应）
        """
        self.tribute_type = tribute_type
        self.giver_seats = giver_seats
        self.receiver_seats = receiver_seats

        # 进贡牌：giver_seat -> card（自动计算，不需要玩家选）
        self.tribute_cards: dict[int, Optional[Card]] = {s: None for s in giver_seats}
        # 还贡牌：receiver_seat -> card（需要玩家手动选）
        self.return_cards: dict[int, Optional[Card]] = {s: None for s in receiver_seats}
        # 还贡确认状态
        self.return_confirmed: dict[int, bool] = {s: False for s in receiver_seats}

    def is_return_complete(self) -> bool:
        return all(self.return_confirmed.values())


def determine_tribute(
    finish_order: list[int],
    players: list[Player],
    level_rank: str,
    force_quan_dong: bool = False,
) -> Optional[TributeState]:
    """
    根据出完顺序决定进贡类型，返回 TributeState 或 None（无需进贡）。

    土皇上：第1名和第4名同队 → 返回 None（跳过进贡）。
    反贡：输家队某玩家持有王炸（BJ+RJ） → 反贡。
    全洞：第1、第2同队。
    半洞：第1、第3同队。
    """
    seats = finish_order
    team0 = seats[0] % 2  # 第1名所在队伍
    loser_team = 1 - team0

    # 土皇上检测：第1、第4同队且没有强制进贡标记
    # force_quan_dong（立棍/撅棍后）必须跳过土皇上检测
    if not force_quan_dong and len(seats) == 4 and seats[0] % 2 == seats[3] % 2:
        return None

    # 全洞（含 force_quan_dong 的情形）
    is_quan_dong = force_quan_dong or (len(seats) >= 2 and seats[0] % 2 == seats[1] % 2)
    if is_quan_dong:
        loser_seats = [s for s in seats if s % 2 == loser_team]
        winner_seats = [s for s in seats if s % 2 == team0]
        # 反贡检测：输家有王炸（土皇上已排除，此处输家两人都在）
        loser_players_map = {p.seat: p for p in players if p.team == loser_team}
        fan_gong_holder = None
        for seat in loser_seats[:2]:
            p = loser_players_map[seat]
            ranks = {c.rank for c in p.hand}
            if "BJ" in ranks and "RJ" in ranks:
                fan_gong_holder = seat
                break
        if fan_gong_holder is not None:
            # 反贡：赢家全部给输家进贡
            winner_seats_sorted = sorted(winner_seats[:2])
            loser_seats_sorted = sorted(loser_seats[:2])
            state = TributeState("fan_gong", winner_seats_sorted, loser_seats_sorted)
            _fill_tribute_cards(state, players, level_rank)
            return state
        state = TributeState("quan_dong", loser_seats[:2], winner_seats[:2])
        _fill_tribute_cards(state, players, level_rank)
        return state

    # 半洞：第1、第3同队
    if len(seats) >= 3 and seats[0] % 2 == seats[2] % 2:
        # 反贡检测：第4名（唯一输家）有王炸
        last_seat = seats[3] if len(seats) >= 4 else seats[-1]
        last_player = next((p for p in players if p.seat == last_seat), None)
        if last_player:
            ranks = {c.rank for c in last_player.hand}
            if "BJ" in ranks and "RJ" in ranks:
                # 反贡：半洞赢家给唯一持王炸的输家进贡
                giver = seats[0]   # 第1名
                receiver = last_seat
                state = TributeState("fan_gong", [giver], [receiver])
                _fill_tribute_cards(state, players, level_rank)
                return state
        giver = last_seat           # 最后出完的输家
        receiver = seats[0]         # 第1名
        state = TributeState("ban_dong", [giver], [receiver])
        _fill_tribute_cards(state, players, level_rank)
        return state

    return None


def _fill_tribute_cards(state: TributeState, players: list[Player], level_rank: str):
    """自动为进贡方填入应进贡的牌（最大单牌，不含A）。"""
    player_map = {p.seat: p for p in players}
    for seat in state.giver_seats:
        card = player_map[seat].get_max_tribute_card(level_rank)
        if card is not None:
            state.tribute_cards[seat] = card


def validate_return_card(card: Card) -> bool:
    """还贡的牌不能是A或4。"""
    return card.rank not in ("A", "4")
