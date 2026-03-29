import asyncio
import io
import logging
from datetime import datetime, timezone

import matplotlib.pyplot as plt
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from tg import keyboards


class TelegramBot:
    def __init__(self, settings, orchestrator):
        self.logger = logging.getLogger("bot")
        self.settings = settings
        self.orchestrator = orchestrator
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_cmd))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("profit", self.profit))
        self.app.add_handler(CommandHandler("balance", self.balance))
        self.app.add_handler(CommandHandler("positions", self.positions))
        self.app.add_handler(CommandHandler("performance", self.performance))
        self.app.add_handler(CommandHandler("paper_on", self.paper_on))
        self.app.add_handler(CommandHandler("paper_off", self.paper_off))
        self.app.add_handler(CommandHandler("paper_status", self.paper_status))
        self.app.add_handler(CommandHandler("paper_reset", self.paper_reset))
        self.app.add_handler(CommandHandler("insights", self.insights))
        self.app.add_handler(CallbackQueryHandler(self.on_button))

    async def register_commands(self):
        try:
            await self.app.bot.set_my_commands([
                BotCommand("start", "Show main menu"), BotCommand("help", "Help"), BotCommand("status", "System status"),
                BotCommand("profit", "Show PnL"), BotCommand("balance", "Show balance"), BotCommand("positions", "Open positions"),
                BotCommand("performance", "Balance chart"), BotCommand("paper_on", "Enable paper trading"),
                BotCommand("paper_off", "Disable paper trading"), BotCommand("paper_status", "Paper mode status"),
                BotCommand("paper_reset", "Reset paper account"), BotCommand("insights", "Live insights"),
            ])
        except Exception as exc:
            self.logger.exception("set_my_commands failed: %s", exc)

    async def safe_send(self, chat_id, text, **kwargs):
        try:
            await self.app.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as exc:
            self.logger.exception("Telegram send_message failed: %s", exc)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.effective_message.reply_text("Automated-ervis menu", reply_markup=keyboards.main_menu())
        except Exception as exc:
            self.logger.exception("/start failed: %s", exc)

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.safe_send(update.effective_chat.id, "Use /start and inline buttons.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.safe_send(update.effective_chat.id, self.orchestrator.status_text())

    async def profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.orchestrator.paper_engine.get_stats()
        await self.safe_send(update.effective_chat.id, f"P&L: {stats['total_pnl']:+.2f} USD")

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.safe_send(update.effective_chat.id, f"Balance: {self.orchestrator.paper_engine.balance:.2f} USD")

    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        txt = self.orchestrator.positions_text()
        await self.safe_send(update.effective_chat.id, txt)

    async def paper_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.orchestrator.paper_enabled = True
        await self.safe_send(update.effective_chat.id, "Paper trading ON")

    async def paper_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.orchestrator.paper_enabled = False
        await self.safe_send(update.effective_chat.id, "Paper trading OFF")

    async def paper_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.safe_send(update.effective_chat.id, f"Paper mode: {'ON' if self.orchestrator.paper_enabled else 'OFF'}")

    async def paper_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.orchestrator.paper_engine.reset_account()
        await self.safe_send(update.effective_chat.id, "Paper account reset")

    def generate_pnl_chart(self, balance_history: list[dict]) -> io.BytesIO:
        xs = [x["timestamp"] for x in balance_history]
        ys = [x["balance"] for x in balance_history]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(xs, ys)
        ax.set_title("Balance History")
        ax.set_ylabel("USD")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            history = self.orchestrator.paper_engine.balance_history
            if not history:
                await self.safe_send(update.effective_chat.id, "No balance history yet.")
                return
            buf = await asyncio.to_thread(self.generate_pnl_chart, history)
            await self.app.bot.send_photo(chat_id=update.effective_chat.id, photo=buf, caption="Performance chart")
        except Exception as exc:
            self.logger.exception("performance failed: %s", exc)

    async def insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = await self.orchestrator.build_insights_text()
        await self.safe_send(update.effective_chat.id, text, parse_mode=ParseMode.HTML, reply_markup=keyboards.insights_menu())

    async def on_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        try:
            await q.answer()
            action = q.data
            if action == "back_main" or action == "refresh_main":
                await q.edit_message_text("Automated-ervis menu", reply_markup=keyboards.main_menu())
            elif action == "paper_menu":
                await q.edit_message_text("Paper controls", reply_markup=keyboards.paper_menu())
            elif action == "settings_menu":
                await q.edit_message_text("Settings", reply_markup=keyboards.settings_menu())
            elif action == "start_bot":
                self.orchestrator.bot_running = True
                await q.edit_message_text("Bot started", reply_markup=keyboards.main_menu())
            elif action == "stop_bot":
                self.orchestrator.bot_running = False
                await q.edit_message_text("Bot stopped", reply_markup=keyboards.main_menu())
            elif action == "paper_on":
                self.orchestrator.paper_enabled = True
                await q.edit_message_text("Paper trading ON", reply_markup=keyboards.paper_menu())
            elif action == "paper_off":
                self.orchestrator.paper_enabled = False
                await q.edit_message_text("Paper trading OFF", reply_markup=keyboards.paper_menu())
            elif action == "paper_status":
                await q.edit_message_text(f"Paper mode: {'ON' if self.orchestrator.paper_enabled else 'OFF'}", reply_markup=keyboards.paper_menu())
            elif action == "paper_reset":
                self.orchestrator.paper_engine.reset_account()
                await q.edit_message_text("Paper account reset", reply_markup=keyboards.paper_menu())
            elif action == "status":
                await q.edit_message_text(self.orchestrator.status_text(), reply_markup=keyboards.main_menu())
            elif action == "positions":
                await q.edit_message_text(self.orchestrator.positions_text(), reply_markup=keyboards.main_menu())
            elif action == "profit":
                stats = self.orchestrator.paper_engine.get_stats()
                await q.edit_message_text(f"P&L: {stats['total_pnl']:+.2f} USD", reply_markup=keyboards.main_menu())
            elif action == "performance":
                await self.performance(update, context)
            elif action == "live_mode":
                await q.edit_message_text("Live mode not implemented (paper default).", reply_markup=keyboards.main_menu())
            elif action == "view_config":
                await q.edit_message_text(f"Timeframe={self.orchestrator.settings.timeframe}, Scan={self.orchestrator.settings.scan_interval_seconds}s", reply_markup=keyboards.settings_menu())
            elif action == "resume":
                self.orchestrator.bot_running = True
                await q.edit_message_text("Trading resumed", reply_markup=keyboards.settings_menu())
            elif action == "ai_status":
                await q.edit_message_text(f"AI model ready: {self.orchestrator.ai_engine.model is not None}", reply_markup=keyboards.settings_menu())
            elif action == "recent_trades":
                txt = self.orchestrator.recent_trades_text()
                await q.edit_message_text(txt, reply_markup=keyboards.settings_menu())
            elif action == "change_tf":
                self.orchestrator.settings.timeframe = "3m" if self.orchestrator.settings.timeframe == "1m" else "1m"
                self.orchestrator.data_handler.timeframe = self.orchestrator.settings.timeframe
                await q.edit_message_text(f"Timeframe changed to {self.orchestrator.settings.timeframe}", reply_markup=keyboards.settings_menu())
            elif action in ("insights", "insights_refresh"):
                text = await self.orchestrator.build_insights_text()
                try:
                    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.insights_menu())
                except Exception:
                    await self.safe_send(q.message.chat_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboards.insights_menu())
            else:
                await q.edit_message_text(f"Unhandled action: {action}", reply_markup=keyboards.main_menu())
        except Exception as exc:
            self.logger.exception("Button handler failed: %s", exc)
            try:
                await q.message.reply_text("Button processing failed, please retry.", reply_markup=keyboards.main_menu())
            except Exception as e2:
                self.logger.exception("Fallback button response failed: %s", e2)

    async def startup(self):
        await self.app.initialize()
        await self.app.start()
        await self.register_commands()
        await self.app.updater.start_polling(drop_pending_updates=True)

    async def shutdown(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_alert(self, text: str):
        if not self.settings.telegram_chat_id:
            return
        await self.safe_send(self.settings.telegram_chat_id, text)
