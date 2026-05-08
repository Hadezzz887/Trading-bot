"""
🛡️ RISK MANAGER
Manajemen risiko & kalkulasi ukuran posisi
"""
from config import CONFIG


class RiskManager:
    def __init__(self, exchange):
        self.exchange = exchange
        self.cfg = CONFIG

    def calculate_position_size(self, balance_usdt: float, symbol: str, confidence: int) -> float:
        base_risk = self.cfg["RISK_PER_TRADE_PCT"] / 100
        conf_mult = 0.5 + (confidence / 100)
        size = balance_usdt * base_risk * conf_mult
        max_size = balance_usdt * (self.cfg["MAX_PORTFOLIO_PCT"] / 100)
        return round(min(size, max_size), 2)

    def can_open_position(self, active_positions: dict) -> bool:
        return len(active_positions) < self.cfg["MAX_POSITIONS"]
