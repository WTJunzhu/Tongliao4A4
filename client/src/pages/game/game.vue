<template>
  <view class="game-shell">
    <view class="game-inner">

      <!-- 对家 -->
      <view class="row-top" ref="rowTopRef">
        <view class="pchip" :class="{ active: opponent?.seat === gs?.current_seat }">
          <text class="pname">{{ opponent?.name || '—' }}</text>
          <view class="fan fan-h">
            <view v-for="i in fanN(opponent)" :key="i" class="cb" :style="fanH(i-1, fanN(opponent))" />
          </view>
          <view v-if="opponent?.hand_count > 0" class="nbadge">{{ opponent?.hand_count }}</view>
        </view>
        <PlayBadge :action="seatAction(opponent?.seat)" :level-rank="levelRank" />
      </view>

      <!-- 左 | 桌面 | 右 -->
      <view class="row-mid">

        <view class="side" ref="leftSideRef">
          <view class="pchip" :class="{ active: leftOpp?.seat === gs?.current_seat }">
            <text class="pname">{{ leftOpp?.name || '—' }}</text>
            <view class="fan fan-v">
              <view v-for="i in fanN(leftOpp)" :key="i" class="cb" :style="fanV(i-1, fanN(leftOpp))" />
            </view>
            <view v-if="leftOpp?.hand_count > 0" class="nbadge">{{ leftOpp?.hand_count }}</view>
          </view>
        </view>

        <view class="side-badge">
          <PlayBadge :action="seatAction(leftOpp?.seat)" :level-rank="levelRank" compact />
        </view>

        <view class="table-center" ref="tableCenterRef">
          <view class="level-chip">级牌 {{ levelRank }}</view>
          <text class="curr-hint">{{ currentHint }}</text>
          <text class="hui-hint">本局 {{ levelRank }} 是会</text>
        </view>

        <view class="side-badge">
          <PlayBadge :action="seatAction(rightOpp?.seat)" :level-rank="levelRank" compact />
        </view>

        <view class="side" ref="rightSideRef">
          <view class="pchip" :class="{ active: rightOpp?.seat === gs?.current_seat }">
            <text class="pname">{{ rightOpp?.name || '—' }}</text>
            <view class="fan fan-v">
              <view v-for="i in fanN(rightOpp)" :key="i" class="cb" :style="fanV(i-1, fanN(rightOpp))" />
            </view>
            <view v-if="rightOpp?.hand_count > 0" class="nbadge">{{ rightOpp?.hand_count }}</view>
          </view>
        </view>

      </view>

      <!-- 我的出牌 -->
      <view class="row-myplay">
        <PlayBadge :action="seatAction(seat)" :level-rank="levelRank" />
      </view>

      <!-- 手牌：flex 等间距，wrap=nowrap，自动收缩 -->
      <view
        class="row-hand"
        ref="handRowRef"
        @touchstart.prevent="onHandTouchStart"
        @touchmove.prevent="onHandTouchMove"
        @touchend="onHandTouchEnd"
      >
        <view
          v-for="(card, i) in myHand"
          :key="i"
          class="hand-card"
          @tap="toggleSelect(i)"
        >
          <CardSprite :card="card" :level-rank="levelRank" :selected="selectedIndices.includes(i)" />
        </view>
      </view>

      <!-- 按钮 -->
      <view class="row-actions">
        <template v-if="isMyTurn && gamePhase === 'PLAYING'">
          <button class="btn play" @tap="playCards" :disabled="!selectedIndices.length">出牌</button>
          <button class="btn pass" @tap="pass"      :disabled="!canPass">不要</button>
        </template>
      </view>

    </view>

    <!-- 弹窗层 -->
    <ChaDialog        v-if="gamePhase === 'CHA_ASKING'  && gs?.asking_seat === store.mySeat" @respond="respondCha" />
    <DianDialog       v-if="gamePhase === 'DIAN_ASKING' && gs?.asking_seat === store.mySeat" @respond="respondDian" />
    <LigunDialog      v-if="store.ligunAskSeat === store.mySeat" @respond="respondLigun" />
    <TributePanel     v-if="store.tributePhase === 'tribute_select'" />
    <ReturnSubmitPanel v-if="store.tributePhase === 'return_submit'" :my-hand="myHand" @submit="submitReturn" />
    <RoundSummary     v-if="store.roundSummary && !store.roundSummary.game_over" :summary="store.roundSummary" @close="store.roundSummary = null" />
    <GameOver         v-if="store.roundSummary?.game_over" :winner-team="store.roundSummary.winner_team" @back="goLobby" />
    <FirstSeatDialog  v-if="store.firstSeatCandidates?.includes(store.mySeat)" @respond="respondFirstSeat" />

    <!-- 飞牌动画层 -->
    <CardFlyOverlay
      v-for="fly in flyAnims"
      :key="fly.id"
      :card="fly.card"
      :from-rect="fly.fromRect"
      :to-rect="fly.toRect"
      :level-rank="levelRank"
      @done="removeFly(fly.id)"
    />
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { useGameStore }   from "../../store/game";
import { socket }         from "../../utils/socket";
import CardSprite         from "../../components/CardSprite.vue";
import PlayBadge          from "../../components/PlayBadge.vue";
import ChaDialog          from "../../components/ChaDialog.vue";
import DianDialog         from "../../components/DianDialog.vue";
import LigunDialog        from "../../components/LigunDialog.vue";
import TributePanel       from "../../components/TributePanel.vue";
import ReturnSubmitPanel  from "../../components/ReturnSubmitPanel.vue";
import RoundSummary       from "../../components/RoundSummary.vue";
import GameOver           from "../../components/GameOver.vue";
import FirstSeatDialog    from "../../components/FirstSeatDialog.vue";
import CardFlyOverlay     from "../../components/CardFlyOverlay.vue";

const store = useGameStore();
const gs    = computed(() => store.gameState);
const selectedIndices = ref([]);
const latestAction    = ref({});
const handRowRef      = ref(null);
const rowTopRef       = ref(null);
const leftSideRef     = ref(null);
const rightSideRef    = ref(null);
const tableCenterRef  = ref(null);

// ---- 飞牌动画 ----
const flyAnims = ref([]);
let _flyIdCounter = 0;

function getSeatRect(targetSeat) {
  const relSeat = ((targetSeat - store.mySeat) % 4 + 4) % 4;
  let el;
  if (relSeat === 0) el = handRowRef.value;
  else if (relSeat === 2) el = rowTopRef.value;
  else if (relSeat === 3) el = leftSideRef.value;
  else el = rightSideRef.value;
  if (!el) return null;
  const dom = el.$el ?? el;
  return dom.getBoundingClientRect?.() ?? null;
}

function addFly(card, fromRect, toRect) {
  if (!fromRect || !toRect) return;
  flyAnims.value.push({ id: ++_flyIdCounter, card, fromRect, toRect });
}

function removeFly(id) {
  flyAnims.value = flyAnims.value.filter(f => f.id !== id);
}

// 半洞进贡：牌从输家直接飞到赢家
socket.on("tribute_auto_apply", (data) => {
  if (!data.card) return;
  addFly(data.card, getSeatRect(data.giver_seat), getSeatRect(data.receiver_seat));
});

// 全洞进贡：tribute_start 时牌从输家手牌区飞到中心面板
socket.on("tribute_start", (data) => {
  if (data.type !== "quan_dong" || !data.tribute_cards) return;
  const centerRect = tableCenterRef.value?.getBoundingClientRect?.() ?? null;
  for (const [giverSeatStr, card] of Object.entries(data.tribute_cards)) {
    addFly(card, getSeatRect(Number(giverSeatStr)), centerRect);
  }
});

// 全洞进贡：确认选牌后牌从中心面板飞到各赢家
socket.on("tribute_cards_to_winners", (data) => {
  const centerRect = tableCenterRef.value?.getBoundingClientRect?.() ?? null;
  for (const t of (data.transfers || [])) {
    addFly(t.card, centerRect, getSeatRect(t.receiver_seat));
  }
});

// 还贡（半洞/全洞均适用）：还贡牌从赢家飞回输家
socket.on("return_cards_delivered", (data) => {
  for (const t of (data.transfers || [])) {
    addFly(t.card, getSeatRect(t.returner_seat), getSeatRect(t.original_giver_seat));
  }
});

// 拖动选牌状态
let _dragSelecting = false;
let _dragInitSet   = false;  // 第一张牌是选中还是取消
let _dragTouched   = new Set();

function _cardIndexAtX(clientX) {
  if (!handRowRef.value) return -1;
  const el = handRowRef.value.$el ?? handRowRef.value;
  const cards = el.querySelectorAll(".hand-card");
  for (let i = 0; i < cards.length; i++) {
    const r = cards[i].getBoundingClientRect();
    if (clientX >= r.left && clientX <= r.right) return i;
  }
  return -1;
}

function onHandTouchStart(e) {
  if (!isMyTurn.value) return;
  _dragSelecting = true;
  _dragInitSet = false;
  _dragTouched = new Set();
  const touch = e.touches[0];
  const idx = _cardIndexAtX(touch.clientX);
  if (idx !== -1) {
    _dragTouched.add(idx);
    const already = selectedIndices.value.includes(idx);
    _dragInitSet = !already;
    if (_dragInitSet) selectedIndices.value.push(idx);
    else selectedIndices.value = selectedIndices.value.filter(i => i !== idx);
  }
}

function onHandTouchMove(e) {
  if (!_dragSelecting || !isMyTurn.value) return;
  const touch = e.touches[0];
  const idx = _cardIndexAtX(touch.clientX);
  if (idx === -1 || _dragTouched.has(idx)) return;
  _dragTouched.add(idx);
  if (_dragInitSet) {
    if (!selectedIndices.value.includes(idx)) selectedIndices.value.push(idx);
  } else {
    selectedIndices.value = selectedIndices.value.filter(i => i !== idx);
  }
}

function onHandTouchEnd() {
  _dragSelecting = false;
}

const levelRank  = computed(() => gs.value?.level_rank || "3");
const gamePhase  = computed(() => gs.value?.state || "");
const myHand     = computed(() => store.myPlayer?.hand || []);
const isMyTurn   = computed(() => store.isMyTurn);
const seat       = computed(() => store.mySeat);
const players    = computed(() => gs.value?.players || []);

const canPass = computed(() => {
  const lps = gs.value?.last_play_seat;
  return lps != null && lps >= 0 && lps !== store.mySeat;
});

function playerAt(rel) {
  const s = ((seat.value + rel) % 4 + 4) % 4;
  return players.value.find(p => p.seat === s) || null;
}
const opponent = computed(() => playerAt(2));
const leftOpp  = computed(() => playerAt(3));
const rightOpp = computed(() => playerAt(1));

const currentHint = computed(() => {
  const cur = gs.value?.current_seat;
  if (cur == null) return "";
  if (cur === seat.value) return "轮到你了";
  const p = players.value.find(x => x.seat === cur);
  return `${p?.name || (cur+1)+"号"} 出牌中`;
});

function seatAction(s) { return s != null ? (latestAction.value[s] ?? null) : null; }

function fanN(p) { return Math.min(p?.hand_count || 0, 5); }
function fanH(i, n) {
  const off = n <= 1 ? 0 : (i - (n-1)/2) * 9;
  return { transform: `translateX(${off}px)`, zIndex: i };
}
function fanV(i, n) {
  const off = n <= 1 ? 0 : (i - (n-1)/2) * 7;
  return { transform: `translateY(${off}px)`, zIndex: i };
}

function toggleSelect(i) {
  if (!isMyTurn.value) return;
  const idx = selectedIndices.value.indexOf(i);
  if (idx === -1) selectedIndices.value.push(i);
  else selectedIndices.value.splice(idx, 1);
}

function playCards()    { socket.emit("play_cards", { card_indices: selectedIndices.value }); selectedIndices.value = []; }
function pass()          { socket.emit("pass_turn", {}); }
function respondCha(v)   { socket.emit("respond_cha",   { do_cha:   v }); }
function respondDian(v)  { socket.emit("respond_dian",  { do_dian:  v }); }
function respondLigun(v) { socket.emit("respond_ligun", { do_ligun: v }); }
function respondFirstSeat() { socket.emit("respond_first_seat", {}); store.firstSeatCandidates = null; }
function submitReturn(i) { socket.emit("tribute_return_submit", { card_index: i }); }
function goLobby() {
  store.reset(); socket.disconnect();
  uni.reLaunch({ url: "/pages/lobby/lobby" });
}

let prevLPS = -1;
socket.on("game_action", (data) => {
  selectedIndices.value = [];
  const t = data?.type;
  if (t === "played" && data.seat != null) {
    latestAction.value = { ...latestAction.value, [data.seat]: data };
  } else if (t === "passed" && data.seat != null) {
    latestAction.value = { ...latestAction.value, [data.seat]: { type: "pass", seat: data.seat } };
  }
});
socket.on("game_state", (data) => {
  const lps = data?.last_play_seat ?? -1;
  if (lps === -1 && prevLPS !== -1) latestAction.value = {};
  prevLPS = lps;
});
</script>

<style scoped>
.game-shell {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  padding-top: var(--window-top, 44px);
  box-sizing: border-box;
  background: radial-gradient(ellipse at top, #16213e 0%, #0d1117 100%);
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.game-inner {
  width: min(800px, 100%);
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto auto auto;
  gap: 8px;
  padding: 10px 12px;
  box-sizing: border-box;
}

/* 对家 */
.row-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

/* 中排 */
.row-mid {
  display: flex;
  align-items: stretch;
  gap: 10px;
  min-height: 0;
}
.side {
  width: 110px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.side-badge {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 70px;
}
.table-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(15,25,41,0.65);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
}

/* 我的出牌 */
.row-myplay {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 44px;
}

/* 手牌：flex 行，均分间距，不换行，自动压缩 */
.row-hand {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: flex-end;
  gap: 6px;
  overflow: hidden;
  /* 牌高 68px + 选中上移 20px + 余量 */
  min-height: 96px;
  padding-top: 24px; /* 为选中上移留空间 */
}

/* 按钮 */
.row-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  min-height: 48px;
}

/* 玩家块 */
.pchip {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid transparent;
  transition: border-color .2s, background .2s;
}
.pchip.active {
  border-color: rgba(233,69,96,0.65);
  background: rgba(233,69,96,0.13);
}
.pname {
  font-size: 14px;
  color: #ccc;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 牌背扇形 */
.fan { position: relative; display: flex; align-items: center; justify-content: center; }
.fan-h { width: 52px; height: 36px; }
.fan-v { width: 30px; height: 46px; }
.cb {
  position: absolute;
  width: 22px; height: 32px;
  background: linear-gradient(135deg, #1a3a6a, #0f3460, #0a2444);
  border-radius: 3px;
  border: 1px solid #2a5aaa;
  box-shadow: 0 1px 3px rgba(0,0,0,.5);
}
.fan-v .cb { width: 20px; height: 28px; }
.nbadge {
  position: absolute;
  right: -2px; bottom: -2px;
  background: #e94560;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  min-width: 18px; height: 18px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  padding: 0 3px;
}

/* 桌面 */
.level-chip {
  font-size: 14px;
  background: rgba(249,185,12,0.2);
  color: #f9b90c;
  padding: 4px 14px;
  border-radius: 12px;
  border: 1px solid rgba(249,185,12,0.4);
}
.curr-hint { font-size: 14px; color: #999; }
.hui-hint  { font-size: 13px; color: #f9b90c; opacity: 0.85; }

/* 按钮 */
.btn {
  border-radius: 10px;
  padding: 10px 40px;
  font-size: 16px;
  border: none;
  font-weight: bold;
  cursor: pointer;
}
.btn.play { background: #e94560; color: #fff; }
.btn.pass { background: #1a3a6a; color: #ccc; }
.btn[disabled] { opacity: 0.4; cursor: default; }
</style>
