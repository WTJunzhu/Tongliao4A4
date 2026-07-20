<template>
  <view class="game">
    <!-- 对家（座位+2） -->
    <OpponentBar :player="opponent" position="top" />

    <!-- 中间区域：左对手 + 桌面 + 右对手 -->
    <view class="middle">
      <OpponentBar :player="leftOpp" position="left" />

      <view class="table-area">
        <view class="table-cards">
          <CardSprite
            v-for="(card, i) in tableCards"
            :key="i"
            :card="card"
            :level-rank="levelRank"
          />
          <view v-if="!tableCards.length" class="table-empty">—</view>
        </view>
        <view class="current-hint">
          {{ currentHint }}
        </view>
      </view>

      <OpponentBar :player="rightOpp" position="right" />
    </view>

    <!-- 我的手牌 -->
    <view class="my-hand">
      <CardSprite
        v-for="(card, i) in myHand"
        :key="i"
        :card="card"
        :level-rank="levelRank"
        :selected="selectedIndices.includes(i)"
        @tap="toggleSelect(i)"
      />
    </view>

    <!-- 操作按钮 -->
    <view class="actions" v-if="isMyTurn && gamePhase === 'PLAYING'">
      <button class="btn play" @tap="playCards" :disabled="!selectedIndices.length">出牌</button>
      <button class="btn pass" @tap="pass" :disabled="!canPass">不要</button>
    </view>

    <!-- 叉询问 -->
    <ChaDialog
      v-if="gamePhase === 'CHA_ASKING' && gs?.asking_seat === store.mySeat"
      @respond="respondCha"
    />

    <!-- 点询问 -->
    <DianDialog
      v-if="gamePhase === 'DIAN_ASKING' && gs?.asking_seat === store.mySeat"
      @respond="respondDian"
    />

    <!-- 立棍弹窗 -->
    <LigunDialog
      v-if="store.ligunAskSeat === store.mySeat"
      @respond="respondLigun"
    />

    <!-- 进贡/还贡选牌 -->
    <TributePanel
      v-if="store.tributePhase === 'tribute_select' || store.tributePhase === 'return_select'"
    />

    <!-- 还贡提交 -->
    <ReturnSubmitPanel
      v-if="store.tributePhase === 'return_submit'"
      :my-hand="myHand"
      @submit="submitReturn"
    />

    <!-- 局结算 -->
    <RoundSummary
      v-if="store.roundSummary && !store.roundSummary.game_over"
      :summary="store.roundSummary"
      @close="store.roundSummary = null"
    />

    <!-- 游戏结束 -->
    <GameOver
      v-if="store.roundSummary?.game_over"
      :winner-team="store.roundSummary.winner_team"
      @back="goLobby"
    />
  </view>
</template>

<script setup>
import { computed } from "vue";
import { useGameStore } from "../../store/game";
import { socket } from "../../utils/socket";
import CardSprite from "../../components/CardSprite.vue";
import OpponentBar from "../../components/OpponentBar.vue";
import ChaDialog from "../../components/ChaDialog.vue";
import DianDialog from "../../components/DianDialog.vue";
import LigunDialog from "../../components/LigunDialog.vue";
import TributePanel from "../../components/TributePanel.vue";
import ReturnSubmitPanel from "../../components/ReturnSubmitPanel.vue";
import RoundSummary from "../../components/RoundSummary.vue";
import GameOver from "../../components/GameOver.vue";
import { ref } from "vue";

const store = useGameStore();
const gs = computed(() => store.gameState);
const selectedIndices = ref([]);

const levelRank = computed(() => gs.value?.level_rank || "3");
const gamePhase = computed(() => gs.value?.state || "");
const tableCards = computed(() => gs.value?.table || []);
const myHand = computed(() => store.myPlayer?.hand || []);
const isMyTurn = computed(() => store.isMyTurn);
const canPass = computed(() => gs.value?.last_play_seat != null);

// 4 个方位的对手（按座位相对位置排布）
const seat = computed(() => store.mySeat);
const players = computed(() => gs.value?.players || []);

function playerAt(relSeat) {
  const s = (seat.value + relSeat) % 4;
  return players.value.find((p) => p.seat === s);
}
const opponent  = computed(() => playerAt(2)); // 对面
const leftOpp   = computed(() => playerAt(3)); // 左手边
const rightOpp  = computed(() => playerAt(1)); // 右手边

const currentHint = computed(() => {
  const cur = gs.value?.current_seat;
  if (cur == null) return "";
  if (cur === seat.value) return "轮到你出牌";
  const p = players.value.find((x) => x.seat === cur);
  return `等待 ${p?.name || cur + "号"} 出牌`;
});

function toggleSelect(i) {
  if (!isMyTurn.value) return;
  const idx = selectedIndices.value.indexOf(i);
  if (idx === -1) selectedIndices.value.push(i);
  else selectedIndices.value.splice(idx, 1);
}

function playCards() {
  socket.emit("play_cards", { card_indices: selectedIndices.value });
  selectedIndices.value = [];
}

function pass() {
  socket.emit("pass_turn", {});
}

function respondCha(doCha) {
  socket.emit("respond_cha", { do_cha: doCha });
}

function respondDian(doDian) {
  socket.emit("respond_dian", { do_dian: doDian });
}

function respondLigun(doLigun) {
  socket.emit("respond_ligun", { do_ligun: doLigun });
}

function submitReturn(cardIndex) {
  socket.emit("tribute_return_submit", { card_index: cardIndex });
}

function goLobby() {
  store.reset();
  socket.disconnect();
  uni.reLaunch({ url: "/pages/lobby/lobby" });
}

// 收到 game_action 时重新请求游戏状态（服务端会主动 push game_state，此处只清空选牌）
socket.on("game_action", () => { selectedIndices.value = []; });
</script>

<style scoped>
.game {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a2e;
  padding: 16rpx;
  box-sizing: border-box;
  overflow: hidden;
}
.middle {
  flex: 1;
  display: flex;
  align-items: stretch;
  gap: 8rpx;
  overflow: hidden;
}
.table-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0f1929;
  border-radius: 16rpx;
}
.table-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  justify-content: center;
  padding: 16rpx;
  min-height: 120rpx;
}
.table-empty { color: #444; font-size: 28rpx; }
.current-hint {
  color: #aaa;
  font-size: 26rpx;
  padding-top: 12rpx;
}
.my-hand {
  display: flex;
  flex-wrap: wrap;
  gap: 6rpx;
  justify-content: center;
  padding: 8rpx 0;
  min-height: 140rpx;
  align-items: flex-end;
}
.actions {
  display: flex;
  gap: 24rpx;
  padding: 16rpx 0 8rpx;
  justify-content: center;
}
.btn {
  border-radius: 12rpx;
  padding: 22rpx 60rpx;
  font-size: 32rpx;
  border: none;
}
.btn.play { background: #e94560; color: #fff; }
.btn.pass { background: #0f3460; color: #ccc; }
.btn[disabled] { opacity: 0.4; }
</style>
