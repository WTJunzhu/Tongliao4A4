"""
立棍/撅棍状态管理。
"""
from typing import Optional


class LigunState:
    """立棍选择阶段的状态。"""

    def __init__(self, seat_order: list[int]):
        """
        seat_order: 本局出牌顺序下的玩家座位列表（依次轮询）。
        """
        self.seat_order = seat_order
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

        yes_votes = [s for s, v in self.votes.items() if v is True]

        # 所有人都投完票了
        if self.current_ask_idx >= len(self.seat_order):
            if len(yes_votes) == 1:
                self.li_gun_seat = yes_votes[0]
                self.done = True
                return {"status": "ligun", "li_gun_seat": self.li_gun_seat}
            elif len(yes_votes) == 0:
                self.done = True
                return {"status": "no_ligun"}
            else:
                # 多人立棍，重置投票，开始下一轮
                self.votes = {s: None for s in self.seat_order}
                self.current_ask_idx = 0
                return {"status": "continue", "next_seat": self.current_ask_seat}

        # 还没投完
        return {"status": "continue", "next_seat": self.current_ask_seat}
