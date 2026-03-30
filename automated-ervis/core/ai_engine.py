import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


class AIEngine:
    def __init__(self):
        self.logger = logging.getLogger("ai_engine")
        self.model_path = Path("ai_model.joblib")
        self.records: list[tuple[list[float], int]] = []
        self.model = None
        self.last_train_size = 0
        self._load_model()

    def _load_model(self):
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
                self.logger.info("Loaded AI model from disk")
        except Exception as exc:
            self.logger.exception("Failed loading AI model: %s", exc)

    def _features(self, indicators: dict) -> list[float]:
        return [
            float(indicators.get("rsi", 50.0)),
            float(indicators.get("ema_spread", 0.0)),
            float(indicators.get("macd_hist", 0.0)),
            float(indicators.get("volume_ratio", 1.0)),
        ]

    def record_trade_result(self, indicators: dict, won: bool):
        self.records.append((self._features(indicators), 1 if won else 0))
        self.logger.info("AI record added. total=%d", len(self.records))
        if len(self.records) >= 10 and (len(self.records) - self.last_train_size >= 5 or self.model is None):
            self.train()

    def train(self):
        try:
            x = np.array([r[0] for r in self.records])
            y = np.array([r[1] for r in self.records])
            self.model = RandomForestClassifier(n_estimators=120, random_state=42)
            self.model.fit(x, y)
            joblib.dump(self.model, self.model_path)
            self.last_train_size = len(self.records)
            self.logger.info("AI trained on %d trades", len(self.records))
        except Exception as exc:
            self.logger.exception("AI train failed: %s", exc)

    def should_allow_trade(self, signal) -> tuple[bool, float, str]:
        if signal.score >= 4:
            return True, 1.0, "score_4_override"
        if self.model is None:
            return True, 1.0, "model_not_ready"
        try:
            proba = float(self.model.predict_proba([self._features(signal.indicators)])[0][1])
            allow = not (proba < 0.35 and signal.score < 3)
            reason = "ai_pass" if allow else "ai_block"
            self.logger.info("AI decision symbol=%s confidence=%.3f score=%d allow=%s", signal.symbol, proba, signal.score, allow)
            return allow, proba, reason
        except Exception as exc:
            self.logger.exception("AI decision failed: %s", exc)
            return True, 1.0, "ai_error_allow"
