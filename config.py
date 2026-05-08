"""
⚙️ KONFIGURASI BOT TRADING
Edit file ini untuk mengubah parameter bot
"""

# ══════════════════════════════════════════════════════
#  🔧 KONFIGURASI UTAMA
# ══════════════════════════════════════════════════════

CONFIG = {

    # ── Mode & Safety ─────────────────────────────────
    "PAPER_TRADING":        True,      # True = simulasi, False = live (HATI-HATI!)
    "TIMEFRAME":            "15m",     # Timeframe candle: 1m, 5m, 15m, 1h, 4h
    "CANDLE_LIMIT":         200,       # Jumlah candle untuk analisis

    # ── Interval & Timing ─────────────────────────────
    "LOOP_INTERVAL_SEC":    60,        # Detik antar cycle utama
    "SCREEN_INTERVAL_SEC":  300,       # Scan koin baru tiap 5 menit
    "MAX_HOLD_HOURS":       24,        # Maksimal hold posisi (jam)

    # ── Manajemen Posisi ──────────────────────────────
    "MAX_POSITIONS":        5,         # Maksimal posisi terbuka bersamaan
    "MAX_TRADES_PER_DAY":  20,         # Batas trade per hari
    "MIN_ORDER_USDT":       10,        # Minimum order dalam USDT
    "RISK_PER_TRADE_PCT":   2.0,       # % modal per trade (risk management)
    "MAX_PORTFOLIO_PCT":    20.0,      # % max modal untuk satu koin

    # ── Take Profit & Stop Loss ───────────────────────
    "TAKE_PROFIT_PCT":      3.0,       # % Take Profit dari entry
    "STOP_LOSS_PCT":        1.5,       # % Stop Loss dari entry
    "TRAILING_STOP":        False,     # Aktifkan trailing stop
    "TRAILING_STOP_PCT":    1.0,       # % trailing stop

    # ── RSI Settings ──────────────────────────────────
    "RSI_PERIOD":           14,        # Period RSI
    "RSI_OVERSOLD":         30,        # Level oversold (sinyal BUY)
    "RSI_OVERBOUGHT":       70,        # Level overbought (sinyal SELL)

    # ── Moving Average Settings ───────────────────────
    "MA_SHORT":             9,         # MA periode pendek (EMA)
    "MA_MEDIUM":            21,        # MA periode menengah (EMA)
    "MA_LONG":              50,        # MA periode panjang (SMA)
    "USE_EMA":              True,      # True = EMA, False = SMA

    # ── MACD Settings ─────────────────────────────────
    "MACD_FAST":            12,
    "MACD_SLOW":            26,
    "MACD_SIGNAL":          9,

    # ── Bollinger Bands ───────────────────────────────
    "BB_PERIOD":            20,
    "BB_STD":               2,

    # ── Volume Filter ─────────────────────────────────
    "MIN_VOLUME_24H_USDT":  1_000_000, # Min volume 24h $1M
    "VOLUME_SPIKE_MULT":    1.5,       # Minimum volume spike multiplier

    # ── Screener Filter ───────────────────────────────
    "SCREENER_TOP_N":       50,        # Top N koin yang di-scan
    "SCREENER_MIN_PRICE":   0.00001,   # Harga minimum
    "SCREENER_MAX_PRICE":   100_000,   # Harga maksimum

    # ── Signal Confidence ─────────────────────────────
    "MIN_CONFIDENCE":       60,        # Minimum confidence untuk entry (%)

    # ── News Sentiment ────────────────────────────────
    "NEWS_POSITIVE_THRESHOLD": 65,     # Score berita positif (0-100)
    "NEWS_NEGATIVE_THRESHOLD": 35,     # Score berita negatif (0-100)
    "NEWS_CACHE_MINUTES":   15,        # Cache berita selama N menit
    "NEWS_WEIGHT":          0.25,      # Bobot news dalam keputusan (0-1)

    # ── Blacklist Temp ────────────────────────────────
    "BLACKLIST_AFTER_SL_HOURS": 4,    # Skip koin N jam setelah kena SL
}


# ══════════════════════════════════════════════════════
#  📋 WHITELIST / BLACKLIST KOIN
# ══════════════════════════════════════════════════════

# Daftar koin yang SELALU di-scan (prioritas tinggi)
TRADING_PAIRS_WHITELIST = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
    "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT",
    "MATIC/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT",
    "LTC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT",
]

# Koin yang TIDAK pernah di-trade
PERMANENT_BLACKLIST = [
    "USDC/USDT", "BUSD/USDT", "DAI/USDT",  # Stablecoin
    "WBTC/USDT",                              # Wrapped token
]
