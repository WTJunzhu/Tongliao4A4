<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">选择还贡牌</view>
      <view class="desc">从手牌中选一张还给对方（不能选A或4）</view>

      <view class="hand">
        <view
          v-for="(item, i) in validHand"
          :key="i"
          class="card-wrap"
          :class="{ selected: selectedIdx === i }"
          @tap="selectedIdx = i"
        >
          <CardSprite :card="item.card" :level-rank="levelRank" :selected="selectedIdx === i" />
          <text v-if="item.tributeLabel" class="tribute-label">{{ item.tributeLabel }}</text>
        </view>
      </view>

      <button
        class="btn submit"
        :disabled="selectedIdx === null"
        @tap="submit"
      >
        提交还贡
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from "vue";
import { useGameStore } from "../store/game";
import CardSprite from "./CardSprite.vue";

const props = defineProps({ myHand: { type: Array, default: () => [] } });
const emit = defineEmits(["submit"]);

const store = useGameStore();
const levelRank = computed(() => store.gameState?.level_rank || "3");
const selectedIdx = ref(null);
const mySeat = computed(() => store.mySeat);

// 进贡信息：找出哪张牌是别人进贡给我的
const tributeInfo = computed(() => store.tributeInfo?.tribute_info || {});
const tributeCard = computed(() => {
  // 找进贡给我（receiver_seat === mySeat）的那条记录
  for (const [giverSeat, info] of Object.entries(tributeInfo.value)) {
    if (info.receiver_seat === mySeat.value) {
      return { giverSeat: Number(giverSeat), card: info.card };
    }
  }
  return null;
});

function getPlayerName(seat) {
  const p = store.gameState?.players?.find(pl => pl.seat === seat);
  return p?.name || `${seat + 1}号`;
}

// 过滤合法牌，标注进贡来源
const validHand = computed(() =>
  props.myHand
    .map((card, i) => {
      let tributeLabel = null;
      const tc = tributeCard.value;
      if (tc && card.rank === tc.card.rank && card.suit === tc.card.suit) {
        tributeLabel = `${getPlayerName(tc.giverSeat)}进贡`;
      }
      return { card, i, tributeLabel };
    })
    .filter(({ card }) => card.rank !== "A" && card.rank !== "4")
);

function submit() {
  if (selectedIdx.value === null) return;
  const originalIdx = validHand.value[selectedIdx.value].i;
  emit("submit", originalIdx);
  selectedIdx.value = null;
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
.title { font-size: 18px; font-weight: bold; color: #3498db; margin-bottom: 6px; }
.desc { font-size: 13px; color: #aaa; margin-bottom: 20px; }
.hand {
  display: flex; flex-wrap: wrap; gap: 10px;
  justify-content: center; margin-bottom: 24px;
}
.card-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  border-radius: 8px; padding: 6px;
  border: 2px solid transparent; transition: border-color .15s;
}
.card-wrap.selected { border-color: #e94560; background: rgba(233,69,96,0.1); }
.tribute-label {
  font-size: 10px; color: #f39c12;
  background: rgba(243,156,18,0.15);
  padding: 1px 6px; border-radius: 6px;
}
.btn.submit {
  background: #3498db; color: #fff; border: none;
  border-radius: 10px; padding: 12px; font-size: 16px; width: 100%;
}
.btn.submit[disabled] { background: #555; color: #999; }
</style>
