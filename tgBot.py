import os
import pandas as pd
from moex_parser import MOEXParser
from anomaly_detector import AnomalyDetector
from config import Config
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from ChartDrawer import ChartDrawer
import csv
from datetime import datetime
from parameters import Parameters

# Пути к CSV-файлам
TICKERS_CSV = Parameters.TICKERS_CSV
ANOMALIES_CSV = Parameters.ANOMALIES_CSV

# Состояния для ConversationHandler
ADD_TICKER, CHOOSE_EMA = range(2)

# функции для работы с CSV
def ensure_tickers_csv():
    if not os.path.exists(TICKERS_CSV):
        df = pd.DataFrame(columns=['username', 'user_id', 'ticker', 'ema', 'level'])
        df.to_csv(TICKERS_CSV, index=False)

def add_ticker_to_csv(username, user_id, ticker, ema_list, level=None):
    ensure_tickers_csv()
    df = pd.read_csv(TICKERS_CSV)
    if ema_list:
        for ema in ema_list:
            df = pd.concat([df, pd.DataFrame([{'username': username, 'user_id': user_id, 'ticker': ticker, 'ema': ema, 'level': level}])], ignore_index=True)
    elif level is not None:
        df = pd.concat([df, pd.DataFrame([{'username': username, 'user_id': user_id, 'ticker': ticker, 'ema': None, 'level': level}])], ignore_index=True)
    df.to_csv(TICKERS_CSV, index=False)

def user_tickers(user_id):
    ensure_tickers_csv()
    df = pd.read_csv(TICKERS_CSV)
    return df[df['user_id'] == user_id]

# далее функции-обработчики тг
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = Parameters.MAIN_MENU_BUTTONS
    await update.message.reply_text(
        'Привет! Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def add_ticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # очищаем все временные данные при старте добавления тикера
    keyboard = [['Назад']]
    await update.message.reply_text('Введите тикер (например, SBER):', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ADD_TICKER

async def add_ticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    if ticker == 'НАЗАД':
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    parser = MOEXParser()
    price = parser.get_current_price(ticker)
    if price is None:
        await update.message.reply_text('Тикер не найден. Попробуйте снова:')
        return ADD_TICKER
    context.user_data['new_ticker'] = ticker
    keyboard = [['Добавить уровень', 'Добавить EMA'], ['Сохранить тикер', 'Назад']]
    await update.message.reply_text(
        f'Тикер {ticker} найден! Что сделать дальше?',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return 'TICKER_ACTIONS_NEW'

# меню действий после ввода тикера
async def ticker_actions_new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ticker = context.user_data.get('new_ticker')
    user = update.effective_user
    if text == 'Добавить уровень':
        await update.message.reply_text('Введите уровень (например, 150.0):')
        return 'ADD_LEVEL_NEW'
    elif text == 'Добавить EMA':
        await update.message.reply_text('Введите EMA (20, 50, 100):')
        return 'ADD_EMA_NEW'
    elif text == 'Сохранить тикер':
        levels = context.user_data.get('new_levels', [])
        emas = context.user_data.get('new_emas', [])
        if not levels and not emas:
            await update.message.reply_text('Добавьте хотя бы один уровень или EMA перед сохранением тикера.')
            return 'TICKER_ACTIONS_NEW'
        # Сохраняем все уровни и EMA
        for level in levels:
            add_ticker_to_csv(user.username, user.id, ticker, ema_list=[], level=level)
        for ema in emas:
            add_ticker_to_csv(user.username, user.id, ticker, ema_list=[ema], level=None)
        await update.message.reply_text(f'Тикер {ticker} сохранён!')
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    elif text == 'Назад':
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_ACTIONS_NEW'

# Добавление уровня
async def add_level_new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.user_data.get('new_ticker')
    user = update.effective_user
    try:
        level = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text('Некорректный формат уровня. Введите число, например: 150.0')
        return 'ADD_LEVEL_NEW'
    # Сохраняем уровень во временный список
    if 'new_levels' not in context.user_data:
        context.user_data['new_levels'] = []
    context.user_data['new_levels'].append(level)
    await update.message.reply_text(f'Уровень {level} добавлен для {ticker}!')
    # Не отправляем клавиатуру с действиями, чтобы не скрывалась кнопка "Сохранить тикер"
    return 'TICKER_ACTIONS_NEW'

# Добавление EMA
async def add_ema_new_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = context.user_data.get('new_ticker')
    user = update.effective_user
    try:
        ema = int(update.message.text.strip())
        if ema not in [20, 50, 100]:
            raise ValueError
    except ValueError:
        await update.message.reply_text('Некорректный выбор EMA. Введите 20, 50 или 100:')
        return 'ADD_EMA_NEW'
    # Сохраняем EMA во временный список
    if 'new_emas' not in context.user_data:
        context.user_data['new_emas'] = []
    context.user_data['new_emas'].append(ema)
    await update.message.reply_text(f'EMA {ema} добавлена для {ticker}!')
    # Не отправляем клавиатуру с действиями, чтобы не скрывалась кнопка "Сохранить тикер"
    return 'TICKER_ACTIONS_NEW'

# Просмотр тикеров пользователя
async def my_tickers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    df = user_tickers(user.id)
    if df.empty:
        await update.message.reply_text('У вас пока нет добавленных тикеров.')
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    msg = 'Ваши тикеры:\n'
    tickers = []
    for ticker, group in df.groupby('ticker'):
        emas = ', '.join(str(int(e)) for e in group['ema'].dropna().unique() if str(e) != '' and not pd.isna(e))
        levels = ', '.join(str(l) for l in group['level'].dropna().unique() if str(l) != '' and not pd.isna(l))
        if not emas and not levels:
            continue
        msg += f'• {ticker}:'
        if emas:
            msg += f' EMA {emas}'
        if levels:
            msg += f' уровни: {levels}'
        msg += '\n'
        tickers.append(ticker)
    await update.message.reply_text(msg)
    keyboard = [['Назад']]
    await update.message.reply_text('Введите тикер из списка, чтобы открыть меню управления этим тикером:', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    context.user_data['my_tickers_list'] = tickers
    return 'TICKER_MENU_SELECT'

# Меню тикера
async def ticker_menu_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    if ticker == 'НАЗАД':
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()  # очищаем временные данные
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    tickers = context.user_data.get('my_tickers_list', [])
    if ticker not in tickers:
        await update.message.reply_text('Такого тикера нет в вашем списке. Введите тикер из таблицы или нажмите Назад:')
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
        # Оставляем только последние 100 точек
        data = data[-100:]
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
        keyboard = Parameters.MAIN_MENU_BUTTONS
        context.user_data.clear()  # очищаем временные данные
        await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_MENU_ACTIONS'

# Меню редактирования тикера
async def ticker_edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ticker = context.user_data.get('selected_ticker')
    if text == 'Удалить EMA':
        await update.message.reply_text('Введите EMA, которую хотите удалить (20, 50 или 100):')
        return 'DELETE_EMA'
    elif text == 'Удалить уровень':
        await update.message.reply_text('Введите уровень, который хотите удалить (точное значение):')
        return 'DELETE_LEVEL'
    elif text == 'Назад':
        keyboard = [['График', 'Редактировать тикер'], ['Назад']]
        await update.message.reply_text(f'Меню тикера {ticker}:', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return 'TICKER_MENU_ACTIONS'
    else:
        await update.message.reply_text('Пожалуйста, выберите действие из меню.')
        return 'TICKER_EDIT_MENU'

# Удаление EMA
async def delete_ema_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ticker = context.user_data.get('selected_ticker')
    try:
        ema_to_delete = int(update.message.text.strip())
        if ema_to_delete not in [20, 50, 100]:
            raise ValueError
    except ValueError:
        await update.message.reply_text('Введите корректное значение EMA (20, 50 или 100):')
        return 'DELETE_EMA'
    df = pd.read_csv(TICKERS_CSV)
    before = len(df)
    df = df[~((df['user_id'] == user.id) & (df['ticker'] == ticker) & (df['ema'] == ema_to_delete))]
    # После удаления EMA — если у тикера не осталось ни одной EMA и ни одного уровня, удаляем тикер полностью
    df_check = df[(df['user_id'] == user.id) & (df['ticker'] == ticker)]
    if df_check.empty or (
        df_check['ema'].isna().all() or (df_check['ema'] == '').all()
    ) and (
        df_check['level'].isna().all() or (df_check['level'] == '').all()
    ):
        df = df[~((df['user_id'] == user.id) & (df['ticker'] == ticker))]
    df.to_csv(TICKERS_CSV, index=False)
    after = len(df)
    if before == after:
        await update.message.reply_text(f'EMA {ema_to_delete} не найдена для {ticker}.')
    else:
        if df_check.empty or (
            df_check['ema'].isna().all() or (df_check['ema'] == '').all()
        ) and (
            df_check['level'].isna().all() or (df_check['level'] == '').all()
        ):
            await update.message.reply_text(f'Тикер {ticker} больше не отслеживается.')
            keyboard = Parameters.MAIN_MENU_BUTTONS
            context.user_data.clear()
            await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return ConversationHandler.END
        else:
            await update.message.reply_text(f'EMA {ema_to_delete} удалена для {ticker}.')
    keyboard = [['Удалить EMA', 'Удалить уровень'], ['Назад']]
    await update.message.reply_text('Что вы хотите отредактировать?', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return 'TICKER_EDIT_MENU'

async def delete_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ticker = context.user_data.get('selected_ticker')
    try:
        level_to_delete = float(update.message.text.strip().replace(',', '.'))
    except ValueError:
        await update.message.reply_text('Введите корректное значение уровня (например, 320.0):')
        return 'DELETE_LEVEL'
    df = pd.read_csv(TICKERS_CSV)
    mask = (df['user_id'] == user.id) & (df['ticker'] == ticker) & (df['level'] == level_to_delete)
    if not mask.any():
        await update.message.reply_text(f'Уровень {level_to_delete} не найден для {ticker}.')
    else:
        df.loc[mask, 'level'] = float('nan')
        # После удаления уровня — если у тикера не осталось ни одной EMA и ни одного уровня, удаляем тикер полностью
        df_check = df[(df['user_id'] == user.id) & (df['ticker'] == ticker)]
        if df_check['ema'].isna().all() or (df_check['ema'] == '').all():
            ema_empty = True
        else:
            ema_empty = False
        if df_check['level'].isna().all() or (df_check['level'] == '').all():
            level_empty = True
        else:
            level_empty = False
        if ema_empty and level_empty:
            df = df[~((df['user_id'] == user.id) & (df['ticker'] == ticker))]
            await update.message.reply_text(f'Тикер {ticker} больше не отслеживается.')
            keyboard = Parameters.MAIN_MENU_BUTTONS
            context.user_data.clear()
            df.to_csv(TICKERS_CSV, index=False)
            await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return ConversationHandler.END
        df.to_csv(TICKERS_CSV, index=False)
        await update.message.reply_text(f'Уровень {level_to_delete} удалён для {ticker}.')
    keyboard = [['Удалить EMA', 'Удалить уровень'], ['Назад']]
    await update.message.reply_text('Что вы хотите отредактировать?', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return 'TICKER_EDIT_MENU'

#  обработчик для кнопки История аномалий
async def history_anomalies_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    anomalies_file = Parameters.ANOMALIES_CSV
    if not os.path.exists(anomalies_file):
        await update.message.reply_text('У вас пока нет истории аномалий.')
        return
    df = pd.read_csv(anomalies_file)
    user_anomalies = df[df['user_id'] == user.id]
    if user_anomalies.empty:
        await update.message.reply_text('У вас пока нет истории аномалий.')
        return
    # Формируем шапку таблицы
    msg = 'Тикер | Дата | Тип аномалии | Цена | Уровень/EMA\n'
    msg += '-'*55 + '\n'
    for _, row in user_anomalies.iterrows():
        anomaly_type = row['anomaly_type']
        if anomaly_type == 'support_break':
            anomaly_type_str = 'Пробитие поддержки'
        elif anomaly_type == 'resistance_break':
            anomaly_type_str = 'Пробитие сопротивления'
        elif anomaly_type == 'ema_cross':
            anomaly_type_str = f"Пересечение EMA {row['ema_window']}"
        else:
            anomaly_type_str = anomaly_type
        level_or_ema = row['level'] if pd.notna(row['level']) and row['level'] != '' else row['ema']
        msg += f"{row['ticker']} | {row['date']} | {anomaly_type_str} | {row['price']} | {level_or_ema}\n"
    await update.message.reply_text(msg)

async def add_ticker_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = Parameters.MAIN_MENU_BUTTONS
    context.user_data.clear()
    await update.message.reply_text('Вы вернулись в главное меню.', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ConversationHandler.END

#Проверка аномалий и отправка сообщений
async def check_anomalies_job(context: ContextTypes.DEFAULT_TYPE):
    parser = MOEXParser()
    detector = AnomalyDetector()
    ensure_tickers_csv()
    if not os.path.exists(TICKERS_CSV):
        return
    df = pd.read_csv(TICKERS_CSV)
    if df.empty:
        return
    users = df['user_id'].unique()
    for user_id in users:
        user_df = df[df['user_id'] == user_id]
        username = user_df['username'].iloc[0] if 'username' in user_df.columns else ''
        for ticker in user_df['ticker'].unique():
            ticker_df = user_df[user_df['ticker'] == ticker]
            emas = [int(e) for e in ticker_df['ema'].dropna().unique() if str(e) != '' and not pd.isna(e)]
            levels = [float(l) for l in ticker_df['level'].dropna().unique() if str(l) != '' and not pd.isna(l)]
            # Для простоты: поддерживаем только один уровень как resistance и один как support (можно расширить)
            support = min(levels) if levels else None
            resistance = max(levels) if levels else None
            price = parser.get_current_price(ticker)
            if price is None:
                continue
            # Обновляем историю для EMA
            detector.update_ema_history(ticker, price, ema_windows=emas)
            # Проверка аномалий по уровням
            level_anomaly = detector.check_level_anomaly(price, support, resistance)
            anomalies = []
            if level_anomaly:
                level_anomaly['ticker'] = ticker
                anomalies.append(level_anomaly)
            # Проверка аномалий по EMA
            ema_anomalies = detector.check_ema_anomaly(ticker, price, ema_windows=emas)
            anomalies.extend(ema_anomalies)
            # Отправка сообщений и запись в CSV
            for anomaly in anomalies:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Формируем информативное сообщение
                if anomaly['type'] in ('support_break', 'resistance_break'):
                    level_type = 'поддержки' if anomaly.get('level_type') == 'support' else 'сопротивления'
                    msg = (f"Тикер: {ticker}\n"
                           f"Дата: {now}\n"
                           f"Пробитие {level_type}\n"
                           f"Цена: {anomaly.get('current_price', '')}\n"
                           f"Уровень: {anomaly.get('level', '')}")
                elif anomaly['type'] == 'ema_cross':
                    msg = (f"Тикер: {ticker}\n"
                           f"Дата: {now}\n"
                           f"Пересечение EMA {anomaly.get('ema_window', '')}\n"
                           f"Цена: {anomaly.get('current_price', '')}\n"
                           f"EMA: {anomaly.get('ema', '')}")
                else:
                    msg = f"{ticker} {now} {anomaly['type']} {anomaly.get('current_price', '')}"
                try:
                    await context.bot.send_message(chat_id=int(user_id), text=msg)
                except Exception as e:
                    print(f"Ошибка отправки сообщения: {e}")
                # Запись в anomalies.csv
                row = {
                    'user_id': user_id,
                    'username': username,
                    'ticker': ticker,
                    'date': now,
                    'anomaly_type': anomaly['type'],
                    'price': anomaly.get('current_price', ''),
                    'level': anomaly.get('level', ''),
                    'level_type': anomaly.get('level_type', ''),
                    'ema_window': anomaly.get('ema_window', ''),
                    'ema': anomaly.get('ema', '')
                }
                file_exists = os.path.exists(ANOMALIES_CSV)
                with open(ANOMALIES_CSV, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(row)
                # Удаление уровня после срабатывания аномалии
                if anomaly['type'] in ('support_break', 'resistance_break'):
                    # Удаляем уровень из tickers.csv
                    df = pd.read_csv(TICKERS_CSV)
                    mask = (df['user_id'] == user_id) & (df['ticker'] == ticker) & (df['level'] == anomaly.get('level'))
                    df = df[~mask]
                    # Удаляем строки, где и ema, и level пустые (или NaN) для этого пользователя и тикера
                    empty_mask = (
                        (df['user_id'] == user_id) &
                        (df['ticker'] == ticker) &
                        ((df['ema'].isna() | (df['ema'] == '')) & (df['level'].isna() | (df['level'] == '')))
                    )
                    df = df[~empty_mask]
                    # Если после удаления не осталось ни одной записи по тикеру для пользователя — удаляем тикер полностью
                    user_ticker_df = df[(df['user_id'] == user_id) & (df['ticker'] == ticker)]
                    if user_ticker_df.empty:
                        df = df[~((df['user_id'] == user_id) & (df['ticker'] == ticker))]
                    df.to_csv(TICKERS_CSV, index=False)

def main():
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^Добавить тикер$'), add_ticker_start),
            MessageHandler(filters.Regex('^Мои тикеры$'), my_tickers_handler),
            MessageHandler(filters.Regex('^История аномалий$'), history_anomalies_handler)
        ],
        states={
            ADD_TICKER: [
                MessageHandler(filters.Regex('^Назад$'), add_ticker_back_handler),
                MessageHandler(filters.TEXT & ~filters.Regex('^(Мои тикеры|История аномалий|Добавить тикер)$'), add_ticker_handler)
            ],
            'TICKER_ACTIONS_NEW': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_actions_new_handler)],
            'ADD_LEVEL_NEW': [MessageHandler(filters.TEXT & ~filters.COMMAND, add_level_new_handler)],
            'ADD_EMA_NEW': [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ema_new_handler)],
            'TICKER_MENU_SELECT': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_menu_select_handler)],
            'TICKER_MENU_ACTIONS': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_menu_actions_handler)],
            'TICKER_EDIT_MENU': [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_edit_menu_handler)],
            'DELETE_EMA': [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_ema_handler)],
            'DELETE_LEVEL': [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_level_handler)],
        },
        fallbacks=[]
    )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    # Запуск периодической проверки аномалий
    job_queue = application.job_queue
    job_queue.run_repeating(check_anomalies_job, interval=Parameters.ANOMALY_CHECK_INTERVAL_SEC, first=10)  # каждые 3 минуты
    application.run_polling()

if __name__ == "__main__":
    main()