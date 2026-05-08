"""
╔══════════════════════════════════════════════════════════════════╗
║         CRYPTO AUTO TRADING BOT - OKX Exchange                  ║
║  Indikator : RSI + Moving Average + News Sentiment              ║
║  Mode      : Auto Trading (semua koin/screener otomatis)        ║
╚══════════════════════════════════════════════════════════════════╝

Dependencies:
    pip install ccxt pandas ta requests colorama python-dotenv websockets

File struktur:
    trading_bot.py      ← file utama (ini)
    config.py           ← konfigurasi & parameter
    indicators.py       ← RSI, MA, signal logic
    news_sentiment.py   ← analisis berita & hype
    risk_manager.py     ← manajemen risiko & sizing
    telegram_notify.py  ← notifikasi Telegram
    screener.py         ← scan semua koin otomatis
    logger.py           ← logging & riwayat trade

Setup:
    1. pip install ccxt pandas ta requests colorama python-dotenv
    2. Isi .env dengan API keys (lihat .env.example)
    3. python trading_bot.py
"""

import asyncio
import time
import os
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

# Import modul lokal
from config import CONFIG, TRADING_PAIRS_WHITELIST
from indicators import TechnicalAnalysis
from news_sentiment import NewsSentiment
from risk_manager import RiskManager
from telegram_notify import TelegramNotifier
from screener import CoinScreener
from logger import TradeLogger

import ccxt


# ══════════════════════════════════════════════════════
#  🤖 MAIN TRADING BOT
# ══════════════════════════════════════════════════════

class CryptoTradingBot:
    def __init__(self):
        print(f"{Fore.CYAN}  Inisialisasi bot...{Style.RESET_ALL}")

        # Setup OKX exchange
        self.exchange = ccxt.okx({
            "apiKey":     os.getenv("OKX_API_KEY", ""),
            "secret":     os.getenv("OKX_SECRET_KEY", ""),
            "password":   os.getenv("OKX_PASSPHRASE", ""),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })

        # Paper trading mode
        if CONFIG["PAPER_TRADING"]:
            self.exchange.set_sandbox_mode(True)
            print(f"{Fore.YELLOW}  ⚠️  PAPER TRADING MODE AKTIF (tidak ada uang nyata){Style.RESET_ALL}")

        # Inisialisasi komponen
        self.ta          = TechnicalAnalysis()
        self.news        = NewsSentiment()
        self.risk        = RiskManager(self.exchange)
        self.notifier    = TelegramNotifier()
        self.screener    = CoinScreener(self.exchange)
        self.logger      = TradeLogger()

        # State bot
        self.active_positions = {}   # {symbol: position_data}
        self.blacklist         = set()  # Koin yang di-skip sementara
        self.last_screened     = 0
        self.trade_count_today = 0
        self.running           = False

        print(f"{Fore.GREEN}  ✅ Bot siap!{Style.RESET_ALL}")

    # ──────────────────────────────────────────────────
    #  KONEKSI & VALIDASI
    # ──────────────────────────────────────────────────
    def connect(self):
        """Test koneksi ke OKX"""
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance["USDT"]["free"] if "USDT" in balance else 0
            print(f"{Fore.GREEN}  ✅ Terhubung ke OKX{Style.RESET_ALL}")
            print(f"  💰 Saldo USDT: ${usdt_balance:.2f}")
            return True, usdt_balance
        except Exception as e:
            print(f"{Fore.RED}  ❌ Gagal koneksi OKX: {e}{Style.RESET_ALL}")
            return False, 0

    # ──────────────────────────────────────────────────
    #  ANALISIS KOIN
    # ──────────────────────────────────────────────────
    def analyze_coin(self, symbol: str) -> dict:
        """
        Analisis lengkap satu koin:
        - Technical: RSI + MA
        - News: sentiment score
        - Gabungkan jadi sinyal final
        """
        result = {
            "symbol": symbol,
            "signal": "HOLD",   # BUY / SELL / HOLD
            "confidence": 0,    # 0-100
            "rsi": None,
            "ma_signal": None,
            "news_score": 0,
            "reasons": [],
        }

        try:
            # Ambil data OHLCV
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=CONFIG["TIMEFRAME"],
                limit=CONFIG["CANDLE_LIMIT"]
            )
            if len(ohlcv) < 50:
                return result

            # ── Analisis Teknikal ──────────────────────────
            ta_signal = self.ta.analyze(ohlcv)
            result["rsi"]       = ta_signal["rsi"]
            result["ma_signal"] = ta_signal["ma_signal"]

            # ── News Sentiment ─────────────────────────────
            coin_name = symbol.replace("/USDT", "").replace("/BTC", "")
            news_score = self.news.get_sentiment(coin_name)
            result["news_score"] = news_score

            # ── Gabungkan Sinyal ───────────────────────────
            buy_score  = 0
            sell_score = 0
            reasons    = []

            # RSI scoring
            rsi = ta_signal["rsi"]
            if rsi is not None:
                if rsi <= CONFIG["RSI_OVERSOLD"]:
                    buy_score += 35
                    reasons.append(f"RSI oversold ({rsi:.1f})")
                elif rsi <= 40:
                    buy_score += 15
                    reasons.append(f"RSI rendah ({rsi:.1f})")
                elif rsi >= CONFIG["RSI_OVERBOUGHT"]:
                    sell_score += 35
                    reasons.append(f"RSI overbought ({rsi:.1f})")
                elif rsi >= 60:
                    sell_score += 15
                    reasons.append(f"RSI tinggi ({rsi:.1f})")

            # MA scoring
            ma = ta_signal["ma_signal"]
            if ma == "GOLDEN_CROSS":
                buy_score += 30
                reasons.append("Golden Cross (MA)")
            elif ma == "BULLISH":
                buy_score += 20
                reasons.append("Harga di atas MA (bullish)")
            elif ma == "DEATH_CROSS":
                sell_score += 30
                reasons.append("Death Cross (MA)")
            elif ma == "BEARISH":
                sell_score += 20
                reasons.append("Harga di bawah MA (bearish)")

            # Momentum scoring
            momentum = ta_signal.get("momentum", "NEUTRAL")
            if momentum == "BULLISH":
                buy_score += 10
                reasons.append("Momentum bullish")
            elif momentum == "BEARISH":
                sell_score += 10
                reasons.append("Momentum bearish")

            # Volume scoring
            vol_signal = ta_signal.get("volume_signal", "NORMAL")
            if vol_signal == "HIGH":
                if buy_score > sell_score:
                    buy_score += 10
                    reasons.append("Volume tinggi (konfirmasi)")
                else:
                    sell_score += 10

            # News sentiment scoring
            if news_score >= CONFIG["NEWS_POSITIVE_THRESHOLD"]:
                buy_score += 25
                reasons.append(f"Sentimen berita positif ({news_score:.0f}/100)")
            elif news_score >= 60:
                buy_score += 10
                reasons.append(f"Sentimen berita cukup positif ({news_score:.0f}/100)")
            elif news_score <= CONFIG["NEWS_NEGATIVE_THRESHOLD"]:
                sell_score += 25
                reasons.append(f"Sentimen berita negatif ({news_score:.0f}/100)")
            elif news_score <= 40:
                sell_score += 10
                reasons.append(f"Sentimen berita cukup negatif ({news_score:.0f}/100)")

            # Tentukan sinyal final
            result["reasons"] = reasons
            if buy_score >= CONFIG["MIN_CONFIDENCE"] and buy_score > sell_score:
                result["signal"]     = "BUY"
                result["confidence"] = min(buy_score, 100)
            elif sell_score >= CONFIG["MIN_CONFIDENCE"] and sell_score > buy_score:
                result["signal"]     = "SELL"
                result["confidence"] = min(sell_score, 100)

        except Exception as e:
            print(f"{Fore.RED}  [ERR] Analisis {symbol}: {e}{Style.RESET_ALL}")

        return result

    # ──────────────────────────────────────────────────
    #  EKSEKUSI ORDER
    # ──────────────────────────────────────────────────
    def execute_buy(self, symbol: str, analysis: dict):
        """Eksekusi order BUY"""
        try:
            balance   = self.exchange.fetch_balance()
            usdt_free = balance["USDT"]["free"]

            # Hitung ukuran posisi
            position_size_usdt = self.risk.calculate_position_size(
                usdt_free, symbol, analysis["confidence"]
            )

            if position_size_usdt < CONFIG["MIN_ORDER_USDT"]:
                print(f"  [SKIP] {symbol} - balance tidak cukup (${position_size_usdt:.2f})")
                return False

            # Ambil harga terkini
            ticker  = self.exchange.fetch_ticker(symbol)
            price   = ticker["last"]
            amount  = position_size_usdt / price

            # Hitung TP dan SL
            tp_price = price * (1 + CONFIG["TAKE_PROFIT_PCT"] / 100)
            sl_price = price * (1 - CONFIG["STOP_LOSS_PCT"] / 100)

            # Eksekusi order
            if not CONFIG["PAPER_TRADING"]:
                order = self.exchange.create_market_buy_order(symbol, amount)
                order_id = order["id"]
            else:
                order_id = f"PAPER_{int(time.time())}"

            # Simpan posisi
            self.active_positions[symbol] = {
                "order_id":    order_id,
                "entry_price": price,
                "amount":      amount,
                "tp_price":    tp_price,
                "sl_price":    sl_price,
                "entry_time":  time.time(),
                "analysis":    analysis,
                "usdt_value":  position_size_usdt,
            }

            self.trade_count_today += 1

            # Log
            self.logger.log_trade("BUY", symbol, price, amount, analysis)

            # Print
            print(f"{Fore.GREEN}  ✅ BUY {symbol} @ ${price:.4f} | "
                  f"${position_size_usdt:.2f} | "
                  f"TP: ${tp_price:.4f} | SL: ${sl_price:.4f}{Style.RESET_ALL}")

            # Telegram notifikasi
            self.notifier.send_trade_alert(
                action="BUY", symbol=symbol, price=price,
                amount=position_size_usdt, tp=tp_price, sl=sl_price,
                analysis=analysis
            )
            return True

        except Exception as e:
            print(f"{Fore.RED}  [ERR] Gagal BUY {symbol}: {e}{Style.RESET_ALL}")
            return False

    def execute_sell(self, symbol: str, reason: str = "Signal"):
        """Eksekusi order SELL"""
        if symbol not in self.active_positions:
            return False

        try:
            pos    = self.active_positions[symbol]
            ticker = self.exchange.fetch_ticker(symbol)
            price  = ticker["last"]
            amount = pos["amount"]

            pnl_pct = ((price - pos["entry_price"]) / pos["entry_price"]) * 100
            pnl_usdt = (price - pos["entry_price"]) * amount

            if not CONFIG["PAPER_TRADING"]:
                order = self.exchange.create_market_sell_order(symbol, amount)

            # Log
            self.logger.log_trade("SELL", symbol, price, amount,
                                  pos["analysis"], pnl_pct, reason)

            print(f"{'  ✅' if pnl_pct > 0 else '  ❌'} "
                  f"SELL {symbol} @ ${price:.4f} | "
                  f"PnL: {'+' if pnl_pct > 0 else ''}{pnl_pct:.2f}% "
                  f"(${pnl_usdt:+.2f}) | {reason}")

            # Telegram notifikasi
            self.notifier.send_close_alert(
                symbol=symbol, price=price,
                pnl_pct=pnl_pct, pnl_usdt=pnl_usdt, reason=reason
            )

            del self.active_positions[symbol]
            return True

        except Exception as e:
            print(f"{Fore.RED}  [ERR] Gagal SELL {symbol}: {e}{Style.RESET_ALL}")
            return False

    # ──────────────────────────────────────────────────
    #  MONITOR POSISI AKTIF
    # ──────────────────────────────────────────────────
    def monitor_positions(self):
        """Cek TP/SL untuk semua posisi aktif"""
        for symbol in list(self.active_positions.keys()):
            try:
                pos    = self.active_positions[symbol]
                ticker = self.exchange.fetch_ticker(symbol)
                price  = ticker["last"]

                # Cek Take Profit
                if price >= pos["tp_price"]:
                    print(f"{Fore.GREEN}  🎯 TP HIT: {symbol}{Style.RESET_ALL}")
                    self.execute_sell(symbol, "Take Profit")

                # Cek Stop Loss
                elif price <= pos["sl_price"]:
                    print(f"{Fore.RED}  🛑 SL HIT: {symbol}{Style.RESET_ALL}")
                    self.execute_sell(symbol, "Stop Loss")

                # Cek max hold time
                elif time.time() - pos["entry_time"] > CONFIG["MAX_HOLD_HOURS"] * 3600:
                    print(f"{Fore.YELLOW}  ⏰ MAX HOLD TIME: {symbol}{Style.RESET_ALL}")
                    self.execute_sell(symbol, "Max Hold Time")

            except Exception as e:
                print(f"{Fore.RED}  [ERR] Monitor {symbol}: {e}{Style.RESET_ALL}")

    # ──────────────────────────────────────────────────
    #  MAIN LOOP
    # ──────────────────────────────────────────────────
    async def run(self):
        """Loop utama bot"""
        self.running = True
        print(f"\n{Fore.GREEN}  🚀 Bot mulai berjalan...{Style.RESET_ALL}\n")

        # Notif start
        self.notifier.send_message(
            f"🤖 <b>Trading Bot AKTIF</b>\n"
            f"Exchange: OKX\n"
            f"Mode: {'Paper' if CONFIG['PAPER_TRADING'] else 'Live'} Trading\n"
            f"Timeframe: {CONFIG['TIMEFRAME']}\n"
            f"Max posisi: {CONFIG['MAX_POSITIONS']}\n"
            f"TP: {CONFIG['TAKE_PROFIT_PCT']}% | SL: {CONFIG['STOP_LOSS_PCT']}%"
        )

        cycle = 0
        while self.running:
            cycle += 1
            print(f"\n{Fore.CYAN}{'═'*55}")
            print(f"  CYCLE #{cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Posisi aktif: {len(self.active_positions)}/{CONFIG['MAX_POSITIONS']}")
            print(f"{'═'*55}{Style.RESET_ALL}")

            # 1. Monitor posisi aktif (TP/SL)
            if self.active_positions:
                print(f"\n{Fore.YELLOW}  [1/3] Monitor posisi...{Style.RESET_ALL}")
                self.monitor_positions()

            # 2. Screener koin baru
            now = time.time()
            if now - self.last_screened >= CONFIG["SCREEN_INTERVAL_SEC"]:
                print(f"\n{Fore.YELLOW}  [2/3] Screener koin...{Style.RESET_ALL}")
                candidates = self.screener.scan(
                    exclude=set(self.active_positions.keys()) | self.blacklist
                )
                self.last_screened = now
                print(f"  Ditemukan {len(candidates)} kandidat")
            else:
                candidates = []

            # 3. Analisis & trading
            if candidates and len(self.active_positions) < CONFIG["MAX_POSITIONS"]:
                print(f"\n{Fore.YELLOW}  [3/3] Analisis kandidat...{Style.RESET_ALL}")

                # Cek batas trade harian
                if self.trade_count_today >= CONFIG["MAX_TRADES_PER_DAY"]:
                    print(f"  ⚠️ Batas trade harian tercapai ({self.trade_count_today})")
                else:
                    for symbol in candidates:
                        if len(self.active_positions) >= CONFIG["MAX_POSITIONS"]:
                            break
                        if symbol in self.active_positions:
                            continue

                        print(f"  Analisis {symbol}...", end=" ")
                        analysis = self.analyze_coin(symbol)

                        rsi_str  = f"RSI:{analysis['rsi']:.1f}" if analysis["rsi"] else "RSI:N/A"
                        news_str = f"News:{analysis['news_score']:.0f}"
                        ma_str   = analysis["ma_signal"] or "N/A"

                        print(f"{rsi_str} | {ma_str} | {news_str} | "
                              f"Signal: {analysis['signal']} ({analysis['confidence']}%)")

                        if (analysis["signal"] == "BUY"
                                and analysis["confidence"] >= CONFIG["MIN_CONFIDENCE"]):
                            self.execute_buy(symbol, analysis)
                            await asyncio.sleep(1)  # Delay antar order

            # Tampilkan ringkasan posisi
            if self.active_positions:
                print(f"\n  📊 Posisi Aktif:")
                for sym, pos in self.active_positions.items():
                    try:
                        ticker = self.exchange.fetch_ticker(sym)
                        cur_price = ticker["last"]
                        pnl = ((cur_price - pos["entry_price"]) / pos["entry_price"]) * 100
                        color = Fore.GREEN if pnl > 0 else Fore.RED
                        print(f"    {sym:20} Entry:${pos['entry_price']:.4f} "
                              f"Now:${cur_price:.4f} "
                              f"{color}PnL:{pnl:+.2f}%{Style.RESET_ALL}")
                    except Exception:
                        pass

            # Tunggu sebelum cycle berikutnya
            wait = CONFIG["LOOP_INTERVAL_SEC"]
            print(f"\n  ⏳ Menunggu {wait}s sebelum cycle berikutnya...")
            await asyncio.sleep(wait)

    def stop(self):
        self.running = False
        print(f"\n{Fore.YELLOW}  Bot dihentikan.{Style.RESET_ALL}")


# ══════════════════════════════════════════════════════
#  🚀 ENTRY POINT
# ══════════════════════════════════════════════════════

async def main():
    from dotenv import load_dotenv
    load_dotenv()

    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"""
{Fore.GREEN}╔══════════════════════════════════════════════════════════╗
║       CRYPTO AUTO TRADING BOT — OKX                      ║
║       RSI + Moving Average + News Sentiment              ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

    bot = CryptoTradingBot()

    # Test koneksi
    connected, balance = bot.connect()
    if not connected and not CONFIG["PAPER_TRADING"]:
        print(f"{Fore.RED}  Cek API keys di file .env{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}  Konfigurasi aktif:{Style.RESET_ALL}")
    print(f"  Mode        : {'⚠️  PAPER TRADING' if CONFIG['PAPER_TRADING'] else '🔴 LIVE TRADING'}")
    print(f"  Timeframe   : {CONFIG['TIMEFRAME']}")
    print(f"  Max posisi  : {CONFIG['MAX_POSITIONS']}")
    print(f"  Take Profit : {CONFIG['TAKE_PROFIT_PCT']}%")
    print(f"  Stop Loss   : {CONFIG['STOP_LOSS_PCT']}%")
    print(f"  RSI Oversold: {CONFIG['RSI_OVERSOLD']}")
    print(f"  RSI Overbought: {CONFIG['RSI_OVERBOUGHT']}")
    print(f"  Min confidence: {CONFIG['MIN_CONFIDENCE']}%")
    print(f"\n  Tekan Ctrl+C untuk berhenti\n")

    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}  Bot dihentikan. Sampai jumpa!{Style.RESET_ALL}")
