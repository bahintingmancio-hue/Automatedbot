import logging
from typing import Optional

import ccxt
import pandas as pd


class DataHandler:
    def __init__(self, api_key: str, api_secret: str, passphrase: str, timeframe: str = "1m"):
        self.logger = logging.getLogger("data_handler")
        self.timeframe = timeframe
        self.exchange = ccxt.okx(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "password": passphrase,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )

    def validate_symbols(self, symbols: list[str]) -> list[str]:
        valid: list[str] = []
        try:
            markets = self.exchange.load_markets()
            for sym in symbols:
                if sym in markets:
                    valid.append(sym)
                else:
                    self.logger.warning("Symbol unavailable on OKX, skipping: %s", sym)
        except Exception as exc:
            self.logger.exception("Failed to validate symbols: %s", exc)
        return valid

    def fetch_ohlcv(self, symbol: str, limit: int = 150) -> Optional[pd.DataFrame]:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=limit)
            if not ohlcv:
                return None
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df
        except Exception as exc:
            self.logger.exception("fetch_ohlcv error for %s: %s", symbol, exc)
            return None

    def fetch_ticker_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker.get("last") or 0)
        except Exception as exc:
            self.logger.exception("fetch_ticker_price error for %s: %s", symbol, exc)
            return None
