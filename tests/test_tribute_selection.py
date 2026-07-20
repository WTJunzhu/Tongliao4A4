"""
TributeSelectionState 单元测试。
覆盖：预选、冲突换牌请求、确认、超时兜底、半洞（单选）等场景。
"""
import pytest
from server.models.card import Card, Suit
from server.models.tribute import TributeSelectionState


def c(rank, suit=Suit.SPADE):
    return Card(suit, rank)


def make_sel_2(cards_override=None):
    """全洞：2 个选择器，2 张牌。"""
    cards = cards_override or {1: c("Q"), 3: c("K")}
    return TributeSelectionState(selector_seats=[0, 2], cards=cards)


def make_sel_1():
    """半洞：1 个选择器，1 张牌。"""
    return TributeSelectionState(selector_seats=[0], cards={3: c("J")})


# ------------------------------------------------------------------
# 基本预选
# ------------------------------------------------------------------

class TestSelect:
    def test_select_free_card(self):
        sel = make_sel_2()
        r = sel.select(0, 1)
        assert r["ok"] and r["status"] == "selected"
        assert sel.selections[0] == 1

    def test_select_nonexistent_giver(self):
        sel = make_sel_2()
        r = sel.select(0, 99)
        assert not r["ok"]
        assert r["reason"] == "invalid_card"

    def test_non_selector_cannot_select(self):
        sel = make_sel_2()
        r = sel.select(1, 1)   # 座位1不是选择器
        assert not r["ok"]
        assert r["reason"] == "not_a_selector"

    def test_reselect_own_card(self):
        """选择器可以换选另一张牌。"""
        sel = make_sel_2()
        sel.select(0, 1)
        r = sel.select(0, 3)
        assert r["ok"] and r["status"] == "selected"
        assert sel.selections[0] == 3

    def test_conflict_creates_swap_request(self):
        """座位2先选1号的牌，座位0再选同一张 → 交换请求。"""
        sel = make_sel_2()
        sel.select(2, 1)
        r = sel.select(0, 1)
        assert r["ok"] and r["status"] == "swap_request"
        assert r["target_seat"] == 2
        assert sel.pending_swap == {"requester_seat": 0, "target_seat": 2}

    def test_select_blocked_during_pending_swap(self):
        """有 pending_swap 时不能继续选牌。"""
        sel = make_sel_2()
        sel.select(2, 1)
        sel.select(0, 1)   # 触发 pending_swap
        r = sel.select(2, 3)
        assert not r["ok"]
        assert r["reason"] == "pending_swap"


# ------------------------------------------------------------------
# 交换请求响应
# ------------------------------------------------------------------

class TestSwapRespond:
    def test_accept_swap(self):
        sel = make_sel_2()
        sel.select(2, 1)    # 座位2选了1号牌
        sel.select(0, 3)    # 座位0选了3号牌（无冲突）
        # 再触发冲突：座位0现在去抢1号牌
        sel.select(0, 1)    # pending_swap: requester=0, target=2
        r = sel.respond_swap(2, True)
        assert r["ok"] and r["swapped"]
        # 交换后：座位0得到1号，座位2得到3号（原来0的选择）
        assert sel.selections[0] == 1
        assert sel.selections[2] == 3
        assert sel.pending_swap is None

    def test_accept_swap_when_requester_had_no_selection(self):
        """requester 原本没有选牌。"""
        sel = make_sel_2()
        sel.select(2, 1)    # 座位2选1号
        # 座位0还没选，直接抢
        sel.select(0, 1)    # pending_swap
        r = sel.respond_swap(2, True)
        assert r["ok"] and r["swapped"]
        assert sel.selections[0] == 1
        assert sel.selections[2] is None   # target 交出牌后没有选择

    def test_reject_swap(self):
        sel = make_sel_2()
        sel.select(2, 1)
        sel.select(0, 1)   # pending_swap
        r = sel.respond_swap(2, False)
        assert r["ok"] and not r["swapped"]
        assert sel.selections[2] == 1   # target 保留原选
        assert sel.pending_swap is None

    def test_only_target_can_respond(self):
        sel = make_sel_2()
        sel.select(2, 1)
        sel.select(0, 1)   # requester=0, target=2
        r = sel.respond_swap(0, True)   # requester 不能响应
        assert not r["ok"]

    def test_no_pending_swap_error(self):
        sel = make_sel_2()
        r = sel.respond_swap(2, True)
        assert not r["ok"]
        assert r["reason"] == "no_pending_swap"


# ------------------------------------------------------------------
# 确认
# ------------------------------------------------------------------

class TestConfirm:
    def test_cannot_confirm_before_all_selected(self):
        sel = make_sel_2()
        sel.select(0, 1)   # 只有座位0选了
        r = sel.confirm(0)
        assert not r["ok"]
        assert r["reason"] == "cannot_confirm_yet"

    def test_cannot_confirm_during_pending_swap(self):
        sel = make_sel_2()
        sel.select(0, 1)
        sel.select(2, 3)
        sel.select(0, 3)   # 触发 pending_swap
        r = sel.confirm(2)
        assert not r["ok"]

    def test_can_confirm_when_all_selected(self):
        sel = make_sel_2()
        sel.select(0, 1)
        sel.select(2, 3)
        assert sel.can_confirm()
        r = sel.confirm(0)
        assert r["ok"] and not r["complete"]
        r = sel.confirm(2)
        assert r["ok"] and r["complete"]
        assert len(sel.confirmations) == 2

    def test_single_selector_confirm(self):
        """半洞：一人选一张，确认即完成。"""
        sel = make_sel_1()
        sel.select(0, 3)
        r = sel.confirm(0)
        assert r["ok"] and r["complete"]

    def test_non_selector_cannot_confirm(self):
        sel = make_sel_2()
        sel.select(0, 1)
        sel.select(2, 3)
        r = sel.confirm(1)
        assert not r["ok"]


# ------------------------------------------------------------------
# 超时兜底
# ------------------------------------------------------------------

class TestResolveTimeout:
    def test_resolve_fills_all(self):
        """两人都没选，超时后各分一张。"""
        sel = make_sel_2()
        sel.resolve_timeout()
        assert sel.selections[0] is not None
        assert sel.selections[2] is not None
        # 两张牌不同
        assert sel.selections[0] != sel.selections[2]
        assert sel.can_confirm()

    def test_resolve_clears_pending_swap(self):
        """有 pending_swap 时超时，先到先得：target 保留，requester 放弃。"""
        sel = make_sel_2()
        sel.select(2, 1)    # 座位2先选1号
        sel.select(0, 1)    # 触发 pending_swap（requester=0）
        sel.resolve_timeout()
        # target(2) 保留 giver=1 的牌；requester(0) 得到剩余的 giver=3 的牌
        assert sel.selections[2] == 1
        assert sel.selections[0] == 3
        assert sel.pending_swap is None

    def test_resolve_keeps_existing_selection(self):
        """已选好的保留，未选的补填。"""
        sel = make_sel_2()
        sel.select(0, 1)    # 座位0选了，座位2没选
        sel.resolve_timeout()
        assert sel.selections[0] == 1
        assert sel.selections[2] == 3   # 剩余牌分给2


# ------------------------------------------------------------------
# to_dict 序列化
# ------------------------------------------------------------------

class TestToDict:
    def test_to_dict_keys(self):
        sel = make_sel_2()
        sel.select(0, 1)
        d = sel.to_dict()
        assert "selector_seats" in d
        assert "cards" in d
        assert "selections" in d
        assert "pending_swap" in d
        assert "confirmations" in d
        assert "can_confirm" in d

    def test_selections_string_keys(self):
        sel = make_sel_2()
        d = sel.to_dict()
        for k in d["selections"]:
            assert isinstance(k, str)

    def test_cards_serialized(self):
        sel = make_sel_2()
        d = sel.to_dict()
        for k, v in d["cards"].items():
            assert isinstance(k, str)
            assert "rank" in v
