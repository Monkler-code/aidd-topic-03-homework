"""Service for strategy backtesting and simulation."""

from __future__ import annotations

from datetime import datetime

from dashboard.models import (
    HistoricalPrice,
    Share,
    StrategyRule,
    StrategyTrade,
    TradingStrategy,
)


class StrategyBacktester:
    """Service for running backtests on trading strategies."""

    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
        self.rules = list(strategy.rules.order_by("priority"))
        self.trades: list[StrategyTrade] = []
        self.virtual_cash = 100000.0  # Start with 100k virtual cash
        self.holdings: dict[str, int] = {}  # ticker -> quantity

    def run_backtest(self, share: Share, days: int = 365) -> list[StrategyTrade]:
        """
        Run a backtest for a strategy on a specific share's historical data.

        Returns the list of simulated trades.
        """
        # Get historical data
        historical_data = (
            HistoricalPrice.objects.filter(share=share)
            .order_by("date")
            .values("date", "open_price", "high", "low", "close", "volume")
        )

        if not historical_data:
            return []

        data_list = list(historical_data)
        if days:
            data_list = data_list[-days:]

        # Simulate each day
        for i, day_data in enumerate(data_list):
            current_price = day_data["close"]
            current_high = day_data["high"]
            current_low = day_data["low"]

            # Calculate change from previous day
            if i > 0:
                prev_price = data_list[i - 1]["close"]
                change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price != 0 else 0
            else:
                change_pct = 0

            # Evaluate rules in priority order
            for rule in self.rules:
                triggered = self._evaluate_rule(rule, current_price, current_high, current_low, change_pct)

                if triggered:
                    self._execute_trade(rule, share, current_price, day_data["date"])

        # Save trades to database
        self._save_trades(share)

        # Update strategy
        self.strategy.last_run_at = datetime.now()
        self.strategy.save(update_fields=["last_run_at"])

        return self.trades

    def _evaluate_rule(
        self,
        rule: StrategyRule,
        current_price: float,
        current_high: float,
        current_low: float,
        change_pct: float,
    ) -> bool:
        """Evaluate a single rule against current market data."""
        field = rule.condition_field
        operator = rule.condition_operator
        value = rule.condition_value

        # Get the value to compare
        if field == "close":
            compare_value = current_price
        elif field == "high":
            compare_value = current_high
        elif field == "low":
            compare_value = current_low
        elif field == "change_pct":
            compare_value = change_pct
        else:
            compare_value = current_price

        # Evaluate the condition
        if operator == "gt":
            return compare_value > value
        elif operator == "lt":
            return compare_value < value
        elif operator == "gte":
            return compare_value >= value
        elif operator == "lte":
            return compare_value <= value
        elif operator == "cross_up":
            # Price crossed above value (previous < value, current >= value)
            return False  # Simplified
        elif operator == "cross_down":
            # Price crossed below value (previous > value, current <= value)
            return False  # Simplified

        return False

    def _execute_trade(
        self,
        rule: StrategyRule,
        share: Share,
        price: float,
        trade_date: datetime,
    ):
        """Execute a simulated trade based on a triggered rule."""
        quantity = 10  # Default trade size

        trade = StrategyTrade.objects.create(
            strategy=self.strategy,
            share=share,
            action=rule.action,
            quantity=quantity,
            price=price,
            date=trade_date,
            rule_triggered=str(rule),
        )
        self.trades.append(trade)

        # Update virtual portfolio
        ticker = share.ticker
        if rule.action == "BUY":
            cost = quantity * price
            if cost <= self.virtual_cash:
                self.virtual_cash -= cost
                self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
            else:
                # Not enough cash, reduce quantity
                quantity = int(self.virtual_cash / price) if price > 0 else 0
                if quantity > 0:
                    cost = quantity * price
                    self.virtual_cash -= cost
                    self.holdings[ticker] = self.holdings.get(ticker, 0) + quantity
        elif rule.action == "SELL":
            if ticker in self.holdings and self.holdings[ticker] > 0:
                actual_qty = min(quantity, self.holdings[ticker])
                revenue = actual_qty * price
                self.virtual_cash += revenue
                self.holdings[ticker] -= actual_qty
                if self.holdings[ticker] <= 0:
                    del self.holdings[ticker]

    def _save_trades(self, share: Share):
        """Mark trades in database."""
        for trade in self.trades:
            trade.save()

    @staticmethod
    def calculate_metrics(trades: list[StrategyTrade], virtual_cash: float) -> dict:
        """Calculate performance metrics for a backtest."""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "final_cash": virtual_cash,
            }

        total_trades = len(trades)
        buy_trades = [t for t in trades if t.action == "BUY"]
        sell_trades = [t for t in trades if t.action == "SELL"]

        # Calculate P&L for sell trades
        profits = []
        for sell_tx in sell_trades:
            # Find matching buy trades (FIFO)
            buy_txs = [
                b for b in buy_trades
                if b.share_id == sell_tx.share_id and b.date <= sell_tx.date
            ]
            if buy_txs:
                avg_buy_price = sum(b.price for b in buy_txs[:sell_tx.quantity]) / min(sell_tx.quantity, len(buy_txs))
                pnl = (sell_tx.price - avg_buy_price) * sell_tx.quantity
                profits.append(pnl)

        winning = sum(1 for p in profits if p > 0)
        losing = sum(1 for p in profits if p < 0)
        win_rate = (winning / len(profits) * 100) if profits else 0.0

        # Calculate total return
        total_profit = sum(profits)
        initial_cash = 100000.0
        total_return_pct = round(((virtual_cash + total_profit) / initial_cash - 1) * 100, 2)

        # Calculate max drawdown (simplified)
        equity_curve = [initial_cash]
        cumulative_pnl = 0
        for pnl in profits:
            cumulative_pnl += pnl
            equity_curve.append(initial_cash + cumulative_pnl)

        peak = equity_curve[0]
        max_drawdown = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            drawdown = ((peak - eq) / peak * 100) if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return {
            "total_trades": total_trades,
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": round(win_rate, 2),
            "total_return_pct": total_return_pct,
            "max_drawdown_pct": round(max_drawdown, 2),
            "final_cash": round(virtual_cash, 2),
        }
