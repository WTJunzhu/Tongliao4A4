<template>
  <view class="fsd-overlay">
    <view class="fsd-box">
      <text class="fsd-title">选择先手</text>
      <text class="fsd-hint">你可以点击"我先出"，或等待队友选择</text>
      <button class="fsd-btn" @tap="$emit('respond')">我先出</button>
    </view>
  </view>
</template>

<script setup>
defineEmits(["respond"]);
</script>

<style scoped>
.fsd-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.fsd-box {
  background: #16213e;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px;
  padding: 28px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  min-width: 260px;
}
.fsd-title { font-size: 18px; font-weight: bold; color: #eee; }
.fsd-hint  { font-size: 13px; color: #888; text-align: center; }
.fsd-btn {
  background: #e94560;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 40px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 4px;
}
</style>
