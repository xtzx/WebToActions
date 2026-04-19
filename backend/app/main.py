from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.browser.playwright_bridge import BrowserBridge, PlaywrightBridge
from app.core import get_settings
from app.core.config import Settings
from app.evidence.service.evidence_writer import EvidenceWriter
from app.evidence.service.session_state_collector import SessionStateCollector
from app.infrastructure.db.recording_repository import SqliteRecordingRepository
from app.infrastructure.db.session_repository import SqliteBrowserSessionRepository
from app.infrastructure.db.runtime import initialize_sqlite_runtime
from app.infrastructure.storage.storage_bootstrap import bootstrap_storage_layout
from app.recording.api.routes.recordings import router as recordings_router
from app.recording.service.recorder_orchestrator import (
    RecorderOrchestrator,
    RecordingEventBroker,
)
from app.review.api.routes.reviews import router as reviews_router
from app.review.service.metadata_analysis_service import MetadataAnalysisService
from app.review.service.review_job_runner import ReviewJobRunner
from app.review.service.review_service import ReviewService
from app.session.api.routes.sessions import router as sessions_router
from app.session.service.browser_session_manager import BrowserSessionManager


BrowserBridgeFactory = Callable[[Settings], BrowserBridge]


def _default_browser_bridge_factory(settings: Settings) -> BrowserBridge:
    return PlaywrightBridge(
        browser_channel=settings.browser_channel,
        browser_headless=settings.browser_headless,
    )


def create_app(
    *,
    browser_bridge_factory: BrowserBridgeFactory | None = None,
) -> FastAPI:
    settings = get_settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage_layout = bootstrap_storage_layout(settings.webtoactions_data_dir)
        sqlite_runtime = initialize_sqlite_runtime(storage_layout.database_path)
        recording_repository = SqliteRecordingRepository(sqlite_runtime.session_factory)
        session_repository = SqliteBrowserSessionRepository(sqlite_runtime.session_factory)
        session_manager = BrowserSessionManager(
            repository=session_repository,
            profiles_root=storage_layout.root / "profiles",
        )
        recorder_orchestrator = RecorderOrchestrator(
            browser_bridge=(browser_bridge_factory or _default_browser_bridge_factory)(
                settings
            ),
            session_manager=session_manager,
            recording_repository=recording_repository,
            evidence_writer=EvidenceWriter(storage_layout=storage_layout),
            session_state_collector=SessionStateCollector(),
            event_broker=RecordingEventBroker(),
        )
        review_service = ReviewService(recording_repository=recording_repository)
        review_job_runner = ReviewJobRunner(
            metadata_analysis_service=MetadataAnalysisService(
                recording_repository=recording_repository,
                storage_root=storage_layout.root,
            ),
            recording_repository=recording_repository,
        )
        app.state.storage_layout = storage_layout
        app.state.sqlite_runtime = sqlite_runtime
        app.state.recording_repository = recording_repository
        app.state.browser_session_repository = session_repository
        app.state.browser_session_manager = session_manager
        app.state.recorder_orchestrator = recorder_orchestrator
        app.state.review_service = review_service
        app.state.review_job_runner = review_job_runner
        try:
            yield
        finally:
            sqlite_runtime.engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(sessions_router, prefix=settings.api_prefix)
    app.include_router(recordings_router, prefix=settings.api_prefix)
    app.include_router(reviews_router, prefix=settings.api_prefix)
    return app


app = create_app()
