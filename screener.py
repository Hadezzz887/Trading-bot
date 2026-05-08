"""
🔍 COIN SCREENER
Scan otomatis semua koin di OKX berdasarkan volume & trending
"""
import time
from config import CONFIG, PERMANENT_BLACKLIST, TRADING_PAIRS_WHITELIST


class CoinScreener:
    def __init__(self, exchange):
        self.exchange = exchange
        self.cfg = CONFIG
        self._markets_cache = None
        self._cache_time = 0

    def scan(self, exclude: set = None) -> list:
        from news_sentiment import NewsSentiment

        exclude = exclude or set()
        candidates = []

        # Prioritas 1: Whitelist
        for pair in TRADING_PAIRS_WHITELIST:
            if pair not in exclude and pair not in PERMANENT_BLACKLIST:
                candidates.append(pair)

        try:
            tickers = self.exchange.fetch_tickers()
            scored = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith("/USDT"):
                    continue
                if symbol in exclude or symbol in PERMANENT_BLACKLIST or symbol in candidates:
                    continue

                vol_24h = ticker.get("quoteVolume", 0) or 0
                price   = ticker.get("last", 0) or 0
                change  = ticker.get("percentage", 0) or 0

                if vol_24h < self.cfg["MIN_VOLUME_24H_USDT"]:
                    continue
                if not (self.cfg["SCREENER_MIN_PRICE"] <= price <= self.cfg["SCREENER_MAX_PRICE"]):
                    continue

                score = vol_24h / 1_000_000 + abs(change) * 10
                scored.append((symbol, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            candidates.extend([s for s, _ in scored[:self.cfg["SCREENER_TOP_N"]]])

        except Exception as e:
            print(f"  [SCREENER ERR] {e}")

        # Koin trending dari CoinGecko
        try:
            trending = NewsSentiment().get_top_trending_coins()
            for coin in trending:
                pair = f"{coin}/USDT"
                if pair not in candidates and pair not in exclude:
                    candidates.insert(0, pair)
        except Exception:
            pass

        return candidates[:self.cfg["SCREENER_TOP_N"]]
