"""Service for portfolio management and P&L calculations."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from dashboard.models import Portfolio, Share, Transaction


class PortfolioCalculator:
    """Service for portfolio calculations using weighted average cost method."""

    @staticmethod
    def create_portfolio(user, name: str) -> Portfolio:
        """Create a new portfolio for the user."""
        return Portfolio.objects.create(user=user, name=name)

    @staticmethod
    def add_transaction(
        portfolio: Portfolio,
        share: Share,
        transaction_type: str,
        quantity: int,
        price: float,
        commission: float = 0,
    ) -> Transaction:
        """Add a buy or sell transaction to a portfolio."""
        return Transaction.objects.create(
            portfolio=portfolio,
            share=share,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            commission=commission,
        )

    @staticmethod
    def get_holdings(portfolio: Portfolio) -> list[dict]:
        """
        Calculate current holdings for a portfolio using weighted average cost.

        Returns a list of dicts with:
        - share info
        - quantity held
        - average buy price
        - current price
        - market value
        - unrealized P&L (absolute and percentage)
        """
        transactions = portfolio.transactions.select_related("share").order_by("date")

        # Track quantity and total cost per share
        holdings: dict[str, dict] = {}

        for tx in transactions:
            ticker = tx.share.ticker
            if ticker not in holdings:
                holdings[ticker] = {
                    "share_id": tx.share.id,
                    "ticker": tx.share.ticker,
                    "name": tx.share.name,
                    "figi": tx.share.figi,
                    "currency": tx.share.currency,
                    "quantity": 0,
                    "total_cost": 0.0,
                    "average_price": 0.0,
                    "current_price": tx.share.last_price or 0.0,
                }

            holding = holdings[ticker]

            if tx.transaction_type == "BUY":
                cost = tx.quantity * tx.price + tx.commission
                old_total_cost = holding["total_cost"]
                old_quantity = holding["quantity"]
                holding["quantity"] += tx.quantity
                holding["total_cost"] = old_total_cost + cost
                # Weighted average price
                if holding["quantity"] > 0:
                    holding["average_price"] = round(
                        holding["total_cost"] / holding["quantity"], 2
                    )
            else:  # SELL
                # Reduce quantity, average price stays the same
                holding["quantity"] -= tx.quantity
                if holding["quantity"] > 0:
                    # Reduce total cost proportionally
                    holding["total_cost"] = holding["average_price"] * holding["quantity"]
                else:
                    holding["total_cost"] = 0.0
                    holding["average_price"] = 0.0

        # Calculate current values
        result = []
        for ticker, holding in holdings.items():
            if holding["quantity"] <= 0:
                continue

            current_price = holding.get("current_price", 0) or 0
            market_value = holding["quantity"] * current_price
            cost_basis = holding["total_cost"]
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (
                round((unrealized_pnl / cost_basis) * 100, 2) if cost_basis > 0 else 0.0
            )

            result.append({
                "share_id": holding["share_id"],
                "ticker": holding["ticker"],
                "name": holding["name"],
                "figi": holding["figi"],
                "currency": holding["currency"],
                "quantity": holding["quantity"],
                "average_price": holding["average_price"],
                "current_price": current_price,
                "market_value": round(market_value, 2),
                "cost_basis": round(cost_basis, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": unrealized_pnl_pct,
            })

        return result

    @staticmethod
    def get_portfolio_summary(portfolio: Portfolio) -> dict:
        """Get a summary of portfolio value and performance."""
        holdings = PortfolioCalculator.get_holdings(portfolio)

        total_market_value = sum(h["market_value"] for h in holdings)
        total_cost_basis = sum(h["cost_basis"] for h in holdings)
        total_unrealized_pnl = total_market_value - total_cost_basis
        total_pnl_pct = (
            round((total_unrealized_pnl / total_cost_basis) * 100, 2)
            if total_cost_basis > 0
            else 0.0
        )

        # Calculate realized P&L from sell transactions using FIFO
        realized_pnl = 0.0
        buy_transactions = list(
            portfolio.transactions.filter(transaction_type="BUY").order_by("date")
        )
        buy_finger = 0
        buy_qty_remaining = buy_transactions[buy_finger].quantity if buy_transactions else 0

        for sell_tx in portfolio.transactions.filter(transaction_type="SELL").order_by("date"):
            sell_qty = sell_tx.quantity
            remaining_to_fill = sell_qty
            sell_proceeds = sell_tx.total_amount

            while remaining_to_fill > 0 and buy_finger < len(buy_transactions):
                fill_qty = min(remaining_to_fill, buy_qty_remaining)
                buy_avg_cost = buy_transactions[buy_finger].total_amount / buy_transactions[buy_finger].quantity
                cost_for_fill = buy_avg_cost * fill_qty
                realized_pnl += sell_proceeds * (fill_qty / sell_qty) - cost_for_fill
                buy_qty_remaining -= fill_qty
                if buy_qty_remaining <= 0:
                    buy_finger += 1
                    buy_qty_remaining = (
                        buy_transactions[buy_finger].quantity
                        if buy_finger < len(buy_transactions)
                        else 0
                    )
                remaining_to_fill -= fill_qty

        return {
            "portfolio_id": portfolio.id,
            "name": portfolio.name,
            "holdings_count": len(holdings),
            "total_market_value": round(total_market_value, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_unrealized_pnl_pct": total_pnl_pct,
            "total_realized_pnl": round(realized_pnl, 2),
            "holdings": holdings,
        }

    @staticmethod
    def get_transaction_history(portfolio: Portfolio) -> list[dict]:
        """Get full transaction history for a portfolio."""
        transactions = portfolio.transactions.select_related("share").order_by("-date")
        result = []
        for tx in transactions:
            result.append({
                "id": tx.id,
                "type": tx.get_transaction_type_display(),
                "type_code": tx.transaction_type,
                "share_ticker": tx.share.ticker,
                "share_name": tx.share.name,
                "quantity": tx.quantity,
                "price": tx.price,
                "commission": tx.commission,
                "total_amount": round(tx.total_amount, 2),
                "date": tx.date,
            })
        return result
