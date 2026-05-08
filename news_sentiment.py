"""
📰 NEWS SENTIMENT ANALYZER
Mengambil & menganalisis berita kripto dari berbagai sumber
untuk mendeteksi hype dan sentimen pasar
"""

import requests
import time
import json
from datetime import datetime, timedelta
from config import CONFIG


class NewsSentiment:
    def __init__(self):
        self.cache = {}          # {coin: {"score": X, "time": T, "headlines": []}}
        self.cache_duration = CONFIG["NEWS_CACHE_MINUTES"] * 60

        # Kata kunci positif/negatif untuk scoring
        self.POSITIVE_WORDS = [
            "bull", "bullish", "surge", "soar", "rally", "pump", "moon",
            "breakout", "ath", "all-time high", "adoption", "partnership",
            "launch", "upgrade", "listing", "buy", "accumulate", "growth",
            "positive", "gain", "profit", "rise", "climb", "strong",
            "naik", "bullish", "bagus", "positif", "potensi", "kuat",
            "institutional", "mainstream", "approved", "etf", "invest",
        ]
        self.NEGATIVE_WORDS = [
            "bear", "bearish", "crash", "dump", "fall", "drop", "plunge",
            "hack", "exploit", "rug", "scam", "ban", "regulation", "sec",
            "lawsuit", "sell", "short", "negative", "risk", "fear",
            "turun", "jatuh", "buruk", "negatif", "bahaya", "larangan",
            "fraud", "ponzi", "collapse", "liquidation", "delisted",
        ]
        self.HYPE_WORDS = [
            "trending", "viral", "hype", "hot", "popular", "buzz",
            "massive", "huge", "breaking", "urgent", "alert", "now",
            "explode", "100x", "1000x", "gem", "hidden",
        ]

    # ──────────────────────────────────────────────────
    #  FETCH BERITA
    # ──────────────────────────────────────────────────
    def fetch_cryptopanic(self, coin: str) -> list:
        """
        Fetch berita dari CryptoPanic API (gratis)
        Optional: daftar di cryptopanic.com untuk API key
        """
        try:
            api_key = ""  # Kosong = public, isi jika punya key
            base_url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                "auth_token": api_key if api_key else "public",
                "currencies": coin.upper(),
                "kind": "news",
                "public": "true",
            }
            resp = requests.get(base_url, params=params, timeout=8)
            if resp.ok:
                data = resp.json()
                results = data.get("results", [])
                headlines = []
                for item in results[:10]:
                    title = item.get("title", "")
                    votes = item.get("votes", {})
                    positive = votes.get("positive", 0)
                    negative = votes.get("negative", 0)
                    headlines.append({
                        "title": title,
                        "positive_votes": positive,
                        "negative_votes": negative,
                        "source": "cryptopanic",
                    })
                return headlines
        except Exception as e:
            pass
        return []

    def fetch_coingecko_sentiment(self, coin: str) -> dict:
        """
        Ambil sentiment data dari CoinGecko (gratis, tanpa key)
        """
        try:
            coin_map = {
                "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
                "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
                "AVAX": "avalanche-2", "DOT": "polkadot", "MATIC": "matic-network",
                "LINK": "chainlink", "UNI": "uniswap", "ATOM": "cosmos",
                "LTC": "litecoin", "NEAR": "near", "FTM": "fantom",
                "ALGO": "algorand", "DOGE": "dogecoin", "SHIB": "shiba-inu",
            }
            coin_id = coin_map.get(coin.upper(), coin.lower())
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "false",
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                data = resp.json()
                sentiment_up = data.get("sentiment_votes_up_percentage", 50)
                market_data  = data.get("market_data", {})
                price_change_24h = market_data.get("price_change_percentage_24h", 0) or 0
                community_data = data.get("community_data", {})
                twitter_followers = community_data.get("twitter_followers", 0) or 0

                return {
                    "sentiment_up_pct": sentiment_up,
                    "price_change_24h": price_change_24h,
                    "twitter_followers": twitter_followers,
                }
        except Exception:
            pass
        return {}

    def fetch_alternative_fear_greed(self) -> int:
        """
        Ambil Fear & Greed Index (0=extreme fear, 100=extreme greed)
        """
        try:
            resp = requests.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=5
            )
            if resp.ok:
                data = resp.json()
                return int(data["data"][0]["value"])
        except Exception:
            pass
        return 50  # Default neutral

    # ──────────────────────────────────────────────────
    #  ANALISIS SENTIMEN
    # ──────────────────────────────────────────────────
    def score_text(self, text: str) -> float:
        """
        Score teks berdasarkan kata kunci positif/negatif
        Returns: -1.0 (sangat negatif) hingga +1.0 (sangat positif)
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        pos_count  = sum(1 for w in self.POSITIVE_WORDS if w in text_lower)
        neg_count  = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)
        hype_count = sum(0.5 for w in self.HYPE_WORDS if w in text_lower)

        total = pos_count + neg_count + hype_count
        if total == 0:
            return 0.0

        # Normalize ke -1 hingga +1
        score = (pos_count - neg_count) / (total + 1)
        return max(-1.0, min(1.0, score))

    def get_sentiment(self, coin: str) -> float:
        """
        Dapatkan skor sentimen untuk satu koin
        Returns: 0-100 (0=sangat negatif, 50=netral, 100=sangat positif)
        """
        # Cek cache
        now = time.time()
        if coin in self.cache:
            cached = self.cache[coin]
            if now - cached["time"] < self.cache_duration:
                return cached["score"]

        score_components = []
        headlines = []

        # 1. Fear & Greed Index (global market sentiment)
        fg_index = self.fetch_alternative_fear_greed()
        # Konversi ke kontribusi score: 0-100 langsung digunakan
        score_components.append(("fear_greed", fg_index, 0.2))

        # 2. CoinGecko sentiment & data
        cg_data = self.fetch_coingecko_sentiment(coin)
        if cg_data:
            # Community sentiment votes
            cg_sentiment = cg_data.get("sentiment_up_pct", 50)
            score_components.append(("cg_sentiment", cg_sentiment, 0.3))

            # Price momentum sebagai proxy sentimen
            price_change = cg_data.get("price_change_24h", 0)
            price_score  = 50 + (price_change * 2)  # +1% = +2 point
            price_score  = max(0, min(100, price_score))
            score_components.append(("price_momentum", price_score, 0.2))

        # 3. CryptoPanic headlines
        news_list = self.fetch_cryptopanic(coin)
        if news_list:
            text_scores = []
            for news in news_list:
                title    = news["title"]
                headlines.append(title)
                raw_score = self.score_text(title)

                # Bobot dari votes komunitas
                pos_v = news.get("positive_votes", 0)
                neg_v = news.get("negative_votes", 0)
                vote_weight = 1.0 + (pos_v - neg_v) * 0.05
                text_scores.append(raw_score * vote_weight)

            if text_scores:
                avg_text = sum(text_scores) / len(text_scores)
                # Konversi -1..+1 ke 0..100
                news_score = 50 + avg_text * 35
                news_score = max(0, min(100, news_score))
                score_components.append(("news_text", news_score, 0.3))

        # Hitung weighted average
        if not score_components:
            final_score = 50.0
        else:
            total_weight = sum(w for _, _, w in score_components)
            final_score  = sum(v * w for _, v, w in score_components) / total_weight

        final_score = round(max(0, min(100, final_score)), 1)

        # Cache hasil
        self.cache[coin] = {
            "score":     final_score,
            "time":      now,
            "headlines": headlines[:5],
            "components": score_components,
        }

        return final_score

    def get_top_trending_coins(self) -> list:
        """
        Ambil daftar koin yang sedang trending dari CoinGecko
        """
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/search/trending",
                timeout=8
            )
            if resp.ok:
                data  = resp.json()
                coins = data.get("coins", [])
                return [c["item"]["symbol"].upper() for c in coins]
        except Exception:
            pass
        return []

    def get_cached_headlines(self, coin: str) -> list:
        """Ambil headline dari cache"""
        if coin in self.cache:
            return self.cache[coin].get("headlines", [])
        return []
