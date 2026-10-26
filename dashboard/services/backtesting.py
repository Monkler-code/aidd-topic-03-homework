from bisect import bisect_right
from datetime import datetime, time, timedelta
from decimal import Decimal, DecimalException, ROUND_FLOOR, localcontext

from django.db import transaction as db_transaction
from django.utils import timezone

from dashboard.models import HistoricalPrice, StrategyRun, StrategyTrade

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
MAX_BACKTEST_DAYS = 3650
MAX_LOOKBACK_DAYS = 3650


def _stored_decimal(value, model, field_name, description):
    """Round a calculated value to its database field and reject overflow."""
    field = model._meta.get_field(field_name)
    value = Decimal(value)
    if not value.is_finite():
        raise ValueError(f"{description} не помещается в допустимый диапазон.")

    quantum = Decimal(1).scaleb(-field.decimal_places)
    precision = max(
        50,
        field.max_digits + 2,
        len(value.as_tuple().digits) + field.decimal_places + 2,
        value.adjusted() + field.decimal_places + 2,
    )
    with localcontext() as context:
        context.prec = precision
        rounded = value.quantize(quantum)

    max_value = Decimal(10) ** (field.max_digits - field.decimal_places)
    if abs(rounded) >= max_value:
        raise ValueError(f"{description} превышает допустимый диапазон хранения.")
    return rounded


@db_transaction.atomic
def run_backtest(strategy, start_date, end_date):
    try:
        return _run_backtest(strategy, start_date, end_date)
    except (DecimalException, OverflowError) as exc:
        raise ValueError(
            "Результаты симуляции превышают допустимый числовой диапазон."
        ) from exc


def _run_backtest(strategy, start_date, end_date):
    if start_date > end_date:
        raise ValueError("Начальная дата должна быть не позже конечной.")
    if (end_date - start_date).days > MAX_BACKTEST_DAYS:
        raise ValueError("Период симуляции не может превышать 3650 дней.")
    if end_date > timezone.localdate():
        raise ValueError("Конечная дата не может быть в будущем.")
    if strategy.lookback_days > MAX_LOOKBACK_DAYS:
        raise ValueError("Окно анализа не может превышать 3650 дней.")
    if strategy.commission_percent > ONE_HUNDRED:
        raise ValueError("Комиссия не может превышать 100%.")

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
                    buy_quantity = _stored_decimal(
                        buy_quantity,
                        StrategyTrade,
                        "quantity",
                        "Количество сделки",
                    )
                    notional = buy_quantity * price
                    commission = _stored_decimal(
                        notional * fee_rate,
                        StrategyTrade,
                        "commission",
                        "Комиссия сделки",
                    )
                    entry_cost = notional + commission
                    quantity = buy_quantity
                    cash -= entry_cost
                    trade_rows.append(
                        StrategyTrade(
                            side=StrategyTrade.Side.BUY,
                            executed_at=row.captured_at,
                            quantity=buy_quantity,
                            price=_stored_decimal(
                                price, StrategyTrade, "price", "Цена сделки"
                            ),
                            commission=commission,
                        )
                    )

        elif quantity > ZERO:
            net_proceeds_factor = ONE_HUNDRED - strategy.commission_percent
            target_net_proceeds = (
                entry_cost
                * (ONE_HUNDRED + strategy.sell_profit_percent)
                / ONE_HUNDRED
            )
            sell_threshold = (
                target_net_proceeds * ONE_HUNDRED / (quantity * net_proceeds_factor)
                if net_proceeds_factor > ZERO
                else None
            )
            if sell_threshold is not None and price >= sell_threshold:
                notional = quantity * price
                commission = _stored_decimal(
                    notional * fee_rate,
                    StrategyTrade,
                    "commission",
                    "Комиссия сделки",
                )
                realized = notional - commission - entry_cost
                realized = _stored_decimal(
                    realized,
                    StrategyTrade,
                    "realized_pnl",
                    "Прибыль или убыток сделки",
                )
                cash += notional - commission
                trade_rows.append(
                    StrategyTrade(
                        side=StrategyTrade.Side.SELL,
                        executed_at=row.captured_at,
                        quantity=quantity,
                        price=_stored_decimal(
                            price, StrategyTrade, "price", "Цена сделки"
                        ),
                        commission=commission,
                        realized_pnl=realized,
                    )
                )
                closed_trade_results.append(realized)
                quantity = ZERO
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
        commission = _stored_decimal(
            notional * fee_rate,
            StrategyTrade,
            "commission",
            "Комиссия сделки",
        )
        realized = notional - commission - entry_cost
        realized = _stored_decimal(
            realized,
            StrategyTrade,
            "realized_pnl",
            "Прибыль или убыток сделки",
        )
        cash += notional - commission
        trade_rows.append(
            StrategyTrade(
                side=StrategyTrade.Side.SELL,
                executed_at=last_row.captured_at,
                quantity=quantity,
                price=_stored_decimal(
                    last_row.close, StrategyTrade, "price", "Цена сделки"
                ),
                commission=commission,
                realized_pnl=realized,
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
    initial_capital = _stored_decimal(
        initial_capital, StrategyRun, "initial_capital", "Начальный капитал"
    )
    final_equity = _stored_decimal(
        final_equity, StrategyRun, "final_equity", "Конечный капитал"
    )
    return_percent = _stored_decimal(
        return_percent, StrategyRun, "return_percent", "Доходность"
    )
    max_drawdown = _stored_decimal(
        max_drawdown,
        StrategyRun,
        "max_drawdown_percent",
        "Максимальная просадка",
    )
    run = StrategyRun.objects.create(
        strategy=strategy,
        strategy_snapshot={
            "strategy_name": strategy.name,
            "share": {
                "id": strategy.share_id,
                "ticker": strategy.share.ticker,
                "name": strategy.share.name,
                "currency": strategy.share.currency,
            },
            "buy_drop_percent": str(strategy.buy_drop_percent),
            "lookback_days": strategy.lookback_days,
            "sell_profit_percent": str(strategy.sell_profit_percent),
            "commission_percent": str(strategy.commission_percent),
            "initial_capital": str(initial_capital),
        },
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        final_equity=final_equity,
        return_percent=return_percent,
        max_drawdown_percent=max_drawdown,
        winning_trades=sum(result > ZERO for result in closed_trade_results),
        losing_trades=sum(result < ZERO for result in closed_trade_results),
    )
    for item in trade_rows:
        item.run = run
    StrategyTrade.objects.bulk_create(trade_rows)
    return run
