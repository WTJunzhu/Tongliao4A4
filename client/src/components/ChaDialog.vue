<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">叉！</view>
      <view class="desc">你有两张相同的牌可以叉，是否叉牌？</view>
      <view class="actions">
        <button class="btn no" @tap="$emit('respond', false)">不叉</button>
        <button class="btn yes" @tap="$emit('respond', true)">叉！</button>
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
.title { font-size: 48rpx; font-weight: bold; color: #e94560; margin-bottom: 20rpx; }
.desc { font-size: 30rpx; color: #aaa; margin-bottom: 40rpx; }
.actions { display: flex; gap: 24rpx; justify-content: center; }
.btn { flex: 1; border-radius: 12rpx; padding: 28rpx; font-size: 32rpx; border: none; }
.btn.yes { background: #e94560; color: #fff; }
.btn.no { background: #0f3460; color: #ccc; }
</style>
