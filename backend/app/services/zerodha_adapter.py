from app.schemas import Candle


class ZerodhaAdapter:
    """
    Placeholder adapter boundary for Kite Connect integration.
    Keep broker I/O here so deterministic analysis engines stay pure.
    """

    async def fetch_historical_candles(self, symbol: str, timeframe: str) -> list[Candle]:
        raise NotImplementedError("Wire Kite Connect historical API here.")

    async def stream_live_ticks(self, symbol: str) -> None:
        raise NotImplementedError("Wire Kite Connect websocket streaming here.")

    async def fetch_options_context(self, symbol: str) -> dict:
        raise NotImplementedError("Wire PCR/OI context here.")
