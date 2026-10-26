from django import forms
from decimal import Decimal

from .models import (
    Portfolio,
    PriceAlert,
    Share,
    TradingStrategy,
    Transaction,
    Watchlist,
)


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"


class WatchlistForm(forms.ModelForm):
    class Meta:
        model = Watchlist
        fields = ("name",)


class WatchlistShareForm(forms.Form):
    share = forms.ModelChoiceField(queryset=Share.objects.order_by("ticker"))


class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ("share", "direction", "target_price")

    def clean_target_price(self):
        target_price = self.cleaned_data["target_price"]
        if target_price <= 0:
            raise forms.ValidationError("Целевая цена должна быть больше нуля.")
        return target_price


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ("name", "currency")


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("share", "side", "quantity", "price", "commission")

    def clean_commission(self):
        return self.cleaned_data.get("commission") or Decimal("0")


class TradingStrategyForm(forms.ModelForm):
    class Meta:
        model = TradingStrategy
        fields = (
            "name",
            "share",
            "buy_drop_percent",
            "lookback_days",
            "sell_profit_percent",
            "commission_percent",
            "initial_capital",
        )

    def clean_commission_percent(self):
        return self.cleaned_data.get("commission_percent") or Decimal("0")


class StrategyRunForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            self.add_error("end_date", "Конечная дата должна быть не раньше начальной.")
        return cleaned_data
