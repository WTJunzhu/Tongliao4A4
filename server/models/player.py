from typing import Optional
from .card import Card, Suit
from .hand_type import detect, sort_hand, Hand


class Player:
    def __init__(self, player_id: str, name: str, seat: int):
        self.id = player_id
        self.name = name
        self.seat = seat                 # 0~3
        self.team = seat % 2             # 0=A队(座位0,2)，1=B队(座位1,3)
        self.hand: list[Card] = []
        self.finished = False
        self.finish_order: Optional[int] = None  # 第几个出完（1~4）
        self.locked = False              # 立棍时队友被锁定

    # ------------------------------------------------------------------
    # 手牌管理
    # ------------------------------------------------------------------

    def set_hand(self, cards: list[Card], level_rank: str):
        self.hand = sort_hand(cards, level_rank)

    def has_card_at(self, indices: list[int]) -> bool:
        return all(0 <= i < len(self.hand) for i in indices)

    def peek_cards(self, indices: list[int]) -> list[Card]:
        return [self.hand[i] for i in indices]

    def remove_cards(self, indices: list[int]) -> list[Card]:
        indices_set = sorted(set(indices), reverse=True)
        removed = [self.hand[i] for i in sorted(indices)]
        for i in indices_set:
            self.hand.pop(i)
        return removed

    # ------------------------------------------------------------------
    # 叉/点查询
    # ------------------------------------------------------------------

    def can_cha(self, rank: str, level_rank: str) -> bool:
        """手中是否有两张 rank 牌（可以叉）。"""
        matching = [c for c in self.hand if c.rank == rank]
        return len(matching) >= 2

    def get_cha_cards(self, rank: str) -> list[Card]:
        """返回手中两张 rank 牌（用于叉）。"""
        matching = [c for c in self.hand if c.rank == rank]
        return matching[:2]

    def can_dian(self, rank: str) -> bool:
        """手中是否有一张 rank 牌（可以点）。"""
        return any(c.rank == rank for c in self.hand)

    def get_dian_card(self, rank: str) -> Optional[Card]:
        for c in self.hand:
            if c.rank == rank:
                return c
        return None

    # ------------------------------------------------------------------
    # 进贡查询
    # ------------------------------------------------------------------

    def get_max_tribute_card(self, level_rank: str) -> Optional[Card]:
        """返回应进贡的牌：最大单牌，但不能是A。"""
        eligible = sorted(
            [c for c in self.hand if c.rank != "A"],
            key=lambda c: c.get_value(level_rank),
            reverse=True,
        )
        if eligible:
            return eligible[0]
        # 全是A的极端情况：只能进贡A
        return self.hand[0] if self.hand else None

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self, reveal_hand=False) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "seat": self.seat,
            "team": self.team,
            "finished": self.finished,
            "finish_order": self.finish_order,
            "hand_count": len(self.hand),
            "locked": self.locked,
        }
        if reveal_hand:
            base["hand"] = [c.to_dict() for c in self.hand]
        return base

