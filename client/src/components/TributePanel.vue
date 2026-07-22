<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">{{ title }}</view>

      <!-- 牌池 -->
      <view class="card-pool">
        <view
          v-for="(card, giverSeat) in poolCards"
          :key="giverSeat"
          class="pool-slot"
          :class="{
            'selected-by-me': mySelection == giverSeat,
            'selected-by-other': otherSelection == giverSeat && mySelection != giverSeat,
            'contested': isContested(giverSeat),
          }"
          @tap="selectCard(Number(giverSeat))"
        >
          <CardSprite :card="card" :level-rank="levelRank" />
          <text class="giver-label">{{ playerName(Number(giverSeat)) }}进贡</text>
          <view class="selector-label">
            <text v-if="mySelection == giverSeat" class="label me">我选</text>
            <text v-else-if="otherSelection == giverSeat" class="label other">Ta选</text>
          </view>
        </view>
      </view>

      <!-- 交换请求提示 -->
      <view v-if="swapRequest" class="swap-notice">
        <text>对方想换你选的牌，是否同意？</text>
        <view class="swap-actions">
          <button class="btn no-swap" @tap="respondSwap(false)">不同意</button>
          <button class="btn yes-swap" @tap="respondSwap(true)">同意换</button>
        </view>
      </view>

      <!-- 确认按钮：仅当 can_confirm 且无待处理换牌请求 -->
      <button
        v-if="!swapRequest"
        class="btn confirm"
        :disabled="!sel?.can_confirm || alreadyConfirmed"
        @tap="confirm"
      >
        {{ alreadyConfirmed ? "等待对方确认..." : "确认" }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed } from "vue";
import { useGameStore } from "../store/game";
import { socket } from "../utils/socket";
import CardSprite from "./CardSprite.vue";

const store = useGameStore();

const sel = computed(() => store.selectionState);
const levelRank = computed(() => store.gameState?.level_rank || "3");
const phase = computed(() => store.tributePhase);

const title = computed(() =>
  phase.value === "tribute_select" ? "进贡选牌" : "还贡选牌"
);

const poolCards = computed(() => sel.value?.cards || {});

// 玩家名称（用于进贡标签）
function playerName(seat) {
  const p = store.gameState?.players?.find(pl => pl.seat === seat);
  return p?.name || `${seat + 1}号`;
}

// 我的预选（giver_seat）
const mySelection = computed(() => {
  const s = sel.value?.selections;
  if (!s) return null;
  const myKey = String(store.mySeat);
  return s[myKey] ?? null;
});

// 另一名选择器的预选
const otherSelection = computed(() => {
  const s = sel.value?.selections;
  if (!s) return null;
  const myKey = String(store.mySeat);
  for (const [k, v] of Object.entries(s)) {
    if (k !== myKey) return v;
  }
  return null;
});

function isContested(giverSeat) {
  const swap = sel.value?.pending_swap;
  if (!swap) return false;
  const s = sel.value?.selections;
  const targetKey = String(swap.target_seat);
  return s && s[targetKey] == giverSeat;
}

// 是否有针对我的交换请求（我是 target）
const swapRequest = computed(() => {
  const swap = sel.value?.pending_swap;
  if (!swap) return null;
  return swap.target_seat === store.mySeat ? swap : null;
});

const alreadyConfirmed = computed(() =>
  sel.value?.confirmations?.includes(store.mySeat)
);

function selectCard(giverSeat) {
  socket.emit("tribute_select", { giver_seat: giverSeat });
}

function respondSwap(accept) {
  socket.emit("tribute_swap_respond", { accept });
}

function confirm() {
  socket.emit("tribute_confirm", {});
}
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.75);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.dialog {
  background: #16213e; border-radius: 14px; padding: 28px 24px;
  width: min(480px, 92vw); text-align: center; color: #eee;
}
.title {
  font-size: 18px; font-weight: bold; margin-bottom: 20px; color: #f39c12;
}
.card-pool {
  display: flex; gap: 20px; justify-content: center; margin-bottom: 20px;
}
.pool-slot {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 10px; border-radius: 10px; border: 2px solid transparent;
  transition: all 0.2s;
}
.pool-slot.selected-by-me { border-color: #e94560; background: rgba(233,69,96,0.1); }
.pool-slot.selected-by-other { border-color: #3498db; background: rgba(52,152,219,0.1); }
.pool-slot.contested { border-color: #f39c12; background: rgba(243,156,18,0.1); }
.giver-label {
  font-size: 11px; color: #f39c12;
  background: rgba(243,156,18,0.15);
  padding: 2px 8px; border-radius: 6px;
}
.selector-label { min-height: 22px; }
.label { font-size: 12px; padding: 2px 8px; border-radius: 6px; }
.label.me { background: #e94560; color: #fff; }
.label.other { background: #3498db; color: #fff; }
.swap-notice {
  background: #0f3460; border-radius: 10px; padding: 16px;
  margin-bottom: 16px; font-size: 14px; color: #f39c12;
}
.swap-actions { display: flex; gap: 12px; margin-top: 12px; justify-content: center; }
.btn {
  border-radius: 10px; padding: 12px 20px; font-size: 15px; border: none;
}
.btn.confirm { background: #e94560; color: #fff; width: 100%; padding: 14px; font-size: 16px; }
.btn.confirm[disabled] { background: #555; color: #999; }
.btn.yes-swap { background: #27ae60; color: #fff; }
.btn.no-swap { background: #0f3460; color: #ccc; }
</style>
