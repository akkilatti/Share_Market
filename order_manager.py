# order_manager.py - Order Management System

import logging
from datetime import datetime
import pandas as pd
from config import Config

logger = logging.getLogger(__name__)

class OrderManager:
    def __init__(self, fyers_client):
        self.fyers = fyers_client
        self.symbol = Config.SYMBOL
        self.quantity = Config.QUANTITY
        self.positions = {}
        self.orders = {}
    
    def place_buy_order(self, price, order_type="MARKET"):
        """Place a buy order"""
        try:
            data = {
                "symbol": self.symbol,
                "qty": self.quantity,
                "type": 2,  # Buy
                "side": 1,  # Long
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False"
            }
            
            if order_type == "LIMIT":
                data["productType"] = "MARGIN"
                data["limitPrice"] = price
                data["type"] = 1  # Limit order
            
            response = self.fyers.place_order(data)
            
            if response['code'] == 200:
                order_id = response['id']
                logger.info(f"Buy order placed successfully. Order ID: {order_id}")
                
                # Store order details
                self.orders[order_id] = {
                    'symbol': self.symbol,
                    'side': 'BUY',
                    'quantity': self.quantity,
                    'price': price,
                    'type': order_type,
                    'timestamp': datetime.now(),
                    'status': 'PLACED'
                }
                
                return order_id
            else:
                logger.error(f"Failed to place buy order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            return None
    
    def place_sell_order(self, price, order_type="MARKET"):
        """Place a sell order"""
        try:
            data = {
                "symbol": self.symbol,
                "qty": self.quantity,
                "type": 2,  # Sell
                "side": -1,  # Short
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False"
            }
            
            if order_type == "LIMIT":
                data["productType"] = "MARGIN"
                data["limitPrice"] = price
                data["type"] = 1  # Limit order
            
            response = self.fyers.place_order(data)
            
            if response['code'] == 200:
                order_id = response['id']
                logger.info(f"Sell order placed successfully. Order ID: {order_id}")
                
                # Store order details
                self.orders[order_id] = {
                    'symbol': self.symbol,
                    'side': 'SELL',
                    'quantity': self.quantity,
                    'price': price,
                    'type': order_type,
                    'timestamp': datetime.now(),
                    'status': 'PLACED'
                }
                
                return order_id
            else:
                logger.error(f"Failed to place sell order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
            return None
    
    def place_stop_loss_order(self, trigger_price, side="SELL"):
        """Place a stop loss order"""
        try:
            data = {
                "symbol": self.symbol,
                "qty": self.quantity,
                "type": 3,  # Stop loss order
                "side": -1 if side == "SELL" else 1,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": trigger_price,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False"
            }
            
            response = self.fyers.place_order(data)
            
            if response['code'] == 200:
                order_id = response['id']
                logger.info(f"Stop loss order placed. Order ID: {order_id}, Trigger: {trigger_price}")
                
                self.orders[order_id] = {
                    'symbol': self.symbol,
                    'side': f'SL_{side}',
                    'quantity': self.quantity,
                    'trigger_price': trigger_price,
                    'type': 'STOP_LOSS',
                    'timestamp': datetime.now(),
                    'status': 'PLACED'
                }
                
                return order_id
            else:
                logger.error(f"Failed to place stop loss order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing stop loss order: {e}")
            return None
    
    def place_target_order(self, target_price, side="SELL"):
        """Place a target profit order"""
        try:
            data = {
                "symbol": self.symbol,
                "qty": self.quantity,
                "type": 1,  # Limit order
                "side": -1 if side == "SELL" else 1,
                "productType": "INTRADAY",
                "limitPrice": target_price,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False"
            }
            
            response = self.fyers.place_order(data)
            
            if response['code'] == 200:
                order_id = response['id']
                logger.info(f"Target order placed. Order ID: {order_id}, Target: {target_price}")
                
                self.orders[order_id] = {
                    'symbol': self.symbol,
                    'side': f'TARGET_{side}',
                    'quantity': self.quantity,
                    'target_price': target_price,
                    'type': 'TARGET',
                    'timestamp': datetime.now(),
                    'status': 'PLACED'
                }
                
                return order_id
            else:
                logger.error(f"Failed to place target order: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing target order: {e}")
            return None
    
    def cancel_order(self, order_id):
        """Cancel an order"""
        try:
            data = {"id": order_id}
            response = self.fyers.cancel_order(data)
            
            if response['code'] == 200:
                logger.info(f"Order {order_id} cancelled successfully")
                if order_id in self.orders:
                    self.orders[order_id]['status'] = 'CANCELLED'
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id):
        """Get order status"""
        try:
            response = self.fyers.orderbook()
            
            if response['code'] == 200:
                orders = response['orderBook']
                for order in orders:
                    if order['id'] == order_id:
                        status = order['status']
                        if order_id in self.orders:
                            self.orders[order_id]['status'] = status
                        return status
                return None
            else:
                logger.error(f"Failed to get order status: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    def get_positions(self):
        """Get current positions"""
        try:
            response = self.fyers.positions()
            
            if response['code'] == 200:
                positions = response['netPositions']
                self.positions = {}
                
                for pos in positions:
                    symbol = pos['symbol']
                    quantity = pos['qty']
                    if quantity != 0:  # Only non-zero positions
                        self.positions[symbol] = {
                            'quantity': quantity,
                            'avg_price': pos['avgPrice'],
                            'current_price': pos['ltp'],
                            'pnl': pos['pl'],
                            'side': 'LONG' if quantity > 0 else 'SHORT'
                        }
                
                return self.positions
            else:
                logger.error(f"Failed to get positions: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return None
    
    def calculate_stop_loss_price(self, entry_price, side="LONG"):
        """Calculate stop loss price based on percentage"""
        try:
            if side == "LONG":
                sl_price = entry_price * (1 - Config.STOP_LOSS_PERCENT / 100)
            else:
                sl_price = entry_price * (1 + Config.STOP_LOSS_PERCENT / 100)
            
            return round(sl_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return None
    
    def calculate_target_price(self, entry_price, side="LONG"):
        """Calculate target price based on percentage"""
        try:
            if side == "LONG":
                target_price = entry_price * (1 + Config.TARGET_PERCENT / 100)
            else:
                target_price = entry_price * (1 - Config.TARGET_PERCENT / 100)
            
            return round(target_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculating target: {e}")
            return None
    
    def execute_ema_strategy(self, signal, current_price):
        """Execute EMA crossover strategy"""
        try:
            # Get current positions
            positions = self.get_positions()
            current_position = positions.get(self.symbol, {})
            
            if signal == 1:  # Buy signal
                if not current_position or current_position.get('quantity', 0) <= 0:
                    logger.info(f"Executing BUY signal at price: {current_price}")
                    
                    # Place buy order
                    buy_order_id = self.place_buy_order(current_price)
                    
                    if buy_order_id:
                        # Calculate stop loss and target
                        sl_price = self.calculate_stop_loss_price(current_price, "LONG")
                        target_price = self.calculate_target_price(current_price, "LONG")
                        
                        # Place stop loss and target orders
                        if sl_price:
                            self.place_stop_loss_order(sl_price, "SELL")
                        
                        if target_price:
                            self.place_target_order(target_price, "SELL")
                        
                        return buy_order_id
                else:
                    logger.info("Already in LONG position, skipping BUY signal")
            
            elif signal == -1:  # Sell signal
                if current_position and current_position.get('quantity', 0) > 0:
                    logger.info(f"Executing SELL signal at price: {current_price}")
                    
                    # Place sell order to close long position
                    sell_order_id = self.place_sell_order(current_price)
                    return sell_order_id
                else:
                    logger.info("No LONG position to close, skipping SELL signal")
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing EMA strategy: {e}")
            return None
    
    def get_order_history(self):
        """Get order history"""
        try:
            response = self.fyers.orderbook()
            
            if response['code'] == 200:
                return response['orderBook']
            else:
                logger.error(f"Failed to get order history: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return None
    
    def print_summary(self):
        """Print trading summary"""
        try:
            print("\n" + "="*50)
            print("TRADING SUMMARY")
            print("="*50)
            
            # Print positions
            positions = self.get_positions()
            if positions:
                print("\nCURRENT POSITIONS:")
                for symbol, pos in positions.items():
                    print(f"{symbol}: {pos['quantity']} @ {pos['avg_price']} | P&L: {pos['pnl']}")
            else:
                print("\nNo open positions")
            
            # Print recent orders
            print(f"\nRECENT ORDERS ({len(self.orders)}):")
            for order_id, order in self.orders.items():
                print(f"{order_id}: {order['side']} {order['quantity']} @ {order.get('price', 'Market')} - {order['status']}")
            
            print("="*50)
            
        except Exception as e:
            logger.error(f"Error printing summary: {e}")

if __name__ == "__main__":
    # Example usage
    from auth import FyersAuth
    
    # Authenticate
    auth = FyersAuth()
    if auth.load_token():
        # Initialize order manager
        order_manager = OrderManager(auth.fyers)
        
        # Get current positions
        positions = order_manager.get_positions()
        print("Current positions:", positions)
        
        # Print summary
        order_manager.print_summary()
    else:
        print("Authentication failed!")