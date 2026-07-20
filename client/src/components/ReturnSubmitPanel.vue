<template>
  <view class="dialog-mask">
    <view class="dialog">
      <view class="title">选择还贡牌</view>
      <view class="desc">从手牌中选一张还给对方（不能选A或4）</view>

      <view class="hand">
        <view
          v-for="(card, i) in validHand"
          :key="i"
          class="card-wrap"
          :class="{ selected: selectedIdx === i }"
          @tap="selectedIdx = i"
        >
          <CardSprite :card="card.card" :level-rank="levelRank" :selected="selectedIdx === i" />
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

// 过滤出合法牌（不含A/4）并保留原始 index
const validHand = computed(() =>
  props.myHand
    .map((card, i) => ({ card, i }))
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
  background: #16213e; border-radius: 20rpx; padding: 48rpx 40rpx;
  width: 680rpx; text-align: center; color: #eee;
}
.title { font-size: 40rpx; font-weight: bold; color: #3498db; margin-bottom: 12rpx; }
.desc { font-size: 26rpx; color: #aaa; margin-bottom: 32rpx; }
.hand {
  display: flex; flex-wrap: wrap; gap: 12rpx;
  justify-content: center; margin-bottom: 40rpx;
}
.card-wrap { border-radius: 8rpx; }
.btn.submit {
  background: #3498db; color: #fff; border: none;
  border-radius: 12rpx; padding: 28rpx; font-size: 32rpx; width: 100%;
}
.btn.submit[disabled] { background: #555; color: #999; }
</style>
