# anomaly_detector.py
import logging
from collections import deque


class AnomalyDetector:
    def __init__(self, window_size=5, price_change_threshold=1.0):
        self.window_size = window_size
        self.price_change_threshold = price_change_threshold
        self.price_history = {}
        self.logger = logging.getLogger(__name__)

    def init_ticker(self, ticker: str):
        if ticker not in self.price_history:
            self.price_history[ticker] = deque(maxlen=self.window_size)

    def update_price(self, ticker: str, price: float):
        self.init_ticker(ticker)
        self.price_history[ticker].append(price)

    def check_level_anomaly(self, current_price: float, support: float, resistance: float):
        if resistance is not None and current_price > resistance:
            return {
                "type": "resistance_break",
                "current_price": current_price,
                "level": resistance,
                "level_type": "resistance"
            }
        if support is not None and current_price < support:
            return {
                "type": "support_break",
                "current_price": current_price,
                "level": support,
                "level_type": "support"
            }
        return None

    def init_ticker_ema(self, ticker: str, ema_windows=(20, 50, 100)):
        if not hasattr(self, 'ema_history'):
            self.ema_history = {}
        if ticker not in self.ema_history:
            self.ema_history[ticker] = {}
            for window in ema_windows:
                self.ema_history[ticker][window] = []

    def update_ema_history(self, ticker: str, price: float, ema_windows=(20, 50, 100)):
        self.init_ticker_ema(ticker, ema_windows)
        for window in ema_windows:
            self.ema_history[ticker][window].append(price)
            if len(self.ema_history[ticker][window]) > window * 3:
                self.ema_history[ticker][window] = self.ema_history[ticker][window][-window*3:]

    def calculate_ema(self, ticker: str, window: int):
        if not hasattr(self, 'ema_history') or ticker not in self.ema_history or window not in self.ema_history[ticker]:
            return None
        prices = self.ema_history[ticker][window]
        if len(prices) < window:
            return None
        ema = prices[0]
        k = 2 / (window + 1)
        for price in prices[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def check_ema_anomaly(self, ticker: str, current_price: float, ema_windows=(20, 50, 100)):
        anomalies = []
        for window in ema_windows:
            ema = self.calculate_ema(ticker, window)
            if ema is None:
                continue
            prices = self.ema_history[ticker][window]
            if len(prices) < 2:
                continue
            prev_price = prices[-2]
            crossed = (prev_price < ema and current_price >= ema) or (prev_price > ema and current_price <= ema)
            if crossed:
                anomalies.append({
                    "type": "ema_cross",
                    "ticker": ticker,
                    "ema_window": window,
                    "ema": ema,
                    "current_price": current_price
                })
        return anomalies

    def detect_anomalies(self, ticker: str, current_price: float, support=None, resistance=None, ema_windows=(20, 50, 100)):
        anomalies = []
        self.update_price(ticker, current_price)
        self.update_ema_history(ticker, current_price, ema_windows)
        sma_anomaly = self.check_sma_anomaly(ticker, current_price)
        if sma_anomaly:
            anomalies.append(sma_anomaly)
        level_anomaly = self.check_level_anomaly(current_price, support, resistance)
        if level_anomaly:
            level_anomaly["ticker"] = ticker
            anomalies.append(level_anomaly)
        ema_anomalies = self.check_ema_anomaly(ticker, current_price, ema_windows)
        anomalies.extend(ema_anomalies)
        return anomalies