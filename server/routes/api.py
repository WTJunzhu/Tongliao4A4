import random
import string
from flask import Blueprint, jsonify, request
from ..store import rooms, sessions, player_room, register_session

api_bp = Blueprint("api", __name__)


def _gen_room_id() -> str:
    """生成4位大写字母房间ID，避免与已有房间重复。"""
    for _ in range(100):
        rid = "".join(random.choices(string.ascii_uppercase, k=4))
        if rid not in rooms:
            return rid
    raise RuntimeError("无法生成唯一房间ID")


@api_bp.route("/rooms", methods=["GET"])
def list_rooms():
    return jsonify([r.to_dict() for r in rooms.values()])


@api_bp.route("/rooms", methods=["POST"])
def create_room():
    from ..models.room import Room
    room_id = _gen_room_id()
    room = Room(room_id)
    rooms[room_id] = room
    return jsonify({"room_id": room_id}), 201


@api_bp.route("/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    room = rooms.get(room_id.upper())
    if not room:
        return jsonify({"error": "not found"}), 404
    return jsonify(room.to_dict())


@api_bp.route("/reconnect", methods=["POST"])
def reconnect():
    """
    断线重连接口。客户端传 player_id，服务端返回该玩家的房间和座位信息。
    前端据此重新发起 WebSocket 连接，然后通过 WS 事件 reconnect_session 恢复会话。
    """
    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id", "")
    if not player_id:
        return jsonify({"error": "missing player_id"}), 400

    room_id = player_room.get(player_id)
    if not room_id:
        return jsonify({"error": "no session"}), 404

    room = rooms.get(room_id)
    if not room:
        player_room.pop(player_id, None)
        return jsonify({"error": "room gone"}), 404

    player = room.get_player_by_id(player_id)
    if not player:
        return jsonify({"error": "player not in room"}), 404

    return jsonify({
        "room_id": room_id,
        "seat": player.seat,
        "game_active": room.game is not None,
    })
