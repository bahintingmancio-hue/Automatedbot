import logging
import time
from datetime import datetime, timezone


class RiskManager:
    def __init__(self, settings):
        self.logger = logging.getLogger("risk_manager")
        self.settings = settings
        self.consecutive_losses = 0
        self.cooldown_until = 0.0
        self.day_start_balance = settings.paper_start_balance
        self.day_start_date = datetime.now(timezone.utc).date()

    def _roll_day(self, balance: float) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self.day_start_date:
            self.day_start_date = today
            self.day_start_balance = balance
            self.consecutive_losses = 0
            self.cooldown_until = 0.0

    def can_open_trade(self, balance: float, open_trades_count: int) -> tuple[bool, str]:
        self._roll_day(balance)
        now = time.time()
        if now < self.cooldown_until:
            return False, "Cooldown active"
        if open_trades_count >= self.settings.max_open_trades:
            return False, "Max open trades reached"
        available_balance = balance - (open_trades_count * self.settings.trade_amount_usd)
        if available_balance < self.settings.min_available_balance:
            return False, "Insufficient available balance"
        daily_loss = (self.day_start_balance - balance) / max(self.day_start_balance, 1e-9)
        if daily_loss >= self.settings.daily_loss_limit_pct:
            return False, "Daily loss limit reached"
        return True, "OK"

    def on_trade_closed(self, pnl_usd: float) -> tuple[bool, str]:
        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        if self.consecutive_losses >= self.settings.max_consecutive_losses:
            self.cooldown_until = time.time() + self.settings.cooldown_seconds
            self.logger.warning("Risk pause activated for %ss", self.settings.cooldown_seconds)
            self.consecutive_losses = 0
            return True, "Risk pause activated"
        return False, "No pause"
