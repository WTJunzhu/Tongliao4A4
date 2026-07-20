# 通辽4A4 扑克游戏 - 设计文档

## 一、项目概述

**通辽4A4** 是一套前后端分离的在线多人扑克游戏，完整实现东北地区流行的"四幺四"扑克玩法，并融入通辽地区的特色规则，支持微信小程序和 H5 浏览器双端游玩。

### 1.1 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 后端 | Python 3 + Flask + Flask-SocketIO | REST API（房间管理）+ WebSocket（游戏实时通信） |
| 前端 | uni-app (Vue 3) | 一套代码，编译输出微信小程序 + H5 |
| 通信 | HTTP REST + WebSocket | `uni.connectSocket` 连接 Flask-SocketIO |
| 部署 | 自有服务器 + 微信小程序 | 后端 Flask 部署服务器，前端通过 WebSocket 连接 |

### 1.2 为什么选 uni-app 而不是原生小程序

- uni-app 同一套代码可以编译成**微信小程序**和 **H5 网页版**，方便 GitHub 开源后其他人也能直接浏览器试玩
- Vue 3 开发体验优于小程序原生，组件化更成熟
- 对 WebSocket 的封装（`uni.connectSocket`）与 Socket.IO 兼容
- GitHub 开源后降低二次开发门槛

### 1.3 双端游玩路径

```
┌──────────────────────────────────────────────┐
│             uni-app 前端源码                  │
│                                              │
│   编译 ──► 微信小程序 ──► 微信扫码游玩       │
│   编译 ──► H5 网页     ──► 浏览器直接打开   │
└──────────────────────────────────────────────┘
```

---

## 二、架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────┐
│              前端 (uni-app)                  │
│  ┌─────────────────────────────────────┐    │
│  │  pages/index/     (大厅/房间列表)     │    │
│  │  pages/room/      (房间等待)         │    │
│  │  pages/game/      (游戏主界面)        │    │
│  ├─────────────────────────────────────┤    │
│  │  utils/ws.js         (WebSocket 连接) │    │
│  │  utils/api.js        (HTTP API 调用)  │    │
│  │  store/              (Vuex/Pinia)     │    │
│  └─────────────────────────────────────┘    │
│         │                                    │
│         │ HTTP REST + WebSocket              │
└─────────┼────────────────────────────────────┘
          │
┌─────────┴────────────────────────────────────┐
│           后端 (Python Flask + SocketIO)      │
│  ┌─────────────────────────────────────┐    │
│  │  routes/api.py      (REST API)      │    │
│  │  routes/ws.py       (WebSocket)      │    │
│  ├─────────────────────────────────────┤    │
│  │  models/card.py      (牌)            │    │
│  │  models/deck.py       (牌堆)          │    │
│  │  models/hand_type.py   (牌型识别)     │    │
│  │  models/player.py     (玩家)          │    │
│  │  models/game.py       (单局逻辑)      │    │
│  │  models/room.py       (房间/升级)      │    │
│  │  models/tribute.py    (进贡系统)       │    │
│  │  models/ligun.py      (立棍系统)       │    │
│  └─────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

### 2.2 分层设计原则

遵循原 DESIGN.md 中"模型层与后端完全隔离"的优良设计，同时将通辽4A4的特色逻辑模块化：

| 层 | 职责 | 依赖 |
|----|------|------|
| `models/` | 纯游戏规则逻辑，不依赖任何网络库 | 无外部依赖 |
| `routes/` | REST API + WebSocket 通信 + 会话管理 | Flask, models |
| `frontend/` | uni-app 前端，UI 渲染与交互 | uni-app, Vue 3 |

**通辽4A4 独有模块：**
- `models/tribute.py` — 进贡/还贡/反贡/土皇上逻辑
- `models/ligun.py` — 立棍/撅棍系统

---

## 三、数据模型

### 3.1 Card（牌）

```
属性:
  - suit: SPADE | HEART | CLUB | DIAMOND | JOKER
  - rank: "3"~"A", "2", "BJ"(小王), "RJ"(大王)
  - is_red: boolean         # 用于 4A4 花色判定

方法:
  - get_value(level_rank): int    # 带级牌加成的权重值
  - is_joker(): boolean
  - eq(other): boolean
```

**级牌权重映射**（以打 5 为例）：

| 牌 | 大王 | 小王 | 5(级牌) | 2 | A | K | ... | 6 | 3 | 4 |
|---|---|---|---|---|---|---|---|---|---|---|
| 权重 | 15 | 14 | 13 | 12 | 11 | 10 | ... | 4 | 3 | 2 |

- 没有计入级牌的牌（如上表打5时的3和4）按原牌点降序排列
- 权重越大的牌面板越大，同牌型的比较依赖此权重

### 3.2 HandType（牌型）

牌型等级（从低到高）：

| 等级 | 牌型 | ID | 说明 |
|------|------|----|------|
| 1 | 单张 | single | 任意一张牌 |
| 2 | 对子 | pair | 两张相同牌点 |
| 3 | 单龙 | straight | ≥3 张连续单牌，不含 2/王/级牌 |
| 4 | 双龙 | straight_pairs | ≥3 对连续对子，不含 2/王/级牌 |
| 5 | 三炸 | triple | 三张相同牌点 |
| 6 | 四炸 | quad | 四张相同牌点 |
| 7 | 王炸 | joker_bomb | 大王 + 小王 |
| 8 | 四幺四 | four_one_four | 两张 4 + 一张 A，纯红>纯黑>花 |

**牌型识别逻辑（`hand_type.py`）：**

```
hand_type.py
├── detect_hand_type(cards) → HandType   # 识别任意牌组属于哪种牌型
├── can_beat(my_cards, last_cards) → bool # 我的牌能否打上家
├── get_beat_options(hand, last_play)    # 从手牌中枚举所有可出选择
└── sort_hand(cards)                      # 手牌排序
```

### 3.3 Player（玩家）

```
属性:
  - id: str
  - seat: 0|1|2|3          # 座位号
  - team: 0|1               # 队伍 (0=A队, 1=B队)
  - hand: List[Card]         # 手牌
  - finished: boolean        # 是否已出完牌
  - finish_order: int        # 出完顺序（1~4）

方法:
  - sort_hand()
  - has_cards(indices)
  - remove_cards(indices) → List[Card]
  - can_cha(rank) → bool          # 能否叉某牌点
  - can_dian(rank) → bool          # 能否点某牌点
  - get_cha_cards(rank) → [Card, Card]
  - get_dian_card(rank) → Card
  - get_max_single() → Card         # 获取最大单牌（进贡用）
```

### 3.4 Game（单局游戏状态机）

```
状态:
  TRIBUTE            → 进贡阶段
  PRE_PLAY           → 是否立棍选择阶段
  PLAYING            → 出牌阶段
  CHA_ASKING        → 询问叉牌中
  DIAN_ASKING        → 询问点牌中
  ROUND_END          → 一局结束
```

完整状态转移：

```
    ┌──────────┐
    │ INIT     │
    └────┬─────┘
         │ 进贡判断
    ┌────▼──────┐
    │ TRIBUTE   │  ← 进贡/还贡交互
    └────┬──────┘
         │ 立棍选择
    ┌────▼──────┐
    │ PRE_PLAY │  ← 每人是否立棍
    └────┬──────┘
         │
    ┌────▼──────┐     出单张(非王)且有人可叉
    │ PLAYING  ├───────────────────┐
    └────▲─────┘                   │
         │                        │
         │                    ┌────▼──────────┐
         │                    │ CHA_ASKING    │
         │                    └────┬──────┬───┘
         │             有人点       │      │ 无人点(所有可叉者都Pass)
         │    ┌────────────┘      │      │
         │    │                   │      └──────┐
         │    │              ┌────▼──────┐      │
         │    │              │ DIAN_ASKING│     │
         │    │              └────┬───────┘      │
         │    │                   │              │
         │    │ 无人点             有人点         │
         │    │ (所有可点者均Pass)   │              │
         │    │                   │              │
         │    │              ┌────▼──────┐       │
         │    │              │ PLAYING   │       │
         │    │              └──────────┘       │
         │    │                                │
         │    └────────────────────────────────┘
         │
    ┌────▼──────┐
    │ROUND_END  │  → 结算 → 进入下一局
    └───────────┘
```

### 3.5 Room（房间）

```
属性:
  - id: str
  - players: List[Player]
  - game: Game
  - team_levels: {0: "3"~"A", 1: "3"~"A"}   # 两队各自独立的级别
  - on_stage_team: 0|1                         # 当前台上队伍
  - rounds: List[RoundResult]                  # 历史局

RoundResult:
  - finish_order: List[int]    # 四名玩家出完牌的顺序（座位号，先出完的在前）
  - is_quan_dong: boolean
  - is_ban_dong: boolean
  - is_fan_dong: boolean
  - is_li_gun: boolean         # 本局是否触发立棍
  - li_gun_success: boolean    # 立棍成功/撅棍
  - next_force_tribute: boolean  # 下一局是否强制执行全洞进贡还贡
```

**升/降级与台上/台下关系：**

- 两队级别**完全独立**，下台时级别冻结，上台后从自己的级别继续
- 升级条件：台上队伍**全洞(+2级) / 半洞(+1级)**；台下队无论何种胜法均**只上台、不升级**
- 3/J/A 是不可跳过的检查点，必须全洞才可离开；多级提升遇到第一个检查点立即停住
- 实际可达级别序列：**3 → 5 → 6 → 7 → 8 → 9 → 10 → J → K → A**（4/Q/2 永远不可达）
- 打J被台下先出完(反洞) → **直J**: 台上队退回打3并下台
- 打A被台下先出完(反洞) → **直A**: 台上队退回打J并下台
- 台下队立棍成功时例外：**上台 + 升2级**（同样受升级截断约束）

**胜利条件判断（`check_game_over`）：**

```python
def check_game_over(team, level_before, level_after):
    # 触发条件：打A全洞 → 回到打3，然后再次打3全洞
    if level_before == "A" and level_after == "3":
        team.awaiting_final_3 = True   # 标记：下次打3全洞即胜
    if level_before == "3" and is_quan_dong and team.awaiting_final_3:
        return True   # 游戏结束，该队获胜
    return False
```

胜利路径：`打3全洞 → ... → 打J全洞 → ... → 打A全洞 → 打3全洞 → 游戏结束`

---

## 四、通辽特色 —— 立棍系统

立棍是通辽4A4区别于其他地区4A4的主要特点，需要在进贡结束后出牌开始前的前端UI中实现一个特殊的选择交互。

### 4.1 触发时机

```
进贡/还贡流程结束后 → 进入"立棍选择阶段" → 按出牌顺序轮询每个玩家
```

### 4.2 选择流程

```
轮次:
  每个玩家选择: [立棍] 或 [不立棍]
  
  ↓ 无人选择立棍 → 进入正常出牌流程
  ↓ 多于1人选择 → 继续下一轮次
  ↓ 只有1人选择 → 进入立棍流程
```

### 4.3 立棍流程

```
状态:
  li_gun_mode: boolean
  li_gun_player: seat      # 立棍的玩家
  li_gun_teammate: seat    # 立棍者的队友（本局不可操作）

游戏变化:
  - 立棍者获得首轮出牌权
  - 队友手牌自动托管(或隐藏)，不能出牌
  - 对手两名玩家正常出牌，可以正常叉/点
  - 其他规则不变
```

### 4.4 立棍结算

```
立棍成功(立棍者第一个出完):
  台上队立棍成功 → 连升3级(不越过3/J/A)
  台下队立棍成功 → 上台 + 升2级
  下一局: 全洞进贡还贡

撅棍(立棍者不是第一个出完):
  立即结束本局
  对方队视为台上 + 升2级
  下一局: 全洞进贡还贡
```

**关于立棍和级牌(会)的关系**：立棍不改变当前级别，只影响本局奖惩级数。被立棍一方的牌不能包含级牌和2，与正常规则一致。

---

## 五、核心时序设计

### 5.1 出牌主流程

```
正常顺序: P0 → P1 → P2 → P3 → P0 → ...

叉打断:  P0出单X → 询问P1能叉否 → 询问P2能叉否 → P2叉!
         → 跳过P0和P1 → 询问P2下家P3能否点 → 询问P0能否点 → P0点！
         → P0获得出牌权 → 继续正常顺序

死叉:  P0出单X → ... → P2叉! → 无人点 → P2获得出牌权
```

### 5.2 叉牌询问机制

```
1. 玩家出单张(非王)后
2. 服务器计算所有可叉的玩家（非出牌者，手中有对子）
3. 向可叉的玩家依次发送 cha_ask 事件
4. 所有可叉玩家都 Pass → 继续正常出牌
5. 有人叉 → 叉的玩家获得即时出牌权 → 进入点牌询问
```

### 5.3 点牌询问机制

```
1. 有人叉后
2. 服务器计算所有可点的玩家（非叉者，手中有同点单牌）
3. 向可点的玩家依次发送 dian_ask 事件
4. 所有可点玩家都 Pass → 叉的玩家获得出牌权(死叉)
5. 有人点 → 点的玩家获得出牌权 → 恢复正常出牌
```

### 5.4 防作弊设计 — 叉牌询问

为防通过询问顺序判定身份，叉牌询问须：

```
- 用前端倒计时(如15s)遮掩后端询问，让所有可叉者在界面上同时曝光但倒计时相同
- 同一时刻所有可叉者看到"是否叉牌"选项
- 点牌询问同理
```

### 5.5 接风

```
玩家A出完牌 → 下一个活跃玩家→ B是A队友 → B是最后的出牌者 → B出完 → 风给B → B重新出牌
或：所有人 pass → A → B → B直接获得出牌权

风与叉/点叉：叉打断风，正常风仍遵循 叉/点打断。
```

---

## 六、通信协议

### 6.1 REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/rooms` | GET | 房间列表 |
| `/api/rooms` | POST | 创建房间 |
| `/api/rooms/<id>` | GET | 房间信息（人数、级别等） |

### 6.2 WebSocket 事件

**客户端 → 服务端：**

| 事件 | 数据 | 说明 |
|------|------|------|
| `join_room` | `{room_id, name}` | 加入房间 |
| `start_game` | `{}` | 房主开始 |
| `play_cards` | `{card_indices}` | 出牌 |
| `pass_turn` | `{}` | 不出 |
| `respond_cha` | `{do_cha: bool}` | 是否叉 |
| `respond_dian` | `{do_dian: bool}` | 是否点 |
| `respond_tribute` | `{indices}` | 进贡选择 |
| `respond_tribute_back` | `{indices}` | 还贡选择 |
| `respond_ligun` | `{do_ligun: bool}` | 是否立棍 |

**服务端 → 客户端：**

| 事件 | 说明 |
|------|------|
| `room_state` | 房间状态更新（人数/级别/台上队伍等） |
| `game_started` | 本局开始，附发牌信息 |
| `your_turn` | 轮到你了（action=play/cha/dian/tribute/ligun） |
| `game_action` | 其他玩家的出牌动作广播 |
| `round_end` | 本局结束，结算信息 |
| `player_left` | 玩家掉线/离开 |
| `error` | 错误信息 |

### 6.3 信息隐藏

每个玩家的 `game_state` 推送只含：
- 自己手牌（完整可见）
- 其他玩家手牌数量
- 当前桌面出牌
- 出牌记录摘要

---

## 七、前端设计

### 7.1 页面路由

```
pages/index       → 大厅：创建/加入房间
pages/room        → 房间：等待玩家，开始游戏
pages/game       → 游戏主界面
```

### 7.2 游戏界面布局（横屏 / 自适应）

```
┌─────────────────────────────────────┐
│  对家(顶) 姓名 | 手牌数 | role标签  │
│  ┌───────────────────────────────┐   │
│  │        出牌显示区              │   │
│  │   (中央桌面，显示所有玩家出牌)    │   │
│  │                              │   │
│  └───────────────────────────────┘   │
│  左右为左右玩家信息(小)              │
│  ┌───────────────────────────────┐   │
│  │         我的手牌              │   │
│  │   可选/已选牌高亮，滑动      │   │
│  │   [出牌] [Pass] 按钮          │   │
│  └───────────────────────────────┘   │
└─────────────────────────────────────┘
```

> 详细的 UI 原型和交互细节将在项目搭建后制作。

### 7.3 前端技术选型

- 框架: Vue 3 Composition API
- 状态管理: Pinia（轻量替代 Vuex）
- WebSocket: `uni.connectSocket` + 二次封装
- CSS: uView UI 作为基础组件库，手写内嵌样式实现通辽4A4定制化界面

### 7.4 关键交互

| 交互 | 实现方式 |
|------|---------|
| 选牌出牌 | 点击手牌高亮，支持单选/多选/清空 |
| 叉/点选择 | 模态弹窗 + 倒计时(15s) |
| 立棍选择 | 弹出选项 yes/no，本环节专有界面 |
| 进贡选牌 | 列表选择符合规则的牌 |
| 手牌排序 | 自动按牌型聚类(color) + 大小升序排列 |
| 防误触 | Pass 按钮确认弹窗 |

---

## 八、文件结构

```
Tongliao4A4/
├── server/                    # Python 后端
│   ├── server.py              # Flask 入口
│   ├── requirements.txt       # 依赖列表
│   ├── config.py              # 配置（端口/SocketIO 参数等）
│   ├── models/
│   │   ├── __init__.py
│   │   ├── card.py           # 牌/Card/花色/权重
│   │   ├── deck.py           # 牌堆/洗牌/发牌
│   │   ├── hand_type.py      # 8 种牌型识别/比较
│   │   ├── player.py         # 玩家手牌管理/叉点查询
│   │   ├── game.py           # 单局状态机/出牌校验/叉点循环
│   │   ├── room.py           # 升级/台上台下
│   │   ├── tribute.py        # 通辽特色：进贡/还贡/反贡/土皇上
│   │   └── ligun.py          # 通辽特色：立棍/撅棍系统
│   └── routes/
│       ├── __init__.py
│       ├── api.py             # REST 路由
│       └── ws.py              # WebSocket 事件处理
│
├── frontend/                  # uni-app 前端
│   ├── package.json
│   ├── pages/
│   │   ├── index/index.vue    # 大厅
│   │   ├── room/room.vue      # 房间
│   │   └── game/game.vue       # 游戏主界面
│   ├── components/
│   │   ├── CardFace.vue        # 卡牌面组件
│   │   ├── PlayerHand.vue      # 手牌展示组件
│   │   ├── GameBoard.vue       # 桌面出牌区
│   │   ├── TributeModal.vue    # 进贡选择弹窗
│   │   └── LigunModal.vue      # 立棍选择弹窗
│   ├── utils/
│   │   ├── ws.js                # WebSocket 封装
│   │   ├── api.js               # HTTP 请求封装
│   │   └── constants.js          # 常量（牌型/花色枚举）
│   ├── store/
│   │   ├── game.js               # 游戏状态 Pinia store
│   │   └── room.js               # 房间状态
│   ├── static/
│   └── App.vue
│
├── DESIGN.md                  # 本文档
├── GAME_RULES.md              # 通辽4A4完整规则
└── README.md                  # 项目说明 + 快速开始
```

---

## 九、游戏最终胜利条件

- 双方初始打3。持有红桃3的队伍获得第一局的上台权利。
- 按级别顺序推进：3 → 4 → … → A。
- 团队在打A且全洞获胜 → 回到打3。该队在打3再全洞获胜 → **该队赢得整场游戏**。
- 一队获得最终胜利，游戏结束。

### 伪代码

```
def check_game_end(team_that_just_finished):
    # 条件1: 刚打完打A全洞获胜 → 回到打3
    if team.state == "A_WON" and game.just_won_at_A:
        team.level = "3"
        team.state = "BACK_TO_3"
    
    # 条件2: 回到打3后再次全洞获胜 → 最终胜利
    if team.state == "BACK_TO_3" and game.is_quan_dong:
        declare_winner(team)
```

## 十、游戏流程完整伪代码

```
class Game:
    def start_round():
        # 1. 判断是否需要进贡
        if previous_round_has_tribute:
            do_tribute_phase()
        
        # 2. 发牌
        deck.shuffle()
        deal_cards(players)   # 玩家手牌排序
        
        # 3. 立棍选择
        do_ligun_phase()
        if li_gun_mode:
            disable_teammate_controls()

        # 4. 确定首家
        if first_game:
            first_player = find_red_3_holder()
        elif tribute_happened:
            # 被进贡方决定谁先出
        else:
            # 上一局最先出完者
        
        # 5. 出牌循环
        current = first_player
        while not round_over:
            action = wait_for_action(current)
            
            if action.type == "PLAY":
                if is_cha_possible(action.cards):
                    do_cha_phase()
                execute_play(current, action.cards)
            
            elif action.type == "PASS":
                consecutive_passes += 1
                if consecutive_passes >= 3 and everyone_passed:
                    last_player_gets_new_turn()
            
            elif action.type == "CHA":
                enter_cha_phase()
            
            elif action.type == "DIAN":
                enter_dian_phase()
        
        # 6. 结算
        rank_players_by_finish_order()
        # Determine outcome: 全洞 / 半洞 / ...
        
        # 7. 根据结果升级/切换台上台下
        apply_level_changes()
        
        # 8. 检查是否全场胜利
        check_game_end()

### 最终胜利条件

- 双方从打3开始。第一局红桃3持有者上台。
- 队伍从打3 → ... → A → 回到打3 → 全洞获胜。**打3再次全洞获胜才宣告最终胜利。**
- `打A → 回到打3` 是必要条件，不是充分条件。必须再次全洞获胜。

```

---

## 十一、开发阶段规划

### Phase 1: 后端核心规则引擎
- `card.py`, `deck.py`, `hand_type.py`：牌型识别/比较算法
- `player.py`：玩家模型/叉点查询
- `game.py`：状态机/出牌循环
- 单元测试（核心规则覆盖）

### Phase 2: 通信层
- Flask 工程搭建
- REST API 实现
- WebSocket 事件处理
- 单人调试前端（用浏览器 Hook）

### Phase 3: 进贡/立棍模块
- `tribute.py`：全洞/半洞进贡
- `ligun.py`：立棍流程
- 这两块逻辑脱离核心规则，应先确保核心出牌正确

### Phase 4: uni-app 前端
- 大厅/房间页面
- 游戏界面（牌面/桌面/选牌交互）
- 叉点/进贡/立棍弹窗
- H5 编译测试

### Phase 5: 微信小程序编译
- uni-app 编译微信小程序
- ws 兼容性调整
- 微信内真机测试

### Phase 6: 打磨/deploy
- GitHub README 编写
- 部署脚本
- 微信群分享体验

---

## 十一、与其它 4A4 实现的主要区别

| 特性 | 原4A4实现 | 通辽4A4 本项目 |
|------|----------|----------|
| 双龙 | 无限制 | **不能自由出双龙(除清牌)、只能被 4A4 炸** |
| 级牌 | 仅对单张有影响 | **所有牌型中级牌同等权重** |
| 进贡 | 全洞/半洞进贡 | **全洞还贡/半洞/反贡/土皇上完整体系** |
| 立棍 | 无 | **✓ 通辽特色：立棍成功/撅棍机制** |
| 平台 | H5 浏览器 | **微信小程序 + H5 双端** |
| 叉牌询问 | 顺时针逐一询问 | **防作弊：倒计时掩盖，多个可叉者同时曝光** |