import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()


class Config:
    # Обязательные настройки
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не найден в .env файле!")

    # Настройки базы данных
    DB_PATH = os.getenv('DB_PATH', 'anomaly_bot.db')
    DB_RETENTION_DAYS = int(os.getenv('DB_RETENTION_DAYS', 30))

    # Настройки API
    MOEX_API_URL = "https://iss.moex.com/iss"
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 10))

    # Список тикеров по умолчанию
    DEFAULT_TICKERS = ["SBER", "GAZP", "YNDX", "VTBR", "TCSG"]

    # Интервал обновления данных (в секундах)
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', 300))