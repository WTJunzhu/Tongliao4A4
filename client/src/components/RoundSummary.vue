<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">本局结束</view>

      <view class="row">
        <text class="label">胜者：</text>
        <text class="value" :class="'team' + summary.winner_team">
          {{ summary.winner_team === 0 ? "A队" : "B队" }}
        </text>
      </view>

      <view v-if="summary.level_after" class="row">
        <text class="label">升级：</text>
        <text class="value">{{ summary.level_before }} → {{ summary.level_after }}</text>
      </view>

      <view v-if="summary.is_quan_dong" class="tag quan">全洞</view>
      <view v-if="summary.is_ban_dong" class="tag ban">半洞</view>
      <view v-if="summary.zhi_j" class="tag penalty">直J惩罚</view>
      <view v-if="summary.zhi_a" class="tag penalty">直A惩罚</view>
      <view v-if="summary.li_gun_success !== undefined" class="tag" :class="summary.li_gun_success ? 'ligun-ok' : 'ligun-fail'">
        {{ summary.li_gun_success ? "立棍成功" : "撅棍" }}
      </view>

      <button class="btn close" @tap="$emit('close')">继续</button>
    </view>
  </view>
</template>

<script setup>
defineProps({ summary: { type: Object, required: true } });
defineEmits(["close"]);
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.8);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.dialog {
  background: #16213e; border-radius: 20rpx; padding: 60rpx 48rpx;
  width: 600rpx; text-align: center; color: #eee;
}
.title { font-size: 48rpx; font-weight: bold; margin-bottom: 40rpx; }
.row { display: flex; justify-content: center; gap: 16rpx; margin-bottom: 20rpx; font-size: 32rpx; }
.label { color: #888; }
.value { font-weight: bold; }
.value.team0 { color: #7eb8ff; }
.value.team1 { color: #ff9999; }
.tag {
  display: inline-block; padding: 8rpx 24rpx; border-radius: 8rpx;
  font-size: 26rpx; margin: 8rpx;
}
.quan { background: #1a4a8a; color: #7eb8ff; }
.ban { background: #1a3a1a; color: #7dff7d; }
.penalty { background: #5a1a1a; color: #ff9999; }
.ligun-ok { background: #1a5a2a; color: #7dff7d; }
.ligun-fail { background: #5a3a1a; color: #ffb870; }
.btn.close {
  margin-top: 40rpx; background: #0f3460; color: #eee;
  border: none; border-radius: 12rpx; padding: 28rpx; font-size: 32rpx; width: 100%;
}
</style>
