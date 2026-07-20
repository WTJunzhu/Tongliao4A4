<template>
  <view class="lobby">
    <view class="title">通辽4A4</view>

    <view class="form">
      <input
        v-model="name"
        class="input"
        placeholder="输入昵称"
        maxlength="8"
      />

      <button class="btn primary" @tap="createRoom">创建房间</button>

      <view class="divider">或</view>

      <input
        v-model="joinCode"
        class="input code"
        placeholder="输入4位房间码"
        maxlength="4"
        :style="{ textTransform: 'uppercase' }"
      />
      <button class="btn" @tap="joinRoom">加入房间</button>
    </view>

    <view v-if="error" class="error">{{ error }}</view>
  </view>
</template>

<script setup>
import { ref } from "vue";
import { useGameStore } from "../../store/game";
import { socket } from "../../utils/socket";

const store = useGameStore();
const name = ref("");
const joinCode = ref("");
const error = ref("");

async function createRoom() {
  if (!name.value.trim()) { error.value = "请输入昵称"; return; }
  error.value = "";
  try {
    const res = await uni.request({ url: "/api/rooms", method: "POST" });
    const roomId = res.data.room_id;
    await _connect(roomId);
  } catch (e) {
    error.value = "创建失败，请重试";
  }
}

async function joinRoom() {
  if (!name.value.trim()) { error.value = "请输入昵称"; return; }
  const code = joinCode.value.trim().toUpperCase();
  if (code.length !== 4) { error.value = "请输入4位房间码"; return; }
  error.value = "";
  await _connect(code);
}

async function _connect(roomId) {
  socket.connect();
  store.initListeners();

  socket.on("error", (data) => { error.value = data.msg; });
  socket.on("joined", (data) => {
    store.savePlayerId(data.player_id);
    store.roomId = data.room_id;
    store.mySeat = data.seat;
    uni.navigateTo({ url: `/pages/room/room` });
  });

  socket.emit("join_room", { room_id: roomId, name: name.value.trim() });
}
</script>

<style scoped>
.lobby {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 40rpx;
  background: #1a1a2e;
  color: #eee;
}
.title {
  font-size: 72rpx;
  font-weight: bold;
  color: #e94560;
  margin-bottom: 80rpx;
  letter-spacing: 4rpx;
}
.form {
  width: 100%;
  max-width: 600rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
.input {
  background: #16213e;
  border: 2rpx solid #0f3460;
  border-radius: 12rpx;
  padding: 24rpx 32rpx;
  color: #eee;
  font-size: 32rpx;
}
.input.code { letter-spacing: 8rpx; text-align: center; }
.btn {
  background: #0f3460;
  color: #eee;
  border-radius: 12rpx;
  padding: 28rpx;
  font-size: 32rpx;
  text-align: center;
  border: none;
}
.btn.primary { background: #e94560; color: #fff; }
.divider {
  text-align: center;
  color: #666;
  font-size: 28rpx;
}
.error {
  color: #e94560;
  font-size: 28rpx;
  margin-top: 24rpx;
}
</style>
