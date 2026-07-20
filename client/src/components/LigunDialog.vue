<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">立棍？</view>
      <view class="desc">
        你要立棍吗？立棍后你必须第一名完成，否则对手升2级。
      </view>
      <view class="actions">
        <button class="btn no" @tap="$emit('respond', false)">不立</button>
        <button class="btn yes" @tap="$emit('respond', true)">立棍！</button>
      </view>
    </view>
  </view>
</template>

<script setup>
defineEmits(["respond"]);
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.dialog {
  background: #16213e; border-radius: 20rpx; padding: 48rpx 40rpx;
  width: 580rpx; text-align: center; color: #eee;
}
.title { font-size: 48rpx; font-weight: bold; color: #8e44ad; margin-bottom: 20rpx; }
.desc { font-size: 28rpx; color: #aaa; margin-bottom: 40rpx; line-height: 1.6; }
.actions { display: flex; gap: 24rpx; justify-content: center; }
.btn { flex: 1; border-radius: 12rpx; padding: 28rpx; font-size: 32rpx; border: none; }
.btn.yes { background: #8e44ad; color: #fff; }
.btn.no { background: #0f3460; color: #ccc; }
</style>
