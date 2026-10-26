from datetime import timedelta

from django.utils import timezone
from plotly.graph_objs import Scatter
from plotly.offline import plot

from .tbank import get_invest_client, quotation_to_float


def get_graph(share):
    from t_tech.invest import CandleInterval

    with get_invest_client() as client:
        x_data, y_data = [], []
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=timezone.now() - timedelta(days=180),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            x_data.append(candle.time.date())
            y_data.append(quotation_to_float(candle.close))
    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        include_plotlyjs="cdn",
        show_link=False,
        link_text="",
    )
    return plot_div
