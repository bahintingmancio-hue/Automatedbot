import asyncio
import logging
import pathlib
import shutil
import sys
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import SETTINGS
from core.ai_engine import AIEngine
from core.data_handler import DataHandler
from core.paper_engine import PaperTradingEngine
from core.risk_manager import RiskManager
from core.strategy import StrategyEngine
from tg.bot import TelegramBot

for p in pathlib.Path(".").rglob("__pycache__"):
    shutil.rmtree(p, ignore_errors=True)


def setup_logging(level: str = "INFO"):
    pathlib.Path("logs").mkdir(exist_ok=True)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))

    file_handler = logging.FileHandler("logs/errors.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))

    ai_file = logging.FileHandler("logs/ai.log")
    ai_file.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))

    trades_file = logging.FileHandler("logs/trades.log")
    trades_file.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))

    for name in ("strategy", "paper_engine", "risk_manager", "data_handler", "ai_engine", "bot", "main"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.setLevel(level)
        lg.addHandler(console_handler)
        lg.addHandler(file_handler)
        if name == "ai_engine":
            lg.addHandler(ai_file)
        if name in ("paper_engine", "main"):
            lg.addHandler(trades_file)
        lg.propagate = False


class TradingOrchestrator:
    def __init__(self, settings):
        self.logger = logging.getLogger("main")
        self.settings = settings
        self.bot_running = True
        self.paper_enabled = True
        self.data_handler = DataHandler(settings.okx_api_key, settings.okx_api_secret, settings.okx_passphrase, settings.timeframe)
        self.strategy = StrategyEngine()
        self.paper_engine = PaperTradingEngine(settings.paper_start_balance, settings.trade_amount_usd)
        self.risk_manager = RiskManager(settings)
        self.ai_engine = AIEngine()
        self.valid_symbols = []
        self.telegram = TelegramBot(settings, self)
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    async def initialize(self):
        try:
            self.valid_symbols = await asyncio.to_thread(self.data_handler.validate_symbols, self.settings.symbols)
            self.logger.info("Validated symbols: %s", self.valid_symbols)
            self.scheduler.add_job(self.daily_summary, "cron", hour=0, minute=0)
            self.scheduler.start()
        except Exception as exc:
            self.logger.exception("Initialization error: %s", exc)

    def status_text(self) -> str:
        stats = self.paper_engine.get_stats()
        return (
            f"Bot={'ON' if self.bot_running else 'OFF'} | Paper={'ON' if self.paper_enabled else 'OFF'}\n"
            f"Timeframe={self.settings.timeframe} | Symbols={len(self.valid_symbols)}\n"
            f"Balance={stats['balance']:.2f} | PnL={stats['total_pnl']:+.2f}"
        )

    def positions_text(self) -> str:
        open_positions = self.paper_engine.get_open_positions_summary()
        if not open_positions:
            return "No open positions"
        rows = [f"#{p['trade_id']} {p['symbol']} entry={p['entry']:.6f} pnl={p['pnl']:+.4f}" for p in open_positions]
        return "Open positions:\n" + "\n".join(rows)

    def recent_trades_text(self) -> str:
        trades = self.paper_engine.get_recent_trades(5)
        if not trades:
            return "No recent trades"
        return "\n".join([f"{t.symbol} {t.pnl_usd:+.3f} ({t.reason_close})" for t in trades])

    async def build_insights_text(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        snapshot = []
        prices = {}
        for symbol in self.valid_symbols:
            try:
                df = await asyncio.to_thread(self.data_handler.fetch_ohlcv, symbol)
                if df is None or df.empty:
                    continue
                sig = self.strategy.generate_signal(df, symbol)
                prices[symbol] = sig.price
                snapshot.append(f"{symbol} | ${sig.price:,.6f} | RSI={sig.indicators['rsi']:.1f} | EMA={'BULL' if sig.indicators['ema_fast']>sig.indicators['ema_slow'] else 'BEAR'} | Score={sig.score} {sig.action}")
                await asyncio.sleep(0.5)
            except Exception as exc:
                self.logger.exception("Insights fetch failed %s: %s", symbol, exc)

        open_rows = []
        for p in self.paper_engine.get_open_positions_summary(prices):
            opened = datetime.fromisoformat(p["opened_at"])
            delta = datetime.now(timezone.utc) - opened
            mm, ss = divmod(int(delta.total_seconds()), 60)
            open_rows.append(f"{p['symbol']} | Entry ${p['entry']:.6f} -> Now ${p['now']:.6f} | {p['pnl']:+.2f}$ | {mm}m {ss}s")

        closed = self.paper_engine.get_recent_trades(5)
        closed_rows = []
        for t in closed:
            if t.closed_at:
                hold_sec = int((datetime.fromisoformat(t.closed_at) - datetime.fromisoformat(t.opened_at)).total_seconds())
                closed_rows.append(f"{t.symbol} {t.pnl_usd:+.2f}$ | {hold_sec//60}m hold | {t.reason_close}")

        stats = self.paper_engine.get_stats()
        return (
            f"<b>LIVE INSIGHTS — {now}</b>\n\n"
            f"<b>MARKET SNAPSHOT</b>\n" + ("\n".join(snapshot) if snapshot else "No data") + "\n\n"
            f"<b>OPEN TRADES (live PnL)</b>\n" + ("\n".join(open_rows) if open_rows else "No open trades") + "\n\n"
            f"<b>LAST 5 CLOSED TRADES</b>\n" + ("\n".join(closed_rows) if closed_rows else "No closed trades") + "\n\n"
            f"Balance: ${stats['balance']:.2f} | P&L: {stats['total_pnl']:+.2f}$"
        )

    async def daily_summary(self):
        try:
            stats = self.paper_engine.get_stats()
            await self.telegram.send_alert(f"Daily summary: balance={stats['balance']:.2f} pnl={stats['total_pnl']:+.2f}")
        except Exception as exc:
            self.logger.exception("daily_summary failed: %s", exc)

    async def scan_once(self):
        if not (self.bot_running and self.paper_enabled):
            return
        for symbol in self.valid_symbols:
            try:
                df = await asyncio.to_thread(self.data_handler.fetch_ohlcv, symbol)
                if df is None or df.empty:
                    await asyncio.sleep(0.5)
                    continue
                signal = self.strategy.generate_signal(df, symbol)

                open_trades = [t for t in self.paper_engine.trades if t.status == "OPEN" and t.symbol == symbol]

                for t in list(open_trades):
                    if signal.price <= t.stoploss:
                        closed = self.paper_engine.close_trade(t.trade_id, signal.price, "stoploss")
                        if closed:
                            await self.telegram.send_alert(f"Stoploss triggered: {symbol} pnl={closed.pnl_usd:+.2f}$")
                            paused, msg = self.risk_manager.on_trade_closed(closed.pnl_usd)
                            self.ai_engine.record_trade_result(signal.indicators, closed.pnl_usd > 0)
                            if paused:
                                await self.telegram.send_alert(msg)

                if signal.action == "SELL":
                    if open_trades:
                        for t in open_trades:
                            closed = self.paper_engine.close_trade(t.trade_id, signal.price, "sell_signal")
                            if closed:
                                await self.telegram.send_alert(
                                    f"Trade closed: {symbol} entry={closed.entry_price:.6f} exit={closed.exit_price:.6f} pnl={closed.pnl_usd:+.2f}$"
                                )
                                paused, msg = self.risk_manager.on_trade_closed(closed.pnl_usd)
                                self.ai_engine.record_trade_result(signal.indicators, closed.pnl_usd > 0)
                                if paused:
                                    await self.telegram.send_alert(msg)
                    await asyncio.sleep(0.5)
                    continue

                if signal.action == "BUY":
                    open_count = len([t for t in self.paper_engine.trades if t.status == "OPEN"])
                    can_open, reason = self.risk_manager.can_open_trade(self.paper_engine.balance, open_count)
                    allow_ai, ai_conf, _ = self.ai_engine.should_allow_trade(signal)
                    if can_open and allow_ai and not open_trades:
                        sl = signal.price * (1 - self.settings.stoploss_pct)
                        trade = self.paper_engine.open_trade(symbol, signal.price, sl, f"signal={signal.score}")
                        if trade:
                            await self.telegram.send_alert(
                                f"Trade opened: {symbol} entry={trade.entry_price:.6f} SL={trade.stoploss:.6f} size={self.settings.trade_amount_usd}$ AI={ai_conf:.2f}"
                            )
                    else:
                        self.logger.info("BUY skipped %s reason=%s ai_allow=%s", symbol, reason, allow_ai)

                await asyncio.sleep(0.5)
            except Exception as exc:
                self.logger.exception("scan_once error for %s: %s", symbol, exc)
                await self.telegram.send_alert(f"System error on {symbol}: {exc}")

    async def run_loop(self):
        while True:
            await self.scan_once()
            await asyncio.sleep(self.settings.scan_interval_seconds)


async def main():
    setup_logging(SETTINGS.log_level)
    orchestrator = TradingOrchestrator(SETTINGS)
    await orchestrator.initialize()
    await orchestrator.telegram.startup()
    try:
        await orchestrator.run_loop()
    finally:
        await orchestrator.telegram.shutdown()


if __name__ == "__main__":
    import time

    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("Stopped by user.")
            break
        except Exception as e:
            logging.error(f"CRASH: {e} — restarting in 10s...")
            time.sleep(10)
