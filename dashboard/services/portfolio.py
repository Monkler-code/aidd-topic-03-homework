from collections import defaultdict
from decimal import Decimal

from django.db import transaction as db_transaction

from dashboard.models import Portfolio, Transaction

ZERO = Decimal("0")


def _portfolio_transactions(portfolio):
    prefetched = getattr(portfolio, "_prefetched_objects_cache", {})
    if "transactions" in prefetched:
        return list(portfolio.transactions.all())
    return portfolio.transactions.select_related("share").iterator(chunk_size=1000)


def calculate_positions(portfolio, transactions=None):
    if transactions is None:
        transactions = _portfolio_transactions(portfolio)
    positions = defaultdict(lambda: {"quantity": ZERO, "average_cost": ZERO})
    for item in transactions:
        position = positions[item.share_id]
        if item.side == Transaction.Side.BUY:
            old_cost = position["quantity"] * position["average_cost"]
            added_cost = item.quantity * item.price + item.commission
            position["quantity"] += item.quantity
            position["average_cost"] = (
                (old_cost + added_cost) / position["quantity"]
                if position["quantity"]
                else ZERO
            )
        else:
            position["quantity"] -= item.quantity
            if position["quantity"] <= ZERO:
                position["quantity"] = ZERO
                position["average_cost"] = ZERO
    return positions


@db_transaction.atomic
def record_transaction(
    *, portfolio, share, side, quantity, price, commission=ZERO
):
    """Record a trade while enforcing long-only inventory and average cost."""
    portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
    quantity = Decimal(quantity)
    price = Decimal(price)
    commission = Decimal(commission)

    if quantity <= ZERO:
        raise ValueError("Количество должно быть больше нуля.")
    if price <= ZERO:
        raise ValueError("Цена должна быть больше нуля.")
    if commission < ZERO:
        raise ValueError("Комиссия не может быть отрицательной.")
    if share.currency.upper() != portfolio.currency.upper():
        raise ValueError("Валюты акции и портфеля должны совпадать.")
    if side not in Transaction.Side.values:
        raise ValueError("Неизвестный тип сделки.")

    realized_pnl = ZERO
    if side == Transaction.Side.SELL:
        position = calculate_positions(portfolio).get(
            share.pk, {"quantity": ZERO, "average_cost": ZERO}
        )
        if quantity > position["quantity"]:
            raise ValueError("Нельзя продать больше акций, чем есть в портфеле.")
        realized_pnl = quantity * (price - position["average_cost"]) - commission

    return Transaction.objects.create(
        portfolio=portfolio,
        share=share,
        side=side,
        quantity=quantity,
        price=price,
        commission=commission,
        realized_pnl=realized_pnl,
    )


def get_portfolio_summary(portfolio):
    state = _new_summary_state()
    for item in _portfolio_transactions(portfolio):
        _apply_summary_transaction(state, item)
    return _build_portfolio_summary(state)


def get_portfolio_summaries(portfolios):
    """Build summaries for a page of portfolios using one streaming query."""
    portfolio_ids = [portfolio.pk for portfolio in portfolios]
    if not portfolio_ids:
        return {}

    states = {portfolio_id: _new_summary_state() for portfolio_id in portfolio_ids}
    transactions = (
        Transaction.objects.filter(portfolio_id__in=portfolio_ids)
        .select_related("share")
        .order_by("portfolio_id", "executed_at", "id")
        .iterator(chunk_size=1000)
    )
    for item in transactions:
        _apply_summary_transaction(states[item.portfolio_id], item)
    return {
        portfolio_id: _build_portfolio_summary(state)
        for portfolio_id, state in states.items()
    }


def _new_summary_state():
    return {
        "positions": {},
        "shares": {},
        "realized_pnl": ZERO,
        "invested": ZERO,
    }


def _apply_summary_transaction(state, item):
    if item.side == Transaction.Side.BUY:
        position = state["positions"].setdefault(
            item.share_id, {"quantity": ZERO, "average_cost": ZERO}
        )
        old_cost = position["quantity"] * position["average_cost"]
        added_cost = item.quantity * item.price + item.commission
        position["quantity"] += item.quantity
        position["average_cost"] = (old_cost + added_cost) / position["quantity"]
        state["shares"][item.share_id] = item.share
        state["invested"] += added_cost
    else:
        state["realized_pnl"] += item.realized_pnl
        position = state["positions"].get(item.share_id)
        if position is not None:
            position["quantity"] -= item.quantity
            if position["quantity"] <= ZERO:
                state["positions"].pop(item.share_id, None)
                state["shares"].pop(item.share_id, None)


def _build_portfolio_summary(state):
    positions = state["positions"]
    shares = state["shares"]
    holdings = []
    market_value = ZERO
    cost_basis = ZERO
    unrealized_pnl = ZERO
    unpriced_tickers = []

    for share_id, position in positions.items():
        quantity = position["quantity"]
        if quantity <= ZERO:
            continue
        share = shares[share_id]
        basis = quantity * position["average_cost"]
        last_price = share.last_price
        value = quantity * last_price if last_price is not None else None
        pnl = value - basis if value is not None else None
        cost_basis += basis
        if value is None:
            unpriced_tickers.append(share.ticker)
        else:
            market_value += value
            unrealized_pnl += pnl
        holdings.append(
            {
                "share": share,
                "quantity": quantity,
                "average_cost": position["average_cost"],
                "last_price": last_price,
                "market_value": value,
                "unrealized_pnl": pnl,
            }
        )

    realized_pnl = state["realized_pnl"]
    has_unpriced_positions = bool(unpriced_tickers)
    if has_unpriced_positions:
        market_value = None
        unrealized_pnl = None
        total_pnl = None
        return_percent = None
    else:
        total_pnl = realized_pnl + unrealized_pnl
        return_percent = (
            total_pnl / state["invested"] * 100 if state["invested"] else ZERO
        )
    return {
        "holdings": holdings,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "return_percent": return_percent,
        "unpriced_tickers": unpriced_tickers,
    }
