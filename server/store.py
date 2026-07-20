# 全局内存存储（单进程，开发阶段用）
import threading
import time
from typing import Optional

rooms: dict = {}     # room_id -> Room
sessions: dict = {}  # player_id -> socket sid

# 断线重连：player_id -> room_id
player_room: dict = {}

_cleanup_lock = threading.Lock()
ROOM_IDLE_SECONDS = 3600  # 1小时无活动的房间自动清理


def register_session(player_id: str, sid: str, room_id: str):
    sessions[player_id] = sid
    player_room[player_id] = room_id


def remove_session(sid: str) -> Optional[str]:
    """sid 断线时清理 sessions，返回对应 player_id。"""
    player_id = _sid_to_player_id(sid)
    if player_id:
        sessions.pop(player_id, None)
    return player_id


def _sid_to_player_id(sid: str) -> Optional[str]:
    for pid, s in sessions.items():
        if s == sid:
            return pid
    return None


def cleanup_idle_rooms():
    """清理超时无活动的房间。"""
    now = time.time()
    with _cleanup_lock:
        to_delete = []
        for room_id, room in rooms.items():
            last = getattr(room, "last_activity", now)
            if now - last > ROOM_IDLE_SECONDS:
                to_delete.append(room_id)
        for room_id in to_delete:
            room = rooms.pop(room_id)
            for p in room.players:
                player_room.pop(p.id, None)
                sessions.pop(p.id, None)


def start_cleanup_thread():
    """启动后台清理线程（应用启动时调用一次）。"""
    def _loop():
        while True:
            time.sleep(300)
            try:
                cleanup_idle_rooms()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
