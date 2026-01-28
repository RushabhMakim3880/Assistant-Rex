import asyncio
import sys
import os

# Add the current directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.stock_agent import StockAgent

async def test_prediction_output():
    agent = StockAgent()
    print("Testing Stock Analysis with Prediction Engine...")
    
    # Test with a common stock
    symbol = "RELIANCE"
    print(f"Analyzing {symbol}...")
    
    data = await agent.analyze_stock(symbol)
    
    if "error" in data:
        print(f"FAILED: {data['error']}")
        return

    print("\n[SUCCESS] Basic Analysis Data Fetched.")
    print(f"Current Price: {data['current_price']}")
    
    # Verify Short-Term Predictions
    if "short_term_predictions" in data:
        print("\n[SUCCESS] Short-Term Predictions Table:")
        print(f"{'Period':<15} | {'Dir':<10} | {'Predicted':<10} | {'Range':<20} | {'Conf'}")
        print("-" * 75)
        for p in data["short_term_predictions"]:
            price_range = f"{p['range_min']} - {p['range_max']}"
            print(f"{p['period']:<15} | {p['icon']} {p['direction']:<8} | {p['predicted']:<10} | {price_range:<20} | {p['confidence']}%")
    else:
        print("\n[FAILED] short_term_predictions missing from output!")

    # Verify Decision Assist
    if "decision_assist" in data:
        da = data["decision_assist"]
        print("\n[SUCCESS] Decision Assist:")
        print(f"Recommendation: {da['recommendation']}")
        print(f"Confidence: {da['confidence']}%")
        print(f"Justification: {da['justification']}")
    else:
        print("\n[FAILED] decision_assist missing from output!")

    # Verify AI Recommendation enriched
    if "recommendation" in data:
        rec = data["recommendation"]
        print("\n[SUCCESS] AI Synthesis:")
        print(f"Signal: {rec.get('signal')}")
        print(f"Reasoning: {rec.get('reasoning')}")
        print(f"Risk: {rec.get('risk_factor')}")
    else:
        print("\n[FAILED] recommendation (AI) missing from output!")

if __name__ == "__main__":
    asyncio.run(test_prediction_output())
