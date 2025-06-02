import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue
)
from config import Config

# Инициализация конфигурации
config = Config()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("Настройки", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 Бот мониторинга аномалий акций\n\n"
        "Используйте кнопки ниже для управления:",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "settings":
        await settings_menu(query)


async def settings_menu(query):
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton("Выбрать тикеры", callback_data="select_tickers")],
        [InlineKeyboardButton("Установить пороги", callback_data="set_thresholds")],
        [InlineKeyboardButton("Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="⚙️ Настройки параметров:",
        reply_markup=reply_markup
    )


def main():
    """Основная функция запуска бота"""
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск бота
    logger.info("Бот запущен и ожидает сообщений...")
    application.run_polling()


if __name__ == "__main__":
    main()