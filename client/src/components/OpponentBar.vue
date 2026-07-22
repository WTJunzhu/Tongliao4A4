<template>
  <view class="opp-bar" :class="[position, { active: player?.seat === currentSeat, finished: player?.finished }]">
    <view class="name-row">
      <text class="name">{{ player?.name || "—" }}</text>
      <text v-if="player?.finished" class="finished-tag">完</text>
    </view>
    <view class="hand-stack">
      <view class="card-fan">
        <view
          v-for="i in Math.min(handCount, 5)"
          :key="i"
          class="card-back"
          :style="fanStyle(i - 1, Math.min(handCount, 5))"
        />
      </view>
      <view v-if="handCount > 0" class="count-badge">{{ handCount }}</view>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  player:      { type: Object, default: null },
  position:    { type: String, default: "top" },
  currentSeat: { type: Number, default: -1 },
});

const handCount = computed(() => props.player?.hand_count || 0);

function fanStyle(i, total) {
  const spread = 7;
  const offset = total <= 1 ? 0 : (i - (total - 1) / 2) * spread;
  if (props.position === "top") return { transform: `translateX(${offset}px)`, zIndex: i };
  return { transform: `translateY(${offset}px)`, zIndex: i };
}
</script>

<style scoped>
.opp-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #ccc;
  font-size: 12px;
  position: relative;
  padding: 4px 6px;
  border-radius: 8px;
  transition: background 0.2s;
}
.opp-bar.active {
  background: rgba(233, 69, 96, 0.15);
  outline: 1px solid rgba(233, 69, 96, 0.5);
}
.opp-bar.finished { opacity: 0.6; }
.opp-bar.left, .opp-bar.right {
  justify-content: center;
  min-width: 56px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.name {
  font-size: 11px;
  color: #ccc;
  max-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.finished-tag {
  background: #27ae60;
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
}

.hand-stack {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-fan {
  position: relative;
  width: 36px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-back {
  position: absolute;
  width: 22px;
  height: 32px;
  background: linear-gradient(135deg, #1a3a6a 0%, #0f3460 60%, #0a2444 100%);
  border-radius: 3px;
  border: 1px solid #2a5aaa;
  box-shadow: 0 1px 3px rgba(0,0,0,0.5);
}
.count-badge {
  position: absolute;
  right: -14px;
  top: 50%;
  transform: translateY(-50%);
  background: #e94560;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
}
</style>
