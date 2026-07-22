<template>
  <view v-if="show" class="fly-card" :style="flyStyle">
    <CardSprite :card="card" :level-rank="levelRank" :selected="false" />
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import CardSprite from "./CardSprite.vue";

const props = defineProps({
  card: { type: Object, required: true },
  fromRect: { type: Object, required: true }, // DOMRect or {left, top, width, height}
  toRect: { type: Object, required: true },
  levelRank: { type: String, default: "3" },
});
const emit = defineEmits(["done"]);

const show = ref(true);
const arrived = ref(false);

const CARD_W = 48;
const CARD_H = 68;

const cx = (r) => r.left + r.width / 2;
const cy = (r) => r.top + r.height / 2;

const flyStyle = computed(() => {
  const x = (arrived.value ? cx(props.toRect) : cx(props.fromRect)) - CARD_W / 2;
  const y = (arrived.value ? cy(props.toRect) : cy(props.fromRect)) - CARD_H / 2;
  return {
    left: x + "px",
    top: y + "px",
    transition: arrived.value
      ? "left 0.65s cubic-bezier(0.4,0,0.2,1), top 0.65s cubic-bezier(0.4,0,0.2,1), opacity 0.15s ease 0.55s"
      : "none",
    opacity: arrived.value ? "0.95" : "1",
  };
});

onMounted(() => {
  // 双帧触发：保证初始位置先渲染，再开始 transition
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      arrived.value = true;
      setTimeout(() => {
        show.value = false;
        emit("done");
      }, 800);
    });
  });
});
</script>

<style scoped>
.fly-card {
  position: fixed;
  pointer-events: none;
  z-index: 300;
}
</style>
