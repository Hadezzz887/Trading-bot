"""
📊 INDIKATOR TEKNIKAL
RSI, Moving Average (EMA/SMA), MACD, Bollinger Bands, Volume
"""

import pandas as pd
import numpy as np
from config import CONFIG


class TechnicalAnalysis:
    def __init__(self):
        self.cfg = CONFIG

    # ──────────────────────────────────────────────────
    #  KONVERSI DATA
    # ──────────────────────────────────────────────────
    def ohlcv_to_df(self, ohlcv: list) -> pd.DataFrame:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df.astype(float)

    # ──────────────────────────────────────────────────
    #  RSI
    # ──────────────────────────────────────────────────
    def calc_rsi(self, close: pd.Series, period: int = None) -> pd.Series:
        if period is None:
            period = self.cfg["RSI_PERIOD"]
        delta  = close.diff()
        gain   = delta.clip(lower=0)
        loss   = -delta.clip(upper=0)
        avg_g  = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_l  = loss.ewm(com=period - 1, min_periods=period).mean()
        rs     = avg_g / avg_l.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    # ──────────────────────────────────────────────────
    #  MOVING AVERAGES
    # ──────────────────────────────────────────────────
    def calc_ema(self, close: pd.Series, period: int) -> pd.Series:
        return close.ewm(span=period, adjust=False).mean()

    def calc_sma(self, close: pd.Series, period: int) -> pd.Series:
        return close.rolling(window=period).mean()

    def calc_ma(self, close: pd.Series, period: int) -> pd.Series:
        """EMA atau SMA berdasarkan config"""
        return self.calc_ema(close, period) if self.cfg["USE_EMA"] else self.calc_sma(close, period)

    # ──────────────────────────────────────────────────
    #  MACD
    # ──────────────────────────────────────────────────
    def calc_macd(self, close: pd.Series) -> dict:
        fast   = self.calc_ema(close, self.cfg["MACD_FAST"])
        slow   = self.calc_ema(close, self.cfg["MACD_SLOW"])
        macd   = fast - slow
        signal = self.calc_ema(macd, self.cfg["MACD_SIGNAL"])
        hist   = macd - signal
        return {"macd": macd, "signal": signal, "histogram": hist}

    # ──────────────────────────────────────────────────
    #  BOLLINGER BANDS
    # ──────────────────────────────────────────────────
    def calc_bb(self, close: pd.Series) -> dict:
        period = self.cfg["BB_PERIOD"]
        std    = self.cfg["BB_STD"]
        mid    = close.rolling(window=period).mean()
        band   = close.rolling(window=period).std()
        upper  = mid + std * band
        lower  = mid - std * band
        pct_b  = (close - lower) / (upper - lower + 1e-10)
        return {"upper": upper, "mid": mid, "lower": lower, "pct_b": pct_b}

    # ──────────────────────────────────────────────────
    #  VOLUME ANALYSIS
    # ──────────────────────────────────────────────────
    def analyze_volume(self, volume: pd.Series) -> str:
        """Deteksi volume spike"""
        avg_vol  = volume.rolling(20).mean().iloc[-1]
        cur_vol  = volume.iloc[-1]
        if avg_vol > 0 and cur_vol >= avg_vol * self.cfg["VOLUME_SPIKE_MULT"]:
            return "HIGH"
        elif avg_vol > 0 and cur_vol <= avg_vol * 0.5:
            return "LOW"
        return "NORMAL"

    # ──────────────────────────────────────────────────
    #  MOMENTUM
    # ──────────────────────────────────────────────────
    def analyze_momentum(self, close: pd.Series) -> str:
        """Cek momentum dari pergerakan harga"""
        roc_5  = (close.iloc[-1] - close.iloc[-6])  / close.iloc[-6]  * 100
        roc_10 = (close.iloc[-1] - close.iloc[-11]) / close.iloc[-11] * 100
        if roc_5 > 1 and roc_10 > 2:
            return "BULLISH"
        elif roc_5 < -1 and roc_10 < -2:
            return "BEARISH"
        return "NEUTRAL"

    # ──────────────────────────────────────────────────
    #  ANALISIS UTAMA
    # ──────────────────────────────────────────────────
    def analyze(self, ohlcv: list) -> dict:
        """
        Analisis lengkap teknikal:
        Returns dict berisi semua sinyal
        """
        result = {
            "rsi":           None,
            "ma_signal":     "NEUTRAL",
            "macd_signal":   "NEUTRAL",
            "bb_signal":     "NEUTRAL",
            "momentum":      "NEUTRAL",
            "volume_signal": "NORMAL",
            "ma_short":      None,
            "ma_medium":     None,
            "ma_long":       None,
        }

        try:
            df = self.ohlcv_to_df(ohlcv)
            close  = df["close"]
            volume = df["volume"]

            # ── RSI ───────────────────────────────────────
            rsi = self.calc_rsi(close)
            result["rsi"] = round(rsi.iloc[-1], 2)

            # ── Moving Averages ───────────────────────────
            ma_s = self.calc_ma(close, self.cfg["MA_SHORT"])
            ma_m = self.calc_ma(close, self.cfg["MA_MEDIUM"])
            ma_l = self.calc_ma(close, self.cfg["MA_LONG"])

            result["ma_short"]  = round(ma_s.iloc[-1], 6)
            result["ma_medium"] = round(ma_m.iloc[-1], 6)
            result["ma_long"]   = round(ma_l.iloc[-1], 6)

            cur_price = close.iloc[-1]

            # Golden Cross: MA short baru melewati MA long dari bawah
            if (ma_s.iloc[-1] > ma_l.iloc[-1] and
                    ma_s.iloc[-2] <= ma_l.iloc[-2]):
                result["ma_signal"] = "GOLDEN_CROSS"
            # Death Cross: MA short baru melewati MA long dari atas
            elif (ma_s.iloc[-1] < ma_l.iloc[-1] and
                    ma_s.iloc[-2] >= ma_l.iloc[-2]):
                result["ma_signal"] = "DEATH_CROSS"
            # Bullish: harga di atas semua MA
            elif cur_price > ma_s.iloc[-1] > ma_m.iloc[-1]:
                result["ma_signal"] = "BULLISH"
            # Bearish: harga di bawah semua MA
            elif cur_price < ma_s.iloc[-1] < ma_m.iloc[-1]:
                result["ma_signal"] = "BEARISH"
            else:
                result["ma_signal"] = "NEUTRAL"

            # ── MACD ──────────────────────────────────────
            macd = self.calc_macd(close)
            hist_cur  = macd["histogram"].iloc[-1]
            hist_prev = macd["histogram"].iloc[-2]
            macd_cur  = macd["macd"].iloc[-1]

            if hist_cur > 0 and hist_prev <= 0:
                result["macd_signal"] = "BULLISH_CROSS"
            elif hist_cur < 0 and hist_prev >= 0:
                result["macd_signal"] = "BEARISH_CROSS"
            elif hist_cur > 0 and macd_cur > 0:
                result["macd_signal"] = "BULLISH"
            elif hist_cur < 0 and macd_cur < 0:
                result["macd_signal"] = "BEARISH"

            # ── Bollinger Bands ───────────────────────────
            bb = self.calc_bb(close)
            pct_b = bb["pct_b"].iloc[-1]
            if pct_b <= 0.05:
                result["bb_signal"] = "OVERSOLD"     # Harga menyentuh lower band
            elif pct_b >= 0.95:
                result["bb_signal"] = "OVERBOUGHT"   # Harga menyentuh upper band
            elif 0.4 <= pct_b <= 0.6:
                result["bb_signal"] = "NEUTRAL"

            # ── Volume ────────────────────────────────────
            result["volume_signal"] = self.analyze_volume(volume)

            # ── Momentum ──────────────────────────────────
            result["momentum"] = self.analyze_momentum(close)

        except Exception as e:
            print(f"  [TA ERR] {e}")

        return result
