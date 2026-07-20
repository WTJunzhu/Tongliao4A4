<template>
  <view
    class="card"
    :class="[suitClass, { selected, level: isLevel, joker: isJoker }]"
    @tap="$emit('tap')"
  >
    <view class="rank top">{{ displayRank }}</view>
    <view class="suit-icon">{{ suitIcon }}</view>
    <view class="rank bottom">{{ displayRank }}</view>
    <view v-if="isLevel" class="level-mark">级</view>
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  card: { type: Object, required: true },
  levelRank: { type: String, default: "3" },
  selected: { type: Boolean, default: false },
});
defineEmits(["tap"]);

const SUIT_ICON = { spade: "♠", heart: "♥", club: "♣", diamond: "♦", joker: "🃏" };
const SUIT_CLASS = { spade: "black", heart: "red", club: "black", diamond: "red", joker: "joker-suit" };

const suitIcon = computed(() => SUIT_ICON[props.card.suit] || "");
const suitClass = computed(() => SUIT_CLASS[props.card.suit] || "");
const isLevel = computed(() => props.card.rank === props.levelRank && props.card.suit !== "joker");
const isJoker = computed(() => props.card.suit === "joker");

const displayRank = computed(() => {
  if (props.card.suit === "joker") return props.card.rank === "RJ" ? "大" : "小";
  return props.card.rank;
});
</script>

<style scoped>
.card {
  width: 72rpx;
  height: 100rpx;
  background: #fff;
  border-radius: 8rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 6rpx 4rpx;
  font-size: 26rpx;
  font-weight: bold;
  position: relative;
  box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.4);
  transition: transform 0.15s;
  box-sizing: border-box;
  user-select: none;
}
.card.selected { transform: translateY(-16rpx); box-shadow: 0 8rpx 16rpx rgba(233,69,96,0.5); }
.card.red { color: #c0392b; }
.card.black { color: #1a1a2e; }
.card.joker-suit { color: #6c3483; }
.card.level { background: #fff8dc; border: 2rpx solid #f39c12; }
.suit-icon { font-size: 30rpx; }
.rank.bottom { transform: rotate(180deg); }
.level-mark {
  position: absolute;
  top: 2rpx;
  right: 4rpx;
  font-size: 18rpx;
  color: #f39c12;
}
</style>
