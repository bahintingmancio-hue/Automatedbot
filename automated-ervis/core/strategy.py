import logging
from dataclasses import dataclass

import pandas as pd


@dataclass
class Signal:
    action: str
    symbol: str
    price: float
    confidence: float
    score: int
    reason: str
    indicators: dict


class StrategyEngine:
    def __init__(self):
        self.logger = logging.getLogger("strategy")

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))

    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Signal:
        close = df["close"].astype(float)
        volume = df["volume"].astype(float)

        ema_fast = self._ema(close, 9)
        ema_slow = self._ema(close, 21)
        macd_line = self._ema(close, 12) - self._ema(close, 26)
        macd_signal = self._ema(macd_line, 9)
        macd_hist = macd_line - macd_signal
        rsi = self._rsi(close, 14)

        last_price = float(close.iloc[-1])
        last_rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50.0
        last_ema_fast = float(ema_fast.iloc[-1])
        last_ema_slow = float(ema_slow.iloc[-1])
        last_macd_hist = float(macd_hist.iloc[-1])
        vol_ratio = float(volume.iloc[-1] / max(volume.tail(20).mean(), 1e-9))

        buy_score = 0
        sell_score = 0
        details = []

        if last_rsi < 45:
            buy_score += 1
            details.append("RSI<45")
        elif last_rsi > 55:
            sell_score += 1
            details.append("RSI>55")

        ema_bull = last_ema_fast > last_ema_slow
        if ema_bull:
            buy_score += 1
            details.append("EMA_BULL")
        else:
            sell_score += 1
            details.append("EMA_BEAR")

        if last_macd_hist > 0:
            buy_score += 1
            details.append("MACD_POS")
        elif last_macd_hist < 0:
            sell_score += 1
            details.append("MACD_NEG")

        if vol_ratio > 0.8:
            buy_score += 1
            sell_score += 1
            details.append("VOL>0.8")

        action = "HOLD"
        score = max(buy_score, sell_score)
        if buy_score >= 2 and buy_score >= sell_score:
            action = "BUY"
            score = buy_score
        elif sell_score >= 2 and sell_score > buy_score:
            action = "SELL"
            score = sell_score

        self.logger.info(
            "%s | RSI=%.2f | EMA=%s | MACD=%+.6f | Score=%d | %s",
            symbol,
            last_rsi,
            "BULL" if ema_bull else "BEAR",
            last_macd_hist,
            score,
            action,
        )

        return Signal(
            action=action,
            symbol=symbol,
            price=last_price,
            confidence=min(score / 4.0, 1.0),
            score=score,
            reason=",".join(details),
            indicators={
                "rsi": last_rsi,
                "ema_fast": last_ema_fast,
                "ema_slow": last_ema_slow,
                "ema_spread": last_ema_fast - last_ema_slow,
                "macd_hist": last_macd_hist,
                "volume_ratio": vol_ratio,
            },
        )
