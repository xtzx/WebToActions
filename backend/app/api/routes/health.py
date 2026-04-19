from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def get_health() -> dict[str, str]:
    return {
        "status": "ok",
        "stage": "spike",
    }


@router.get("/spike/context")
def get_spike_context() -> dict[str, str]:
    return {
        "stage": "spike",
        "targetPython": "3.11+",
        "runtimePython": "3.10.0",
        "browserEngine": "playwright",
    }
