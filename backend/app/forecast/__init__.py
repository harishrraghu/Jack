"""Forecast package — exposes the module-level Jill singleton."""
from app.forecast.predictor import JillPredictor, jill

__all__ = ["JillPredictor", "jill"]
