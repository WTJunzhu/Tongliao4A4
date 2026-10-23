"""
单局游戏状态机。

状态转移：
  WAITING → TRIBUTE → PRE_PLAY → PLAYING ↔ CHA_ASKING ↔ DIAN_ASKING → ROUND_END
"""
import threading
from enum import Enum, auto
from typing import Optional

from .card import Card
from .player import Player
from .hand_type import Hand, HandRank, detect, sort_hand


class GameState(Enum):
    WAITING = auto()
    TRIBUTE = auto()        # 进贡/还贡阶段
    PRE_PLAY = auto()       # 立棍选择阶段
    PLAYING = auto()        # 正常出牌
    CHA_ASKING = auto()     # 询问是否叉
    DIAN_ASKING = auto()    # 询问是否点
    ROUND_END = auto()


class Game:
    def __init__(self, players: list[Player], level_rank: str):
        self.players = players          # 按座位0~3排列
        self.level_rank = level_rank
        self.state = GameState.WAITING
        self.lock = threading.Lock()

        # 出牌状态
        self.current_seat: int = 0          # 当前应出牌的座位
        self.last_play_seat: int = -1       # 最后出牌的座位
        self.last_play: Optional[Hand] = None
        self.table: list[Card] = []         # 桌面最新一组牌

        # Pass 追踪：记录自上次有效出牌后，在场且尚未出完的玩家中已经 pass 的座位集合
        self.passed_seats: set[int] = set()

        # 叉/点状态
        self.cha_rank: Optional[str] = None      # 当前等待叉/点的牌点
        self.cha_seat: Optional[int] = None      # 叉牌者的座位（叉完后等待点）
        self.asking_seat: Optional[int] = None   # 当前正在被询问的座位

        # 出完牌顺序
        self.finish_order: list[int] = []       # 按先后记录座位号

        # 立棍状态
        self.li_gun_mode = False
        self.li_gun_seat: Optional[int] = None
        self.li_gun_teammate_seat: Optional[int] = None

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def get_player(self, seat: int) -> Player:
        return self.players[seat]

    def active_seats(self) -> list[int]:
        """仍有手牌、未被锁定的在场玩家座位。"""
        return [p.seat for p in self.players if not p.finished and not p.locked]

    def next_seat(self, from_seat: int) -> int:
        """按出牌方向找下一个在场（未出完且未锁定）的玩家座位。

        from_seat 本身可能已出完（刚出完最后一张），仍从它的下家开始找。
        """
        active = set(self.active_seats())
        for i in range(1, 5):
            s = (from_seat + i) % 4
            if s in active:
                return s
        return from_seat

    def all_others_passed(self) -> bool:
        """除最后出牌者外，所有在场玩家是否全部 pass。"""
        active = set(self.active_seats())
        others = active - {self.last_play_seat}
        return others.issubset(self.passed_seats)

    # ------------------------------------------------------------------
    # 出牌处理
    # ------------------------------------------------------------------

    def play(self, seat: int, card_indices: list[int]) -> dict:
        """玩家出牌，返回 {"ok": bool, "reason": str, "events": list}。"""
        with self.lock:
            player = self.get_player(seat)
            if seat != self.current_seat:
                return {"ok": False, "reason": "not_your_turn"}
            if self.state not in (GameState.PLAYING,):
                return {"ok": False, "reason": "wrong_state"}
            if not player.has_card_at(card_indices):
                return {"ok": False, "reason": "invalid_indices"}

            cards = player.peek_cards(card_indices)
            hand = detect(cards, self.level_rank)
            if hand is None:
                return {"ok": False, "reason": "invalid_hand_type"}

            # 如果桌面有牌，必须能管上
            if self.last_play is not None:
                if not hand.can_beat(self.last_play):
                    return {"ok": False, "reason": "cannot_beat"}

            # 首家不能直接出双龙（除非清牌）
            if self.last_play is None and hand.rank == HandRank.STRAIGHT_PAIRS:
                remaining_after = len(player.hand) - len(card_indices)
                if remaining_after != 0:
                    return {"ok": False, "reason": "cannot_lead_straight_pairs"}

            # 执行出牌
            player.remove_cards(card_indices)
            self.table = hand.cards
            self.last_play = hand
            self.last_play_seat = seat
            self.passed_seats.clear()

            events = [{"type": "played", "seat": seat, "cards": [c.to_dict() for c in hand.cards]}]

            self._mark_finished_if_empty(player, events)

            # 同队两人都已出完（或立棍局有人出完）时立即结算，不再询问叉
            if self._round_over():
                self._end_round(events)
                return {"ok": True, "events": events}

            # 检查叉机会（只有出单张时）
            if hand.rank == HandRank.SINGLE and not cards[0].is_joker():
                cha_seat = self._find_cha_candidate(hand.cards[0].rank, seat)
                if cha_seat is not None:
                    self.cha_rank = hand.cards[0].rank
                    self.asking_seat = cha_seat
                    self.state = GameState.CHA_ASKING
                    events.append({"type": "cha_ask", "asking_seat": cha_seat, "rank": self.cha_rank})
                    return {"ok": True, "events": events}

            # 前进到下一玩家
            self.current_seat = self.next_seat(seat)
            events.append({"type": "next_turn", "seat": self.current_seat})
            return {"ok": True, "events": events}

    def pass_turn(self, seat: int) -> dict:
        """玩家 Pass。"""
        with self.lock:
            if seat != self.current_seat:
                return {"ok": False, "reason": "not_your_turn"}
            if self.state != GameState.PLAYING:
                return {"ok": False, "reason": "wrong_state"}
            if self.last_play is None:
                return {"ok": False, "reason": "must_lead"}

            self.passed_seats.add(seat)
            events = [{"type": "passed", "seat": seat}]

            if self.all_others_passed():
                # 最后出牌者重新获得出牌权；他已出完则由队友接风
                self._give_lead(self.last_play_seat, events)
            else:
                self.current_seat = self.next_seat(seat)
                events.append({"type": "next_turn", "seat": self.current_seat})

            return {"ok": True, "events": events}

    # ------------------------------------------------------------------
    # 叉/点处理
    # ------------------------------------------------------------------

    def respond_cha(self, seat: int, do_cha: bool) -> dict:
        with self.lock:
            if self.state != GameState.CHA_ASKING or seat != self.asking_seat:
                return {"ok": False, "reason": "not_your_ask"}

            events = []
            if do_cha:
                player = self.get_player(seat)
                cha_cards = player.get_cha_cards(self.cha_rank)
                indices = [player.hand.index(c) for c in cha_cards]
                player.remove_cards(indices)
                self.table = cha_cards
                self.last_play = detect(cha_cards, self.level_rank)
                self.last_play_seat = seat
                self.cha_seat = seat
                self.passed_seats.clear()
                events.append({"type": "cha", "seat": seat, "rank": self.cha_rank})

                self._mark_finished_if_empty(player, events)
                if self._round_over():
                    self._end_round(events)
                    return {"ok": True, "events": events}

                # 寻找可点的玩家（叉者出完也照常询问）
                dian_seat = self._find_dian_candidate(self.cha_rank, seat)
                if dian_seat is not None:
                    self.asking_seat = dian_seat
                    self.state = GameState.DIAN_ASKING
                    events.append({"type": "dian_ask", "asking_seat": dian_seat, "rank": self.cha_rank})
                else:
                    self._after_cha_no_dian(events)
            else:
                # 此玩家放弃叉，没有其他人可叉（一副牌一种牌点只有一人能叉）
                self._resume_normal_play(events)

            return {"ok": True, "events": events}

    def respond_dian(self, seat: int, do_dian: bool) -> dict:
        with self.lock:
            if self.state != GameState.DIAN_ASKING or seat != self.asking_seat:
                return {"ok": False, "reason": "not_your_ask"}

            events = []
            if do_dian:
                player = self.get_player(seat)
                dian_card = player.get_dian_card(self.cha_rank)
                idx = player.hand.index(dian_card)
                player.remove_cards([idx])
                self.table = [dian_card]
                self.last_play = detect([dian_card], self.level_rank)
                self.last_play_seat = seat
                self.passed_seats.clear()
                events.append({"type": "dian", "seat": seat, "rank": self.cha_rank})

                self._mark_finished_if_empty(player, events)

                # 点后是无解状态：点者获得出牌权（已出完则队友接风）
                self.cha_rank = None
                self.cha_seat = None
                self.asking_seat = None

                if self._round_over():
                    self._end_round(events)
                else:
                    self.state = GameState.PLAYING
                    self._give_lead(seat, events)
            else:
                # 放弃点 → 死叉
                self._after_cha_no_dian(events)

            return {"ok": True, "events": events}

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _find_cha_candidate(self, rank: str, played_seat: int) -> Optional[int]:
        """找到能叉的玩家（只有一人）。"""
        for p in self.players:
            if p.seat != played_seat and not p.finished and not p.locked:
                if p.can_cha(rank, self.level_rank):
                    return p.seat
        return None

    def _find_dian_candidate(self, rank: str, cha_seat: int) -> Optional[int]:
        """找到能点的玩家（只有一人）。"""
        for p in self.players:
            if p.seat != cha_seat and not p.finished and not p.locked:
                if p.can_dian(rank):
                    return p.seat
        return None

    def _after_cha_no_dian(self, events: list):
        """死叉：叉者获得出牌权（已出完则队友接风）。"""
        cha_seat = self.cha_seat
        self.cha_rank = None
        self.asking_seat = None
        self.cha_seat = None
        self.state = GameState.PLAYING
        self._give_lead(cha_seat, events)

    def _give_lead(self, seat: int, events: list):
        """把自由出牌权交给 seat；seat 已出完时交给其队友（接风）。

        调用前已确认本局未结束，所以 seat 出完时队友必定还在场。
        """
        self.last_play = None
        self.passed_seats.clear()
        if self.get_player(seat).finished:
            self.current_seat = (seat + 2) % 4
            events.append({"type": "jiefeng", "seat": self.current_seat})
        else:
            self.current_seat = seat
            events.append({"type": "new_lead", "seat": seat})

    def _mark_finished_if_empty(self, player: Player, events: list):
        if player.hand or player.finished:
            return
        player.finished = True
        player.finish_order = len(self.finish_order) + 1
        self.finish_order.append(player.seat)
        events.append({"type": "player_finished", "seat": player.seat, "order": player.finish_order})

    def _end_round(self, events: list):
        self.state = GameState.ROUND_END
        self.cha_rank = None
        self.cha_seat = None
        self.asking_seat = None
        events.append({"type": "round_end", "finish_order": self.finish_order})

    def _resume_normal_play(self, events: list):
        """叉被放弃，回到正常出牌流程。"""
        self.cha_rank = None
        self.asking_seat = None
        self.state = GameState.PLAYING
        # 回到原来该出牌的下一家
        self.current_seat = self.next_seat(self.last_play_seat)
        events.append({"type": "next_turn", "seat": self.current_seat})

    def _round_over(self) -> bool:
        """判断本局是否结束；结束时按出牌方向补全未出完玩家的 finish_order。

        - 立棍局：任何人出完即结束（立棍成功或撅棍）
        - 普通局：同一队两人都出完即结束（之后的名次不影响结算）
        """
        done = set(self.finish_order)
        if self.li_gun_mode:
            over = len(done) >= 1
        else:
            over = any({t, t + 2} <= done for t in (0, 1))
        if not over:
            return False
        start = self.finish_order[-1]
        for i in range(1, 4):
            p = self.get_player((start + i) % 4)
            if not p.finished:
                p.finished = True
                p.finish_order = len(self.finish_order) + 1
                self.finish_order.append(p.seat)
        return True

    # ------------------------------------------------------------------
    # 序列化（供前端同步用）
    # ------------------------------------------------------------------

    def state_for_seat(self, viewer_seat: int) -> dict:
        """生成某玩家视角的游戏状态。"""
        players_info = []
        for p in self.players:
            info = p.to_dict(reveal_hand=(p.seat == viewer_seat))
            players_info.append(info)
        return {
            "state": self.state.name,
            "level_rank": self.level_rank,
            "current_seat": self.current_seat,
            "last_play_seat": self.last_play_seat,
            "table": [c.to_dict() for c in self.table],
            "leading": self.last_play is None,   # 当前出牌者是否自由出牌（不能 Pass）
            "asking_seat": self.asking_seat,
            "cha_rank": self.cha_rank,
            "finish_order": self.finish_order,
            "li_gun_mode": self.li_gun_mode,
            "li_gun_seat": self.li_gun_seat,
            "players": players_info,
        }
