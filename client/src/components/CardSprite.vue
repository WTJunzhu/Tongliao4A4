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
  card:      { type: Object,  required: true },
  levelRank: { type: String,  default: "3" },
  selected:  { type: Boolean, default: false },
});
defineEmits(["tap"]);

const SUIT_ICON  = { spade:"♠", heart:"♥", club:"♣", diamond:"♦", joker:"🃏" };
const SUIT_CLASS = { spade:"black", heart:"red", club:"black", diamond:"red", joker:"joker-suit" };

const suitIcon  = computed(() => SUIT_ICON[props.card.suit]  || "");
const suitClass = computed(() => SUIT_CLASS[props.card.suit] || "");
const isLevel   = computed(() => props.card.rank === props.levelRank && props.card.suit !== "joker");
const isJoker   = computed(() => props.card.suit === "joker");
const displayRank = computed(() => {
  if (props.card.suit === "joker") return props.card.rank === "RJ" ? "大" : "小";
  return props.card.rank;
});
</script>

<style scoped>
.card {
  width: 48px;
  height: 68px;
  background: #fff;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 4px 3px;
  font-size: 14px;
  font-weight: bold;
  position: relative;
  box-shadow: 0 2px 5px rgba(0,0,0,.55);
  box-sizing: border-box;
  user-select: none;
  flex-shrink: 0;
  transition: transform 0.12s, box-shadow 0.12s;
}
.card.selected {
  transform: translateY(-20px);
  box-shadow: 0 10px 18px rgba(233,69,96,.65);
}
.card.red       { color: #c0392b; }
.card.black     { color: #1a1a2e; }
.card.joker-suit{ color: #6c3483; }
.card.level     { background: #fff8dc; border: 1px solid #f39c12; }
.suit-icon      { font-size: 18px; }
.rank           { font-size: 13px; line-height: 1; }
.rank.bottom    { transform: rotate(180deg); }
.level-mark {
  position: absolute;
  top: 2px; right: 3px;
  font-size: 11px;
  color: #f39c12;
}
</style>
