from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes.health import router as health_router
from app.action.api.routes.actions import router as actions_router
from app.action.service.action_orchestrator import ActionOrchestrator
from app.browser.playwright_bridge import BrowserBridge, PlaywrightBridge
from app.core import get_settings
from app.core.config import Settings
from app.evidence.service.evidence_writer import EvidenceWriter
from app.execution.api.routes.executions import router as executions_router
from app.execution.service.browser_replayer import (
    BrowserReplayer,
    PlaywrightBrowserReplayer,
)
from app.execution.service.execution_service import ExecutionService
from app.importexport.api.routes.importexport import router as importexport_router
from app.importexport.service.export_service import ExportService
from app.importexport.service.import_service import ImportService
from app.infrastructure.db.action_repository import SqliteActionMacroRepository
from app.infrastructure.db.execution_repository import SqliteExecutionRunRepository
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
BrowserReplayerFactory = Callable[[Settings], BrowserReplayer]


def _default_browser_bridge_factory(settings: Settings) -> BrowserBridge:
    return PlaywrightBridge(
        browser_channel=settings.browser_channel,
        browser_headless=settings.browser_headless,
    )


def _default_browser_replayer_factory(settings: Settings) -> BrowserReplayer:
    return PlaywrightBrowserReplayer(
        browser_channel=settings.browser_channel,
        browser_headless=settings.browser_headless,
    )


def _maybe_register_frontend_runtime_routes(app: FastAPI, settings: Settings) -> None:
    if not settings.frontend_static_enabled:
        return

    dist_dir = settings.frontend_dist_dir
    index_path = dist_dir / "index.html"
    if not dist_dir.exists() or not index_path.exists():
        return

    api_prefix = settings.api_prefix.lstrip("/")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index() -> FileResponse:
        return FileResponse(index_path)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_path(full_path: str) -> FileResponse:
        if full_path == api_prefix or full_path.startswith(f"{api_prefix}/"):
            raise HTTPException(status_code=404, detail="API route not found.")

        asset_path = _resolve_frontend_asset_path(dist_dir, full_path)
        if asset_path is not None and asset_path.is_file():
            return FileResponse(asset_path)
        if PurePosixPath(full_path).suffix:
            raise HTTPException(status_code=404, detail="Frontend asset not found.")
        return FileResponse(index_path)


def _resolve_frontend_asset_path(dist_dir: Path, full_path: str) -> Path | None:
    candidate = (dist_dir / Path(full_path)).resolve()
    try:
        candidate.relative_to(dist_dir.resolve())
    except ValueError:
        return None
    return candidate


def create_app(
    *,
    browser_bridge_factory: BrowserBridgeFactory | None = None,
    browser_replayer_factory: BrowserReplayerFactory | None = None,
) -> FastAPI:
    settings = get_settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        storage_layout = bootstrap_storage_layout(settings.webtoactions_data_dir)
        sqlite_runtime = initialize_sqlite_runtime(storage_layout.database_path)
        recording_repository = SqliteRecordingRepository(sqlite_runtime.session_factory)
        session_repository = SqliteBrowserSessionRepository(sqlite_runtime.session_factory)
        action_repository = SqliteActionMacroRepository(
            sqlite_runtime.session_factory,
            storage_layout=storage_layout,
        )
        execution_repository = SqliteExecutionRunRepository(
            sqlite_runtime.session_factory,
            storage_layout=storage_layout,
        )
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
        action_orchestrator = ActionOrchestrator(
            recording_repository=recording_repository,
            action_repository=action_repository,
        )
        execution_service = ExecutionService(
            action_repository=action_repository,
            recording_repository=recording_repository,
            execution_repository=execution_repository,
            session_manager=session_manager,
            browser_replayer=(browser_replayer_factory or _default_browser_replayer_factory)(
                settings
            ),
            storage_root=storage_layout.root,
        )
        importexport_export_service = ExportService(
            recording_repository=recording_repository,
            action_repository=action_repository,
            execution_repository=execution_repository,
            storage_layout=storage_layout,
        )
        importexport_import_service = ImportService(
            recording_repository=recording_repository,
            action_repository=action_repository,
            execution_repository=execution_repository,
            session_manager=session_manager,
            session_factory=sqlite_runtime.session_factory,
            storage_root=storage_layout.root,
        )
        app.state.storage_layout = storage_layout
        app.state.sqlite_runtime = sqlite_runtime
        app.state.recording_repository = recording_repository
        app.state.browser_session_repository = session_repository
        app.state.action_repository = action_repository
        app.state.execution_repository = execution_repository
        app.state.browser_session_manager = session_manager
        app.state.recorder_orchestrator = recorder_orchestrator
        app.state.review_service = review_service
        app.state.review_job_runner = review_job_runner
        app.state.action_orchestrator = action_orchestrator
        app.state.execution_service = execution_service
        app.state.importexport_export_service = importexport_export_service
        app.state.importexport_import_service = importexport_import_service
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
    app.include_router(actions_router, prefix=settings.api_prefix)
    app.include_router(executions_router, prefix=settings.api_prefix)
    app.include_router(importexport_router, prefix=settings.api_prefix)
    _maybe_register_frontend_runtime_routes(app, settings)
    return app


app = create_app()
