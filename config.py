# config.py - Configuration file for FYERS API

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # FYERS API Credentials
    CLIENT_ID = os.getenv('FYERS_CLIENT_ID', 'YOUR_CLIENT_ID')
    SECRET_KEY = os.getenv('FYERS_SECRET_KEY', 'YOUR_SECRET_KEY')
    REDIRECT_URI = os.getenv('FYERS_REDIRECT_URI', 'https://127.0.0.1:5000/auth')
    TOTP_KEY = os.getenv('FYERS_TOTP_KEY', 'YOUR_TOTP_KEY')  # For 2FA
    
    # Trading Parameters
    SYMBOL = 'NSE:RELIANCE-EQ'  # Stock symbol to trade
    QUANTITY = 1  # Number of shares to trade
    
    # EMA Parameters
    EMA_SHORT = 5   # Short EMA period
    EMA_LONG = 21   # Long EMA period
    
    # Risk Management
    STOP_LOSS_PERCENT = 10.0  # Stop loss percentage
    TARGET_PERCENT = 10.0     # Target profit percentage
    
    # Trading Settings
    TIMEFRAME = '30'  # 30-minute candles
    MAX_POSITIONS = 1  # Maximum open positions
    TRADING_START_TIME = '09:15'
    TRADING_END_TIME = '15:30'
    
    # Data Settings
    HISTORICAL_DAYS = 100  # Days of historical data to fetch

# Create .env file template
ENV_TEMPLATE = """
# FYERS API Credentials
FYERS_CLIENT_ID=your_client_id_here
FYERS_SECRET_KEY=your_secret_key_here
FYERS_REDIRECT_URI=https://127.0.0.1:5000/auth
FYERS_TOTP_KEY=your_totp_key_here

# Optional: Set log level
LOG_LEVEL=INFO
"""

def create_env_template():
    """Create a template .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(ENV_TEMPLATE)
        print("Created .env template file. Please fill in your credentials.")

if __name__ == "__main__":
    create_env_template()