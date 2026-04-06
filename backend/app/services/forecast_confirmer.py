from app.schemas import ForecastConfirmation, ForecastResult


class ForecastConfirmer:
    def confirm(
        self,
        signal_direction: str,
        forecast: ForecastResult | None,
        atr: float,
    ) -> ForecastConfirmation:
        if forecast is None:
            return ForecastConfirmation(
                available=False,
                agrees=False,
                confident=False,
                no_reversal=False,
                confirmed=False,
            )

        # 1. Direction agreement
        if signal_direction == "BUY_CALL":
            agrees = forecast.direction == "up"
        elif signal_direction == "BUY_PUT":
            agrees = forecast.direction == "down"
        else:
            agrees = False

        # 2. Confidence: band width < 1.5 * ATR
        band_width = forecast.p90[-1] - forecast.p10[-1] if forecast.p90 and forecast.p10 else forecast.confidence_band
        confident = atr > 0 and band_width < 1.5 * atr

        # 3. No immediate reversal: first 2 candles of p50 don't move against signal
        no_reversal = True
        if len(forecast.p50) >= 2:
            if signal_direction == "BUY_CALL":
                # p50 should not drop in first 2 steps
                if forecast.p50[1] < forecast.p50[0]:
                    no_reversal = False
            elif signal_direction == "BUY_PUT":
                # p50 should not rise in first 2 steps
                if forecast.p50[1] > forecast.p50[0]:
                    no_reversal = False

        confirmed = agrees and confident and no_reversal

        return ForecastConfirmation(
            available=True,
            agrees=agrees,
            confident=confident,
            no_reversal=no_reversal,
            confirmed=confirmed,
            band_width=round(band_width, 2),
            forecast_direction=forecast.direction,
        )
