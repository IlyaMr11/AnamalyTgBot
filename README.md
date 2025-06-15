# Anomaly MOEX Telegram Bot

## Описание

Telegram-бот для отслеживания аномалий на Московской бирже (MOEX) с хранением пользовательских настроек и истории в CSV. Поддерживает EMA, уровни, графики, историю аномалий и гибкое меню.

---

## Быстрый старт: установка и запуск в Anaconda

### 1. Установите Anaconda
Скачайте и установите Anaconda с официального сайта:  
https://www.anaconda.com/products/distribution

---

### 2. Клонируйте репозиторий

```bash
git clone https://github.com/IlyaMr11/AnamalyTgBot.git
cd AnamalyTgBot
```

---

### 3. Создайте и активируйте окружение

```bash
conda create -n anomaly-tg-bot python=3.11
conda activate anomaly-tg-bot
```

---

### 4. Установите зависимости

#### 4.1. Установите основные библиотеки через conda

```bash
conda install pandas numpy matplotlib requests python-dateutil pytz lxml
```

#### 4.2. Установите остальные зависимости через pip

```bash
pip install -r requirements.txt
```
 **Важно:**  
 Для поддержки JobQueue в python-telegram-bot обязательно используйте pip и убедитесь, что установлен пакет `python-telegram-bot[job-queue]`.  
 Если потребуется, выполните:
 ```bash
 pip install "python-telegram-bot[job-queue]"
 ```

---

### 5. Настройте переменные окружения

Создайте файл `.env` в корне проекта и добавьте ваш Telegram Bot Token:

```
TELEGRAM_TOKEN=ваш_токен_бота
```

---

### 6. (Рекомендуется) Настройте .gitignore

Добавьте в `.gitignore`:

```
.env
tickers.csv
anomalies.csv
__pycache__/
*.pyc
```

---

### 7. Запустите бота

```bash
python tgBot.py
```

## Важно

- **tickers.csv** и **anomalies.csv** создаются автоматически при первом запуске.  
  Не добавляйте их в git-репозиторий!
- Все основные параметры вынесены в файл `parameters.py` для удобства настройки.
- Для корректной работы JobQueue используйте pip-установку python-telegram-bot с опцией `[job-queue]`.


