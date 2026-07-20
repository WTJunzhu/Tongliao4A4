"""
pytest 配置与共用 fixtures。
"""
import sys
import os
import pytest

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import create_app
from server.store import rooms, sessions, player_room


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture(autouse=True)
def clear_store():
    """每个测试前后清空全局存储，避免状态污染。"""
    rooms.clear()
    sessions.clear()
    player_room.clear()
    yield
    rooms.clear()
    sessions.clear()
    player_room.clear()


# ------------------------------------------------------------------
# 游戏模型快捷构建
# ------------------------------------------------------------------

from server.models.room import Room
from server.models.player import Player
from server.models.card import Card, Suit
from server.models.deck import build_deck, shuffle_and_deal


def make_room(room_id="TEST") -> Room:
    room = Room(room_id)
    for i in range(4):
        room.add_player(Player(f"p{i}", f"P{i}", i))
    return room


def make_started_room(room_id="TEST") -> Room:
    """返回已经过 start_first_round 的房间（处于 PLAYING 状态）。"""
    room = make_room(room_id)
    room.start_first_round()
    return room


def force_hands(game, hands: dict):
    """
    强制设置各座位手牌。
    hands: {seat: [Card, ...]}
    """
    for seat, cards in hands.items():
        game.players[seat].hand = list(cards)
