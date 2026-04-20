from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

PLAYWRIGHT_IMPORT_ERROR: Exception | None = None

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    PLAYWRIGHT_IMPORT_ERROR = exc
    PlaywrightError = Exception  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page, Playwright
else:
    BrowserContext = Page = Playwright = Any


@dataclass(frozen=True)
class ReplayRequestStep:
    id: str
    title: str
    request_id: str
    request_method: str
    request_url: str
    request_headers: tuple[tuple[str, str], ...]
    request_body_text: str | None
    navigate_url: str | None


class ReplayCallbacks(Protocol):
    def on_log(
        self,
        *,
        message: str,
        step_id: str | None = None,
        step_title: str | None = None,
        current_url: str | None = None,
    ) -> None: ...


class BrowserReplayer(Protocol):
    def replay(
        self,
        *,
        profile_dir: Path,
        steps: tuple[ReplayRequestStep, ...],
        callbacks: ReplayCallbacks,
    ) -> dict[str, object]: ...


class PlaywrightBrowserReplayer:
    def __init__(self, *, browser_channel: str, browser_headless: bool) -> None:
        self._browser_channel = browser_channel
        self._browser_headless = browser_headless

    def replay(
        self,
        *,
        profile_dir: Path,
        steps: tuple[ReplayRequestStep, ...],
        callbacks: ReplayCallbacks,
    ) -> dict[str, object]:
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright Python is not installed. Run "
                "\"python -m pip install -e './backend[dev]'\" and "
                "\"playwright install chromium\" first."
            ) from PLAYWRIGHT_IMPORT_ERROR

        playwright = sync_playwright().start()
        context: BrowserContext | None = None
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile_dir),
                **_launch_kwargs(
                    browser_channel=self._browser_channel,
                    browser_headless=self._browser_headless,
                ),
            )
            page = context.pages[0] if context.pages else context.new_page()
            return _replay_steps(page=page, steps=steps, callbacks=callbacks)
        finally:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            playwright.stop()


def _launch_kwargs(*, browser_channel: str, browser_headless: bool) -> dict[str, Any]:
    launch_kwargs: dict[str, Any] = {"headless": browser_headless}
    if browser_channel and browser_channel != "chromium":
        launch_kwargs["channel"] = browser_channel
    return launch_kwargs


def _replay_steps(
    *,
    page: Page,
    steps: tuple[ReplayRequestStep, ...],
    callbacks: ReplayCallbacks,
) -> dict[str, object]:
    step_outcomes: list[dict[str, object]] = []
    current_url: str | None = None

    for step in steps:
        if step.navigate_url:
            callbacks.on_log(
                message=f"打开页面 {step.navigate_url}",
                step_id=step.id,
                step_title=step.title,
                current_url=step.navigate_url,
            )
            page.goto(step.navigate_url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("load", timeout=10_000)
            except PlaywrightError:
                pass
            current_url = step.navigate_url

        callbacks.on_log(
            message=f"开始执行 {step.title}",
            step_id=step.id,
            step_title=step.title,
            current_url=current_url or str(getattr(page, "url", "")) or step.request_url,
        )
        result = page.evaluate(
            """
            async ({ url, method, headers, body }) => {
              const response = await fetch(url, {
                method,
                headers,
                body: body ?? undefined,
                credentials: 'include'
              });
              const text = await response.text();
              return {
                status: response.status,
                bodyPreview: text.slice(0, 400)
              };
            }
            """,
            {
                "url": step.request_url,
                "method": step.request_method,
                "headers": dict(step.request_headers),
                "body": step.request_body_text,
            },
        )
        current_url = str(getattr(page, "url", "")) or current_url or step.request_url
        callbacks.on_log(
            message=f"完成执行 {step.title}",
            step_id=step.id,
            step_title=step.title,
            current_url=current_url,
        )
        outcome = {
            "stepId": step.id,
            "requestId": step.request_id,
            "requestBodyPreview": step.request_body_text,
            "responseStatus": int(result.get("status", 0)),
            "responseBodyPreview": result.get("bodyPreview"),
        }
        if outcome["responseStatus"] >= 400:
            raise RuntimeError(f"步骤执行失败：{step.title} -> HTTP {outcome['responseStatus']}")
        step_outcomes.append(outcome)

    return {
        "finalUrl": current_url,
        "stepOutcomes": step_outcomes,
    }
