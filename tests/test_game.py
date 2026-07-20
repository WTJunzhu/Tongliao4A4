"""
集成测试：Game 状态机的完整出牌流程。
覆盖：出牌、Pass、接风、叉/点、局结束、finish_order 补全。
"""
import pytest
from server.models.card import Card, Suit
from server.models.game import Game, GameState
from server.models.player import Player
from server.models.hand_type import detect, HandRank


def c(rank, suit=Suit.SPADE):
    return Card(suit, rank)


def make_game(level="3") -> Game:
    players = [Player(f"p{i}", f"P{i}", i) for i in range(4)]
    game = Game(players, level)
    game.state = GameState.PLAYING
    game.current_seat = 0
    return game


def force_hand(game, seat, cards):
    game.players[seat].hand = list(cards)


# ------------------------------------------------------------------
# 基本出牌
# ------------------------------------------------------------------

class TestPlay:
    def test_play_single_advances_turn(self):
        game = make_game()
        force_hand(game, 0, [c("5"), c("7"), c("9")])
        result = game.play(0, [0])
        assert result["ok"]
        assert game.current_seat != 0
        event_types = [e["type"] for e in result["events"]]
        assert "played" in event_types
        assert "next_turn" in event_types

    def test_cannot_play_out_of_turn(self):
        game = make_game()
        force_hand(game, 1, [c("5")])
        result = game.play(1, [0])
        assert not result["ok"]
        assert result["reason"] == "not_your_turn"

    def test_must_beat_table(self):
        game = make_game("10")   # 打10，3不是级牌
        force_hand(game, 0, [c("5"), c("9")])
        force_hand(game, 1, [c("4"), c("7")])
        game.play(0, [1])  # 座位0出9
        # 座位1出4，管不上9
        result = game.play(1, [0])
        assert not result["ok"]
        assert result["reason"] == "cannot_beat"

    def test_bomb_beats_anything(self):
        game = make_game()
        force_hand(game, 0, [c("A"), c("A", Suit.HEART)])  # 出A对
        force_hand(game, 1, [c("K"), c("K", Suit.HEART),
                              c("K", Suit.CLUB), c("K", Suit.DIAMOND)])  # K四炸
        game.play(0, [0, 1])  # 出A对
        result = game.play(1, [0, 1, 2, 3])  # K四炸
        assert result["ok"]

    def test_cannot_lead_straight_pairs_unless_clearing(self):
        game = make_game("10")
        sp = [c("5"), c("5", Suit.HEART), c("6"), c("6", Suit.HEART),
              c("7"), c("7", Suit.HEART)]
        force_hand(game, 0, sp + [c("9")])  # 还有其他牌
        result = game.play(0, list(range(6)))
        assert not result["ok"]
        assert result["reason"] == "cannot_lead_straight_pairs"

    def test_lead_straight_pairs_when_clearing(self):
        game = make_game("10")
        sp = [c("5"), c("5", Suit.HEART), c("6"), c("6", Suit.HEART),
              c("7"), c("7", Suit.HEART)]
        force_hand(game, 0, sp)   # 恰好只有这些
        result = game.play(0, list(range(6)))
        assert result["ok"]


# ------------------------------------------------------------------
# Pass 与 all_others_passed
# ------------------------------------------------------------------

class TestPass:
    def test_pass_advances_turn(self):
        game = make_game()
        force_hand(game, 0, [c("5"), c("9")])
        force_hand(game, 1, [c("7")])
        game.play(0, [1])   # 座位0出9，轮到1
        result = game.pass_turn(1)
        assert result["ok"]
        assert any(e["type"] == "next_turn" for e in result["events"])

    def test_new_lead_when_all_pass(self):
        game = make_game()
        for i in range(4):
            force_hand(game, i, [c("5"), c("7"), c("9"), c("K")])
        game.play(0, [3])   # 座位0出K，轮到1
        game.pass_turn(1)
        game.pass_turn(2)
        result = game.pass_turn(3)
        assert any(e["type"] == "new_lead" for e in result["events"])
        assert game.current_seat == 0
        assert game.last_play is None

    def test_cannot_pass_out_of_turn(self):
        game = make_game()
        result = game.pass_turn(2)
        assert not result["ok"]


# ------------------------------------------------------------------
# 接风
# ------------------------------------------------------------------

class TestJiefeng:
    def test_jiefeng_triggered(self):
        """座位0（队0）出完，其余全pass → 接风给座位2。"""
        game = make_game()
        for i in range(4):
            force_hand(game, i, [c("5"), c("9"), c("K")])
        # 座位0只剩一张K，出掉后走人
        force_hand(game, 0, [c("K")])
        game.play(0, [0])   # 座位0走，轮到1
        assert game.players[0].finished

        game.pass_turn(1)
        game.pass_turn(2)
        result = game.pass_turn(3)
        jiefeng = [e for e in result["events"] if e["type"] == "jiefeng"]
        assert jiefeng, "应触发接风"
        assert jiefeng[0]["seat"] == 2   # 队友
        assert game.current_seat == 2
        assert game.last_play is None

    def test_no_jiefeng_when_teammate_beats(self):
        """队友2管上了座位0的牌后，剩余人pass → new_lead 给座位2，不触发接风。"""
        game = make_game()
        for i in range(4):
            force_hand(game, i, [c("5"), c("7"), c("9")])
        # 座位0出9
        game.current_seat = 0
        force_hand(game, 0, [c("9")])
        game.play(0, [0])   # 座位0走，轮到1
        # 座位1出不了，pass；座位2出王炸管上
        game.pass_turn(1)
        rj = Card(Suit.JOKER, "RJ")
        bj = Card(Suit.JOKER, "BJ")
        game.players[2].hand.insert(0, rj)
        game.players[2].hand.insert(0, bj)
        game.play(2, [0, 1])   # 王炸管上，轮到3
        # 3 pass，1 pass（1已在上面 pass 过，now 轮到3）
        game.pass_turn(3)
        result = game.pass_turn(1)
        jiefeng = [e for e in result["events"] if e["type"] == "jiefeng"]
        new_lead = [e for e in result["events"] if e["type"] == "new_lead"]
        assert not jiefeng
        assert new_lead
        assert game.current_seat == 2


# ------------------------------------------------------------------
# 叉 / 点
# ------------------------------------------------------------------

class TestChaDian:
    def test_cha_ask_triggered(self):
        game = make_game()
        # 座位0出单张5，座位1有两张5可以叉
        force_hand(game, 0, [c("5"), c("9")])
        force_hand(game, 1, [c("5", Suit.HEART), c("5", Suit.DIAMOND), c("7")])
        result = game.play(0, [0])
        cha = [e for e in result["events"] if e["type"] == "cha_ask"]
        assert cha
        assert cha[0]["asking_seat"] == 1
        assert game.state == GameState.CHA_ASKING

    def test_cha_yes_then_dian_ask(self):
        game = make_game()
        force_hand(game, 0, [c("5")])
        force_hand(game, 1, [c("5", Suit.HEART), c("5", Suit.DIAMOND)])
        force_hand(game, 2, [c("5", Suit.CLUB), c("9")])
        game.play(0, [0])   # cha_ask 给座位1
        result = game.respond_cha(1, True)
        dian = [e for e in result["events"] if e["type"] == "dian_ask"]
        assert dian
        assert dian[0]["asking_seat"] == 2

    def test_cha_no_resumes_play(self):
        game = make_game()
        force_hand(game, 0, [c("5"), c("9")])
        force_hand(game, 1, [c("5", Suit.HEART), c("5", Suit.DIAMOND), c("7")])
        for i in [2, 3]:
            force_hand(game, i, [c("7"), c("K")])
        game.play(0, [0])
        result = game.respond_cha(1, False)
        assert game.state == GameState.PLAYING
        next_t = [e for e in result["events"] if e["type"] == "next_turn"]
        assert next_t

    def test_dian_yes_gives_lead(self):
        game = make_game()
        force_hand(game, 0, [c("5")])
        force_hand(game, 1, [c("5", Suit.HEART), c("5", Suit.DIAMOND)])
        force_hand(game, 2, [c("5", Suit.CLUB), c("9")])
        for i in [3]:
            force_hand(game, i, [c("7")])
        game.play(0, [0])
        game.respond_cha(1, True)
        result = game.respond_dian(2, True)
        new_lead = [e for e in result["events"] if e["type"] == "new_lead"]
        assert new_lead
        assert game.current_seat == 2


# ------------------------------------------------------------------
# 局结束 & finish_order 补全
# ------------------------------------------------------------------

class TestRoundEnd:
    def test_finish_order_complete(self):
        """前两名走完后，_round_over 应自动补录剩余两人（active==2时不触发，==1时触发）。"""
        game = make_game()
        for i in range(4):
            force_hand(game, i, [c("K")])

        # 手动模拟前两名走完（队0：座位0,2）
        for order, seat in enumerate([0, 2], start=1):
            p = game.players[seat]
            p.hand = []
            p.finished = True
            p.finish_order = order
            game.finish_order.append(seat)

        # 还有座位1和3，active==2，不应触发
        assert not game._round_over()
        assert len(game.finish_order) == 2

        # 座位1再走，active==1，触发并补录座位3
        game.players[1].hand = []
        game.players[1].finished = True
        game.players[1].finish_order = 3
        game.finish_order.append(1)

        assert game._round_over()
        assert len(game.finish_order) == 4
        assert game.players[3].finish_order == 4
        assert game.players[3].finished

    def test_round_end_event(self):
        """出牌后只剩1人有牌时触发 round_end 事件。"""
        game = make_game()
        # 3人已走，剩座位3
        for seat in [0, 1, 2]:
            p = game.players[seat]
            p.finished = True
            p.finish_order = seat + 1
            game.finish_order.append(seat)
        force_hand(game, 3, [c("5")])
        game.current_seat = 3
        game.last_play = None
        result = game.play(3, [0])
        assert any(e["type"] == "round_end" for e in result["events"])
        assert game.state == GameState.ROUND_END
        assert len(game.finish_order) == 4
