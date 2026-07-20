<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">点？</view>
      <view class="desc">对方叉了，你有相同的牌可以点，是否点牌？</view>
      <view class="actions">
        <button class="btn no" @tap="$emit('respond', false)">不点</button>
        <button class="btn yes" @tap="$emit('respond', true)">点！</button>
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
  width: 560rpx; text-align: center; color: #eee;
}
.title { font-size: 48rpx; font-weight: bold; color: #f39c12; margin-bottom: 20rpx; }
.desc { font-size: 30rpx; color: #aaa; margin-bottom: 40rpx; }
.actions { display: flex; gap: 24rpx; justify-content: center; }
.btn { flex: 1; border-radius: 12rpx; padding: 28rpx; font-size: 32rpx; border: none; }
.btn.yes { background: #f39c12; color: #fff; }
.btn.no { background: #0f3460; color: #ccc; }
</style>
