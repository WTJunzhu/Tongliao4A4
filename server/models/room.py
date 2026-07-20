"""
房间管理：升级系统、台上台下、多局生命周期。
"""
import time
import uuid
from typing import Optional

from .player import Player
from .deck import build_deck, shuffle_and_deal
from .game import Game, GameState

LEVEL_SEQ = ["3", "5", "6", "7", "8", "9", "10", "J", "K", "A"]
CHECKPOINTS = {"3", "J", "A"}   # 必须全洞才能离开的级别


def next_level(current: str, steps: int) -> str:
    """升 steps 级，遇到检查点立即截断。"""
    idx = LEVEL_SEQ.index(current)
    result = current
    for _ in range(steps):
        next_idx = idx + 1
        if next_idx >= len(LEVEL_SEQ):
            next_idx = 0   # A 之后回到 3
        result = LEVEL_SEQ[next_idx]
        idx = next_idx
        if result in CHECKPOINTS:
            break
    return result


class RoundResult:
    def __init__(self, finish_order: list[int]):
        self.finish_order = finish_order   # 座位号列表，先出完在前
        seats = finish_order

        # 全洞：同队第1、第2出完
        self.is_quan_dong = (
            len(seats) >= 2 and seats[0] % 2 == seats[1] % 2
        )
        # 半洞：同队第1、第3出完
        self.is_ban_dong = (
            len(seats) >= 3
            and not self.is_quan_dong
            and seats[0] % 2 == seats[2] % 2
        )
        # 反洞：台下队先出完（由 Room 判断，此处占位）
        self.winner_team: Optional[int] = None

    @property
    def first_seat(self) -> int:
        return self.finish_order[0]

    @property
    def last_seat(self) -> int:
        return self.finish_order[-1]


class Room:
    def __init__(self, room_id: str):
        self.id = room_id
        self.players: list[Player] = []
        self.game: Optional[Game] = None

        # 两队独立级别，初始都打3
        self.team_levels = {0: "3", 1: "3"}
        self.on_stage_team: Optional[int] = None   # 台上队伍（0或1）

        # 胜利状态追踪
        self.awaiting_final_3 = {0: False, 1: False}  # 打A全洞后回到3，等待最终3全洞

        # 历史局
        self.round_results: list[RoundResult] = []
        self.next_force_tribute = False   # 立棍/撅棍后下一局强制全洞进贡

        self.last_activity: float = time.time()

    def touch(self):
        self.last_activity = time.time()

    # ------------------------------------------------------------------
    # 玩家管理
    # ------------------------------------------------------------------

    def add_player(self, player: Player) -> bool:
        if len(self.players) >= 4:
            return False
        self.players.append(player)
        return True

    def is_full(self) -> bool:
        return len(self.players) == 4

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    # ------------------------------------------------------------------
    # 开局
    # ------------------------------------------------------------------

    def start_round(self, first_seat: int):
        """发牌，初始化单局 Game。"""
        level = self.team_levels[self.on_stage_team]
        deck = build_deck()
        hands = shuffle_and_deal(deck)
        for p in self.players:
            p.set_hand(hands[p.seat], level)
            p.finished = False
            p.finish_order = None
            p.locked = False

        self.game = Game(self.players, level)
        self.game.current_seat = first_seat
        self.game.state = GameState.PLAYING

    def start_first_round(self):
        """第一局：先发牌，找红桃3确定首家和台上队，再初始化 Game。"""
        deck = build_deck()
        hands = shuffle_and_deal(deck)
        for p in self.players:
            p.set_hand(hands[p.seat], "3")
            p.finished = False
            p.finish_order = None
            p.locked = False

        first_seat = self.find_red3_seat()
        self.on_stage_team = first_seat % 2

        self.game = Game(self.players, "3")
        self.game.current_seat = first_seat
        self.game.state = GameState.PLAYING
        return first_seat

    def find_red3_seat(self) -> int:
        """找持有红桃3的玩家座位。"""
        for p in self.players:
            for c in p.hand:
                if c.rank == "3" and c.suit.value == "heart":
                    return p.seat
        return 0

    # ------------------------------------------------------------------
    # 结算
    # ------------------------------------------------------------------

    def settle_round(self, finish_order: list[int]) -> dict:
        """根据出完顺序结算升级/切换台上台下，返回结算摘要。"""
        result = RoundResult(finish_order)
        winner_team = finish_order[0] % 2
        loser_team = 1 - winner_team
        result.winner_team = winner_team

        level = self.team_levels[self.on_stage_team]
        summary = {
            "is_quan_dong": result.is_quan_dong,
            "is_ban_dong": result.is_ban_dong,
            "winner_team": winner_team,
            "level_before": level,
        }

        if winner_team == self.on_stage_team:
            # 台上队赢
            steps = 0
            if result.is_quan_dong:
                steps = 2
            elif result.is_ban_dong:
                if level not in CHECKPOINTS:
                    steps = 1
                # 打3/J/A 时半洞不升级
            new_level = next_level(level, steps) if steps > 0 else level
            self.team_levels[self.on_stage_team] = new_level
            summary["level_after"] = new_level

            # 胜利检测
            game_over = self._check_game_over(self.on_stage_team, level, new_level)
            summary["game_over"] = game_over
            summary["game_winner"] = self.on_stage_team if game_over else None
        else:
            # 台下队赢 → 台上队下台，台下队上台（不升级）
            # 直J / 直A 惩罚
            if level == "J":
                self.team_levels[self.on_stage_team] = "3"
                summary["zhi_j"] = True
            elif level == "A":
                self.team_levels[self.on_stage_team] = "J"
                summary["zhi_a"] = True
            self.on_stage_team = winner_team
            summary["level_after"] = self.team_levels[self.on_stage_team]
            summary["game_over"] = False
            summary["new_on_stage"] = self.on_stage_team

        self.round_results.append(result)
        return summary

    def settle_ligun(self, li_gun_seat: int, finish_order: list[int]) -> dict:
        """立棍/撅棍结算。"""
        li_gun_team = li_gun_seat % 2
        opponent_team = 1 - li_gun_team
        level = self.team_levels[self.on_stage_team]
        success = finish_order[0] == li_gun_seat

        self.next_force_tribute = True
        summary = {"li_gun_success": success}

        if success:
            if li_gun_team == self.on_stage_team:
                new_level = next_level(level, 3)
                self.team_levels[self.on_stage_team] = new_level
                summary["level_after"] = new_level
                # level 是修改前的级别（正确的 level_before）
                game_over = self._check_game_over(self.on_stage_team, level, new_level)
                summary["game_over"] = game_over
            else:
                # 台下队立棍成功：上台+升2级
                level_before_ligun = self.team_levels[li_gun_team]
                new_level = next_level(level_before_ligun, 2)
                self.team_levels[li_gun_team] = new_level
                self.on_stage_team = li_gun_team
                summary["level_after"] = new_level
                game_over = self._check_game_over(li_gun_team, level_before_ligun, new_level)
                summary["game_over"] = game_over
        else:
            # 撅棍：对方上台+升2级
            level_before_opp = self.team_levels[opponent_team]
            new_level = next_level(level_before_opp, 2)
            self.team_levels[opponent_team] = new_level
            self.on_stage_team = opponent_team
            summary["level_after"] = new_level
            game_over = self._check_game_over(opponent_team, level_before_opp, new_level)
            summary["game_over"] = game_over

        return summary

    def _check_game_over(self, team: int, level_before: str, level_after: str) -> bool:
        """检查是否触发游戏结束。"""
        # 打A全洞 → 回到打3，标记等待最终打3
        if level_before == "A" and level_after == "3":
            self.awaiting_final_3[team] = True
            return False
        # 再次打3全洞获胜
        if level_before == "3" and level_after != "3" and self.awaiting_final_3[team]:
            return True
        return False

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "player_count": len(self.players),
            "players": [p.to_dict() for p in self.players],
            "on_stage_team": self.on_stage_team,
            "team_levels": self.team_levels,
            "game_state": self.game.state.name if self.game else None,
        }
