import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { socket } from "../utils/socket";

export const useGameStore = defineStore("game", () => {
  // ---- 会话 ----
  const playerId = ref(uni.getStorageSync("player_id") || "");
  const roomId = ref("");
  const mySeat = ref(-1);

  // ---- 房间 ----
  const roomState = ref(null); // room_state 事件负载

  // ---- 游戏 ----
  const gameState = ref(null); // game_state 事件负载（本座位视角）

  // ---- 进贡/还贡 ----
  const tributeInfo = ref(null);     // { type, giver_seats, receiver_seats, selection }
  const tributePhase = ref(null);    // "tribute_select" | "return_submit" | "return_select"
  const selectionState = ref(null);  // TributeSelectionState.to_dict()

  // ---- 立棍 ----
  const ligunAskSeat = ref(null);

  // ---- 结算 ----
  const roundSummary = ref(null);

  // ---- 计算属性 ----
  const myPlayer = computed(() =>
    gameState.value?.players?.find((p) => p.seat === mySeat.value)
  );
  const isMyTurn = computed(() =>
    gameState.value?.current_seat === mySeat.value
  );

  // ---- 初始化 Socket 监听 ----
  function initListeners() {
    socket.on("room_state", (data) => { roomState.value = data; });
    socket.on("game_state", (data) => { gameState.value = data; });
    socket.on("game_started", () => {});
    socket.on("round_end", (data) => { roundSummary.value = data; });
    socket.on("game_over", (data) => { roundSummary.value = { ...roundSummary.value, game_over: true, ...data }; });

    // 立棍
    socket.on("ligun_ask", (data) => { ligunAskSeat.value = data.asking_seat; });
    socket.on("ligun_started", () => { ligunAskSeat.value = null; });

    // 进贡选牌
    socket.on("tribute_start", (data) => {
      tributeInfo.value = data;
      selectionState.value = data.selection;
      tributePhase.value = "tribute_select";
    });
    socket.on("tribute_selection_update", (data) => {
      selectionState.value = data;
    });
    socket.on("tribute_return_request", () => {
      tributePhase.value = "return_submit";
    });
    socket.on("tribute_return_select_start", (data) => {
      selectionState.value = data.selection;
      tributePhase.value = "return_select";
    });
    socket.on("tribute_complete", () => {
      tributeInfo.value = null;
      tributePhase.value = null;
      selectionState.value = null;
    });

    // 游戏动作（出牌、pass、叉、点、接风等）
    socket.on("game_action", () => {});

    socket.on("player_disconnected", () => {});
    socket.on("player_reconnected", () => {});
  }

  function savePlayerId(id) {
    playerId.value = id;
    uni.setStorageSync("player_id", id);
  }

  function reset() {
    roomId.value = "";
    mySeat.value = -1;
    roomState.value = null;
    gameState.value = null;
    tributeInfo.value = null;
    tributePhase.value = null;
    selectionState.value = null;
    ligunAskSeat.value = null;
    roundSummary.value = null;
  }

  return {
    playerId, roomId, mySeat,
    roomState, gameState,
    tributeInfo, tributePhase, selectionState,
    ligunAskSeat, roundSummary,
    myPlayer, isMyTurn,
    initListeners, savePlayerId, reset,
  };
});
