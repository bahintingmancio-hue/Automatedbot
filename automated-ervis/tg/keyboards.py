from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Start Bot", callback_data="start_bot"), InlineKeyboardButton("Stop Bot", callback_data="stop_bot")],
        [InlineKeyboardButton("Paper Mode", callback_data="paper_menu"), InlineKeyboardButton("Live Mode", callback_data="live_mode")],
        [InlineKeyboardButton("Status", callback_data="status"), InlineKeyboardButton("Positions", callback_data="positions")],
        [InlineKeyboardButton("Profit", callback_data="profit"), InlineKeyboardButton("Performance", callback_data="performance")],
        [InlineKeyboardButton("Settings", callback_data="settings_menu"), InlineKeyboardButton("Refresh", callback_data="refresh_main")],
        [InlineKeyboardButton("Insights", callback_data="insights")],
    ])


def paper_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Start Paper Trading", callback_data="paper_on")],
        [InlineKeyboardButton("Stop Paper Trading", callback_data="paper_off")],
        [InlineKeyboardButton("Paper Status", callback_data="paper_status")],
        [InlineKeyboardButton("Reset Paper Account", callback_data="paper_reset")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ])


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("View Config", callback_data="view_config")],
        [InlineKeyboardButton("Resume Trading", callback_data="resume")],
        [InlineKeyboardButton("AI Status", callback_data="ai_status")],
        [InlineKeyboardButton("Recent Trades", callback_data="recent_trades")],
        [InlineKeyboardButton("Change Timeframe", callback_data="change_tf")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ])


def insights_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Refresh Insights", callback_data="insights_refresh")],
        [InlineKeyboardButton("Back to Main Menu", callback_data="back_main")],
    ])
