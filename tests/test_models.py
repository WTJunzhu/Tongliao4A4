"""
单元测试：Card、Hand、Deck、Room 升级系统。
"""
import pytest
from server.models.card import Card, Suit
from server.models.hand_type import Hand, HandRank, detect, _try_straight, _try_straight_pairs
from server.models.deck import build_deck, shuffle_and_deal
from server.models.room import Room, next_level, LEVEL_SEQ, CHECKPOINTS
from server.models.player import Player


# ------------------------------------------------------------------
# Card
# ------------------------------------------------------------------

class TestCard:
    def test_joker_values(self):
        rj = Card(Suit.JOKER, "RJ")
        bj = Card(Suit.JOKER, "BJ")
        assert rj.get_value("3") == 16
        assert bj.get_value("3") == 15

    def test_level_rank_value(self):
        c = Card(Suit.SPADE, "7")
        assert c.get_value("7") == 14   # 级牌固定14

    def test_normal_order(self):
        three = Card(Suit.SPADE, "3")
        ace = Card(Suit.SPADE, "A")
        two = Card(Suit.SPADE, "2")
        assert three.get_value("5") < ace.get_value("5") < two.get_value("5")

    def test_is_red(self):
        assert Card(Suit.HEART, "K").is_red
        assert Card(Suit.DIAMOND, "K").is_red
        assert not Card(Suit.SPADE, "K").is_red
        assert not Card(Suit.CLUB, "K").is_red


# ------------------------------------------------------------------
# HandRank detect
# ------------------------------------------------------------------

def c(rank, suit=Suit.SPADE):
    return Card(suit, rank)


class TestDetect:
    LV = "3"   # 当前打3

    def test_single(self):
        h = detect([c("5")], self.LV)
        assert h.rank == HandRank.SINGLE
        assert h.key == c("5").get_value(self.LV)

    def test_pair(self):
        h = detect([c("7"), c("7", Suit.HEART)], self.LV)
        assert h.rank == HandRank.PAIR

    def test_triple(self):
        h = detect([c("9"), c("9", Suit.HEART), c("9", Suit.DIAMOND)], self.LV)
        assert h.rank == HandRank.TRIPLE

    def test_quad(self):
        cards = [c("K", s) for s in [Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND]]
        h = detect(cards, self.LV)
        assert h.rank == HandRank.QUAD

    def test_joker_bomb(self):
        h = detect([Card(Suit.JOKER, "RJ"), Card(Suit.JOKER, "BJ")], self.LV)
        assert h.rank == HandRank.JOKER_BOMB

    def test_414(self):
        cards = [c("4"), c("4", Suit.HEART), c("A")]
        h = detect(cards, self.LV)
        assert h.rank == HandRank.FOUR_ONE_FOUR

    def test_straight(self):
        cards = [c("5"), c("6"), c("7"), c("8"), c("9")]
        h = detect(cards, "10")   # 打10时5-9都是普通牌
        assert h.rank == HandRank.STRAIGHT

    def test_straight_pairs(self):
        cards = [c("5"), c("5", Suit.HEART),
                 c("6"), c("6", Suit.HEART),
                 c("7"), c("7", Suit.HEART)]
        h = detect(cards, "10")
        assert h.rank == HandRank.STRAIGHT_PAIRS

    def test_invalid(self):
        assert detect([c("5"), c("7")], self.LV) is None

    def test_level_card_not_in_straight(self):
        # 3是级牌，不能组成单龙
        cards = [c("3"), c("4"), c("5"), c("6"), c("7")]
        assert detect(cards, "3") is None


# ------------------------------------------------------------------
# can_beat
# ------------------------------------------------------------------

class TestCanBeat:
    LV = "3"

    def hand(self, cards):
        return detect(cards, self.LV)

    def test_bomb_beats_pair(self):
        triple = self.hand([c("9"), c("9", Suit.HEART), c("9", Suit.DIAMOND)])
        pair = self.hand([c("A"), c("A", Suit.HEART)])
        assert triple.can_beat(pair)
        assert not pair.can_beat(triple)

    def test_higher_quad_beats_lower(self):
        quad_k = self.hand([c("K", s) for s in Suit if s != Suit.JOKER])
        quad_5 = self.hand([c("5", s) for s in Suit if s != Suit.JOKER])
        assert quad_k.can_beat(quad_5)
        assert not quad_5.can_beat(quad_k)

    def test_joker_beats_quad(self):
        jb = self.hand([Card(Suit.JOKER, "RJ"), Card(Suit.JOKER, "BJ")])
        quad = self.hand([c("A", s) for s in Suit if s != Suit.JOKER])
        assert jb.can_beat(quad)
        assert not quad.can_beat(jb)

    def test_414_beats_all(self):
        f14 = self.hand([c("4"), c("4", Suit.HEART), c("A")])
        jb = self.hand([Card(Suit.JOKER, "RJ"), Card(Suit.JOKER, "BJ")])
        assert f14.can_beat(jb)

    def test_straight_pairs_only_beaten_by_414(self):
        sp = detect(
            [c("5"), c("5", Suit.HEART), c("6"), c("6", Suit.HEART),
             c("7"), c("7", Suit.HEART)], "10"
        )
        jb = detect([Card(Suit.JOKER, "RJ"), Card(Suit.JOKER, "BJ")], "10")
        f14 = detect([c("4"), c("4", Suit.HEART), c("A")], "10")
        assert not jb.can_beat(sp)
        assert f14.can_beat(sp)

    def test_same_type_higher_wins(self):
        pair_k = self.hand([c("K"), c("K", Suit.HEART)])
        pair_9 = self.hand([c("9"), c("9", Suit.HEART)])
        assert pair_k.can_beat(pair_9)
        assert not pair_9.can_beat(pair_k)

    def test_different_type_single_vs_pair(self):
        single_a = self.hand([c("A")])
        pair_3 = self.hand([c("3"), c("3", Suit.HEART)])
        assert not single_a.can_beat(pair_3)


# ------------------------------------------------------------------
# Deck
# ------------------------------------------------------------------

class TestDeck:
    def test_build_deck_54(self):
        deck = build_deck()
        assert len(deck) == 54

    def test_no_duplicates(self):
        deck = build_deck()
        assert len(set((c.suit, c.rank) for c in deck)) == 54

    def test_deal_counts(self):
        deck = build_deck()
        hands = shuffle_and_deal(deck)
        assert len(hands) == 4
        counts = sorted(len(h) for h in hands)
        assert counts == [13, 13, 14, 14]

    def test_deal_covers_all_cards(self):
        deck = build_deck()
        hands = shuffle_and_deal(deck)
        total = sum(len(h) for h in hands)
        assert total == 54


# ------------------------------------------------------------------
# Room 升级系统
# ------------------------------------------------------------------

class TestNextLevel:
    def test_normal_step(self):
        assert next_level("3", 1) == "5"
        assert next_level("5", 1) == "6"
        assert next_level("6", 2) == "8"

    def test_checkpoint_truncation(self):
        # 打10升2级：10→J（J是checkpoint，截断）
        assert next_level("10", 2) == "J"
        # 打8升3级：8→9→10→J（J截断）
        assert next_level("8", 3) == "J"

    def test_a_wraps_to_3(self):
        assert next_level("A", 1) == "3"   # A→3，3是checkpoint，截断
        assert next_level("A", 3) == "3"   # 无论多少步，A之后都是3

    def test_j_checkpoint(self):
        # 打J升级必须全洞（settle_round处理），此处只测next_level不跳过J
        assert next_level("9", 2) == "J"   # 9→10→J 截断


class TestRoomSettle:
    def _room(self):
        r = Room("T")
        for i in range(4): r.add_player(Player(f"p{i}", f"P{i}", i))
        r.on_stage_team = 0
        r.team_levels = {0: "3", 1: "3"}
        return r

    def test_quan_dong_upgrades_2(self):
        r = self._room()
        summary = r.settle_round([0, 2, 1, 3])   # 队0全洞
        assert summary["is_quan_dong"]
        assert summary["level_after"] == "6"     # 3→5→6（5不是checkpoint）

    def test_ban_dong_upgrades_1_on_non_checkpoint(self):
        r = self._room()
        r.team_levels[0] = "6"
        summary = r.settle_round([0, 3, 2, 1])   # 队0半洞（1st=0,3rd=2）
        assert summary["is_ban_dong"]
        assert summary["level_after"] == "7"

    def test_ban_dong_no_upgrade_on_checkpoint(self):
        r = self._room()
        r.team_levels[0] = "J"
        summary = r.settle_round([0, 3, 2, 1])
        assert summary["is_ban_dong"]
        assert summary["level_after"] == "J"    # 打J半洞不升

    def test_loser_switches_stage(self):
        r = self._room()
        r.team_levels[0] = "6"
        summary = r.settle_round([1, 3, 0, 2])   # 队1赢
        assert summary["winner_team"] == 1
        assert r.on_stage_team == 1

    def test_zhi_j_penalty(self):
        r = self._room()
        r.team_levels[0] = "J"
        summary = r.settle_round([1, 3, 0, 2])   # 队1赢，直J
        assert summary.get("zhi_j")
        assert r.team_levels[0] == "3"

    def test_zhi_a_penalty(self):
        r = self._room()
        r.team_levels[0] = "A"
        summary = r.settle_round([1, 3, 0, 2])   # 直A
        assert summary.get("zhi_a")
        assert r.team_levels[0] == "J"

    def test_game_over_path(self):
        r = self._room()
        r.team_levels[0] = "A"
        s1 = r.settle_round([0, 2, 1, 3])   # 打A全洞 → 回到3，awaiting_final_3
        assert not s1["game_over"]
        assert r.awaiting_final_3[0]
        assert r.team_levels[0] == "3"

        # 此时 team_levels[0]=="3"，on_stage_team==0，再次全洞应触发胜利
        s2 = r.settle_round([0, 2, 1, 3])
        assert s2["game_over"]
        assert s2["game_winner"] == 0
