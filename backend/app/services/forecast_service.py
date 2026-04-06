import asyncio
from typing import Optional

from app.schemas import Candle, ForecastResult


class ForecastService:
    """Jill — TimesFM probabilistic confirmation layer (Layer 7). Fully optional."""

    def __init__(self) -> None:
        self._model = None
        self._available: bool | None = None  # None = not yet checked

    def _load(self) -> None:
        if self._available is False:
            return
        try:
            import timesfm  # type: ignore[import]

            self._model = timesfm.TimesFm(
                hparams=timesfm.TimesFmHparams(
                    backend="torch",
                    per_core_batch_size=32,
                    horizon_len=8,
                    context_len=128,
                ),
                checkpoint=timesfm.TimesFmCheckpoint(
                    huggingface_repo_id="google/timesfm-2.5-500m-pytorch"
                ),
            )
            self._available = True
        except (ImportError, Exception):
            self._available = False

    async def forecast(self, candles: list[Candle]) -> Optional[ForecastResult]:
        await asyncio.to_thread(self._load)
        if not self._available or self._model is None:
            return None

        closes = [c.close for c in candles[-128:]]
        try:
            point_forecast, quantile_forecast = await asyncio.to_thread(
                self._model.forecast, [closes], freq=[0]
            )
            p10 = quantile_forecast[0, :, 0].tolist()
            p50 = point_forecast[0].tolist()
            p90 = quantile_forecast[0, :, -1].tolist()
            direction = "up" if p50[-1] > closes[-1] else "down"
            magnitude = abs(p50[-1] - closes[-1])
            return ForecastResult(
                direction=direction,
                magnitude=round(magnitude, 2),
                p10=[round(v, 2) for v in p10],
                p50=[round(v, 2) for v in p50],
                p90=[round(v, 2) for v in p90],
                horizon=8,
                confidence_band=round(p90[-1] - p10[-1], 2),
            )
        except Exception:
            return None
