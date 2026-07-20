"""
牌型识别与比较。

8种牌型（从弱到强）：
  single < pair < straight < straight_pairs < triple < quad < joker_bomb < four_one_four
"""
from enum import IntEnum
from typing import Optional
from .card import Card, Suit


class HandRank(IntEnum):
    SINGLE = 1
    PAIR = 2
    STRAIGHT = 3           # 单龙
    STRAIGHT_PAIRS = 4     # 双龙
    TRIPLE = 5             # 三炸
    QUAD = 6               # 四炸
    JOKER_BOMB = 7         # 王炸
    FOUR_ONE_FOUR = 8      # 四幺四


class Hand:
    """识别后的牌型结果。"""
    def __init__(self, rank: HandRank, key: int, cards: list[Card]):
        self.rank = rank   # 牌型等级
        self.key = key     # 同类型比较用的权重（越大越强）
        self.cards = cards

    def can_beat(self, other: "Hand") -> bool:
        """判断 self 能否管 other。"""
        if self.rank == HandRank.FOUR_ONE_FOUR:
            return True
        if other.rank == HandRank.FOUR_ONE_FOUR:
            return False

        # 双龙只能被 4A4 管（上面已处理）
        if other.rank == HandRank.STRAIGHT_PAIRS:
            return False

        # 炸弹可以管任何非炸弹
        self_is_bomb = self.rank >= HandRank.TRIPLE
        other_is_bomb = other.rank >= HandRank.TRIPLE
        if self_is_bomb and not other_is_bomb:
            return True
        if not self_is_bomb and other_is_bomb:
            return False

        # 两者都是炸弹：高等级炸弹直接胜，同等级比 key
        if self_is_bomb and other_is_bomb:
            if self.rank != other.rank:
                return self.rank > other.rank
            return self.key > other.key

        # 同类型非炸弹比较
        if self.rank != other.rank:
            return False
        return self.key > other.key


# ---------------------------------------------------------------------------
# 识别函数
# ---------------------------------------------------------------------------

def _rank_values(cards: list[Card], level_rank: str) -> list[int]:
    return [c.get_value(level_rank) for c in cards]


def detect(cards: list[Card], level_rank: str) -> Optional[Hand]:
    """识别牌型，非法返回 None。"""
    n = len(cards)
    if n == 0:
        return None

    # ---- 四幺四 ----
    if n == 3:
        fours = [c for c in cards if c.rank == "4"]
        aces = [c for c in cards if c.rank == "A"]
        if len(fours) == 2 and len(aces) == 1:
            return Hand(HandRank.FOUR_ONE_FOUR, _414_key(cards), cards)

    # ---- 王炸 ----
    if n == 2:
        ranks = {c.rank for c in cards}
        if ranks == {"BJ", "RJ"}:
            return Hand(HandRank.JOKER_BOMB, 0, cards)

    # ---- 四炸（轰）----
    if n == 4:
        vals = _rank_values(cards, level_rank)
        if len(set(v for v in vals)) == 1 and not any(c.is_joker() for c in cards):
            return Hand(HandRank.QUAD, vals[0], cards)

    # ---- 三炸 ----
    if n == 3:
        vals = _rank_values(cards, level_rank)
        if len(set(vals)) == 1 and not any(c.is_joker() for c in cards):
            return Hand(HandRank.TRIPLE, vals[0], cards)

    # ---- 对子 ----
    if n == 2:
        vals = _rank_values(cards, level_rank)
        if vals[0] == vals[1]:
            return Hand(HandRank.PAIR, vals[0], cards)

    # ---- 单张 ----
    if n == 1:
        return Hand(HandRank.SINGLE, cards[0].get_value(level_rank), cards)

    # ---- 单龙 ----
    if n >= 3:
        result = _try_straight(cards, level_rank)
        if result:
            return result

    # ---- 双龙 ----
    if n >= 6 and n % 2 == 0:
        result = _try_straight_pairs(cards, level_rank)
        if result:
            return result

    return None


def _try_straight(cards: list[Card], level_rank: str) -> Optional[Hand]:
    """尝试识别为单龙。"""
    for c in cards:
        if c.is_joker() or c.rank == "2" or c.rank == level_rank:
            return None
    vals = sorted([c.get_value(level_rank) for c in cards])
    for i in range(1, len(vals)):
        if vals[i] != vals[i - 1] + 1:
            return None
    return Hand(HandRank.STRAIGHT, vals[0], cards)


def _try_straight_pairs(cards: list[Card], level_rank: str) -> Optional[Hand]:
    """尝试识别为双龙（≥3对连续对子）。"""
    for c in cards:
        if c.is_joker() or c.rank == "2" or c.rank == level_rank:
            return None
    vals = sorted([c.get_value(level_rank) for c in cards])
    # 每个值必须恰好出现2次
    from collections import Counter
    cnt = Counter(vals)
    if any(v != 2 for v in cnt.values()):
        return None
    unique = sorted(cnt.keys())
    if len(unique) < 3:
        return None
    for i in range(1, len(unique)):
        if unique[i] != unique[i - 1] + 1:
            return None
    return Hand(HandRank.STRAIGHT_PAIRS, unique[0], cards)


def _414_key(cards: list[Card]) -> int:
    """四幺四的比较权重：纯红=2，纯黑=1，花色=0。"""
    all_red = all(c.is_red for c in cards)
    all_black = all(not c.is_red for c in cards)
    if all_red:
        return 2
    if all_black:
        return 1
    return 0


# ---------------------------------------------------------------------------
# 手牌排序（用于展示）
# ---------------------------------------------------------------------------

def sort_hand(cards: list[Card], level_rank: str) -> list[Card]:
    """按权重降序排列手牌。"""
    return sorted(cards, key=lambda c: c.get_value(level_rank), reverse=True)
