#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Crypto Trading Bot – Универсальный
Поддерживает Binance Testnet и Bybit Testnet.
Выбор биржи через переменную окружения EXCHANGE.
"""

import os
import time
import sys
from dotenv import load_dotenv

# ============================================
# 1. ЗАГРУЗКА ПЕРЕМЕННЫХ ИЗ .env
# ============================================
load_dotenv()

EXCHANGE = os.getenv('EXCHANGE', 'binance').lower()
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
QUANTITY = float(os.getenv('QUANTITY', 0.001))
STOP_LOSS = float(os.getenv('STOP_LOSS', 0.10))
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 120))

print(f"🚀 Запуск бота...")
print(f"📊 Биржа: {EXCHANGE}")
print(f"📈 Торгуем: {SYMBOL}")
print(f"⚖️ Размер сделки: {QUANTITY}")
print(f"🛑 Стоп-лосс: {STOP_LOSS * 100}%")

# ============================================
# 2. ВЫБОР БИРЖИ И ПОДКЛЮЧЕНИЕ
# ============================================

if EXCHANGE == 'binance':
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    if not API_KEY or not API_SECRET:
        raise ValueError("❌ Для Binance нужны BINANCE_API_KEY и BINANCE_API_SECRET в .env")
    
    try:
        client = Client(API_KEY, API_SECRET, testnet=True)
        client.get_server_time()
        print("✅ Подключение к Binance Testnet установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к Binance: {e}")
        sys.exit(1)
    
    def get_klines():
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1DAY, limit=100)
        import pandas as pd
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                           'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                                           'taker_buy_quote', 'ignore'])
        df['close'] = df['close'].astype(float)
        return df
    
    def place_order(side):
        if side == 'BUY':
            return client.order_market_buy(symbol=SYMBOL, quantity=QUANTITY)
        else:
            return client.order_market_sell(symbol=SYMBOL, quantity=QUANTITY)

elif EXCHANGE == 'bybit':
    from pybit.unified_trading import HTTP
    
    API_KEY = os.getenv('BYBIT_API_KEY')
    API_SECRET = os.getenv('BYBIT_API_SECRET')
    
    if not API_KEY or not API_SECRET:
        raise ValueError("❌ Для Bybit нужны BYBIT_API_KEY и BYBIT_API_SECRET в .env")
    
    try:
        session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)
        # ИСПРАВЛЕНО: правильный метод для проверки соединения
        session.get_server_time()
        print("✅ Подключение к Bybit Testnet установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к Bybit: {e}")
        sys.exit(1)
    
    def get_klines():
        import pandas as pd
        response = session.get_kline(category="spot", symbol=SYMBOL, interval="D", limit=100)
        if response['retCode'] != 0:
            raise Exception(f"Ошибка API: {response['retMsg']}")
        data = response['result']['list']
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['close'] = df['close'].astype(float)
        return df
    
    def place_order(side):
        if side == 'BUY':
            return session.place_order(category="spot", symbol=SYMBOL, side="Buy", orderType="Market", qty=str(QUANTITY))
        else:
            return session.place_order(category="spot", symbol=SYMBOL, side="Sell", orderType="Market", qty=str(QUANTITY))

else:
    raise ValueError(f"❌ Неподдерживаемая биржа: {EXCHANGE}. Используйте 'binance' или 'bybit'.")

# ============================================
# 3. ОБЩАЯ ЛОГИКА СТРАТЕГИИ
# ============================================

def calculate_signal(df):
    """Расчет сигнала на основе SMA 5 и SMA 20"""
    if df is None or len(df) < 30:
        return 0
    df['sma5'] = df['close'].rolling(5).mean()
    df['sma20'] = df['close'].rolling(20).mean()
    if df['sma5'].iloc[-1] > df['sma20'].iloc[-1]:
        return 1
    elif df['sma5'].iloc[-1] < df['sma20'].iloc[-1]:
        return -1
    return 0

# ============================================
# 4. ОСНОВНОЙ ЦИКЛ
# ============================================

def main():
    in_position = False
    entry_price = 0.0
    
    print("🔄 Бот готов. Начинаю мониторинг...")
    print("=" * 50)
    
    while True:
        try:
            df = get_klines()
            if df is None:
                print(f"⏳ Нет данных, ждем {SLEEP_TIME} секунд...")
                time.sleep(SLEEP_TIME)
                continue
            
            signal = calculate_signal(df)
            current_price = df['close'].iloc[-1]
            
            print(f"📊 Цена: {current_price:.2f} | Сигнал: {signal} | В позиции: {in_position}")
            
            # Стоп-лосс
            if in_position and entry_price > 0:
                pnl = (current_price - entry_price) / entry_price
                if pnl < -STOP_LOSS:
                    print(f"🛑 СТОП-ЛОСС! Продажа по {current_price:.2f}")
                    place_order('SELL')
                    in_position = False
                    entry_price = 0.0
                    time.sleep(SLEEP_TIME)
                    continue
            
            # Сигнал на покупку
            if signal == 1 and not in_position:
                print(f"📈 Сигнал на покупку по {current_price:.2f}")
                place_order('BUY')
                in_position = True
                entry_price = current_price
            
            # Сигнал на продажу
            elif signal == -1 and in_position:
                print(f"📉 Сигнал на продажу по {current_price:.2f}")
                place_order('SELL')
                in_position = False
                entry_price = 0.0
            
            print(f"⏳ Ждем {SLEEP_TIME} секунд...")
            time.sleep(SLEEP_TIME)
            
        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    main()