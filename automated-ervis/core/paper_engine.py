import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Trade:
    trade_id: int
    symbol: str
    entry_price: float
    qty: float
    stoploss: float
    opened_at: str
    reason_open: str
    status: str = "OPEN"
    exit_price: float = 0.0
    closed_at: str = ""
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    reason_close: str = ""


class PaperTradingEngine:
    def __init__(self, start_balance: float, trade_amount_usd: float):
        self.logger = logging.getLogger("paper_engine")
        self.start_balance = start_balance
        self.balance = start_balance
        self.trade_amount_usd = trade_amount_usd
        self.trade_path = Path("trades_history.json")
        self.balance_path = Path("balance_history.json")
        self.trades: list[Trade] = []
        self.balance_history: list[dict] = []
        self._next_trade_id = 1
        self._load_state()

    def _load_state(self) -> None:
        try:
            if self.trade_path.exists():
                data = json.loads(self.trade_path.read_text())
                self.trades = [Trade(**t) for t in data]
                self._next_trade_id = max([t.trade_id for t in self.trades], default=0) + 1
            if self.balance_path.exists():
                self.balance_history = json.loads(self.balance_path.read_text())
        except Exception as exc:
            self.logger.exception("Failed loading paper state: %s", exc)

    def _save_state(self) -> None:
        try:
            self.trade_path.write_text(json.dumps([asdict(t) for t in self.trades], indent=2))
            self.balance_path.write_text(json.dumps(self.balance_history, indent=2))
        except Exception as exc:
            self.logger.exception("Failed saving paper state: %s", exc)

    def open_trade(self, symbol, price, stoploss, reason) -> Optional[Trade]:
        try:
            qty = self.trade_amount_usd / max(price, 1e-9)
            trade = Trade(
                trade_id=self._next_trade_id,
                symbol=symbol,
                entry_price=price,
                qty=qty,
                stoploss=stoploss,
                opened_at=datetime.now(timezone.utc).isoformat(),
                reason_open=reason,
            )
            self._next_trade_id += 1
            self.trades.append(trade)
            self._save_state()
            self.logger.info("OPENED #%s %s @ %.6f qty=%.8f", trade.trade_id, symbol, price, qty)
            return trade
        except Exception as exc:
            self.logger.exception("open_trade failed: %s", exc)
            return None

    def calculate_profit(self, trade, current_price) -> tuple[float, float]:
        pnl_usd = (current_price - trade.entry_price) * trade.qty
        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
        return pnl_usd, pnl_pct

    def close_trade(self, trade_id, current_price, reason) -> Optional[Trade]:
        try:
            trade = next((t for t in self.trades if t.trade_id == trade_id and t.status == "OPEN"), None)
            if not trade:
                return None
            pnl_usd, pnl_pct = self.calculate_profit(trade, current_price)
            trade.exit_price = current_price
            trade.closed_at = datetime.now(timezone.utc).isoformat()
            trade.status = "CLOSED"
            trade.pnl_usd = pnl_usd
            trade.pnl_pct = pnl_pct
            trade.reason_close = reason
            self.balance += pnl_usd
            self.balance_history.append({"timestamp": trade.closed_at, "balance": round(self.balance, 4)})
            self._save_state()
            self.logger.info("CLOSED #%s %s @ %.6f pnl=%.4f", trade.trade_id, trade.symbol, current_price, pnl_usd)
            return trade
        except Exception as exc:
            self.logger.exception("close_trade failed: %s", exc)
            return None

    def reset_account(self) -> None:
        self.trades = []
        self.balance = self.start_balance
        self.balance_history = []
        self._next_trade_id = 1
        self._save_state()

    def get_stats(self) -> dict:
        closed = [t for t in self.trades if t.status == "CLOSED"]
        wins = [t for t in closed if t.pnl_usd > 0]
        return {
            "balance": self.balance,
            "open_trades": len([t for t in self.trades if t.status == "OPEN"]),
            "closed_trades": len(closed),
            "win_rate": (len(wins) / len(closed) * 100) if closed else 0,
            "total_pnl": self.balance - self.start_balance,
        }

    def get_open_positions_summary(self, prices=None) -> list:
        prices = prices or {}
        rows = []
        for t in [x for x in self.trades if x.status == "OPEN"]:
            now = prices.get(t.symbol, t.entry_price)
            pnl, _ = self.calculate_profit(t, now)
            rows.append({"trade_id": t.trade_id, "symbol": t.symbol, "entry": t.entry_price, "now": now, "pnl": pnl, "opened_at": t.opened_at})
        return rows

    def get_recent_trades(self, n=10) -> list:
        closed = [t for t in self.trades if t.status == "CLOSED"]
        return list(reversed(closed))[:n]
