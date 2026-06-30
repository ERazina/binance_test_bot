
# ============================================
# БОТ ДЛЯ ЛОКАЛЬНОГО ЗАПУСКА (10% СТОП-ЛОСС)
# ============================================
import os
import time
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    raise ValueError("❌ Ключи не найдены! Создай файл .env с BINANCE_API_KEY и BINANCE_API_SECRET")

# ============================================
# 1. ПОДКЛЮЧЕНИЕ К ТЕСТОВОЙ СЕТИ
# ============================================
client = Client(API_KEY, API_SECRET, testnet=True)

try:
    server_time = client.get_server_time()
    print("✅ Подключение к Binance Testnet установлено")
except BinanceAPIException as e:
    print(f"❌ Ошибка: {e}")
    exit()
except Exception as e:
    print(f"❌ Неизвестная ошибка: {e}")
    exit()

# ============================================
# 2. НАСТРОЙКИ
# ============================================
SYMBOL = "BTCUSDT"
QUANTITY = 0.001
STOP_LOSS = 0.10
INTERVAL = Client.KLINE_INTERVAL_1DAY
SLEEP_TIME = 120

print(f"🚀 Бот запущен. Торгуем {SYMBOL}, стоп-лосс {STOP_LOSS*100}%")

# ============================================
# 3. ФУНКЦИИ (те же самые, что работали)
# ============================================
def get_klines():
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=100)
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                           'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                                           'taker_buy_quote', 'ignore'])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"❌ Ошибка получения данных: {e}")
        return None

def get_signal(df):
    if df is None or len(df) < 30:
        return 0
    df['sma5'] = df['close'].rolling(5).mean()
    df['sma20'] = df['close'].rolling(20).mean()
    if df['sma5'].iloc[-1] > df['sma20'].iloc[-1]:
        return 1
    elif df['sma5'].iloc[-1] < df['sma20'].iloc[-1]:
        return -1
    return 0

def place_order(side, quantity):
    try:
        if side == 'BUY':
            order = client.order_market_buy(symbol=SYMBOL, quantity=quantity)
        else:
            order = client.order_market_sell(symbol=SYMBOL, quantity=quantity)
        print(f"✅ {side} {quantity} {SYMBOL} по рынку")
        return order
    except Exception as e:
        print(f"❌ Ошибка ордера: {e}")
        return None

# ============================================
# 4. ОСНОВНОЙ ЦИКЛ
# ============================================
in_position = False
entry_price = 0.0

print("🔄 Бот готов. Начинаю мониторинг...")

while True:
    try:
        df = get_klines()
        if df is None:
            time.sleep(SLEEP_TIME)
            continue
        
        signal = get_signal(df)
        current_price = df['close'].iloc[-1]
        print(f"📊 Цена: {current_price:.2f}, Сигнал: {signal}")
        
        if in_position and entry_price > 0:
            pnl = (current_price - entry_price) / entry_price
            if pnl < -STOP_LOSS:
                print(f"🛑 СТОП-ЛОСС 10%! Продажа по {current_price:.2f}")
                place_order('SELL', QUANTITY)
                in_position = False
                entry_price = 0.0
                time.sleep(SLEEP_TIME)
                continue
        
        if signal == 1 and not in_position:
            print(f"📈 Сигнал на покупку по {current_price:.2f}")
            place_order('BUY', QUANTITY)
            in_position = True
            entry_price = current_price
        
        elif signal == -1 and in_position:
            print(f"📉 Сигнал на продажу по {current_price:.2f}")
            place_order('SELL', QUANTITY)
            in_position = False
            entry_price = 0.0
        
        time.sleep(SLEEP_TIME)
        
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
        break
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(SLEEP_TIME)