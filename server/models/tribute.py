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
    根据上一局出完顺序和本局新发的手牌决定进贡，返回 TributeState 或 None（无需进贡）。

    finish_order 必须是完整的4人顺序（Game 结束时会补全）。
    - 土皇上：第1、第4名同队 → None，由第1名先出。
    - 全洞（含立棍/撅棍后的强制全洞）：输家两人各进贡一张，赢家商量分配；
      赢家各还一张，输家商量分配并商量谁先出。
      反贡：任一输家同时持有大小王 → 进贡/还贡双方颠倒，流程相同。
    - 半洞：第4名给第1名进贡，第1名还贡，第4名先出。
      反贡：第4名本人持有大小王（第2名不参与进贡，有王也不算）→ 第1名给第4名进贡，第1名先出。

    无论哪种情况，下一局都由进贡方（giver_seats）先出；两名进贡方时由他们商量。
    """
    if len(finish_order) < 4:
        return None
    first, last = finish_order[0], finish_order[3]
    win_team = first % 2

    if not force_quan_dong and last % 2 == win_team:
        return None   # 土皇上

    player_map = {p.seat: p for p in players}

    def has_joker_bomb(seat: int) -> bool:
        ranks = {c.rank for c in player_map[seat].hand}
        return "BJ" in ranks and "RJ" in ranks

    is_quan_dong = force_quan_dong or finish_order[1] % 2 == win_team
    if is_quan_dong:
        winners = [win_team, win_team + 2]
        losers = [1 - win_team, 3 - win_team]
        if any(has_joker_bomb(s) for s in losers):
            state = TributeState("fan_gong", winners, losers)
        else:
            state = TributeState("quan_dong", losers, winners)
    else:
        # 半洞：只有第4名本人有王炸才反贡
        if has_joker_bomb(last):
            state = TributeState("fan_gong", [first], [last])
        else:
            state = TributeState("ban_dong", [last], [first])

    _fill_tribute_cards(state, players, level_rank)
    return state


def ligun_ask_start_seat(finish_order: list[int], force_quan_dong: bool = False) -> int:
    """立棍询问从谁开始：土皇上从第1名开始，其余从上一局最后一名开始。"""
    if not force_quan_dong and finish_order[0] % 2 == finish_order[-1] % 2:
        return finish_order[0]
    return finish_order[-1]


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
