"""
规则边界回归测试（2026-10 与规则作者逐条确认）。
"""
from server.models.card import Card, Suit
from server.models.player import Player
from server.models.game import Game, GameState
from server.models.hand_type import detect
from server.models.room import Room
from server.models.tribute import determine_tribute, ligun_ask_start_seat
from server.models.ligun import LigunState

S, H, C, D, J = Suit.SPADE, Suit.HEART, Suit.CLUB, Suit.DIAMOND, Suit.JOKER


def card(rank, suit=S):
    return Card(suit, rank)


def make_game(level="3", li_gun_seat=None):
    players = [Player(f"p{i}", f"P{i}", i) for i in range(4)]
    game = Game(players, level)
    game.state = GameState.PLAYING
    game.current_seat = 0
    if li_gun_seat is not None:
        game.li_gun_mode = True
        game.li_gun_seat = li_gun_seat
        players[(li_gun_seat + 2) % 4].locked = True
    return game


def mark_finished(game, *seats):
    for seat in seats:
        p = game.players[seat]
        p.hand = []
        p.finished = True
        game.finish_order.append(seat)
        p.finish_order = len(game.finish_order)


def make_room(levels=("3", "3"), on_stage=0):
    r = Room("T")
    for i in range(4):
        r.add_player(Player(f"p{i}", f"P{i}", i))
    r.on_stage_team = on_stage
    r.team_levels = {0: levels[0], 1: levels[1]}
    return r


def plain_hands(players):
    fill = [card(r, s) for s in (S, C) for r in ("5", "6", "7", "8", "9", "10", "J")]
    for p in players:
        p.hand = list(fill[:10])


# ------------------------------------------------------------------
# 牌型比较
# ------------------------------------------------------------------

class TestFourOneFour:
    red = detect([card("4", H), card("4", D), card("A", H)], "5")
    black = detect([card("4", S), card("4", C), card("A", S)], "5")
    mixed = detect([card("4", S), card("4", H), card("A", D)], "5")
    mixed2 = detect([card("4", C), card("4", D), card("A", C)], "5")

    def test_order_red_black_mixed(self):
        assert self.red.can_beat(self.black)
        assert self.black.can_beat(self.mixed)
        assert self.red.can_beat(self.mixed)

    def test_lower_cannot_beat_higher(self):
        assert not self.mixed.can_beat(self.red)
        assert not self.mixed.can_beat(self.black)
        assert not self.black.can_beat(self.red)

    def test_same_tier_cannot_beat(self):
        assert not self.mixed2.can_beat(self.mixed)

    def test_ace_as_level_still_414(self):
        h = detect([card("4", H), card("4", D), card("A", H)], "A")
        assert h.rank.name == "FOUR_ONE_FOUR"


class TestStraights:
    LV = "3"

    def straight(self, ranks, suit=D):
        return detect([card(r, suit) for r in ranks], self.LV)

    def pairs(self, ranks):
        return detect([card(r, S) for r in ranks] + [card(r, H) for r in ranks], self.LV)

    def test_straight_needs_same_length(self):
        assert not self.straight(["9", "10", "J"]).can_beat(self.straight(["5", "6", "7", "8"]))
        assert self.straight(["6", "7", "8", "9"]).can_beat(self.straight(["5", "6", "7", "8"], S))

    def test_straight_pairs_beat_any_straight(self):
        sp = self.pairs(["5", "6", "7"])
        assert sp.can_beat(self.straight(["8", "9", "10"]))
        assert sp.can_beat(self.straight(["6", "7", "8", "9", "10", "J", "Q"]))

    def test_straight_pairs_vs_straight_pairs_same_length(self):
        assert self.pairs(["8", "9", "10"]).can_beat(self.pairs(["5", "6", "7"]))
        assert not self.pairs(["8", "9", "10", "J"]).can_beat(self.pairs(["5", "6", "7"]))

    def test_straight_pairs_cannot_beat_other_types(self):
        sp = self.pairs(["5", "6", "7"])
        assert not sp.can_beat(detect([card("3")], self.LV))
        assert not sp.can_beat(detect([card("9"), card("9", H)], self.LV))

    def test_bomb_cannot_beat_straight_pairs_but_beats_straight(self):
        triple = detect([card("9"), card("9", H), card("9", D)], self.LV)
        assert not triple.can_beat(self.pairs(["5", "6", "7"]))
        assert triple.can_beat(self.straight(["5", "6", "7"]))


# ------------------------------------------------------------------
# 本局结束 / 接风 / 叉点出完
# ------------------------------------------------------------------

class TestRoundOver:
    def test_quan_dong_ends_immediately_no_deadlock(self):
        """座位2已走，座位0出最后一张 → 同队两人走完，立即结束。"""
        game = make_game()
        mark_finished(game, 2)
        game.players[0].hand = [Card(J, "RJ")]
        game.players[1].hand = [card("5"), card("7")]
        game.players[3].hand = [card("6"), card("8")]
        result = game.play(0, [0])
        assert game.state == GameState.ROUND_END
        assert any(e["type"] == "round_end" for e in result["events"])
        assert game.finish_order == [2, 0, 1, 3]

    def test_finishing_single_does_not_trigger_cha(self):
        """队友已走，出最后一张单牌即结束，不再询问叉。"""
        game = make_game()
        mark_finished(game, 2)
        game.players[0].hand = [card("9")]
        game.players[1].hand = [card("9", H), card("9", C)]
        game.players[3].hand = [card("6")]
        result = game.play(0, [0])
        assert game.state == GameState.ROUND_END
        assert not any(e["type"] == "cha_ask" for e in result["events"])

    def test_ligun_ends_when_anyone_finishes(self):
        """立棍局：对手先走即撅棍，立即结束。"""
        game = make_game(li_gun_seat=0)
        game.current_seat = 1
        game.players[0].hand = [card("5"), card("6")]
        game.players[1].hand = [card("K")]
        game.players[3].hand = [card("7"), card("8")]
        game.play(1, [0])
        assert game.state == GameState.ROUND_END
        assert game.finish_order[0] == 1
        assert len(game.finish_order) == 4

    def test_pass_rejected_when_leading(self):
        game = make_game()
        game.players[0].hand = [card("5")]
        assert not game.pass_turn(0)["ok"]


class TestChaDianFinish:
    def test_cha_finisher_dead_cha_goes_to_teammate(self):
        """座位1用最后两张叉，无人能点 → 队友座位3接风。"""
        game = make_game()
        game.players[0].hand = [card("9"), card("K")]
        game.players[1].hand = [card("9", H), card("9", C)]
        game.players[2].hand = [card("5"), card("6")]
        game.players[3].hand = [card("5", H), card("6", H)]
        game.play(0, [game.players[0].hand.index(card("9"))])
        result = game.respond_cha(1, True)
        assert game.players[1].finished
        assert game.current_seat == 3
        assert any(e["type"] == "jiefeng" for e in result["events"])

    def test_cha_finisher_can_still_be_dianed(self):
        """座位1用最后两张叉后，仍询问能点的人；点者拿牌权。"""
        game = make_game()
        game.players[0].hand = [card("9"), card("K")]
        game.players[1].hand = [card("9", H), card("9", C)]
        game.players[2].hand = [card("5"), card("6")]
        game.players[3].hand = [card("9", D), card("6", H)]
        game.play(0, [game.players[0].hand.index(card("9"))])
        game.respond_cha(1, True)
        assert game.state == GameState.DIAN_ASKING and game.asking_seat == 3
        game.respond_dian(3, True)
        assert game.current_seat == 3

    def test_dian_finisher_goes_to_teammate(self):
        game = make_game()
        game.players[0].hand = [card("9"), card("K")]
        game.players[1].hand = [card("9", H), card("9", C), card("3")]
        game.players[2].hand = [card("9", D)]
        game.players[3].hand = [card("5", H), card("6", H)]
        game.play(0, [game.players[0].hand.index(card("9"))])
        game.respond_cha(1, True)
        result = game.respond_dian(2, True)
        assert game.players[2].finished
        assert game.current_seat == 0
        assert any(e["type"] == "jiefeng" for e in result["events"])

    def test_original_player_may_dian(self):
        """出单张的人可以点别人对自己的叉。"""
        game = make_game()
        game.players[0].hand = [card("9"), card("9", D), card("K")]
        game.players[1].hand = [card("9", H), card("9", C), card("3")]
        game.players[2].hand = [card("5")]
        game.players[3].hand = [card("6")]
        game.play(0, [0])
        game.respond_cha(1, True)
        assert game.state == GameState.DIAN_ASKING and game.asking_seat == 0


# ------------------------------------------------------------------
# 进贡 / 先出
# ------------------------------------------------------------------

class TestTributeRules:
    def test_ban_dong_only_last_place_jokers_trigger_fan_gong(self):
        players = [Player(f"p{i}", f"P{i}", i) for i in range(4)]
        plain_hands(players)
        players[1].hand += [Card(J, "BJ"), Card(J, "RJ")]   # B1（第2名）有王炸，不影响
        t = determine_tribute([0, 1, 2, 3], players, "5")
        assert t.tribute_type == "ban_dong"
        assert (t.giver_seats, t.receiver_seats) == ([3], [0])

        plain_hands(players)
        players[3].hand += [Card(J, "BJ"), Card(J, "RJ")]   # B2（第4名）有王炸 → 反贡
        t = determine_tribute([0, 1, 2, 3], players, "5")
        assert t.tribute_type == "fan_gong"
        assert (t.giver_seats, t.receiver_seats) == ([0], [3])

    def test_quan_dong_fan_gong_swaps_sides(self):
        players = [Player(f"p{i}", f"P{i}", i) for i in range(4)]
        plain_hands(players)
        players[0].hand += [Card(J, "BJ"), Card(J, "RJ")]
        t = determine_tribute([1, 3, 0, 2], players, "5")
        assert t.tribute_type == "fan_gong"
        assert set(t.giver_seats) == {1, 3}
        assert set(t.receiver_seats) == {0, 2}

    def test_tribute_by_team_not_position(self):
        players = [Player(f"p{i}", f"P{i}", i) for i in range(4)]
        plain_hands(players)
        t = determine_tribute([2, 0, 3, 1], players, "5")
        assert t.tribute_type == "quan_dong"
        assert set(t.giver_seats) == {1, 3}

    def test_ligun_ask_start(self):
        assert ligun_ask_start_seat([0, 2, 1, 3]) == 3       # 全洞：最后一名
        assert ligun_ask_start_seat([0, 1, 2, 3]) == 3       # 半洞：最后一名
        assert ligun_ask_start_seat([0, 1, 3, 2]) == 0       # 土皇上：第1名
        assert ligun_ask_start_seat([0, 1, 3, 2], force_quan_dong=True) == 2


# ------------------------------------------------------------------
# 结算：直J/直A、立棍
# ------------------------------------------------------------------

class TestSettle:
    def test_zhi_j_only_on_fan_dong(self):
        r = make_room(("J", "6"))
        s = r.settle_round([1, 0, 2, 3])          # 台下第1，但不是反洞
        assert not s.get("zhi_j")
        assert r.team_levels[0] == "J" and r.on_stage_team == 1

    def test_zhi_a_on_fan_dong(self):
        r = make_room(("A", "6"))
        s = r.settle_round([1, 3, 0, 2])
        assert s.get("zhi_a") and r.team_levels[0] == "J"

    def test_ligun_success_leaves_checkpoint(self):
        r = make_room(("J", "6"))
        s = r.settle_ligun(0, [0, 1, 2, 3])
        assert s["level_after"] == "A"            # J 升3级，停在 A

    def test_ligun_success_on_final_3_wins(self):
        r = make_room(("3", "6"))
        r.awaiting_final_3[0] = True
        s = r.settle_ligun(0, [0, 1, 2, 3])
        assert s["game_over"] and s["game_winner"] == 0

    def test_jue_gun_stops_at_checkpoint(self):
        r = make_room(("6", "10"))
        s = r.settle_ligun(0, [1, 0, 2, 3])       # 撅棍：队1 10 升2级停在 J
        assert s["level_after"] == "J" and r.on_stage_team == 1

    def test_jue_gun_leaves_checkpoint(self):
        r = make_room(("6", "3"))
        s = r.settle_ligun(0, [1, 0, 2, 3])       # 撅棍方本在3：升2级到5
        assert s["level_after"] == "5"

    def test_jue_gun_wins_on_final_3(self):
        """撅棍方正处于最终打3，撅棍升级离开3即赢下整场。"""
        r = make_room(("6", "3"))
        r.awaiting_final_3[1] = True
        s = r.settle_ligun(0, [1, 0, 2, 3])
        assert s["game_over"] and s["game_winner"] == 1

    def test_on_stage_jue_gun_triggers_zhi_j(self):
        r = make_room(("J", "6"))
        s = r.settle_ligun(0, [1, 0, 2, 3])
        assert s.get("zhi_j") and r.team_levels[0] == "3"

    def test_off_stage_ligun_success_triggers_zhi_a(self):
        r = make_room(("A", "6"))
        s = r.settle_ligun(1, [1, 0, 2, 3])       # 台下队立棍成功：上台+2
        assert s.get("zhi_a") and r.team_levels[0] == "J"
        assert r.on_stage_team == 1 and r.team_levels[1] == "8"


# ------------------------------------------------------------------
# 立棍投票
# ------------------------------------------------------------------

class TestLigunVote:
    def test_second_round_only_yes_voters(self):
        st = LigunState([0, 1, 2, 3])
        for seat, v in [(0, True), (1, False), (2, True), (3, False)]:
            res = st.submit_vote(seat, v)
        assert res == {"status": "continue", "next_seat": 0}
        assert st.seat_order == [0, 2]
        st.submit_vote(0, False)
        res = st.submit_vote(2, True)
        assert res == {"status": "ligun", "li_gun_seat": 2}

    def test_max_rounds_first_yes_wins(self):
        st = LigunState([1, 2, 3, 0])
        for seat in [1, 2, 3, 0]:
            st.submit_vote(seat, seat in (3, 0))
        for _ in range(2):
            st.submit_vote(3, True)
            res = st.submit_vote(0, True)
        assert res == {"status": "ligun", "li_gun_seat": 3}

    def test_all_withdraw_in_later_round(self):
        st = LigunState([0, 1, 2, 3])
        for seat in [0, 1, 2, 3]:
            st.submit_vote(seat, seat < 2)
        st.submit_vote(0, False)
        assert st.submit_vote(1, False) == {"status": "no_ligun"}
