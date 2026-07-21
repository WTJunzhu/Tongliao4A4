"""
机器人 AI：规则级别，会合法出牌，不追求最优策略。

行动策略（按优先级）：
1. 先出：枚举所有合法牌组，优先出最小的能管上桌的牌；若无牌可管则 pass。
   领出时出手中最小的单张（或最小的合法牌型）。
2. 叉：一律不叉（保守策略，避免复杂状态）。
3. 点：一律不点。
4. 立棍：一律不立。
5. 进贡选牌：自动选第一张（超时兜底会处理，此处主动触发）。
6. 还贡提交：选最小合法牌。
7. 还贡选牌：自动选第一张。
"""
import random
from typing import Optional
from .player import Player
from .card import Card
from .hand_type import Hand, HandRank, detect


class BotPlayer(Player):
    """机器人玩家，继承 Player，is_bot=True 供 ws.py 识别。"""
    is_bot: bool = True

    def __init__(self, player_id: str, name: str, seat: int):
        super().__init__(player_id, name, seat)
        self.is_bot = True


# ---------------------------------------------------------------------------
# 行动决策
# ---------------------------------------------------------------------------

def bot_decide_play(hand: list[Card], table: Optional[Hand], level_rank: str) -> Optional[list[int]]:
    """
    决定出哪些牌的下标。
    table=None 表示领出（无上家牌可管）。
    返回下标列表，或 None 表示 pass。
    """
    if not hand:
        return None

    if table is None:
        # 领出：出最小的合法牌型（单张）
        return _lead(hand, level_rank)
    else:
        # 跟牌：找最小能管上的出法
        return _follow(hand, table, level_rank)


def _lead(hand: list[Card], level_rank: str) -> list[int]:
    """领出：优先出最小单张。"""
    # 找所有合法单张，取 value 最小的
    singles = [
        (i, c.get_value(level_rank))
        for i, c in enumerate(hand)
    ]
    singles.sort(key=lambda x: x[1])
    return [singles[0][0]]


def _follow(hand: list[Card], table: Hand, level_rank: str) -> Optional[list[int]]:
    """
    跟牌：找所有能管上 table 的合法出法，返回 value 最小的那组下标。
    找不到时返回 None（pass）。
    """
    n = len(hand)
    candidates = []

    # 枚举与 table 同数量的牌组合（性能可接受，手牌≤14张）
    target_size = len(table.cards)

    # 对于炸弹/4A4，也枚举更大的炸弹
    for combo in _combinations(range(n), target_size):
        cards = [hand[i] for i in combo]
        h = detect(cards, level_rank)
        if h and h.can_beat(table):
            # 用最小牌的 value 作为排序 key，越小越省力
            key = min(c.get_value(level_rank) for c in cards)
            candidates.append((key, list(combo)))

    # 如果桌面非炸弹，还可以用炸弹盖（已在 can_beat 里处理，但大小不同）
    # 额外扫一遍不同尺寸的炸弹
    if table.rank < HandRank.TRIPLE:
        for bomb_size in (2, 3, 4):  # 王炸2、三炸3、四炸4
            for combo in _combinations(range(n), bomb_size):
                cards = [hand[i] for i in combo]
                h = detect(cards, level_rank)
                if h and h.rank >= HandRank.TRIPLE and h.can_beat(table):
                    key = min(c.get_value(level_rank) for c in cards)
                    candidates.append((key, list(combo)))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _combinations(iterable, r):
    """itertools.combinations 的简单替代。"""
    pool = list(iterable)
    n = len(pool)
    if r > n:
        return
    indices = list(range(r))
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j - 1] + 1
        yield tuple(pool[i] for i in indices)


def bot_decide_tribute_select(selector_seats: list, cards: dict, my_seat: int) -> Optional[int]:
    """进贡/还贡选牌：选第一张可用的牌（最简单）。"""
    for giver_seat in cards:
        return giver_seat  # 直接选第一张
    return None


def bot_decide_return_card(hand: list[Card], level_rank: str) -> Optional[int]:
    """还贡提交：选手中最小的合法牌（不含A/4）。"""
    eligible = [
        (i, c.get_value(level_rank))
        for i, c in enumerate(hand)
        if c.rank not in ("A", "4")
    ]
    if not eligible:
        # 理论上不会走到这，兜底选第一张
        return 0
    eligible.sort(key=lambda x: x[1])
    return eligible[0][0]
