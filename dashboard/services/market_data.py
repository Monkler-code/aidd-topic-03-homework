from .tbank import get_invest_client, quotation_to_float
from config.settings import logger


def get_last_data(share):
    with get_invest_client() as client:
        response = client.market_data.get_last_prices(figi=[share.figi])
        if not response.last_prices:
            raise ValueError(f"No last price returned for share {share.figi}")
        last_price = response.last_prices[0]
        logger.info("Get last data for share with id %s", share.id)
        return quotation_to_float(last_price.price), last_price.time
