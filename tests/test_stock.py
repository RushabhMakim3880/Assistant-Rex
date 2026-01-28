import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from stock_agent import StockAgent

async def test_stock_analysis():
    print("Initializing Stock Agent...")
    agent = StockAgent()
    
    symbol = "INFY" # Infosys (NSE Default)
    print(f"\nTesting analysis for: {symbol}")
    
    result = agent.analyze_stock(symbol)
    
    if "error" in result:
        print(f"FAILED: {result['error']}")
    else:
        print(f"SUCCESS: Analyzed {result['name']} ({result['currency']})")
        print(f"Current Price: {result['current_price']}")
        print(f"History Points: {len(result['history'])}")
        print(f"Prediction: {result['prediction']['direction']} ({result['prediction']['confidence']}%)")
        print(f"Target: {result['prediction']['target_low']} - {result['prediction']['target_high']}")
        print(f"Summary: {result['summary']}")
        
    print("\n------------------------------------------------\n")

    symbol_us = "AAPL" # Apple
    print(f"Testing analysis for: {symbol_us}")
    result_us = agent.analyze_stock(symbol_us) # Should fail or need resolving if not .NS? The agent defaults to .NS if no suffix found.
    # Actually my logic was: if not .NS or .BO, append .NS. So AAPL -> AAPL.NS which might fail or be invalid.
    # Let's see what happens. Ideally we want it to support US stocks too if user asks, but requirement said "Initially... limited to NSE and BSE".
    # So if AAPL fails, that is EXPECTED behavior for now!
    
    if "error" in result_us:
        print(f"EXPECTED LIMITATION or ERROR: {result_us['error']}")
    else:
        # If it somehow works (e.g. AAPL.NS exists?)
        print(f"Result: {result_us['name']}")

if __name__ == "__main__":
    asyncio.run(test_stock_analysis())
