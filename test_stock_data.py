import yfinance as yf
import json
from datetime import datetime

def test_stock(ticker):
    print(f"Testing {ticker}...")
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5y")
    
    if hist.empty:
        print("Error: DataFrame is empty")
        return

    print(f"Rows found: {len(hist)}")
    
    history_data = []
    for index, row in hist.iterrows():
        history_data.append({
            "date": index.strftime('%Y-%m-%d'),
            "open": round(row['Open'], 2),
            "high": round(row['High'], 2),
            "low": round(row['Low'], 2),
            "close": round(row['Close'], 2),
            "volume": int(row['Volume'])
        })
    
    print(f"First 5 entries: {json.dumps(history_data[:5], indent=2)}")
    print(f"Last 5 entries: {json.dumps(history_data[-5:], indent=2)}")
    
    # Check for NaNs or Zeros
    nan_count = hist['Close'].isna().sum()
    zero_val_count = (hist['Close'] == 0).sum()
    zero_vol_count = (hist['Volume'] == 0).sum()
    min_close = hist['Close'].min()
    max_close = hist['Close'].max()
    
    print(f"NaN Close values: {nan_count}")
    print(f"Zero Close values: {zero_val_count}")
    print(f"Zero Volume values: {zero_vol_count}")
    print(f"Min Close: {min_close}")
    print(f"Max Close: {max_close}")

if __name__ == "__main__":
    test_stock("RELINFRA.NS")
