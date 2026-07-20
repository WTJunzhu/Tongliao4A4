"""
集成测试：进贡/还贡、立棍、房间完整局流程。
"""
import pytest
from server.models.card import Card, Suit
from server.models.player import Player
from server.models.room import Room
from server.models.game import Game, GameState
from server.models.tribute import determine_tribute, validate_return_card, TributeState
from server.models.ligun import LigunState
from server.models.deck import build_deck, shuffle_and_deal


def c(rank, suit=Suit.SPADE):
    return Card(suit, rank)


def make_room_with_hands():
    r = Room("TEST")
    for i in range(4):
        r.add_player(Player(f"p{i}", f"P{i}", i))
    deck = build_deck()
    hands = shuffle_and_deal(deck)
    for p in r.players:
        p.set_hand(hands[p.seat], "3")
    r.on_stage_team = 0
    r.team_levels = {0: "3", 1: "3"}
    return r


# ------------------------------------------------------------------
# 进贡
# ------------------------------------------------------------------

class TestTribute:
    def test_quan_dong_tribute(self):
        r = make_room_with_hands()
        # 确保输家（seat 1, 3）没有王炸，避免随机触发反贡
        r.players[1].hand = [c("5"), c("7"), c("K"), c("9")]
        r.players[3].hand = [c("6"), c("8"), c("Q"), c("10")]
        ts = determine_tribute([0, 2, 1, 3], r.players, "3")
        assert ts is not None
        assert ts.tribute_type == "quan_dong"
        assert set(ts.giver_seats) == {1, 3}
        assert set(ts.receiver_seats) == {0, 2}
        assert all(ts.tribute_cards[s] is not None for s in ts.giver_seats)

    def test_ban_dong_tribute(self):
        r = make_room_with_hands()
        # 确保最后一名（seat 1）没有王炸，避免触发反贡
        r.players[1].hand = [c("5"), c("7"), c("9"), c("K")]
        ts = determine_tribute([0, 3, 2, 1], r.players, "3")
        assert ts is not None
        assert ts.tribute_type == "ban_dong"
        assert ts.giver_seats == [1]
        assert ts.receiver_seats == [0]

    def test_tuhuan_no_tribute(self):
        r = make_room_with_hands()
        # finish_order: 0,1,3,2 → 第1名0和第4名2同队(队0) → 土皇上
        ts = determine_tribute([0, 1, 3, 2], r.players, "3")
        assert ts is None

    def test_force_quan_dong_bypasses_tuhuan(self):
        r = make_room_with_hands()
        ts = determine_tribute([0, 1, 3, 2], r.players, "3", force_quan_dong=True)
        assert ts is not None
        assert ts.tribute_type == "quan_dong"

    def test_fan_gong_when_loser_has_jokers(self):
        r = make_room_with_hands()
        r.players[1].hand.insert(0, Card(Suit.JOKER, "RJ"))
        r.players[1].hand.insert(0, Card(Suit.JOKER, "BJ"))
        ts = determine_tribute([0, 2, 1, 3], r.players, "3")
        assert ts is not None
        assert ts.tribute_type == "fan_gong"

    def test_tribute_card_not_ace(self):
        r = make_room_with_hands()
        ts = determine_tribute([0, 2, 1, 3], r.players, "3")
        for seat, card in ts.tribute_cards.items():
            if card is not None:
                assert card.rank != "A", f"座位{seat}进贡了A"

    def test_validate_return_card(self):
        assert not validate_return_card(c("A"))
        assert not validate_return_card(c("4"))
        assert validate_return_card(c("K"))
        assert validate_return_card(c("2"))


# ------------------------------------------------------------------
# 立棍
# ------------------------------------------------------------------

class TestLigun:
    def test_no_ligun_when_all_decline(self):
        state = LigunState([0, 1, 2, 3])
        for seat in [0, 1, 2]:
            result = state.submit_vote(seat, False)
            assert result["status"] == "continue"
        result = state.submit_vote(3, False)
        assert result["status"] == "no_ligun"

    def test_single_ligun_vote(self):
        state = LigunState([0, 1, 2, 3])
        state.submit_vote(0, False)
        state.submit_vote(1, True)   # 只有座位1立棍
        state.submit_vote(2, False)
        result = state.submit_vote(3, False)
        assert result["status"] == "ligun"
        assert result["li_gun_seat"] == 1

    def test_multi_vote_restarts(self):
        state = LigunState([0, 1, 2, 3])
        state.submit_vote(0, True)
        state.submit_vote(1, True)   # 两人立棍
        state.submit_vote(2, False)
        result = state.submit_vote(3, False)
        # 多人立棍，重新开始
        assert result["status"] == "continue"
        assert state.current_ask_idx == 0

    def test_ligun_settle_success(self):
        r = make_room_with_hands()
        r.team_levels = {0: "6", 1: "5"}
        r.on_stage_team = 0
        # 台上队座位0立棍成功（座位0第1名）
        summary = r.settle_ligun(0, [0, 2, 1, 3])
        assert summary["li_gun_success"]
        # 打6升3级：6→7→8→9
        assert summary["level_after"] == "9"
        assert r.next_force_tribute

    def test_ligun_settle_fail(self):
        r = make_room_with_hands()
        r.team_levels = {0: "6", 1: "5"}
        r.on_stage_team = 0
        # 台上队座位0立棍失败（座位1第1名）
        summary = r.settle_ligun(0, [1, 3, 0, 2])
        assert not summary["li_gun_success"]
        # 对手（队1）上台并升2级：5→6→7
        assert r.on_stage_team == 1
        assert r.team_levels[1] == "7"
        assert r.next_force_tribute

    def test_ligun_checkpoint_truncation(self):
        r = make_room_with_hands()
        r.team_levels = {0: "9", 1: "3"}
        r.on_stage_team = 0
        # 打9台上队立棍成功，升3级：9→10→J（截断）
        summary = r.settle_ligun(0, [0, 2, 1, 3])
        assert summary["level_after"] == "J"

    def test_xia_tai_ligun_success(self):
        r = make_room_with_hands()
        r.team_levels = {0: "7", 1: "5"}
        r.on_stage_team = 0
        # 台下队(1)座位1立棍成功 → 上台+升2级
        summary = r.settle_ligun(1, [1, 3, 0, 2])
        assert summary["li_gun_success"]
        assert r.on_stage_team == 1
        # 5升2级：5→6→7
        assert r.team_levels[1] == "7"


# ------------------------------------------------------------------
# 完整小局流程（Room + Game 联动）
# ------------------------------------------------------------------

class TestFullRound:
    def test_start_first_round(self):
        r = Room("T")
        for i in range(4):
            r.add_player(Player(f"p{i}", f"P{i}", i))
        first = r.start_first_round()
        assert r.game is not None
        assert r.game.state == GameState.PLAYING
        # 手牌总数54
        total = sum(len(p.hand) for p in r.players)
        assert total == 54
        # 首家持有红桃3
        red3 = Card(Suit.HEART, "3")
        assert any(c == red3 for c in r.players[first].hand)

    def test_settle_then_start_next(self):
        r = Room("T")
        for i in range(4):
            r.add_player(Player(f"p{i}", f"P{i}", i))
        r.start_first_round()
        r.on_stage_team = 0

        # 模拟全洞结束
        fo = [0, 2, 1, 3]
        summary = r.settle_round(fo)
        assert summary["is_quan_dong"]
        old_level = "3"
        new_level = summary["level_after"]
        assert new_level != old_level

        # 开始下一局
        r.start_round(fo[0])
        assert r.game.state == GameState.PLAYING
        assert r.game.current_seat == fo[0]
        # 级牌已更新
        assert r.game.level_rank == new_level

    def test_game_over_sequence(self):
        """完整胜利路径：打A全洞 → 回3 → 再次打3全洞 → 胜利。"""
        r = Room("T")
        for i in range(4):
            r.add_player(Player(f"p{i}", f"P{i}", i))
        r.on_stage_team = 0
        r.team_levels = {0: "A", 1: "3"}
        r.awaiting_final_3[0] = False

        s1 = r.settle_round([0, 2, 1, 3])   # 打A全洞
        assert not s1["game_over"]
        assert r.awaiting_final_3[0]
        assert r.team_levels[0] == "3"

        s2 = r.settle_round([0, 2, 1, 3])   # 打3全洞
        assert s2["game_over"]
        assert s2["game_winner"] == 0
