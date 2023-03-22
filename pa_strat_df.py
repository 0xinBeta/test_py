import pandas as pd
from finta import TA

def pa_strat_df_maker(exchange, symbol, timeframe, limit):
    
    # Load historical data
    candles = exchange.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(candles, columns=[
        'DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'])

    df.DateTime = pd.to_datetime(df.DateTime, unit='ms')

    df['EMA20'] = TA.EMA(df, 21, 'close')
    df['EMA50'] = TA.EMA(df, 50, 'close')
    df['EMA100'] = TA.EMA(df, 100, 'close')
    df['EMA200'] = TA.EMA(df, 200, 'close')


    df['bullish_engulfing'] = ((df['Close'] > df['Open'].shift(1)) & (df['Close'].shift(1) < df['Open'].shift(1))) & (df['Close'] > df['EMA20'])
    df['bearish_engulfing'] = ((df['Close'] < df['Open'].shift(1)) & (df['Close'].shift(1) > df['Open'].shift(1))) & (df['Close'] < df['EMA20'])


    # Compute the ATR values for the given period
    df['ATR'] = TA.ATR(df, 14)
    df['ADX'] = TA.ADX(df, 14)



    # Enter long and short positions
    df['long'] = (df['EMA20'] > df['EMA50']) & (df['EMA50'] > df['EMA100']) & (df['EMA100'] > df['EMA200']) & (df['bullish_engulfing'] == True) #& (df['ADX'] > 25)
    df['short'] = (df['EMA20'] < df['EMA50']) & (df['EMA50'] < df['EMA100']) & (df['EMA100'] < df['EMA200']) & (df['bearish_engulfing'] == True) #& (df['ADX'] > 25)


    return df


