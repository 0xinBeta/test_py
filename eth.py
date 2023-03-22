import ccxt
from pa_strat_df import pa_strat_df_maker
import DontShare as ds
import sys
from datetime import datetime
import time
import balance_tracker as bt
import json
import os
import requests

# Initialize bot run counter
bot_run = 0

# Main loop for restarting the bot after 24-hour pause
while True:
    try:
        # Set up exchange connections for user and public APIs
        exchange_usr = ccxt.binanceusdm({
            'enableRateLimit': True,
            'apiKey': ds.apiKey,
            'secret': ds.secret,
        })

        # Define trading parameters
        symbol = "ET2USDT"
        timeframe = "3m"
        limit = 1000
        leverage = 50

        # Set leverage for the symbol
        exchange_usr.set_leverage(leverage=leverage, symbol=symbol)

        # Get starting wallet balance
        start_wallet_balance = exchange_usr.fetch_balance()[
            'USDT']['total']

        exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
        })


        # Function to save trade data to a JSON file
        def save_trade_data(symbol, open_time, close_time, PnL):
            trade_data = {
                'symbol': symbol,
                'open_time': open_time,
                'close_time': close_time,
                'PnL': PnL
            }

            # Check if the JSON file exists; if not, create an empty list to store trade data
            json_file = 'trade_data.json'
            if not os.path.exists(json_file):
                with open(json_file, 'w') as f:
                    json.dump([], f)

            # Read the existing trade data from the JSON file
            with open(json_file, 'r') as f:
                all_trade_data = json.load(f)

            # Append the new trade data to the list
            all_trade_data.append(trade_data)

            # Save the updated list to the JSON file
            with open(json_file, 'w') as f:
                json.dump(all_trade_data, f)

        # Helper function to calculate order size
        def order_size():
            usdt_balance = exchange_usr.fetch_balance()['USDT']['total']
            df = pa_strat_df_maker(exchange, symbol, timeframe, 1000)
            price_now = df['Close'].iloc[-1]
            order_size = usdt_balance * 0.01 / price_now * leverage
            return max(round(order_size, 2), 0.001)

        # Helper function to get position data
        def get_pos_data(symbol):
            position = exchange_usr.fetch_positions(symbols=[symbol])
            pos_size = position[0]["contracts"]

            return pos_size

        # Helper function to get the current time
        def get_time():
            now = datetime.now()
            date_string = now.strftime("%Y-%m-%d %H:%M:%S")
            return date_string

        # Print start time
        date_time = get_time()
        print(f'>>>>Starting the bot at {date_time}<<<<')

        # Inner loop for trading logic
        while True:

            # Print restart time if the bot has been restarted
            if bot_run > 0:
                date_time = get_time()
                print(f'Restart the bot at {date_time}')

            # Increment bot run counter
            bot_run += 1

            # Get current wallet balance and print balances
            current_wallet_balance = exchange_usr.fetch_balance()[
                'USDT']['total']
            print(
                f'The current wallet balance: {current_wallet_balance}\nThe start wallet balance: {start_wallet_balance}\n=========================')
            
            # Check if the bot should be restarted due to a balance change of 1% or more
            should_restart, balance_change = bt.should_restart_bot(
                current_wallet_balance)

            if should_restart:
                print(
                    f"{'Earned' if balance_change >= 0 else 'Lost'} 1% or more during the day. Pausing the bot for 24 hours.")
                time.sleep(24 * 60 * 60)
                continue

            # Exit if the current wallet balance is less than or equal to 90% of the starting wallet balance
            if current_wallet_balance <= (start_wallet_balance * 0.9):
                sys.exit()
            else:
                is_position_open = False

            # Loop for opening a position
            while is_position_open == False:

                df = pa_strat_df_maker(exchange, symbol, timeframe, limit)
                long_sig = df['long'].iloc[-2]
                short_sig = df['short'].iloc[-2]

                # Open a long position
                if long_sig == True:
                    price = df['Close'].iloc[-1]
                    ema_200 = df['EMA200'].iloc[-1]
                    sl = round(price - (df['ATR'].iloc[-1] * 10), 2)
                    sl_2 = round(((ema_200 - sl) / 2) + sl, 2)
                    create_order_size = order_size()
                    exchange_usr.create_market_buy_order(
                        symbol=symbol,
                        amount=create_order_size
                    )
                    is_position_open = True
                    open_time = get_time()
                    print(f'We opened a long order at {open_time}')

                # Open a short position
                elif short_sig == True:
                    price = df['Close'].iloc[-1]
                    ema_200 = df['EMA200'].iloc[-1]
                    sl = round(price + (df['ATR'].iloc[-1] * 10), 2)
                    sl_2 = round(((sl - ema_200) / 2) + ema_200, 2)
                    create_order_size = order_size()
                    exchange_usr.create_market_sell_order(
                        symbol=symbol,
                        amount=create_order_size
                    )
                    is_position_open = True
                    open_time = get_time()
                    print(f'We opened a short order at {open_time}')

                time.sleep(1)

            # Loop for closing a position
            while is_position_open == True:
                time.sleep(1)
                position = exchange_usr.fetch_positions(symbols=[symbol])
                entry_price = position[0]["entryPrice"]
                initial_price = entry_price
                pos_side = position[0]["side"]

                # Close a long position
                if pos_side == 'long':
                    pos_is_closed = False

                    tp = round(((entry_price - sl) / 5) + entry_price, 2)
                    pos_amount = get_pos_data(symbol=symbol)
                    date_time = get_time()
                    print(
                        f'We have a {pos_side} position at {date_time} | tp:{tp} | sl:{sl}\n=========================')
                    while pos_is_closed == False:
                        df = pa_strat_df_maker(
                            exchange, symbol, timeframe, 1000)
                        price_now = df['Close'].iloc[-1]
                        PnL = round(((price_now - initial_price) /
                                     entry_price) * 100 * leverage, 2)

                        if price_now >= tp or price_now <= sl or price_now <= sl_2 or PnL < -200:
                            pos_amount = get_pos_data(symbol=symbol)
                            exchange_usr.create_market_sell_order(
                                symbol=symbol, amount=pos_amount, params={"reduceOnly": True})
                            pos_is_closed = True
                            is_position_open = False
                            close_time = get_time()
                            save_trade_data(symbol, open_time, close_time, PnL)
                            print(
                                f'Closed {pos_side} position with {PnL}% at {close_time}')

                        time.sleep(1)

                # Close a short position
                elif pos_side == 'short':
                    pos_is_closed = False

                    tp = round(entry_price - ((sl - entry_price) / 5), 2)
                    pos_amount = get_pos_data(symbol=symbol)
                    date_time = get_time()
                    print(
                        f'We have a {pos_side} position at {date_time} | tp:{tp} | sl:{sl}\n=========================')
                    while pos_is_closed == False:
                        df = pa_strat_df_maker(
                            exchange, symbol, timeframe, 1000)
                        price_now = df['Close'].iloc[-1]
                        PnL = round(((initial_price - price_now) /
                                     entry_price) * 100 * leverage, 2)
                        
                        if price_now <= tp or price_now >= sl or price_now >= sl_2 or PnL < -200:
                            pos_amount = get_pos_data(symbol=symbol)
                            exchange_usr.create_market_buy_order(
                                symbol=symbol, amount=pos_amount, params={"reduceOnly": True})
                            pos_is_closed = True
                            is_position_open = False
                            close_time = get_time()
                            save_trade_data(symbol, open_time, close_time, PnL)
                            print(
                                f'Closed {pos_side} position with {PnL}% at {close_time}')

                        time.sleep(1)

                else:
                    date_time = get_time()
                    print(f"ERORR!!!!!! {date_time}")
                    sys.exit()

                time.sleep(180)

    except ccxt.RequestTimeout as e:
        print(type(e).__name__, str(e))
        time.sleep(60)
    except ccxt.DDoSProtection as e:
        # recoverable error, you might want to sleep a bit here and retry later
        print(type(e).__name__, str(e))
        time.sleep(300)
    except ccxt.ExchangeNotAvailable as e:
        # recoverable error, do nothing and retry later
        print(type(e).__name__, str(e))
        time.sleep(60)
    except ccxt.NetworkError as e:
        # do nothing and retry later...
        print(type(e).__name__, str(e))
        time.sleep(60)
    except Exception as e:
        # panic and halt the execution in case of any other error
        print(type(e).__name__, str(e))
        sys.exit()
