from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import Base, engine, get_db_session
from app.schemas import AnalysisResponse, FeedbackMetrics, JournalEntry
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.feedback_engine import FeedbackEngine
from app.services.journal_service import JournalService
from app.services.realtime_manager import RealtimeManager

settings = get_settings()
pipeline = AnalysisPipeline()
journal_service = JournalService()
feedback_engine = FeedbackEngine()
realtime_manager = RealtimeManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.get(f"{settings.api_v1_prefix}/analysis", response_model=AnalysisResponse)
async def get_analysis(
    timeframe: str = Query(default="15m", pattern="^(1d|15m|5m)$"),
    session: AsyncSession = Depends(get_db_session),
):
    analysis = await pipeline.analyze(timeframe)
    strategy_name = next(
        (
            reason
            for reason in analysis.signal.reasons
            if reason in {"Trend Pullback", "Breakout", "Reversal", "Range"}
        ),
        "Observation",
    )
    await journal_service.record_signal(session, analysis.signal, strategy_name, analysis.regime)
    return analysis


@app.get(f"{settings.api_v1_prefix}/journal", response_model=list[JournalEntry])
async def get_journal(session: AsyncSession = Depends(get_db_session)):
    return await journal_service.list_entries(session)


@app.get(f"{settings.api_v1_prefix}/feedback", response_model=FeedbackMetrics)
async def get_feedback(session: AsyncSession = Depends(get_db_session)):
    return await feedback_engine.summarize(session)


@app.websocket("/ws/live")
async def live_updates(websocket: WebSocket):
    await realtime_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            await realtime_manager.push_snapshot()
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)

