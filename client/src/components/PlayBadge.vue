<template>
  <view class="pb" :class="{ compact }">
    <view v-if="action?.type === 'pass'" class="pb-pass">不要</view>
    <view v-else-if="action?.type === 'played' && action.cards?.length" class="pb-cards">
      <view
        v-for="(card, i) in action.cards"
        :key="i"
        class="mc"
        :class="[mcClass(card), { 'mc-lv': card.rank === levelRank && card.suit !== 'joker' }]"
      >
        <text class="mc-r">{{ mcRank(card) }}</text>
        <text class="mc-s">{{ mcSuit(card) }}</text>
      </view>
    </view>
    <view v-else class="pb-empty" />
  </view>
</template>

<script setup>
const SUIT_ICON  = { spade: '♠', heart: '♥', club: '♣', diamond: '♦', joker: '🃏' };
const SUIT_CLASS = { spade: 'black', heart: 'red', club: 'black', diamond: 'red', joker: 'joker' };

const props = defineProps({
  action:    { type: Object, default: null },
  levelRank: { type: String, default: '3' },
  compact:   { type: Boolean, default: false },
});

function mcClass(c) { return SUIT_CLASS[c.suit] || ''; }
function mcSuit(c)  { return SUIT_ICON[c.suit] || ''; }
function mcRank(c) {
  if (c.suit === 'joker') return c.rank === 'RJ' ? '大' : '小';
  return c.rank;
}
</script>

<style scoped>
.pb {
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pb-pass {
  background: rgba(255,255,255,0.1);
  color: #888;
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
}
.pb-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  justify-content: center;
  max-width: 200px;
}
.pb-empty { min-height: 34px; }

/* mini card */
.mc {
  width: 30px;
  height: 42px;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-around;
  padding: 2px 1px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.5);
  box-sizing: border-box;
}
.pb.compact .mc { width: 22px; height: 30px; }

.mc.red   { color: #c0392b; }
.mc.black { color: #1a1a2e; }
.mc.joker { color: #6c3483; }
.mc.mc-lv { background: #fff8dc; outline: 1px solid #f39c12; }

.mc-r { font-size: 10px; font-weight: bold; line-height: 1; }
.mc-s { font-size: 11px; line-height: 1; }
.pb.compact .mc-r { font-size: 8px; }
.pb.compact .mc-s { font-size: 9px; }
</style>
