from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.core.domain_model import DomainModel


class BrowserSessionStatus(StrEnum):
    AVAILABLE = "available"
    RELOGIN_REQUIRED = "relogin_required"
    EXPIRED = "expired"


class BrowserSession(DomainModel):
    id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    status: BrowserSessionStatus = BrowserSessionStatus.AVAILABLE
    login_site_summaries: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_activity_timestamps(self) -> Self:
        if self.last_activity_at < self.created_at:
            raise ValueError("last_activity_at cannot be earlier than created_at.")

        return self

    def _transition(
        self,
        *,
        allowed_from: set[BrowserSessionStatus],
        next_status: BrowserSessionStatus,
    ) -> Self:
        if self.status not in allowed_from:
            raise ValueError(
                f"Cannot transition browser session from {self.status.value} "
                f"to {next_status.value}.",
            )

        return self.validated_copy(
            status=next_status,
            last_activity_at=datetime.now(UTC),
        )

    def require_relogin(self) -> Self:
        return self._transition(
            allowed_from={BrowserSessionStatus.AVAILABLE},
            next_status=BrowserSessionStatus.RELOGIN_REQUIRED,
        )

    def restore(self) -> Self:
        return self._transition(
            allowed_from={BrowserSessionStatus.RELOGIN_REQUIRED},
            next_status=BrowserSessionStatus.AVAILABLE,
        )

    def expire(self) -> Self:
        return self._transition(
            allowed_from={
                BrowserSessionStatus.AVAILABLE,
                BrowserSessionStatus.RELOGIN_REQUIRED,
            },
            next_status=BrowserSessionStatus.EXPIRED,
        )
