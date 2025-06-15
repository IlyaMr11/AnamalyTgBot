import os
import pandas as pd
from moex_parser import MOEXParser
from anomaly_detector import AnomalyDetector
from config import Config
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import matplotlib.pyplot as plt
import io
import numpy as np
from ChartDrawer import ChartDrawer

# Пути к CSV-файлам
TICKERS_CSV = 'tickers.csv'

# Состояния для ConversationHandler
ADD_TICKER, CHOOSE_EMA = range(2)

# --- Хелперы для работы с CSV ---
def ensure_tickers_csv():
    if not os.path.exists(TICKERS_CSV):
        df = pd.DataFrame(columns=['username', 'user_id', 'ticker', 'ema', 'level'])
        df.to_csv(TICKERS_CSV, index=False)

def add_ticker_to_csv(username, user_id, ticker, ema_list, level=None):
    ensure_tickers_csv()
    df = pd.read_csv(TICKERS_CSV)
    for ema in ema_list:
        df = pd.concat([df, pd.DataFrame([{'username': username, 'user_id': user_id, 'ticker': ticker, 'ema': ema, 'level': level}])], ignore_index=True)
    df.to_csv(TICKERS_CSV, index=False)

def user_tickers(user_id):
    ensure_tickers_csv()
    df = pd.read_csv(TICKERS_CSV)
    return df[df['user_id'] == user_id]

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Добавить тикер', 'Мои тикеры'], ['История аномалий']]
    await update.message.reply_text(
        'Привет! Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def add_ticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Введите тикер (например, SBER):')
    return ADD_TICKER

async def add_ticker_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    parser = MOEXParser()
    price = parser.get_current_price(ticker)
    if price is None:
        await update.message.reply_text('Тикер не найден. Попробуйте снова:')
        return ADD_TICKER
    context.user_data['new_ticker'] = ticker
    await update.message.reply_text(
        'Выберите EMA для отслеживания (можно несколько, через запятую):\n20, 50, 100',
    )
    return CHOOSE_EMA

async def add_ticker_choose_ema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ema_text = update.message.text.replace(' ', '')
    ema_list = [int(e) for e in ema_text.split(',') if e in ['20', '50', '100']]
    if not ema_list:
        await update.message.reply_text('Некорректный выбор EMA. Введите числа через запятую (например: 20,50):')
        return CHOOSE_EMA
    ticker = context.user_data['new_ticker']
    user = update.effective_user
    context.user_data['new_ema'] = ema_list
    # Не сохраняем тикер сразу, а предлагаем меню действий
    keyboard = [['Добавить уровень', 'Добавить EMA'], ['Сохранить тикер']]
    await update.message.reply_text(
        f'Тикер {ticker} выбран с EMA: {", ".join(map(str, ema_list))}!\nЧто сделать дальше?',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return 'TICKER_ACTIONS'

# --- Обработчики для меню после выбора EMA ---
async def ticker_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Добавить уровень':
        await update.message.reply_text('Введите уровень (например, 150.0):')
        return 'ADD_LEVEL'
    elif text == 'Добавить EMA':
        await update.message.reply_text('Введите дополнительные EMA (20, 50, 100) через запятую:')
        return 'ADD_EMA'
    elif text == 'Сохранить тикер':
        ticker = context.user_data.get('new_ticker')
        ema_list = context.user_data.get('new_ema', [])
        level = context.user_data.get('new_level', None)
        user = update.effective_user
        add_ticker_to_csv(user.username, user.id, ticker, ema_list, level)
        # Инициализация истории EMA (скачиваем исторические цены)
        parser = MOEXParser()
        closes = parser.get_historical_prices(ticker, interval=1, count=max(ema_list)*3)
        detector = AnomalyDetector()
        for price in closes:
            detector.update_ema_history(ticker, price, ema_list)
        await update.message.reply_text(f'Тикер {ticker} сохранён с EMA: {", ".join(map(str, ema_list))} и уровнем: {level if level else "не задан"}!')
        # Возврат в главное меню
        keyboard = [['Добавить тикер', 'Мои тикеры'], ['История аномалий']]
        await update.message.reply_text(
            'Вы вернулись в главное меню.',
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_ACTIONS'

async def add_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        level = float(update.message.text.replace(',', '.'))
        context.user_data['new_level'] = level
        await update.message.reply_text(f'Уровень {level} добавлен! Теперь выберите дальнейшее действие.',
            reply_markup=ReplyKeyboardMarkup([
                ['Добавить уровень', 'Добавить EMA'], ['Сохранить тикер']
            ], resize_keyboard=True))
        return 'TICKER_ACTIONS'
    except ValueError:
        await update.message.reply_text('Некорректный формат уровня. Введите число, например: 150.0')
        return 'ADD_LEVEL'

async def add_ema_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ema_text = update.message.text.replace(' ', '')
    ema_list = [int(e) for e in ema_text.split(',') if e in ['20', '50', '100']]
    if not ema_list:
        await update.message.reply_text('Некорректный выбор EMA. Введите числа через запятую (например: 20,50):')
        return 'ADD_EMA'
    if 'new_ema' not in context.user_data:
        context.user_data['new_ema'] = []
    context.user_data['new_ema'].extend([e for e in ema_list if e not in context.user_data['new_ema']])
    await update.message.reply_text(f'EMA {", ".join(map(str, ema_list))} добавлены! Теперь выберите дальнейшее действие.',
        reply_markup=ReplyKeyboardMarkup([
            ['Добавить уровень', 'Добавить EMA'], ['Сохранить тикер']
        ], resize_keyboard=True))
    return 'TICKER_ACTIONS'

# --- Просмотр тикеров пользователя ---
async def my_tickers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    df = user_tickers(user.id)
    if df.empty:
        await update.message.reply_text('У вас пока нет добавленных тикеров.')
        # Возврат в главное меню
        keyboard = [['Добавить тикер', 'Мои тикеры'], ['История аномалий']]
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    # Группируем по тикеру, собираем EMA и уровень
    msg = 'Ваши тикеры:\n'
    tickers = []
    for ticker, group in df.groupby('ticker'):
        emas = ', '.join(str(int(e)) for e in group['ema'].unique())
        level = group['level'].dropna().unique()
        level_str = str(level[0]) if len(level) > 0 else 'не задан'
        msg += f'• {ticker}: EMA {emas}, уровень: {level_str}\n'
        tickers.append(ticker)
    await update.message.reply_text(msg)
    await update.message.reply_text('Введите тикер из списка, чтобы открыть меню управления этим тикером:')
    context.user_data['my_tickers_list'] = tickers
    return 'TICKER_MENU_SELECT'

# --- Меню тикера ---
async def ticker_menu_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    tickers = context.user_data.get('my_tickers_list', [])
    if ticker not in tickers:
        await update.message.reply_text('Такого тикера нет в вашем списке. Введите тикер из таблицы:')
        return 'TICKER_MENU_SELECT'
    context.user_data['selected_ticker'] = ticker
    keyboard = [['График', 'Редактировать тикер'], ['Назад']]
    await update.message.reply_text(
        f'Меню тикера {ticker}:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return 'TICKER_MENU_ACTIONS'

async def ticker_menu_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ticker = context.user_data.get('selected_ticker')
    user = update.effective_user
    if text == 'График':
        # Получаем данные для графика
        df = user_tickers(user.id)
        emas = df[df['ticker'] == ticker]['ema'].dropna().unique()
        emas = [int(e) for e in emas]
        level = df[df['ticker'] == ticker]['level'].dropna().unique()
        level_val = float(level[0]) if len(level) > 0 else None
        parser = MOEXParser()
        data = parser.get_historical_prices(ticker, interval=1, count=150)
        if not data:
            await update.message.reply_text('Нет исторических данных для построения графика.')
            return 'TICKER_MENU_ACTIONS'
        dates, closes = zip(*data)
        closes = [c for c in closes if c is not None]
        dates = [d for i, d in enumerate(dates) if closes[i] is not None]
        if len(closes) > 100:
            closes = closes[-100:]
            dates = dates[-100:]
        emas_dict = {}
        for window in emas:
            if len(closes) >= window:
                ema = []
                k = 2 / (window + 1)
                prev_ema = closes[0]
                for price in closes:
                    prev_ema = price * k + prev_ema * (1 - k)
                    ema.append(prev_ema)
                emas_dict[window] = ema
        chart = ChartDrawer.draw_chart(ticker, dates, closes, emas_dict, level=level_val)
        await update.message.reply_photo(chart, caption=f'График {ticker} с EMA и уровнем')
        return 'TICKER_MENU_ACTIONS'
    elif text == 'Редактировать тикер':
        keyboard = [['Удалить EMA', 'Удалить уровень'], ['Назад']]
        await update.message.reply_text('Что вы хотите отредактировать?', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return 'TICKER_EDIT_MENU'
    elif text == 'Назад':
        keyboard = [['Добавить тикер', 'Мои тикеры'], ['История аномалий']]
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_MENU_ACTIONS'

# --- Меню редактирования тикера (заглушки) ---
async def ticker_edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ticker = context.user_data.get('selected_ticker')
    if text == 'Удалить EMA':
        await update.message.reply_text(f'[Заглушка] Здесь будет удаление EMA для {ticker}.')
        return 'TICKER_EDIT_MENU'
    elif text == 'Удалить уровень':
        await update.message.reply_text(f'[Заглушка] Здесь будет удаление уровня для {ticker}.')
        return 'TICKER_EDIT_MENU'
    elif text == 'Назад':
        keyboard = [['График', 'Редактировать тикер'], ['Назад']]
        await update.message.reply_text(f'Меню тикера {ticker}:', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return 'TICKER_MENU_ACTIONS'
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_EDIT_MENU'

# --- Основной запуск ---
def main():
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^Добавить тикер$'), add_ticker_start),
            MessageHandler(filters.Regex('^Мои тикеры$'), my_tickers_handler)
        ],
        states={
            ADD_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ticker_receive)],
            CHOOSE_EMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ticker_choose_ema)],
            'TICKER_ACTIONS': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_actions_handler)],
            'ADD_LEVEL': [MessageHandler(filters.TEXT & ~filters.COMMAND, add_level_handler)],
            'ADD_EMA': [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ema_handler)],
            'TICKER_MENU_SELECT': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_menu_select_handler)],
            'TICKER_MENU_ACTIONS': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_menu_actions_handler)],
            'TICKER_EDIT_MENU': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_edit_menu_handler)],
        },
        fallbacks=[]
    )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()