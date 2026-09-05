# data_handler.py - Market Data Handler

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from config import Config

logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self, fyers_client):
        self.fyers = fyers_client
        self.symbol = Config.SYMBOL
        self.timeframe = Config.TIMEFRAME
    
    def get_historical_data(self, days=None):
        """Fetch historical data for the symbol"""
        try:
            if days is None:
                days = Config.HISTORICAL_DAYS
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for API
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            
            # Fetch data
            data = {
                "symbol": self.symbol,
                "resolution": self.timeframe,
                "date_format": "1",
                "range_from": from_date,
                "range_to": to_date,
                "cont_flag": "1"
            }
            
            response = self.fyers.history(data)
            
            if response['code'] == 200:
                candles = response['candles']
                
                # Convert to DataFrame
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                logger.info(f"Fetched {len(df)} historical candles")
                return df
            else:
                logger.error(f"Failed to fetch historical data: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None
    
    def get_current_price(self):
        """Get current market price"""
        try:
            data = {"symbols": self.symbol}
            response = self.fyers.quotes(data)
            
            if response['code'] == 200:
                quote = response['d'][0]['v']
                current_price = quote['lp']  # Last price
                logger.info(f"Current price of {self.symbol}: {current_price}")
                return current_price
            else:
                logger.error(f"Failed to get current price: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    def calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        try:
            if len(data) < period:
                logger.warning(f"Not enough data for EMA calculation. Need {period}, got {len(data)}")
                return None
            
            ema = data['close'].ewm(span=period, adjust=False).mean()
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return None
    
    def calculate_indicators(self, data):
        """Calculate all required technical indicators"""
        try:
            # Calculate EMAs
            data['ema_5'] = self.calculate_ema(data, Config.EMA_SHORT)
            data['ema_21'] = self.calculate_ema(data, Config.EMA_LONG)
            
            # Calculate EMA crossover signals
            data['ema_diff'] = data['ema_5'] - data['ema_21']
            data['ema_signal'] = 0
            
            # Generate signals
            for i in range(1, len(data)):
                if (data['ema_diff'].iloc[i] > 0 and data['ema_diff'].iloc[i-1] <= 0):
                    data['ema_signal'].iloc[i] = 1  # Buy signal
                elif (data['ema_diff'].iloc[i] < 0 and data['ema_diff'].iloc[i-1] >= 0):
                    data['ema_signal'].iloc[i] = -1  # Sell signal
            
            # Add additional indicators
            data['rsi'] = self.calculate_rsi(data['close'])
            data['atr'] = self.calculate_atr(data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    def calculate_atr(self, data, period=14):
        """Calculate Average True Range"""
        try:
            high_low = data['high'] - data['low']
            high_close = np.abs(data['high'] - data['close'].shift())
            low_close = np.abs(data['low'] - data['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            return atr
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None
    
    def get_market_data(self):
        """Get complete market data with indicators"""
        try:
            # Fetch historical data
            data = self.get_historical_data()
            if data is None:
                return None
            
            # Calculate indicators
            data = self.calculate_indicators(data)
            if data is None:
                return None
            
            # Get current price
            current_price = self.get_current_price()
            if current_price:
                # Add current price info to latest candle
                data.loc[data.index[-1], 'current_price'] = current_price
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    def check_trading_hours(self):
        """Check if market is open for trading"""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # Check if it's a weekday (Monday=0, Sunday=6)
            if now.weekday() >= 5:  # Saturday or Sunday
                return False
            
            # Check trading hours
            if Config.TRADING_START_TIME <= current_time <= Config.TRADING_END_TIME:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking trading hours: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    from auth import FyersAuth
    
    # Authenticate
    auth = FyersAuth()
    if auth.load_token():
        # Initialize data handler
        data_handler = DataHandler(auth.fyers)
        
        # Get market data
        market_data = data_handler.get_market_data()
        if market_data is not None:
            print("Latest data:")
            print(market_data.tail())
            
            # Check latest signals
            latest_signal = market_data['ema_signal'].iloc[-1]
            if latest_signal == 1:
                print("BUY SIGNAL detected!")
            elif latest_signal == -1:
                print("SELL SIGNAL detected!")
            else:
                print("No signal")
        
        # Check trading hours
        is_trading_time = data_handler.check_trading_hours()
        print(f"Trading hours: {is_trading_time}")
    else:
        print("Authentication failed!")