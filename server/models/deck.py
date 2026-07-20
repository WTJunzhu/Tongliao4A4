import random
from .card import Card, Suit


def build_deck() -> list[Card]:
    """生成一副54张牌。"""
    ranks = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
    suits = [Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND]
    deck = [Card(suit, rank) for suit in suits for rank in ranks]
    deck.append(Card(Suit.JOKER, "BJ"))  # 小王
    deck.append(Card(Suit.JOKER, "RJ"))  # 大王
    return deck


def shuffle_and_deal(deck: list[Card]) -> list[list[Card]]:
    """洗牌并逆时针发牌，返回4份手牌。

    54张牌：逆时针每人轮流摸一张。54 = 4*13 + 2，
    所以座位0和座位1各得14张，座位2和座位3各得13张。
    """
    deck = deck[:]
    random.shuffle(deck)
    hands: list[list[Card]] = [[], [], [], []]
    for i, card in enumerate(deck):
        hands[i % 4].append(card)
    return hands
