# moex_parser.py
import requests
from datetime import datetime, timedelta
from parameters import Parameters

class MOEXParser:
    BASE_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities"

    def __init__(self, timeout=10):
        self.timeout = timeout

    def get_current_price(self, ticker: str):
        url = f"{self.BASE_URL}/{ticker}.json"
        params = {"interval": 1}
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if not data["marketdata"]["data"]:
                    print(f"Тикер {ticker} не найден или нет данных.")
                    return None
                columns = data["marketdata"]["columns"]
                for row in data["marketdata"]["data"]:
                    row_dict = dict(zip(columns, row))
                    if row_dict.get("BOARDID") == "TQBR":
                        return row_dict.get("LAST")
                print(f"Тикер {ticker} не торгуется на TQBR или нет актуальных данных.")
                return None
            print(f"Ошибка HTTP: {response.status_code}")
            return None
        except Exception as e:
            print(f"Ошибка сети: {e}")
            return None

    def get_historical_prices(self, ticker: str, interval=None, count=None):
        till = datetime.now()
        interval = interval if interval is not None else Parameters.MOEX_INTERVAL_MINUTES
        count = count if count is not None else Parameters.MOEX_CANDLES_LIMIT
        from_date = till - timedelta(hours=Parameters.MOEX_HISTORY_HOURS)
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}/candles.json"
        params = {
            "interval": interval,  # 1 - 1 минута, 10 - 10 минут, 60 - 1 час
            "from": from_date.strftime('%Y-%m-%d'),
            "till": till.strftime('%Y-%m-%d'),
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
                        dt = datetime.strptime(begin, '%Y-%m-%d %H:%M:%S')
                        result.append((dt, close))
                return result
            print(f"Ошибка HTTP: {response.status_code}")
            return []
        except Exception as e:
            print(f"Ошибка сети: {e}")
            return []