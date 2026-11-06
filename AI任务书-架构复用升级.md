# 任务书：以 ProGyakuten 为蓝本，修复自身缺陷并升级其他卡牌项目架构

> 本文档是给执行 AI 的完整任务说明。**自包含**：所有关键发现、文件路径、缺陷定位均已内嵌，无需重新分析。如与实际代码不符，以实际代码为准并在汇报中指出差异。

---

## 一、你的角色与总目标

你是一名资深全栈工程师，接手维护一组同属一位开发者的多人在线卡牌/桌游项目。这些项目结构同构（WebSocket + 房间 + 座位 + 手牌可见性隔离），但质量参差。其中 **ProGyakuten 的架构分层是唯一方向正确的**，你的任务是：

1. **修复 ProGyakuten 自身的已知缺陷**（阶段一，最高优先级）
2. **将其架构抽取为可复用的共享包**（阶段二）
3. **按统一架构升级其他卡牌项目**（阶段三）

总原则：**先修好样板，再复制模式**。禁止把带已知缺陷的代码搬进其他项目。

---

## 二、资产清单（权威路径）

| 项目 | 权威路径 | 技术栈 | 角色 |
|---|---|---|---|
| **ProGyakuten**（逆转 UNO） | `E:\ProGyakuten\ProGyakuten-latest` | pnpm monorepo，React 19 + Vite + 原生 ws，TypeScript | **架构蓝本**，唯一有分层设计的项目 |
| RivalCourts-NAISHImultiplayer | 需克隆 `github.com/WTJunzhu/RivalCourts-NAISHImultiplayer` | Vue3 + 原生 ws + Prisma | 升级顺序第 1 位 |
| SkullKing | 需克隆 `github.com/WTJunzhu/SkullKing` | React 19 + socket.io，部署 fly.io | 升级顺序第 2 位 |
| TexasHoldem | 需克隆 `github.com/WTJunzhu/TexasHoldem` | 原生 Node + 无框架前端 + socket.io | 升级顺序第 3 位 |
| Tongliao4A4 | 需克隆 `github.com/WTJunzhu/Tongliao4A4` | Flask-SocketIO (Python) + uni-app 客户端 | 升级顺序第 4 位（但其中的小程序断线 bug 是**全场最高优先级 P0**，见 5.4） |
| HexTechBilliards | 需克隆 `github.com/WTJunzhu/HexTechBilliards` | uni-app + WebRTC P2P + 自研物理引擎 | 只复用房间信令层，物理同步不在本次范围 |

克隆时使用 `git clone --depth 1`。**注意**：`E:\ProGyakuten\` 下还有一个 `ProGyakuten-main\ProGyakuten-main\`，那是 5 月 22 日的旧 zip 解压包，**不是权威副本，禁止改动**。

### ProGyakuten 内部结构（你要参考的核心）

```
ProGyakuten-latest/
├── packages/
│   ├── core/        ← 规则引擎：纯函数、零 UI/网络依赖、73 个测试
│   └── protocol/    ← 事件契约：客户端与服务端共享类型，协议变更编译期报错
├── apps/
│   ├── client/      ← React 19 + Vite；src/utils/websocket.ts 是连接封装类
│   └── server/      ← 原生 ws 服务端；roomSnapshot 做视角投影（只下发该玩家可见的状态）
```

**值得复制的三个设计**：
1. `packages/core` 的"规则引擎完全隔离"——规则是纯函数，测试不依赖网络和 DOM
2. `packages/protocol` 的共享类型契约——消灭裸 JSON + 字符串事件名
3. 服务端的视角投影——状态由服务端持有，按玩家过滤下发（而不是客户端自己藏牌）

---

## 三、全局约束（每个阶段都适用）

1. **不改玩法**。规则逻辑、数值、交互流程保持现状，只动架构。
2. **不发布、不部署**。不申请新云资源、不改部署配置（修 Dockerfile 除外）、不做任何域名/备案操作。
3. **IP 问题不处理**。ProGyakuten 含逆转裁判 IP 素材（角色名、台词音效、演出视频），本任务不涉及改名换皮，但**禁止新增**任何 IP 素材引用。
4. **git 规范**：每个独立修复/升级一个 commit，信息写清楚改了什么、为什么。禁止 `--force` push，禁止跳过钩子。
5. **测试优先**：ProGyakuten 的 `packages/core` 有 73 个测试，任何改动后必须全绿。其他项目没有测试的，在动它的服务端前先为现有行为补最小快照测试（先固化现状，再重构）。
6. **遇到与本任务书描述不符的代码现状**（可能已更新），停下来汇报差异，不要硬套方案。

---

## 四、阶段一：修复 ProGyakuten 自身缺陷（P0）

按以下顺序执行，每项独立 commit 并验证。

### 4.1 auth token 内存存储 → 持久化
- **位置**：`apps/server/src/auth.ts`
- **现状**：token 存在内存 `Map` 里，服务端重启全部失效。桌面端尚可忍受，移动端致命（用户切后台回来，本地 token 还在但服务端已不认，直接丢房间）。
- **要求**：改为 SQLite 持久化（项目内已有本地文件存储的先例则沿用），或改 JWT（无状态、不需要存储）。二选一，说明理由。token 生命周期、清理逻辑要显式处理。
- **验收**：重启服务端后，持有旧 token 的客户端重连能恢复座位。

### 4.2 Dockerfile 启动命令修复
- **位置**：根目录 `Dockerfile`
- **现状**：Stage 2 只 COPY 了 `apps/server/dist`，但 `CMD` 是 `npx tsx apps/server/src/index.ts`——runtime 镜像里没有 `src/`，容器起不来。
- **要求**：`CMD` 改为 `node apps/server/dist/index.js`，并核对 dist 产物路径与依赖是否齐（production dependencies 是否被正确 COPY）。
- **验收**：`docker build` 后本地 `docker run` 能起服务（没有 Docker 环境则至少核对多阶段构建的文件路径逻辑，并在汇报中说明未实际验证）。

### 4.3 重连宽限期调整
- **位置**：`apps/server/src/` 中 `RECONNECT_GRACE_MS = 20000`
- **要求**：调整为 60–90 秒（移动端切后台回来需要时间）。同时在客户端 `websocket.ts` 里核对重连退避策略与之匹配。
- **验收**：手动断网 30 秒再恢复，能回到原对局。

### 4.4 未提交的演出视频
- **现状**：`apps/client/public/video/` 下 5 个 mp4（4.9 MB）处于"已 add 未 commit"状态，切分支或 reset 容易丢。
- **要求**：与用户确认后 commit（或由用户自行处理）。这是唯一需要用户决策的项。

---

## 五、阶段二：抽取共享包 + 阶段三：逐项目升级

### 5.1 先抽取共享包（阶段二）

在 ProGyakuten 的 `packages/` 下（或独立仓库，与用户确认）抽出：

- **`@cardkit/protocol`**：基于 `packages/protocol`，泛化为"不绑定具体玩法"的事件契约模板（房间生命周期、加入/离开、行动提交、状态快照、错误码），具体游戏的私有事件由各项目扩展
- **`@cardkit/room`**：基于服务端房间逻辑，泛化房间/座位管理 + 视角投影（`roomSnapshot` 的通用化）
- 客户端连接封装（参考 `apps/client/src/utils/websocket.ts`，预留 `wx.connectSocket` 适配位）

**抽取时保持 ProGyakuten 自身可运行**：抽完后 ProGyakuten 改为依赖共享包，全部测试通过、本地能开一局完整对局，才算抽取完成。

### 5.2 升级顺序与各项目要点（阶段三）

**第 1 位：RivalCourts**
- 原生 ws + `server/ws/ViewProjector.ts` 视角投影，思路与 ProGyakuten 同源，改造成本最低
- 服务端 `GameEngine.ts` 仅 77 行，6 大行动已实现 5 个（缺 8 张史书卡）——**先完成架构升级，史书卡等新功能在升级后的架构上写**
- 客户端 Vue3，`localStorage` / `window` 使用极少，适配顺利

**第 2 位：SkullKing**
- 先把服务端从 socket.io 换到原生 ws（客户端同步换），这是接入共享协议的前提
- 全项目**零 CSS 文件、57 处内联样式**——内联样式写不了 media query，移动端适配无从谈起。升级时顺手把内联样式抽到样式文件，建立基础响应式断点
- React 19 与共享包无冲突

**第 3 位：TexasHoldem**
- 同样先换 socket.io → 原生 ws
- **身份认证是空架子**：靠 nickname 恢复座位，`join` 只校验 name，知道对方昵称就能接管座位看底牌。接入 `@cardkit` 的 token 方案（阶段一 4.1 的成果）
- 底牌隔离本身做对了（`getStateForPlayer` 把所有人 `holeCards` 置 null），迁到视角投影架构时保留这个语义
- 前端无框架、原生 JS，客户端按共享连接封装重写

**第 4 位：Tongliao4A4**
- ⚠️ **其中小程序断线 bug 是全场最高优先级 P0，若时间有限只做一件事就做它**（见 5.4）
- 服务端是 Python (Flask-SocketIO)。可以保留 Python 端不动，只把客户端接入共享协议层——但注意 Socket.IO 的 engine.io 协议与共享包的原生 ws 协议不兼容，若保留 Python 端则共享协议层对其不适用，需在汇报中给出"保留 Python vs 迁 Node"的利弊建议供用户决策
- uni-app 客户端，规则引擎（贡/里杠/叉）在服务端 Python 中，本任务不重写

**HexTechBilliards（范围受限）**
- WebRTC P2P 是其核心，物理同步与卡牌项目完全不同域，**不做架构升级**
- 仅当用户要求时，把房间信令（创建/加入房间）换成 `@cardkit/room`
- 其 `MVP.md` 的 Task 8（WS relay 替代 P2P）是它自己的正确方向，不归本任务管

### 5.3 每个项目的升级验收标准

1. 服务端状态经视角投影下发，客户端**不持有**不该看到的数据（用测试固化：断言下发给玩家 A 的快照中不包含玩家 B 的手牌）
2. 事件走共享协议类型，TypeScript 项目编译期校验（非 TS 项目至少有 JSON Schema 或文档化的契约）
3. 有最小重连测试：断开 → 恢复 → 座位与对局状态还原
4. 原有玩法行为不变（升级前先补的现状快照测试全绿）

### 5.4 独立 P0：Tongliao4A4 小程序端断线 bug

- **位置**：`client/src/utils/socket.js`，小程序（`mp-weixin`）分支
- **现状**：该分支手写了 Socket.IO 协议解析，但只处理了 `42`（业务事件）帧，缺了：
  - `40`（Socket.IO CONNECT）——不发这个，服务端不会创建 socket 对象，`socketio.emit(to=sid)` 全部静默失败，**收不到任何游戏消息**
  - `2` / `3`（心跳 ping/pong）——服务端每 25 秒发 ping，不回 pong 判定超时，**30 秒后必被踢**
- **为什么没被发现**：H5 分支走官方 `socket.io-client`（协议内部处理），只在浏览器测过，一上真机必掉线
- **要求**：补全 `40`、`2`、`3` 帧处理。参照 engine.io 协议：收到 `2` 立即回 `3`；连接建立后发 `40`，收到服务端 `40{"sid":"..."}` 后解析 sid
- **验收**：微信开发者工具真机预览，进入房间后放置 2 分钟不断线、能正常收到对局事件

---

## 六、汇报格式

每完成一个阶段，汇报：
1. 改了哪些文件、每个 commit 的 hash 与说明
2. 验收项逐条通过/未通过的证据（测试输出、截图描述）
3. 发现的、本任务书未覆盖的新问题（只记录，不顺手修）
4. 下一步计划与需要用户决策的点

---

## 七、明确不做的事

- 不申请 ICP 备案、不买服务器、不做任何上线动作
- 不处理 ProGyakuten 的 IP 换皮（改名、替换素材）
- 不重写任何游戏的玩法规则
- 不动 `E:\ProGyakuten\ProGyakuten-main\`（旧 zip 解压包）
- 不动 Unity 项目（VR-waste-sorting、ParkcleanVR）和 Ren'Py 项目（GyakutenMaker）
- HexTechBilliards 不做 WebRTC→WS 的架构改造
