"""Service for generating price charts using Plotly."""

from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now

from config.settings import TINKOFF_TOKEN


def get_graph(share):
    """
    Generate an HTML div with a Plotly line chart showing share price over 180 days.

    Args:
        share: Share model instance

    Returns:
        str: HTML div containing the chart
    """
    with Client(TINKOFF_TOKEN) as client:
        x_data, y_data = [], []
        try:
            for candle in client.get_all_candles(
                figi=share.figi,
                from_=now() - timedelta(days=180),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            ):
                x_data.append(candle.time.date())
                y_data.append(candle.close.units)
        except Exception as exc:
            # Return empty chart on API failure
            x_data = []
            y_data = []

    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.name,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
        link_text="",
    )
    return plot_div
