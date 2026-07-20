<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="trophy">🏆</view>
      <view class="title">游戏结束</view>
      <view class="winner" :class="'team' + winnerTeam">
        {{ winnerTeam === 0 ? "A队" : "B队" }} 获胜！
      </view>
      <button class="btn back" @tap="$emit('back')">返回大厅</button>
    </view>
  </view>
</template>

<script setup>
defineProps({ winnerTeam: { type: Number, required: true } });
defineEmits(["back"]);
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.85);
  display: flex; align-items: center; justify-content: center; z-index: 300;
}
.dialog {
  background: #16213e; border-radius: 24rpx; padding: 80rpx 60rpx;
  width: 600rpx; text-align: center; color: #eee;
}
.trophy { font-size: 120rpx; margin-bottom: 20rpx; }
.title { font-size: 52rpx; font-weight: bold; margin-bottom: 24rpx; }
.winner { font-size: 44rpx; font-weight: bold; margin-bottom: 60rpx; }
.winner.team0 { color: #7eb8ff; }
.winner.team1 { color: #ff9999; }
.btn.back {
  background: #e94560; color: #fff; border: none;
  border-radius: 16rpx; padding: 32rpx; font-size: 36rpx; width: 100%;
}
</style>
