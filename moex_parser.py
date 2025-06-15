# moex_parser.py
import requests
from datetime import datetime
import logging

class MOEXParser:
    BASE_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities"

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def get_current_price(self, ticker: str):
        """Получение текущей цены для одного тикера (синхронно)"""
        url = f"{self.BASE_URL}/{ticker}.json"
        params = {"interval": 1}
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                market_data = dict(zip(
                    data["marketdata"]["columns"],
                    data["marketdata"]["data"][0]
                ))
                return market_data.get('LAST')
            self.logger.error(f"Ошибка HTTP: {response.status_code}")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка сети: {e}")
            return None

    def get_historical_prices(self, ticker: str, interval=60, count=100):
        """Получение исторических данных (дата, цена закрытия) для расчёта EMA/SMA (синхронно)"""
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}/candles.json"
        params = {
            "interval": interval,  # 1 - 1 минута, 10 - 10 минут, 60 - 1 час
            "limit": count
        }
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                candles = data.get("candles", {})
                columns = candles.get("columns", [])
                data_rows = candles.get("data", [])
                if not columns or not data_rows:
                    return []
                close_idx = columns.index("close") if "close" in columns else None
                begin_idx = columns.index("begin") if "begin" in columns else None
                if close_idx is None or begin_idx is None:
                    return []
                result = []
                for row in data_rows:
                    close = row[close_idx]
                    begin = row[begin_idx]
                    if close is not None and begin is not None:
                        # begin формат: '2024-05-24 10:00:00'
                        dt = datetime.strptime(begin, '%Y-%m-%d %H:%M:%S')
                        result.append((dt, close))
                return result
            self.logger.error(f"Ошибка HTTP: {response.status_code}")
            return []
        except Exception as e:
            self.logger.error(f"Ошибка сети: {e}")
            return []