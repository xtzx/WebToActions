from __future__ import annotations

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

from app.session.domain.browser_session import BrowserSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    pass


@router.get("")
def list_sessions(request: Request) -> dict[str, list[dict[str, object]]]:
    manager = request.app.state.browser_session_manager
    sessions = manager.list_sessions()
    return {"items": [_serialize_session(item) for item in sessions]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    _payload: CreateSessionRequest,
    request: Request,
) -> dict[str, object]:
    manager = request.app.state.browser_session_manager
    session = manager.create_session()
    return _serialize_session(session)


def _serialize_session(item: BrowserSession) -> dict[str, object]:
    return {
        "id": item.id,
        "profileId": item.profile_id,
        "status": item.status.value,
        "loginSiteSummaries": list(item.login_site_summaries),
        "createdAt": item.created_at.isoformat(),
        "lastActivityAt": item.last_activity_at.isoformat(),
    }
