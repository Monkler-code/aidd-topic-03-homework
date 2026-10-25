"""Forms for dashboard share management."""

from django import forms

from .models import Share


class ShareModelForm(forms.ModelForm):
    """Form for creating and updating Share instances."""

    class Meta:
        model = Share
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "Наименование"}
            ),
            "ticker": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "Тикер"}
            ),
            "figi": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "FIGI"}
            ),
            "isin": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "ISIN"}
            ),
            "currency": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "Валюта"}
            ),
            "uid": forms.TextInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "UID"}
            ),
            "last_price": forms.NumberInput(
                attrs={"class": "form-control my-3 p-4", "placeholder": "Цена"}
            ),
        }
