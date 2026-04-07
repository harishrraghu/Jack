import argparse
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
IST_TIMEZONE = "Asia/Kolkata"
OHLCV_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


@dataclass
class FetchResult:
    name: str
    path: Path | None
    rows: int
    message: str


def _print(message: str) -> None:
    print(message, flush=True)


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for column in dataframe.columns:
        normalized = str(column).strip().lower()
        rename_map[column] = normalized
    return dataframe.rename(columns=rename_map)


def _find_column(dataframe: pd.DataFrame, *candidates: str) -> str | None:
    normalized = {column.strip().lower(): column for column in dataframe.columns}
    for candidate in candidates:
        match = normalized.get(candidate.strip().lower())
        if match:
            return match
    return None


def _build_timestamp_series(dataframe: pd.DataFrame) -> pd.Series:
    time_column = _find_column(dataframe, "time", "timestamp", "datetime")
    date_column = _find_column(dataframe, "date")

    if date_column and time_column and date_column != time_column:
        combined = (
            dataframe[date_column].astype(str).str.strip()
            + " "
            + dataframe[time_column].astype(str).str.strip()
        )
        timestamps = pd.to_datetime(combined, errors="coerce", dayfirst=True)
        if timestamps.notna().any():
            return timestamps

    if time_column:
        timestamps = pd.to_datetime(dataframe[time_column], errors="coerce", dayfirst=True)
        if timestamps.notna().any():
            return timestamps

    if date_column:
        timestamps = pd.to_datetime(dataframe[date_column], errors="coerce", dayfirst=True)
        if timestamps.notna().any():
            return timestamps

    raise ValueError("Could not parse timestamp from available date/time columns.")


def _to_epoch_seconds(series: pd.Series) -> pd.Series:
    timestamps = series.copy()
    if timestamps.dt.tz is None:
        timestamps = timestamps.dt.tz_localize(IST_TIMEZONE)
    else:
        timestamps = timestamps.dt.tz_convert(IST_TIMEZONE)
    return (timestamps.astype("int64") // 10**9).astype("Int64")


def _prepare_ohlcv_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_columns(dataframe.copy())

    open_column = _find_column(frame, "open")
    high_column = _find_column(frame, "high")
    low_column = _find_column(frame, "low")
    close_column = _find_column(frame, "close", "adj close", "adj_close")
    volume_column = _find_column(frame, "volume")

    required = {
        "open": open_column,
        "high": high_column,
        "low": low_column,
        "close": close_column,
    }
    missing = [name for name, column in required.items() if column is None]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    selected = frame[[open_column, high_column, low_column, close_column]].copy()
    selected.columns = ["open", "high", "low", "close"]

    if volume_column:
        selected["volume"] = pd.to_numeric(frame[volume_column], errors="coerce").fillna(0.0)
    else:
        selected["volume"] = 0.0

    selected["time"] = _to_epoch_seconds(_build_timestamp_series(frame))
    for column in ["open", "high", "low", "close", "volume"]:
        selected[column] = pd.to_numeric(selected[column], errors="coerce")

    selected = selected.dropna(subset=["time", "open", "high", "low", "close"])
    selected["time"] = selected["time"].astype("int64")
    selected["volume"] = selected["volume"].fillna(0.0)
    selected = selected.sort_values("time").drop_duplicates(subset=["time"], keep="last")

    return selected[OHLCV_COLUMNS].reset_index(drop=True)


def _infer_interval_seconds(dataframe: pd.DataFrame) -> int | None:
    if len(dataframe) < 2:
        return None
    deltas = dataframe["time"].diff().dropna()
    deltas = deltas[deltas > 0]
    if deltas.empty:
        return None
    return int(deltas.median())


def _resample_to_15m(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    frame["datetime"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(IST_TIMEZONE)
    frame = frame.set_index("datetime").sort_index()
    resampled = (
        frame.resample("15min")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    resampled["time"] = (resampled["datetime"].astype("int64") // 10**9).astype("int64")
    return resampled[OHLCV_COLUMNS].reset_index(drop=True)


def _save_csv(dataframe: pd.DataFrame, path: Path) -> FetchResult:
    _ensure_data_dir()
    dataframe.to_csv(path, index=False)
    return FetchResult(
        name=path.stem,
        path=path,
        rows=len(dataframe),
        message=f"Saved {len(dataframe)} rows to {path}",
    )


def import_kaggle_csv(source_path: Path) -> FetchResult:
    if not source_path.exists():
        raise FileNotFoundError(f"Kaggle file not found: {source_path}")

    _print(f"Loading Kaggle CSV from {source_path}")
    dataframe = pd.read_csv(source_path)
    prepared = _prepare_ohlcv_frame(dataframe)
    interval_seconds = _infer_interval_seconds(prepared)

    if interval_seconds is not None and interval_seconds < 900:
        _print("Detected sub-15-minute data. Resampling to 15-minute OHLCV.")
        prepared = _resample_to_15m(prepared)
    elif interval_seconds is not None and interval_seconds > 900:
        _print(
            "Warning: Kaggle file does not appear to be 15-minute or 1-minute data. "
            "Saving normalized rows as provided."
        )

    return _save_csv(prepared, DATA_DIR / "banknifty_15m.csv")


def _candidate_futures_symbols(reference: datetime) -> list[str]:
    current_month = datetime(reference.year, reference.month, 1)
    next_month = datetime(reference.year + (1 if reference.month == 12 else 0), (reference.month % 12) + 1, 1)
    candidates = []
    for month_start in [current_month, next_month]:
        candidates.append(f"BANKNIFTY{month_start.strftime('%y').upper()}{month_start.strftime('%b').upper()}FUT")
        candidates.append(f"BANKNIFTY {month_start.strftime('%y').upper()} {month_start.strftime('%b').upper()} FUT")
        candidates.append(f"BANKNIFTY {month_start.strftime('%b').upper()} FUT")
    return candidates


def _normalize_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", symbol.upper())


def _charting_to_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    if isinstance(frame.index, pd.DatetimeIndex):
        frame = frame.reset_index()
    frame = _normalize_columns(frame)

    datetime_column = _find_column(frame, "datetime", "date", "time", "timestamp")
    open_column = _find_column(frame, "open")
    high_column = _find_column(frame, "high")
    low_column = _find_column(frame, "low")
    close_column = _find_column(frame, "close")
    volume_column = _find_column(frame, "volume")

    if None in [datetime_column, open_column, high_column, low_column, close_column]:
        raise ValueError(f"Unexpected OpenChart columns: {list(frame.columns)}")

    selected = frame[[datetime_column, open_column, high_column, low_column, close_column]].copy()
    selected.columns = ["datetime", "open", "high", "low", "close"]
    selected["volume"] = (
        pd.to_numeric(frame[volume_column], errors="coerce").fillna(0.0)
        if volume_column
        else 0.0
    )

    timestamps = pd.to_datetime(selected["datetime"], errors="coerce")
    if timestamps.dt.tz is None:
        timestamps = timestamps.dt.tz_localize(IST_TIMEZONE)
    else:
        timestamps = timestamps.dt.tz_convert(IST_TIMEZONE)

    selected["datetime"] = timestamps
    selected["time"] = (timestamps.astype("int64") // 10**9).astype("int64")
    for column in ["open", "high", "low", "close", "volume"]:
        selected[column] = pd.to_numeric(selected[column], errors="coerce")

    selected = selected.dropna(subset=["datetime", "open", "high", "low", "close"])
    selected = selected.sort_values("datetime").drop_duplicates(subset=["time"], keep="last")
    return selected[["datetime", *OHLCV_COLUMNS]].reset_index(drop=True)


def _resolve_charting_match(results: dict, requested_symbol: str, symbol_type: str) -> dict | None:
    rows = results.get("data") or []
    if not rows:
        return None

    requested_key = _normalize_symbol(requested_symbol)
    type_matches = [row for row in rows if str(row.get("type", "")).lower() == symbol_type.lower()]
    exact_matches = [row for row in type_matches if _normalize_symbol(str(row.get("symbol", ""))) == requested_key]
    if exact_matches:
        return exact_matches[0]

    contains_matches = [
        row for row in type_matches
        if requested_key in _normalize_symbol(str(row.get("symbol", "")))
        or _normalize_symbol(str(row.get("symbol", ""))) in requested_key
    ]
    if contains_matches:
        return contains_matches[0]

    return type_matches[0] if type_matches else rows[0]


def _fetch_bharat_charting_history(
    nse,
    symbol: str,
    segment: str,
    symbol_type: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    search_results = nse.search_charting_symbol(symbol, segment=segment)
    match = _resolve_charting_match(search_results, symbol, symbol_type)
    if not match:
        raise RuntimeError(f"No NSE charting match found for {symbol} in segment {segment}.")

    raw = nse.get_charting_historical_data(
        symbol=match["symbol"],
        token=match["scripcode"],
        symbol_type=symbol_type,
        chart_type="I",
        time_interval=15,
        from_date=int(start.timestamp()),
        to_date=int(end.timestamp()),
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"NSE charting returned no historical data for {match['symbol']}.")

    return _charting_to_frame(raw)


def fetch_recent_nse_charting(futures_symbol: str | None = None, lookback_days: int = 60) -> FetchResult:
    try:
        from Base.NSEBase import NSEBase
    except ImportError as exc:
        raise RuntimeError(
            "Bharat-sm-data-avinash is not installed. Run `pip install Bharat-sm-data-avinash`."
        ) from exc

    nse = NSEBase()
    end = datetime.now()
    start = end - timedelta(days=lookback_days)

    _print(f"Fetching NSE charting spot data from {start:%Y-%m-%d} to {end:%Y-%m-%d}")
    spot = _fetch_bharat_charting_history(
        nse=nse,
        symbol="NIFTY BANK",
        segment="IDX",
        symbol_type="Index",
        start=start,
        end=end,
    )

    candidate_symbols = [futures_symbol] if futures_symbol else _candidate_futures_symbols(end)
    futures_frame: pd.DataFrame | None = None
    chosen_symbol: str | None = None

    for index, symbol in enumerate(candidate_symbols):
        if not symbol:
            continue
        if index > 0:
            time.sleep(2)

        try:
            _print(f"Fetching NSE charting futures data for {symbol}")
            futures_frame = _fetch_bharat_charting_history(
                nse=nse,
                symbol=symbol,
                segment="FO",
                symbol_type="Futures",
                start=start,
                end=end,
            )
            chosen_symbol = symbol
            break
        except Exception as exc:
            _print(f"NSE charting futures fetch failed for {symbol}: {exc}")

    merged = spot.copy()
    merged["volume"] = 0.0

    if futures_frame is not None:
        aligned = pd.merge_asof(
            spot.sort_values("datetime"),
            futures_frame[["datetime", "volume"]].sort_values("datetime"),
            on="datetime",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=1),
            suffixes=("", "_fut"),
        )
        merged["volume"] = aligned["volume_fut"].fillna(0.0)
        _print(f"Using futures volume from {chosen_symbol}")
    else:
        _print("Futures volume was unavailable. Saving spot candles with zero volume.")

    return _save_csv(merged[OHLCV_COLUMNS], DATA_DIR / "banknifty_15m_recent.csv")


def fetch_daily_yfinance(period: str = "5y") -> FetchResult:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Run `pip install yfinance`.") from exc

    _print("Fetching daily BANKNIFTY data from yfinance")
    dataframe = yf.download("^NSEBANK", period=period, interval="1d", auto_adjust=False, progress=False)
    if dataframe is None or dataframe.empty:
        raise RuntimeError("yfinance returned no daily data for ^NSEBANK.")

    if isinstance(dataframe.columns, pd.MultiIndex):
        dataframe.columns = [column[0] for column in dataframe.columns]

    dataframe = dataframe.reset_index()
    dataframe = _normalize_columns(dataframe)
    dataframe = dataframe.rename(columns={"adj close": "adj_close"})

    prepared = _prepare_ohlcv_frame(dataframe)
    return _save_csv(prepared, DATA_DIR / "banknifty_daily.csv")


def _load_existing_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    dataframe = pd.read_csv(path)
    if dataframe.empty:
        return None
    frame = _normalize_columns(dataframe)
    missing = [column for column in OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
    for column in OHLCV_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["time", "open", "high", "low", "close"])
    frame["time"] = frame["time"].astype("int64")
    frame["volume"] = frame["volume"].fillna(0.0)
    return frame[OHLCV_COLUMNS].copy()


def merge_intraday_sources() -> FetchResult:
    sources = [
        DATA_DIR / "banknifty_15m.csv",
        DATA_DIR / "banknifty_15m_recent.csv",
    ]

    frames = [frame for frame in (_load_existing_csv(path) for path in sources) if frame is not None]
    if not frames:
        raise FileNotFoundError("No intraday CSVs found to merge.")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("time").drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    result = _save_csv(merged, DATA_DIR / "banknifty_15m_merged.csv")

    start = datetime.fromtimestamp(int(merged["time"].min()))
    end = datetime.fromtimestamp(int(merged["time"].max()))
    candles_with_volume = int((merged["volume"] > 0).sum())
    _print(
        "Merged summary: "
        f"{start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}, "
        f"{len(merged)} candles, {candles_with_volume} candles with volume > 0"
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and prepare BANKNIFTY historical data.")
    parser.add_argument("--kaggle", type=Path, help="Path to a downloaded Kaggle CSV file.")
    parser.add_argument("--recent", action="store_true", help="Fetch recent 15-minute data via NSE charting.")
    parser.add_argument(
        "--openchart",
        action="store_true",
        help="Deprecated alias for --recent. Kept for compatibility.",
    )
    parser.add_argument("--futures-symbol", help="Explicit BANKNIFTY futures symbol for recent volume.")
    parser.add_argument("--daily", action="store_true", help="Fetch daily data via yfinance.")
    parser.add_argument("--merge", action="store_true", help="Merge existing intraday sources.")
    parser.add_argument("--all", action="store_true", help="Run Kaggle import (if provided), recent fetch, daily, and merge.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not any([args.kaggle, args.recent, args.openchart, args.daily, args.merge, args.all]):
        _print("Nothing to do. Use --help to see available commands.")
        return 1

    exit_code = 0

    def run_step(name: str, fn) -> None:
        nonlocal exit_code
        try:
            result = fn()
            _print(result.message)
        except Exception as exc:
            exit_code = 1
            _print(f"{name} failed: {exc}")

    if args.kaggle:
        run_step("Kaggle import", lambda: import_kaggle_csv(args.kaggle))

    if args.recent or args.openchart or args.all:
        run_step("Recent NSE charting fetch", lambda: fetch_recent_nse_charting(args.futures_symbol))

    if args.daily or args.all:
        run_step("Daily fetch", fetch_daily_yfinance)

    if args.merge or args.all:
        run_step("Merge", merge_intraday_sources)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
