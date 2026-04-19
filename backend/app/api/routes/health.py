from fastapi import APIRouter

from app.core import get_settings


router = APIRouter(tags=["system"])


@router.get("/health")
def get_health() -> dict[str, str | bool]:
    settings = get_settings()

    return {
        "status": "ok",
        "phase": "stage4",
        "appName": settings.app_name,
        "environment": settings.app_env,
        "apiPrefix": settings.api_prefix,
        "targetPython": settings.target_python,
        "runtimePython": settings.runtime_python,
        "dataDir": settings.data_dir_display,
        "browserChannel": settings.browser_channel,
        "browserHeadless": settings.browser_headless,
    }
