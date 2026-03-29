import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    okx_api_key: str = os.getenv("OKX_API_KEY", "")
    okx_api_secret: str = os.getenv("OKX_API_SECRET", "")
    okx_passphrase: str = os.getenv("OKX_PASSPHRASE", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    paper_start_balance: float = float(os.getenv("PAPER_START_BALANCE", "100"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    symbols: list[str] = field(default_factory=lambda: [
        "BTC/USDT", "ETH/USDT", "DOGE/USDT", "SOL/USDT",
        "XRP/USDT", "ADA/USDT", "AVAX/USDT", "POL/USDT",
    ])

    timeframe: str = "1m"
    scan_interval_seconds: int = 45
    trade_amount_usd: float = 10.0
    stoploss_pct: float = 0.03
    max_open_trades: int = 4
    daily_loss_limit_pct: float = 0.15
    max_consecutive_losses: int = 5
    cooldown_seconds: int = 120
    min_available_balance: float = 20.0


SETTINGS = Settings()
