"""
立棍/撅棍状态管理。
"""
from typing import Optional

MAX_LIGUN_ROUNDS = 3   # 最多投票轮数，仍有多人坚持立棍时由本轮顺序第一个立棍者立棍


class LigunState:
    """立棍选择阶段的状态。

    第一轮按出牌顺序询问全部4人；之后每轮只询问上一轮选择立棍的玩家。
    某轮只有1人立棍 → 立棍；无人立棍 → 正常流程。
    """

    def __init__(self, seat_order: list[int]):
        """
        seat_order: 本局询问顺序下的玩家座位列表（依次轮询）。
        """
        self.seat_order = seat_order
        self.round_no = 1
        self.votes: dict[int, Optional[bool]] = {s: None for s in seat_order}
        self.current_ask_idx = 0   # 当前轮询到第几位
        self.li_gun_seat: Optional[int] = None
        self.done = False

    @property
    def current_ask_seat(self) -> Optional[int]:
        if self.current_ask_idx < len(self.seat_order):
            return self.seat_order[self.current_ask_idx]
        return None

    def submit_vote(self, seat: int, do_ligun: bool) -> dict:
        """
        提交一票，返回 {"status": "continue"|"no_ligun"|"ligun", "li_gun_seat": int|None}。
        """
        if seat != self.current_ask_seat:
            return {"status": "error", "reason": "not_your_turn"}

        self.votes[seat] = do_ligun
        self.current_ask_idx += 1

        if self.current_ask_idx < len(self.seat_order):
            return {"status": "continue", "next_seat": self.current_ask_seat}

        # 本轮投完
        yes_votes = [s for s in self.seat_order if self.votes[s] is True]
        if not yes_votes:
            self.done = True
            return {"status": "no_ligun"}
        if len(yes_votes) == 1 or self.round_no >= MAX_LIGUN_ROUNDS:
            self.li_gun_seat = yes_votes[0]
            self.done = True
            return {"status": "ligun", "li_gun_seat": self.li_gun_seat}

        # 多人立棍：下一轮只让这些人再选
        self.round_no += 1
        self.seat_order = yes_votes
        self.votes = {s: None for s in yes_votes}
        self.current_ask_idx = 0
        return {"status": "continue", "next_seat": self.current_ask_seat}
