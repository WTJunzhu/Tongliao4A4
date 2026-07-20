<template>
  <view class="opp-bar" :class="position">
    <view class="name">{{ player?.name || "—" }}</view>
    <view class="cards">
      <view
        v-for="i in (player?.hand_count || 0)"
        :key="i"
        class="card-back"
      />
    </view>
    <view v-if="player?.finished" class="finished-tag">完</view>
  </view>
</template>

<script setup>
defineProps({
  player: { type: Object, default: null },
  position: { type: String, default: "top" }, // top | left | right
});
</script>

<style scoped>
.opp-bar {
  display: flex;
  align-items: center;
  gap: 12rpx;
  color: #ccc;
  font-size: 26rpx;
  position: relative;
}
.opp-bar.top {
  flex-direction: column;
  padding: 8rpx 0;
  min-height: 80rpx;
}
.opp-bar.left, .opp-bar.right {
  flex-direction: column;
  justify-content: center;
  min-width: 80rpx;
  font-size: 22rpx;
}
.cards { display: flex; flex-wrap: wrap; gap: 4rpx; justify-content: center; }
.card-back {
  width: 28rpx;
  height: 40rpx;
  background: #0f3460;
  border-radius: 4rpx;
  border: 1rpx solid #1a5276;
}
.finished-tag {
  background: #27ae60;
  color: #fff;
  font-size: 20rpx;
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
}
</style>
