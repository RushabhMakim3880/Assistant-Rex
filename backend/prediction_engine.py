import pandas as pd
import numpy as np

class PredictionEngine:
    """
    Modular engine for short-term price target and directional prediction.
    Uses technical momentum, volatility-scaled ranges, and trend alignment.
    """
    
    @staticmethod
    def calculate_atr(df, period=14):
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(window=period).mean()

    @staticmethod
    def predict(df, current_price, horizons=[1, 3, 5, 7]):
        """
        Generates numeric predictions and ranges for specified day horizons.
        """
        if df.empty or len(df) < 50:
            return []

        # Technical Inputs
        close = df['Close']
        returns = close.pct_change().dropna()
        volatility = returns.std() # Daily volatility
        
        # ATR for price-based volatility
        df = df.copy()
        df['ATR'] = PredictionEngine.calculate_atr(df)
        current_atr = df['ATR'].iloc[-1] if not np.isnan(df['ATR'].iloc[-1]) else (current_price * 0.02)
        
        # Momentum Indicators
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()
        rsi_14 = df['RSI'].iloc[-1] if 'RSI' in df.columns else 50
        
        # Trend Strength (Slope of last 10 days)
        recent_slope = (close.iloc[-1] - close.iloc[-10]) / 10 if len(close) >= 10 else 0
        
        predictions = []
        
        for h in horizons:
            # 1. Directional Logic
            # Weighted factors: Trend (40%), Momentum (30%), Volatility Shift (30%)
            momentum_score = (50 - rsi_14) / 50 if rsi_14 > 70 or rsi_14 < 30 else (rsi_14 - 50) / 50
            trend_score = 1 if current_price > sma_20.iloc[-1] else -1
            
            # Aggregate probability (simplified)
            prob_up = 0.5 + (0.1 * trend_score) + (0.1 * momentum_score)
            direction = "Increase" if prob_up > 0.5 else "Decrease"
            icon = "↑" if direction == "Increase" else "↓"
            
            # 2. Price Target (Point Estimate)
            # Drift calculation based on slope and volatility scaling
            drift = recent_slope * h * 0.5
            expected_price = current_price + drift
            
            # 3. Expected Range (Volatility Band)
            # Scaling ATR by sqrt(time) for multi-day horizons
            range_width = current_atr * np.sqrt(h) * 1.5
            target_high = expected_price + (range_width / 2)
            target_low = expected_price - (range_width / 2)
            
            # 4. Confidence Scoring
            # Lower confidence for longer horizons and high volatility
            base_confidence = 65 - (h * 2)
            vol_penalty = 10 if volatility > 0.03 else 0
            confidence = max(45, min(85, int(base_confidence - vol_penalty)))

            predictions.append({
                "period": f"{h} Day{'s' if h > 1 else ''}",
                "direction": direction,
                "icon": icon,
                "current": round(current_price, 2),
                "predicted": round(expected_price, 2),
                "range_min": round(target_low, 2),
                "range_max": round(target_high, 2),
                "confidence": confidence,
                "sma50": round(float(sma_50.iloc[-1]), 2) if not np.isnan(sma_50.iloc[-1]) else 0,
                "sma200": round(float(sma_200.iloc[-1]), 2) if not np.isnan(sma_200.iloc[-1]) else 0,
                "rsi": round(float(rsi_14), 2)
            })
            
        return predictions

    @staticmethod
    def get_decision(predictions, rsi, trend):
        """
        Determines the Buy/Sell/Wait recommendation based on prediction aggregate.
        """
        if not predictions:
            return "WAIT", "Insufficient data for decision.", 50

        # Consensus score
        upside_count = sum(1 for p in predictions if p['direction'] == "Increase")
        avg_confidence = sum(p['confidence'] for p in predictions) / len(predictions)
        
        if upside_count >= 3 and rsi < 70 and trend == "Bullish":
            signal = "BUY"
            reason = f"Aggressive Bullish Outlook: {upside_count}/4 horizons predict growth. RSI at {round(rsi, 1)} suggests room before overbought territory. Trend is Bullish (Price > SMAs)."
        elif upside_count <= 1 and rsi > 30 and trend == "Bearish":
            signal = "SELL"
            reason = f"Defensive Bearish Stance: Only {upside_count}/4 horizons show upside. RSI at {round(rsi, 1)} and Bearish trend (Price < SMAs) indicate sustained downward pressure."
        else:
            signal = "WAIT"
            if rsi > 70:
                reason = f"Caution: Short-term targets are UP, but RSI is overbought ({round(rsi, 1)}). Recommend waiting for a pullback."
            elif rsi < 30:
                reason = f"Caution: Trend is Bearish, but RSI is oversold ({round(rsi, 1)}). Expect a potential relief bounce before further decline."
            else:
                reason = f"Neutral: Mixed signals with {upside_count}/4 upside predictions. EMA/SMA alignment is {trend}. No clear breakout confirmed."

        return signal, reason, int(avg_confidence)

        return signal, reason, int(avg_confidence)
