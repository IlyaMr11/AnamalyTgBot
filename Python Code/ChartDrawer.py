import matplotlib.pyplot as plt
import numpy as np
import io
import matplotlib.dates as mdates

class ChartDrawer:
    @staticmethod
    def draw_chart(ticker, dates, closes, emas_dict, level=None):
        plt.figure(figsize=(10, 5))
        closes = np.array(closes)
        plt.plot(dates, closes, label='Цена', color='blue')
        colors = {20: 'orange', 50: 'green', 100: 'red'}
        for window, ema in emas_dict.items():
            ema = np.array(ema)
            plt.plot(dates[-len(ema):], ema, label=f'EMA{window}', color=colors.get(window, None))
        if level is not None:
            plt.axhline(level, color='purple', linestyle='--', label=f'Уровень {level}')
        plt.title(f'{ticker} — график с EMA')
        plt.xlabel('Время')
        plt.ylabel('Цена')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%m %H:%M'))
        plt.gcf().autofmt_xdate()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        return buf 