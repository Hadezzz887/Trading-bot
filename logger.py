"""
📝 TRADE LOGGER
Catat semua aktivitas trading ke CSV
"""
import csv
import os
from datetime import datetime, date


class TradeLogger:
    def __init__(self):
        self.log_file = "trades.csv"
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                csv.writer(f).writerow([
                    "datetime", "action", "symbol", "price", "amount",
                    "rsi", "ma_signal", "news_score", "confidence",
                    "pnl_pct", "pnl_usdt", "reason"
                ])

    def log_trade(self, action, symbol, price, amount, analysis,
                  pnl_pct=None, reason=None):
        try:
            with open(self.log_file, "a", newline="") as f:
                csv.writer(f).writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    action, symbol,
                    f"{price:.8f}", f"{amount:.8f}",
                    analysis.get("rsi", ""),
                    analysis.get("ma_signal", ""),
                    analysis.get("news_score", ""),
                    analysis.get("confidence", ""),
                    f"{pnl_pct:.2f}" if pnl_pct is not None else "",
                    f"{(price * amount * (pnl_pct or 0) / 100):.2f}",
                    reason or "",
                ])
        except Exception as e:
            print(f"  [LOG ERR] {e}")

    def get_daily_stats(self) -> dict:
        today = date.today().strftime("%Y-%m-%d")
        stats = {"date": today, "total_trades": 0,
                 "wins": 0, "losses": 0, "total_pnl": 0.0}
        try:
            with open(self.log_file, "r") as f:
                for row in csv.DictReader(f):
                    if not row["datetime"].startswith(today):
                        continue
                    if row["action"] != "SELL":
                        continue
                    stats["total_trades"] += 1
                    pnl = float(row.get("pnl_pct") or 0)
                    stats["total_pnl"] += pnl
                    if pnl > 0:
                        stats["wins"] += 1
                    elif pnl < 0:
                        stats["losses"] += 1
        except Exception:
            pass
        return stats
