class Parameters:
    # Пути к файлам
    TICKERS_CSV = 'tickers.csv'
    ANOMALIES_CSV = 'anomalies.csv'

    # Интервалы и лимиты
    MOEX_INTERVAL_MINUTES = 1
    MOEX_CANDLES_LIMIT = 150
    MOEX_HISTORY_HOURS = 10  # сколько часов назад брать from для истории

    # Проверка аномалий
    ANOMALY_CHECK_INTERVAL_SEC = 180  # раз в 3 минуты

    # Стандартные EMA
    DEFAULT_EMAS = [20, 50, 100]

    # Telegram
    MAIN_MENU_BUTTONS = [['Добавить тикер', 'Мои тикеры'], ['История аномалий']]