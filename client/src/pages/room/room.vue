<template>
  <view class="room">
    <view class="header">
      <text class="room-id">房间码：{{ store.roomId }}</text>
      <text class="hint">等待玩家加入...</text>
    </view>

    <view class="players">
      <view
        v-for="seat in [0, 1, 2, 3]"
        :key="seat"
        class="player-slot"
        :class="{ me: seat === store.mySeat, filled: getPlayer(seat) }"
      >
        <view class="seat-num">{{ seat + 1 }}号</view>
        <view class="player-name">
          {{ getPlayer(seat)?.name || "等待加入..." }}
        </view>
        <view class="team-tag" :class="'team' + (seat % 2)">
          {{ seat % 2 === 0 ? "A队" : "B队" }}
        </view>
        <view v-if="seat === store.mySeat" class="me-tag">我</view>
      </view>
    </view>

    <button
      v-if="isFull && store.mySeat === 0"
      class="btn start"
      @tap="startGame"
    >
      开始游戏
    </button>
    <view v-else-if="isFull" class="wait-start">等待1号玩家开始游戏</view>
    <view v-else class="wait-players">还需 {{ 4 - playerCount }} 人加入</view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import { useGameStore } from "../../store/game";
import { socket } from "../../utils/socket";

const store = useGameStore();

const players = computed(() => store.roomState?.players || []);
const playerCount = computed(() => players.value.length);
const isFull = computed(() => playerCount.value === 4);

function getPlayer(seat) {
  return players.value.find((p) => p.seat === seat);
}

function startGame() {
  socket.emit("start_game", {});
}

socket.on("game_started", () => {
  uni.redirectTo({ url: "/pages/game/game" });
});
</script>

<style scoped>
.room {
  min-height: 100vh;
  background: #1a1a2e;
  padding: 40rpx;
  color: #eee;
}
.header {
  text-align: center;
  margin-bottom: 60rpx;
}
.room-id {
  display: block;
  font-size: 48rpx;
  font-weight: bold;
  color: #e94560;
  letter-spacing: 8rpx;
}
.hint {
  font-size: 28rpx;
  color: #888;
  margin-top: 12rpx;
}
.players {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.player-slot {
  background: #16213e;
  border: 2rpx solid #0f3460;
  border-radius: 16rpx;
  padding: 30rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
  position: relative;
}
.player-slot.me { border-color: #e94560; }
.player-slot.filled { opacity: 1; }
.player-slot:not(.filled) { opacity: 0.5; }
.seat-num { font-size: 28rpx; color: #888; min-width: 60rpx; }
.player-name { flex: 1; font-size: 36rpx; }
.team-tag {
  font-size: 24rpx;
  padding: 6rpx 16rpx;
  border-radius: 8rpx;
}
.team0 { background: #1a4a8a; color: #7eb8ff; }
.team1 { background: #6b1a1a; color: #ff9999; }
.me-tag {
  position: absolute;
  top: 10rpx;
  right: 16rpx;
  font-size: 22rpx;
  color: #e94560;
}
.btn.start {
  margin-top: 60rpx;
  background: #e94560;
  color: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  font-size: 36rpx;
  width: 100%;
  border: none;
}
.wait-start, .wait-players {
  text-align: center;
  margin-top: 60rpx;
  color: #888;
  font-size: 30rpx;
}
</style>
