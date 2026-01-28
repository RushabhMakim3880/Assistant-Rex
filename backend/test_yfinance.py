import yfinance as yf
import json

def test_market_data():
    tickers = ["GC=F", "SI=F", "^NSEI"]
    data = {}
    
    print("Fetching Commodities...")
    for t in tickers:
        ticker = yf.Ticker(t)
        hist = ticker.history(period="1d")
        if not hist.empty:
            data[t] = {
                "price": hist['Close'].iloc[-1],
                "prev_close": hist['Open'].iloc[-1], # Approx
                "change": hist['Close'].iloc[-1] - hist['Open'].iloc[-1]
            }
            
    print("Commodities Data:", json.dumps(data, indent=2))

    print("\nFetching News...")
    # Try getting news from a major index
    nifty = yf.Ticker("^NSEI")
    news = nifty.news
    print("News Data Sample:", json.dumps(news[:2] if news else [], indent=2))

if __name__ == "__main__":
    test_market_data()
