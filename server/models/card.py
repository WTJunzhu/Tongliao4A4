from enum import Enum


class Suit(Enum):
    SPADE = "spade"
    HEART = "heart"
    CLUB = "club"
    DIAMOND = "diamond"
    JOKER = "joker"


# 权重序列：3=1 < 4=2 < ... < K=11 < A=12 < 2(特殊)=13 < 级牌=14 < BJ=15 < RJ=16
# 但为了和历史代码兼容（级牌=13，BJ=14，RJ=15），把普通牌范围压缩：
# 3=1, 4=2, ..., K=10, A=11  （共11个非级非王普通牌，2在外面单独=12）
_BASE_VALUE = {
    "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
    "8": 6, "9": 7, "10": 8, "J": 9, "Q": 10, "K": 11, "A": 11,
}
# A 和 K 不能同值。正确序列：3<4<5<6<7<8<9<10<J<Q<K<A<2<级牌<BJ<RJ
# 共 11 普通非级非2 + 1(A) = 12 个，加 2/级牌/BJ/RJ 共16个值，需 1..16
# 重新定义：3=1..K=11, A=12, 2=13, 级牌=14, BJ=15, RJ=16
_BASE_VALUE = {
    "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
    "8": 6, "9": 7, "10": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
}


class Card:
    def __init__(self, suit: Suit, rank: str):
        self.suit = suit
        self.rank = rank  # "3"~"A", "2", "BJ", "RJ"

    @property
    def is_red(self) -> bool:
        return self.suit in (Suit.HEART, Suit.DIAMOND)

    def is_joker(self) -> bool:
        return self.suit == Suit.JOKER

    def get_value(self, level_rank: str) -> int:
        """权重序列：3=1 < 4=2 < ... < A=12 < 2=13 < 级牌=14 < BJ=15 < RJ=16"""
        if self.rank == "RJ":
            return 16
        if self.rank == "BJ":
            return 15
        if self.rank == level_rank:
            return 14
        if self.rank == "2":
            return 13
        return _BASE_VALUE[self.rank]

    def to_dict(self) -> dict:
        return {"suit": self.suit.value, "rank": self.rank, "is_red": self.is_red}

    def __repr__(self) -> str:
        suit_symbol = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦", "joker": "🃏"}
        return f"{suit_symbol[self.suit.value]}{self.rank}"

    def __eq__(self, other) -> bool:
        return isinstance(other, Card) and self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))
