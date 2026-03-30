Automated-ervis (crypto paper trading bot)
=========================================

What this is
------------
Automated-ervis is a Telegram-controlled crypto paper trading system for OKX spot symbols.
It does NOT use real money by default. It simulates buys/sells and tracks virtual balance.

Important behavior
------------------
- Long-only trading: BUY opens a long paper trade.
- SELL never opens short. SELL only closes an existing open long on the same symbol.
- Strategy runs every 45 seconds on 1m candles by default.
- You can switch to 3m candles from Telegram Settings.
- Uses POL/USDT (POL is the new name for MATIC on OKX).

How strategy works
------------------
Each symbol gets buy and sell points:
- RSI < 45 => +1 buy
- RSI > 55 => +1 sell
- EMA fast > EMA slow => +1 buy (else +1 sell)
- MACD histogram > 0 => +1 buy (else if <0 => +1 sell)
- Volume ratio > 0.8 => +1 buy and +1 sell

Rules:
- BUY when buy score >= 2 and buy >= sell
- SELL when sell score >= 2 and sell > buy
- Otherwise HOLD

How AI works
------------
- Records RSI, EMA spread, MACD histogram, volume ratio and trade result.
- Before model training, all signals can pass.
- Trains RandomForest after 10 trades, then retrains every 5 new trades.
- After training, blocks only if:
  confidence < 0.35 AND signal score < 3
- Score 4 always passes.

How /insights works
-------------------
- Pulls live OHLCV and computes indicators per symbol.
- Shows market snapshot, live PnL for open trades, and last 5 closed trades.
- Refresh button tries to edit same Telegram message.
- If edit fails (for old messages), bot sends a new message.

Get OKX API keys
----------------
1) Log in to OKX.
2) Go to API Management.
3) Create API key for read market data (and paper as needed).
4) Save key, secret, and passphrase.

Get Telegram bot token + chat id
--------------------------------
1) Message @BotFather and create a bot.
2) Copy bot token into .env.
3) Send a message to your bot.
4) Open: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
5) Find your chat id and place it in TELEGRAM_CHAT_ID.

Install and run
---------------
1) Python 3.10+
2) In automated-ervis folder:
   pip install -r requirements.txt
3) Copy .env.example to .env and fill values.
4) Run:
   python main.py

Run strategy test
-----------------
From automated-ervis folder:
python test_strategy.py

Logs and persistence
--------------------
- logs/trades.log, logs/errors.log, logs/ai.log
- trades_history.json
- balance_history.json

Paper trading meaning
---------------------
Paper trading means fake trades for testing strategy behavior.
No real exchange order is sent by this project.
