"""
📨 TELEGRAM NOTIFIER
"""
import os
import requests


class TelegramNotifier:
    def __init__(self):
        self.token   = os.getenv("TELEGRAM_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            print("  ⚠️  Telegram tidak dikonfigurasi (opsional, isi di .env)")

    def send_message(self, text: str):
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text,
                      "parse_mode": "HTML", "disable_web_page_preview": True},
                timeout=8
            )
        except Exception:
            pass

    def send_trade_alert(self, action, symbol, price, amount, tp, sl, analysis):
        reasons = "\n".join(f"  • {r}" for r in analysis.get("reasons", []))
        emoji   = "🟢" if action == "BUY" else "🔴"
        self.send_message(
            f"{emoji} <b>{action} {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Harga      : <code>${price:.6f}</code>\n"
            f"💵 Nilai      : <code>${amount:.2f} USDT</code>\n"
            f"🎯 Take Profit: <code>${tp:.6f}</code>\n"
            f"🛑 Stop Loss  : <code>${sl:.6f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 RSI   : {analysis.get('rsi', 'N/A')}\n"
            f"📈 MA    : {analysis.get('ma_signal', 'N/A')}\n"
            f"📰 News  : {analysis.get('news_score', 0):.0f}/100\n"
            f"⭐ Score : {analysis.get('confidence', 0)}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Alasan:\n{reasons}"
        )

    def send_close_alert(self, symbol, price, pnl_pct, pnl_usdt, reason):
        emoji = "✅" if pnl_pct > 0 else "❌"
        self.send_message(
            f"{emoji} <b>CLOSE {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Harga  : <code>${price:.6f}</code>\n"
            f"📊 PnL    : <code>{pnl_pct:+.2f}%</code> (${pnl_usdt:+.2f})\n"
            f"📝 Alasan : {reason}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
