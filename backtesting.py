import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from config import Config
from auth import FyersAuth
from data_handler import DataHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EMABacktester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        
    def calculate_ema_signals(self, data):
        """Calculate EMA signals for backtesting"""
        try:
            # Calculate EMAs
            data['ema_5'] = data['close'].ewm(span=Config.EMA_SHORT, adjust=False).mean()
            data['ema_21'] = data['close'].ewm(span=Config.EMA_LONG, adjust=False).mean()
            
            # Calculate signals
            data['ema_diff'] = data['ema_5'] - data['ema_21']
            data['signal'] = 0
            data['position'] = 0
            
            # Generate buy/sell signals
            for i in range(1, len(data)):
                if (data['ema_diff'].iloc[i] > 0 and data['ema_diff'].iloc[i-1] <= 0):
                    data['signal'].iloc[i] = 1  # Buy signal
                elif (data['ema_diff'].iloc[i] < 0 and data['ema_diff'].iloc[i-1] >= 0):
                    data['signal'].iloc[i] = -1  # Sell signal
            
            # Calculate positions
            position = 0
            for i in range(len(data)):
                if data['signal'].iloc[i] == 1:
                    position = 1
                elif data['signal'].iloc[i] == -1:
                    position = 0
                data['position'].iloc[i] = position
            
            return data
            
        except Exception as e:
            logger.error(f"Error calculating EMA signals: {e}")
            return None
    
    def backtest_strategy(self, data):
        """Run backtest on historical data"""
        try:
            # Calculate signals
            data = self.calculate_ema_signals(data)
            if data is None:
                return None
            
            # Initialize tracking variables
            position = 0
            entry_price = 0
            entry_date = None
            shares = 0
            
            # Track equity curve
            data['equity'] = self.initial_capital
            data['returns'] = 0
            
            for i in range(1, len(data)):
                current_price = data['close'].iloc[i]
                current_date = data.index[i]
                signal = data['signal'].iloc[i]
                
                # Buy signal
                if signal == 1 and position == 0:
                    shares = int(self.capital / current_price)
                    if shares > 0:
                        entry_price = current_price
                        entry_date = current_date
                        position = 1
                        self.capital -= shares * current_price
                        
                        logger.info(f"BUY: {shares} shares at {current_price:.2f} on {current_date}")
                
                # Sell signal
                elif signal == -1 and position == 1:
                    if shares > 0:
                        self.capital += shares * current_price
                        
                        # Calculate trade performance
                        profit = (current_price - entry_price) * shares
                        profit_pct = (profit / (entry_price * shares)) * 100
                        
                        trade = {
                            'entry_date': entry_date,
                            'exit_date': current_date,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'shares': shares,
                            'profit': profit,
                            'profit_pct': profit_pct,
                            'duration': (current_date - entry_date).days
                        }
                        self.trades.append(trade)
                        
                        logger.info(f"SELL: {shares} shares at {current_price:.2f} on {current_date} | Profit: {profit:.2f} ({profit_pct:.2f}%)")
                        
                        position = 0
                        shares = 0
                
                # Update equity curve
                current_equity = self.capital
                if position == 1 and shares > 0:
                    current_equity += shares * current_price
                
                data['equity'].iloc[i] = current_equity
                data['returns'].iloc[i] = (current_equity / self.initial_capital - 1) * 100
            
            return data
            
        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
            return None
    
    def calculate_metrics(self, data):
        """Calculate performance metrics"""
        try:
            if not self.trades:
                return {}
            
            trades_df = pd.DataFrame(self.trades)
            
            # Basic metrics
            total_trades = len(self.trades)
            winning_trades = len(trades_df[trades_df['profit'] > 0])
            losing_trades = len(trades_df[trades_df['profit'] < 0])
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Profit metrics
            total_profit = trades_df['profit'].sum()
            avg_profit = trades_df['profit'].mean()
            avg_profit_pct = trades_df['profit_pct'].mean()
            
            # Risk metrics
            max_profit = trades_df['profit'].max()
            max_loss = trades_df['profit'].min()
            
            # Drawdown calculation
            equity = data['equity']
            running_max = equity.expanding().max()
            drawdown = (equity - running_max) / running_max * 100
            max_drawdown = drawdown.min()
            
            # Returns
            final_equity = data['equity'].iloc[-1]
            total_return = (final_equity / self.initial_capital - 1) * 100
            
            # Sharpe ratio (assuming risk-free rate of 6%)
            returns = data['returns'].pct_change().dropna()
            if len(returns) > 0 and returns.std() != 0:
                sharpe_ratio = (returns.mean() - 0.06/252) / returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0
            
            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_return': total_return,
                'avg_profit': avg_profit,
                'avg_profit_pct': avg_profit_pct,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'avg_trade_duration': trades_df['duration'].mean(),
                'final_equity': final_equity
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}
    
    def print_results(self, metrics):
        """Print backtest results"""
        try:
            print("\n" + "="*60)
            print("BACKTEST RESULTS - EMA CROSSOVER STRATEGY")
            print("="*60)
            print(f"Initial Capital: ₹{self.initial_capital:,.2f}")
            print(f"Final Equity: ₹{metrics.get('final_equity', 0):,.2f}")
            print(f"Total Return: {metrics.get('total_return', 0):.2f}%")
            print(f"Total Profit: ₹{metrics.get('total_profit', 0):,.2f}")
            print("-"*60)
            print(f"Total Trades: {metrics.get('total_trades', 0)}")
            print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
            print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
            print(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
            print(f"Average Profit per Trade: ₹{metrics.get('avg_profit', 0):,.2f}")
            print(f"Average Profit Percentage: {metrics.get('avg_profit_pct', 0):.2f}%")
            print(f"Max Profit: ₹{metrics.get('max_profit', 0):,.2f}")
            print(f"Max Loss: ₹{metrics.get('max_loss', 0):,.2f}")
            print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"Average Trade Duration: {metrics.get('avg_trade_duration', 0):.2f} days")
            print("="*60 + "\n")
        
        except Exception as e:
            logger.error(f"Error printing results: {e}")

# Example usage
if __name__ == "__main__":
    # Load your data here
    data_handler = DataHandler()
    historical_data = data_handler.get_historical_data('AAPL', start_date=datetime.now() - timedelta(days=365))

    backtester = EMABacktester(initial_capital=100000)
    backtested_data = backtester.backtest_strategy(historical_data)
    
    if backtested_data is not None:
        metrics = backtester.calculate_metrics(backtested_data)
        backtester.print_results(metrics)
        
        # Plot equity curve
        plt.figure(figsize=(12, 6))
        plt.plot(backtested_data.index, backtested_data['equity'], label='Equity Curve', color='blue')
        plt.title('Equity Curve of EMA Crossover Strategy')
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.legend()
        plt.grid()
        plt.show()
# backtesting.py - Backtest the EMA Strategy

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from config import Config
from auth import FyersAuth
from data_handler import DataHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EMABacktester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        
    def calculate_ema_signals(self, data):
        """Calculate EMA signals for backtesting"""
        try:
            # Calculate EMAs
            data['ema_5'] = data['close'].ewm(span=Config.EMA_SHORT, adjust=False).mean()
            data['ema_21'] = data['close'].ewm(span=Config.EMA_LONG, adjust=False).mean()
            
            # Calculate signals
            data['ema_diff'] = data['ema_5'] - data['ema_21']
            data['signal'] = 0
            data['position'] = 0
            
            # Generate buy/sell signals
            for i in range(1, len(data)):
                if (data['ema_diff'].iloc[i] > 0 and data['ema_diff'].iloc[i-1] <= 0):
                    data['signal'].iloc[i] = 1  # Buy signal
                elif (data['ema_diff'].iloc[i] < 0 and data['ema_diff'].iloc[i-1] >= 0):
                    data['signal'].iloc[i] = -1  # Sell signal
            
            # Calculate positions
            position = 0
            for i in range(len(data)):
                if data['signal'].iloc[i] == 1:
                    position = 1
                elif data['signal'].iloc[i] == -1:
                    position = 0
                data['position'].iloc[i] = position
            
            return data
            
        except Exception as e:
            logger.error(f"Error calculating EMA signals: {e}")
            return None
    
    def backtest_strategy(self, data):
        """Run backtest on historical data"""
        try:
            # Calculate signals
            data = self.calculate_ema_signals(data)
            if data is None:
                return None
            
            # Initialize tracking variables
            position = 0
            entry_price = 0
            entry_date = None
            shares = 0
            
            # Track equity curve
            data['equity'] = self.initial_capital
            data['returns'] = 0
            
            for i in range(1, len(data)):
                current_price = data['close'].iloc[i]
                current_date = data.index[i]
                signal = data['signal'].iloc[i]
                
                # Buy signal
                if signal == 1 and position == 0:
                    shares = int(self.capital / current_price)
                    if shares > 0:
                        entry_price = current_price
                        entry_date = current_date
                        position = 1
                        self.capital -= shares * current_price
                        
                        logger.info(f"BUY: {shares} shares at {current_price:.2f} on {current_date}")
                
                # Sell signal
                elif signal == -1 and position == 1:
                    if shares > 0:
                        self.capital += shares * current_price
                        
                        # Calculate trade performance
                        profit = (current_price - entry_price) * shares
                        profit_pct = (profit / (entry_price * shares)) * 100
                        
                        trade = {
                            'entry_date': entry_date,
                            'exit_date': current_date,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'shares': shares,
                            'profit': profit,
                            'profit_pct': profit_pct,
                            'duration': (current_date - entry_date).days
                        }
                        self.trades.append(trade)
                        
                        logger.info(f"SELL: {shares} shares at {current_price:.2f} on {current_date} | Profit: {profit:.2f} ({profit_pct:.2f}%)")
                        
                        position = 0
                        shares = 0
                
                # Update equity curve
                current_equity = self.capital
                if position == 1 and shares > 0:
                    current_equity += shares * current_price
                
                data['equity'].iloc[i] = current_equity
                data['returns'].iloc[i] = (current_equity / self.initial_capital - 1) * 100
            
            return data
            
        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
            return None
    
    def calculate_metrics(self, data):
        """Calculate performance metrics"""
        try:
            if not self.trades:
                return {}
            
            trades_df = pd.DataFrame(self.trades)
            
            # Basic metrics
            total_trades = len(self.trades)
            winning_trades = len(trades_df[trades_df['profit'] > 0])
            losing_trades = len(trades_df[trades_df['profit'] < 0])
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Profit metrics
            total_profit = trades_df['profit'].sum()
            avg_profit = trades_df['profit'].mean()
            avg_profit_pct = trades_df['profit_pct'].mean()
            
            # Risk metrics
            max_profit = trades_df['profit'].max()
            max_loss = trades_df['profit'].min()
            
            # Drawdown calculation
            equity = data['equity']
            running_max = equity.expanding().max()
            drawdown = (equity - running_max) / running_max * 100
            max_drawdown = drawdown.min()
            
            # Returns
            final_equity = data['equity'].iloc[-1]
            total_return = (final_equity / self.initial_capital - 1) * 100
            
            # Sharpe ratio (assuming risk-free rate of 6%)
            returns = data['returns'].pct_change().dropna()
            if len(returns) > 0 and returns.std() != 0:
                sharpe_ratio = (returns.mean() - 0.06/252) / returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0
            
            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_return': total_return,
                'avg_profit': avg_profit,
                'avg_profit_pct': avg_profit_pct,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'avg_trade_duration': trades_df['duration'].mean(),
                'final_equity': final_equity
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}
    
    def print_results(self, metrics):
        """Print backtest results"""
        try:
            print("\n" + "="*60)
            print("BACKTEST RESULTS - EMA CROSSOVER STRATEGY")
            print("="*60)
            print(f"Initial Capital: ₹{self.initial_capital:,.2f}")
            print(f"Final Equity: ₹{metrics.get('final_equity', 0):,.2f}")
            print(f"Total Return: {metrics.get('total_return', 0):.2f}%")
            print(f"Total Profit: ₹{metrics.get('total_profit', 0):,.2f}")
            print("-"*60)
            print(f"Total Trades: {metrics.get('total_trades', 0)}")
            print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
            print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
            print(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
            print(f"Average Profit per Trade: ₹{metrics.get('avg_profit', 0):,.2f}")
            print(f"Average Profit %: {metrics.get('avg_profit_pct', 0):.2f}%")
            print(f"Average Trade Duration: {metrics.get('avg_trade_duration', 0):.1f} days")
            print("-"*60)
            print(f"Best Trade: ₹{metrics.get('max_profit', 0):,.2f}")
            print(f"Worst Trade: ₹{metrics.get('max_loss', 0):,.2f}")
            print(f"Maximum Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error printing results: {e}")
    
    def plot_results(self, data, symbol):
        """Plot backtest results"""
        try:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
            
            # Plot 1: Price and EMAs with signals
            ax1.plot(data.index, data['close'], label='Close Price', linewidth=1)
            ax1.plot(data.index, data['ema_5'], label=f'EMA {Config.EMA_SHORT}', alpha=0.7)
            ax1.plot(data.index, data['ema_21'], label=f'EMA {Config.EMA_LONG}', alpha=0.7)
            
            # Mark buy/sell signals
            buy_signals = data[data['signal'] == 1]
            sell_signals = data[data['signal'] == -1]
            
            ax1.scatter(buy_signals.index, buy_signals['close'], 
                       color='green', marker='^', s=100, label='Buy Signal', alpha=0.8)
            ax1.scatter(sell_signals.index, sell_signals['close'], 
                       color='red', marker='v', s=100, label='Sell Signal', alpha=0.8)
            
            ax1.set_title(f'{symbol} - EMA Crossover Strategy')
            ax1.set_ylabel('Price (₹)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Equity curve
            ax2.plot(data.index, data['equity'], label='Portfolio Equity', color='blue', linewidth=2)
            ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.7, label='Initial Capital')
            ax2.set_title('Portfolio Equity Curve')
            ax2.set_ylabel('Equity (₹)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: Returns
            ax3.plot(data.index, data['returns'], label='Portfolio Returns', color='purple', linewidth=1)
            ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.7)
            ax3.set_title('Portfolio Returns (%)')
            ax3.set_ylabel('Returns (%)')
            ax3.set_xlabel('Date')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting results: {e}")
    
    def export_trades(self, filename='trades_export.csv'):
        """Export trades to CSV"""
        try:
            if self.trades:
                trades_df = pd.DataFrame(self.trades)
                trades_df.to_csv(filename, index=False)
                logger.info(f"Trades exported to {filename}")
            else:
                logger.warning("No trades to export")
                
        except Exception as e:
            logger.error(f"Error exporting trades: {e}")
    
    def reset(self):
        """Reset backtester for new run"""
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []

def run_backtest(symbol, start_date, end_date, initial_capital=100000):
    """Main function to run backtest"""
    try:
        # Initialize components
        auth = FyersAuth()
        data_handler = DataHandler(auth.get_access_token())
        backtester = EMABacktester(initial_capital=initial_capital)
        
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Fetch historical data
        data = data_handler.fetch_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe='1D'
        )
        
        if data is None or len(data) < Config.EMA_LONG + 10:
            logger.error("Insufficient data for backtesting")
            return None
        
        # Run backtest
        result_data = backtester.backtest_strategy(data)
        if result_data is None:
            logger.error("Backtest failed")
            return None
        
        # Calculate metrics
        metrics = backtester.calculate_metrics(result_data)
        
        # Print results
        backtester.print_results(metrics)
        
        # Plot results
        backtester.plot_results(result_data, symbol)
        
        # Export trades
        backtester.export_trades(f'{symbol}_trades_{start_date}_{end_date}.csv')
        
        return {
            'data': result_data,
            'metrics': metrics,
            'trades': backtester.trades,
            'backtester': backtester
        }
        
    except Exception as e:
        logger.error(f"Error in backtest execution: {e}")
        return None

def compare_strategies(symbols, start_date, end_date, initial_capital=100000):
    """Compare strategy performance across multiple symbols"""
    try:
        results = {}
        
        for symbol in symbols:
            logger.info(f"Running backtest for {symbol}")
            result = run_backtest(symbol, start_date, end_date, initial_capital)
            if result:
                results[symbol] = result['metrics']
        
        # Create comparison DataFrame
        if results:
            comparison_df = pd.DataFrame(results).T
            print("\nSTRATEGY COMPARISON ACROSS SYMBOLS")
            print("="*80)
            print(comparison_df.round(2))
            
            # Save comparison
            comparison_df.to_csv(f'strategy_comparison_{start_date}_{end_date}.csv')
            logger.info("Strategy comparison saved")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in strategy comparison: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    try:
        # Single symbol backtest
        symbol = "NSE:RELIANCE-EQ"
        start_date = "2023-01-01"
        end_date = "2024-01-01"
        
        result = run_backtest(symbol, start_date, end_date, initial_capital=100000)
        
        # Multiple symbol comparison
        symbols = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ"]
        comparison_results = compare_strategies(symbols, start_date, end_date)
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
