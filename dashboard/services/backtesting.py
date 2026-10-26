from bisect import bisect_right
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_FLOOR

from django.db import transaction as db_transaction
from django.utils import timezone

from dashboard.models import HistoricalPrice, StrategyRun, StrategyTrade

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
SIX_PLACES = Decimal("0.000001")
MAX_BACKTEST_DAYS = 3650
MAX_LOOKBACK_DAYS = 3650


def _money(value):
    return value.quantize(SIX_PLACES)


@db_transaction.atomic
def run_backtest(strategy, start_date, end_date):
    if start_date > end_date:
        raise ValueError("Начальная дата должна быть не позже конечной.")
    if (end_date - start_date).days > MAX_BACKTEST_DAYS:
        raise ValueError("Период симуляции не может превышать 3650 дней.")
    if end_date > timezone.localdate():
        raise ValueError("Конечная дата не может быть в будущем.")
    if strategy.lookback_days > MAX_LOOKBACK_DAYS:
        raise ValueError("Окно анализа не может превышать 3650 дней.")

    try:
        history_start = start_date - timedelta(days=strategy.lookback_days)
        history_end = end_date + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("Указана дата за пределами поддерживаемого диапазона.") from exc

    current_timezone = timezone.get_current_timezone()
    history_start_at = timezone.make_aware(
        datetime.combine(history_start, time.min), current_timezone
    )
    history_end_at = timezone.make_aware(
        datetime.combine(history_end, time.min), current_timezone
    )

    rows = list(
        HistoricalPrice.objects.filter(
            share=strategy.share,
            captured_at__gte=history_start_at,
            captured_at__lt=history_end_at,
        ).order_by("captured_at")
    )
    trading_rows = [
        row
        for row in rows
        if timezone.localtime(row.captured_at).date() >= start_date
    ]
    if not trading_rows:
        raise ValueError("За выбранный период нет сохранённых дневных цен.")

    prices_by_date = [timezone.localtime(row.captured_at).date() for row in rows]
    cash = strategy.initial_capital
    initial_capital = strategy.initial_capital
    quantity = ZERO
    average_entry = ZERO
    entry_cost = ZERO
    fee_rate = strategy.commission_percent / ONE_HUNDRED
    peak_equity = initial_capital
    max_drawdown = ZERO
    trade_rows = []
    closed_trade_results = []

    for row in trading_rows:
        price = row.close
        day = timezone.localtime(row.captured_at).date()
        lookback_date = day - timedelta(days=strategy.lookback_days)
        reference_index = bisect_right(prices_by_date, lookback_date) - 1
        reference_price = rows[reference_index].close if reference_index >= 0 else None

        if quantity == ZERO and reference_price:
            buy_threshold = reference_price * (ONE_HUNDRED - strategy.buy_drop_percent) / ONE_HUNDRED
            if price <= buy_threshold:
                affordable = cash / (price * (Decimal("1") + fee_rate))
                buy_quantity = affordable.to_integral_value(rounding=ROUND_FLOOR)
                if buy_quantity > ZERO:
                    notional = buy_quantity * price
                    commission = notional * fee_rate
                    entry_cost = notional + commission
                    average_entry = entry_cost / buy_quantity
                    quantity = buy_quantity
                    cash -= entry_cost
                    trade_rows.append(
                        StrategyTrade(
                            side=StrategyTrade.Side.BUY,
                            executed_at=row.captured_at,
                            quantity=buy_quantity,
                            price=price,
                            commission=_money(commission),
                        )
                    )

        elif quantity > ZERO:
            sell_threshold = average_entry * (
                ONE_HUNDRED + strategy.sell_profit_percent
            ) / ONE_HUNDRED
            if price >= sell_threshold:
                notional = quantity * price
                commission = notional * fee_rate
                realized = notional - commission - entry_cost
                cash += notional - commission
                trade_rows.append(
                    StrategyTrade(
                        side=StrategyTrade.Side.SELL,
                        executed_at=row.captured_at,
                        quantity=quantity,
                        price=price,
                        commission=_money(commission),
                        realized_pnl=_money(realized),
                    )
                )
                closed_trade_results.append(realized)
                quantity = ZERO
                average_entry = ZERO
                entry_cost = ZERO

        equity = cash + quantity * price
        peak_equity = max(peak_equity, equity)
        if peak_equity:
            max_drawdown = max(
                max_drawdown,
                (peak_equity - equity) / peak_equity * ONE_HUNDRED,
            )

    last_row = trading_rows[-1]
    if quantity > ZERO:
        notional = quantity * last_row.close
        commission = notional * fee_rate
        realized = notional - commission - entry_cost
        cash += notional - commission
        trade_rows.append(
            StrategyTrade(
                side=StrategyTrade.Side.SELL,
                executed_at=last_row.captured_at,
                quantity=quantity,
                price=last_row.close,
                commission=_money(commission),
                realized_pnl=_money(realized),
            )
        )
        closed_trade_results.append(realized)

    final_equity = cash
    peak_equity = max(peak_equity, final_equity)
    if peak_equity:
        max_drawdown = max(
            max_drawdown,
            (peak_equity - final_equity) / peak_equity * ONE_HUNDRED,
        )
    return_percent = (
        (final_equity - initial_capital) / initial_capital * ONE_HUNDRED
    )
    run = StrategyRun.objects.create(
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        initial_capital=_money(initial_capital),
        final_equity=_money(final_equity),
        return_percent=_money(return_percent),
        max_drawdown_percent=_money(max_drawdown),
        winning_trades=sum(result > ZERO for result in closed_trade_results),
        losing_trades=sum(result < ZERO for result in closed_trade_results),
    )
    for item in trade_rows:
        item.run = run
    StrategyTrade.objects.bulk_create(trade_rows)
    return run
