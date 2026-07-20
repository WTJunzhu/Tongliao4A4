/**
 * Socket 封装：H5 用 socket.io-client，小程序用 uni WebSocket。
 * 对外暴露统一的 connect / emit / on / off / disconnect 接口。
 */

// #ifdef H5
import { io } from "socket.io-client";
// #endif

const SERVER_URL = import.meta.env.VITE_SERVER_URL || "";

let _socket = null;
const _listeners = {}; // event → [handler]

// #ifdef H5
function _connect() {
  _socket = io(SERVER_URL, { transports: ["websocket"] });
  _socket.onAny((event, ...args) => _dispatch(event, ...args));
}

function _emit(event, data) {
  _socket?.emit(event, data);
}

function _disconnect() {
  _socket?.disconnect();
  _socket = null;
}
// #endif

// #ifndef H5
function _connect() {
  const url = (SERVER_URL || "ws://localhost:5000") + "/socket.io/?EIO=4&transport=websocket";
  _socket = uni.connectSocket({ url, complete: () => {} });

  // uni-app WebSocket 需要手动处理 socket.io 握手帧
  _socket.onMessage(({ data }) => {
    if (typeof data !== "string") return;
    // socket.io 消息格式：42["event",{...}]
    if (data.startsWith("42")) {
      try {
        const [event, payload] = JSON.parse(data.slice(2));
        _dispatch(event, payload);
      } catch {}
    }
  });
}

function _emit(event, data) {
  if (!_socket) return;
  const msg = "42" + JSON.stringify([event, data]);
  _socket.send({ data: msg });
}

function _disconnect() {
  _socket?.close();
  _socket = null;
}
// #endif

function _dispatch(event, ...args) {
  (_listeners[event] || []).forEach((fn) => fn(...args));
}

export const socket = {
  connect: _connect,
  emit: _emit,
  disconnect: _disconnect,

  on(event, handler) {
    if (!_listeners[event]) _listeners[event] = [];
    _listeners[event].push(handler);
  },
  off(event, handler) {
    if (!_listeners[event]) return;
    if (handler) {
      _listeners[event] = _listeners[event].filter((fn) => fn !== handler);
    } else {
      delete _listeners[event];
    }
  },
};
