from collections import defaultdict
from decimal import Decimal

from django.db import transaction as db_transaction

from dashboard.models import Portfolio, Transaction

ZERO = Decimal("0")


def _portfolio_transactions(portfolio):
    prefetched = getattr(portfolio, "_prefetched_objects_cache", {})
    if "transactions" in prefetched:
        return list(portfolio.transactions.all())
    return list(portfolio.transactions.select_related("share").all())


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
    transactions = _portfolio_transactions(portfolio)
    positions = calculate_positions(portfolio, transactions)
    shares = {item.share_id: item.share for item in transactions}
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

    realized_pnl = sum((item.realized_pnl for item in transactions), ZERO)
    invested = sum(
        (
            item.quantity * item.price + item.commission
            for item in transactions
            if item.side == Transaction.Side.BUY
        ),
        ZERO,
    )
    total_pnl = realized_pnl + unrealized_pnl
    return {
        "holdings": holdings,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "return_percent": total_pnl / invested * 100 if invested else ZERO,
        "unpriced_tickers": unpriced_tickers,
    }
