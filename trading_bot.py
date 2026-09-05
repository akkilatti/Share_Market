# trading_bot.py - Main Trading Bot with EMA Strategy

import time
import logging
import pandas as pd
from datetime import datetime, timedelta
import schedule
import signal
import sys
from threading import Thread

from auth import FyersAuth
from data_handler import DataHandler
from order_manager import OrderManager
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EMATradeBot:
    def __init__(self):
        self.auth = None
        self.data_handler = None
        self.order_manager = None
        self.is_running = False
        self.last_signal = 0
        self.last_signal_time = None
        self.trade_count = 0
        self.max_trades_per_day = 5
        self.trading_active = False
        
        # Performance tracking
        self.start_time = datetime.now()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
    
    def initialize(self):
        """Initialize all components"""
        try:
            logger.info("Initializing Trading Bot...")
            
            # Initialize authentication
            self.auth = FyersAuth()
            if not self.auth.load_token():
                logger.info("No valid token found, authenticating...")
                if not self.auth.authenticate():
                    logger.error("Authentication failed!")
                    return False
                self.auth.save_token()
            
            # Initialize data handler and order manager
            self.data_handler = DataHandler(self.auth.fyers)
            self.order_manager = OrderManager(self.auth.fyers)
            
            logger.info("Trading Bot initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            return False
    
    def check_ema_signals(self):
        """Check for EMA crossover signals"""
        try:
            # Get market data with indicators
            market_data = self.data_handler.get_market_data()
            if market_data is None:
                logger.warning("Could not fetch market data")
                return 0, None
            
            # Get latest values
            latest = market_data.iloc[-1]
            previous = market_data.iloc[-2] if len(market_data) > 1 else None
            
            if previous is None:
                return 0, latest
            
            # Check for EMA crossover
            current_signal = latest['ema_signal']
            
            # Additional filters
            current_price = latest.get('current_price', latest['close'])
            rsi = latest.get('rsi', 50)
            
            # Log current market state
            logger.info(f"Price: {current_price:.2f}, EMA5: {latest['ema_5']:.2f}, "
                       f"EMA21: {latest['ema_21']:.2f}, RSI: {rsi:.2f}, Signal: {current_signal}")
            
            # Apply additional filters
            if current_signal == 1:  # Buy signal
                # Filter: RSI should not be overbought
                if rsi > 70:
                    logger.info("Buy signal filtered out - RSI overbought")
                    return 0, latest
                
                # Filter: Price should be above EMA21
                if current_price < latest['ema_21']:
                    logger.info("Buy signal filtered out - Price below EMA21")
                    return 0, latest
            
            elif current_signal == -1:  # Sell signal
                # Filter: RSI should not be oversold for sell
                if rsi < 30:
                    logger.info("Sell signal filtered out - RSI oversold")
                    return 0, latest
            
            return current_signal, latest
            
        except Exception as e:
            logger.error(f"Error checking EMA signals: {e}")
            return 0, None
    
    def execute_trade(self, signal, market_data):
        """Execute trade based on signal"""
        try:
            if self.trade_count >= self.max_trades_per_day:
                logger.info("Max trades per day reached")
                return False
            
            current_price = market_data.get('current_price', market_data['close'])
            
            # Execute the strategy
            order_id = self.order_manager.execute_ema_strategy(signal, current_price)
            
            if order_id:
                self.last_signal = signal
                self.last_signal_time = datetime.now()
                self.trade_count += 1
                self.total_trades += 1
                
                signal_type = "BUY" if signal == 1 else "SELL"
                logger.info(f"Trade executed: {signal_type} at {current_price}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def monitor_positions(self):
        """Monitor existing positions and manage risk"""
        try:
            positions = self.order_manager.get_positions()
            if not positions:
                return
            
            for symbol, position in positions.items():
                if symbol == Config.SYMBOL:
                    pnl = position['pnl']
                    quantity = position['quantity']
                    current_price = position['current_price']
                    avg_price = position['avg_price']
                    
                    # Log position status
                    pnl_percent = (pnl / (avg_price * abs(quantity))) * 100
                    logger.info(f"Position: {quantity} @ {avg_price}, "
                               f"Current: {current_price}, P&L: {pnl} ({pnl_percent:.2f}%)")
                    
                    # Update performance tracking
                    if pnl > 0:
                        self.winning_trades += 1
                    elif pnl < 0:
                        self.losing_trades += 1
                    
                    self.total_pnl += pnl
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def run_strategy_cycle(self):
        """Run one cycle of the trading strategy"""
        try:
            if not self.trading_active:
                return
            
            # Check if market is open
            if not self.data_handler.check_trading_hours():
                if self.trading_active:
                    logger.info("Market closed - stopping trading")
                    self.trading_active = False
                return
            
            logger.info("Running strategy cycle...")
            
            # Check for signals
            signal, market_data = self.check_ema_signals()
            
            if signal != 0 and market_data is not None:
                # Avoid duplicate signals
                if (signal != self.last_signal or 
                    self.last_signal_time is None or 
                    datetime.now() - self.last_signal_time > timedelta(minutes=15)):
                    
                    logger.info(f"New signal detected: {signal}")
                    self.execute_trade(signal, market_data)
                else:
                    logger.info("Signal ignored - too soon after last signal")
            
            # Monitor existing positions
            self.monitor_positions()
            
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
    
    def start_market_session(self):
        """Start trading for the day"""
        try:
            if self.data_handler.check_trading_hours():
                self.trading_active = True
                self.trade_count = 0  # Reset daily trade count
                logger.info("Market session started - Trading activated")
                
                # Print initial summary
                self.print_status()
            else:
                logger.info("Market not open yet")
                
        except Exception as e:
            logger.error(f"Error starting market session: {e}")
    
    def end_market_session(self):
        """End trading for the day"""
        try:
            self.trading_active = False
            logger.info("Market session ended - Trading deactivated")
            
            # Close any open positions (optional)
            positions = self.order_manager.get_positions()
            if positions and Config.SYMBOL in positions:
                logger.info("Closing end-of-day positions...")
                current_price = self.data_handler.get_current_price()
                if current_price:
                    self.order_manager.place_sell_order(current_price)
            
            # Print daily summary
            self.print_daily_summary()
            
        except Exception as e:
            logger.error(f"Error ending market session: {e}")
    
    def print_status(self):
        """Print current bot status"""
        try:
            print("\n" + "="*60)
            print("EMA TRADING BOT STATUS")
            print("="*60)
            print(f"Symbol: {Config.SYMBOL}")
            print(f"Strategy: {Config.EMA_SHORT} & {Config.EMA_LONG} EMA Crossover")
            print(f"Quantity: {Config.QUANTITY}")
            print(f"Stop Loss: {Config.STOP_LOSS_PERCENT}%")
            print(f"Target: {Config.TARGET_PERCENT}%")
            print(f"Trading Active: {self.trading_active}")
            print(f"Trades Today: {self.trade_count}/{self.max_trades_per_day}")
            print(f"Last Signal: {self.last_signal} at {self.last_signal_time}")
            print("="*60)
            
            # Current market data
            current_price = self.data_handler.get_current_price()
            if current_price:
                print(f"Current Price: {current_price}")
            
            # Current positions
            self.order_manager.print_summary()
            
        except Exception as e:
            logger.error(f"Error printing status: {e}")
    
    def print_daily_summary(self):
        """Print daily trading summary"""
        try:
            runtime = datetime.now() - self.start_time
            win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100
            
            print("\n" + "="*60)
            print("DAILY TRADING SUMMARY")
            print("="*60)
            print(f"Runtime: {runtime}")
            print(f"Total Trades: {self.total_trades}")
            print(f"Winning Trades: {self.winning_trades}")
            print(f"Losing Trades: {self.losing_trades}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Total P&L: {self.total_pnl:.2f}")
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error printing daily summary: {e}")
    
    def schedule_tasks(self):
        """Schedule trading tasks"""
        # Market open
        schedule.every().monday.at("09:15").do(self.start_market_session)
        schedule.every().tuesday.at("09:15").do(self.start_market_session)
        schedule.every().wednesday.at("09:15").do(self.start_market_session)
        schedule.every().thursday.at("09:15").do(self.start_market_session)
        schedule.every().friday.at("09:15").do(self.start_market_session)
        
        # Market close
        schedule.every().monday.at("15:30").do(self.end_market_session)
        schedule.every().tuesday.at("15:30").do(self.end_market_session)
        schedule.every().wednesday.at("15:30").do(self.end_market_session)
        schedule.every().thursday.at("15:30").do(self.end_market_session)
        schedule.every().friday.at("15:30").do(self.end_market_session)
        
        # Strategy execution every minute during trading hours
        schedule.every(1).minutes.do(self.run_strategy_cycle)
        
        # Status update every 30 minutes
        schedule.every(30).minutes.do(self.print_status)
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        logger.info("Received interrupt signal, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start the trading bot"""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            if not self.initialize():
                return False
            
            self.is_running = True
            self.schedule_tasks()
            
            logger.info("Trading Bot started successfully!")
            
            # Check if market is currently open
            self.start_market_session()
            
            # Main loop
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        try:
            self.is_running = False
            self.trading_active = False
            
            logger.info("Trading Bot stopped")
            self.print_daily_summary()
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

def main():
    """Main function"""
    print("Starting EMA Trading Bot...")
    print(f"Symbol: {Config.SYMBOL}")
    print(f"Strategy: {Config.EMA_SHORT} & {Config.EMA_LONG} EMA Crossover")
    
    bot = EMATradeBot()
    bot.start()

if __name__ == "__main__":
    main()