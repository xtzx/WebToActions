from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlparse

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


class RecordingCallbacks(Protocol):
    def on_navigation(self, *, url: str, title: str | None) -> None: ...

    def on_request(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
        resource_type: str,
        is_navigation_request: bool,
    ) -> None: ...

    def on_response(
        self,
        *,
        request_id: str,
        status: int,
        status_text: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
    ) -> None: ...

    def on_request_failed(self, *, request_id: str, reason: str) -> None: ...

    def on_upload(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None: ...

    def on_download(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None: ...


class BrowserRecordingHandle(Protocol):
    def stop(self) -> dict[str, Any]: ...


class BrowserBridge(Protocol):
    def start_recording(
        self,
        *,
        profile_dir: Path,
        start_url: str,
        callbacks: RecordingCallbacks,
    ) -> BrowserRecordingHandle: ...


class PlaywrightBridge:
    def __init__(self, *, browser_channel: str, browser_headless: bool) -> None:
        self._browser_channel = browser_channel
        self._browser_headless = browser_headless

    def start_recording(
        self,
        *,
        profile_dir: Path,
        start_url: str,
        callbacks: RecordingCallbacks,
    ) -> BrowserRecordingHandle:
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright Python is not installed. Run "
                "\"python -m pip install -e './backend[dev]'\" and "
                "\"playwright install chromium\" first."
            ) from PLAYWRIGHT_IMPORT_ERROR

        playwright = sync_playwright().start()
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile_dir),
                **_launch_kwargs(
                    browser_channel=self._browser_channel,
                    browser_headless=self._browser_headless,
                ),
            )
            page = context.pages[0] if context.pages else context.new_page()
            _register_page_callbacks(page=page, callbacks=callbacks)
            page.goto(start_url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("load", timeout=10_000)
            except PlaywrightError:
                pass
        except Exception:
            playwright.stop()
            raise

        return _PlaywrightRecordingHandle(
            playwright=playwright,
            context=context,
            page=page,
        )


@dataclass
class _PlaywrightRecordingHandle:
    playwright: Playwright
    context: BrowserContext
    page: Page

    def stop(self) -> dict[str, Any]:
        snapshot = _capture_browser_snapshot(context=self.context, page=self.page)
        try:
            self.context.close()
        finally:
            self.playwright.stop()
        return snapshot


def _launch_kwargs(*, browser_channel: str, browser_headless: bool) -> dict[str, Any]:
    launch_kwargs: dict[str, Any] = {"headless": browser_headless}
    if browser_channel and browser_channel != "chromium":
        launch_kwargs["channel"] = browser_channel
    return launch_kwargs


def _register_page_callbacks(*, page: Page, callbacks: RecordingCallbacks) -> None:
    request_ids: dict[int, str] = {}
    request_counter = 0
    transfer_counter = 0

    def next_request_id() -> str:
        nonlocal request_counter
        request_counter += 1
        return f"req-{request_counter}"

    def next_transfer_id(prefix: str) -> str:
        nonlocal transfer_counter
        transfer_counter += 1
        return f"{prefix}-{transfer_counter}"

    def on_request(request: Any) -> None:
        request_id = next_request_id()
        request_ids[id(request)] = request_id
        callbacks.on_request(
            request_id=request_id,
            method=str(_read_member(request, "method", "")),
            url=str(_read_member(request, "url", "")),
            headers=_header_items(_all_headers(request)),
            body=_request_body_bytes(request),
            resource_type=str(_read_member(request, "resource_type", "unknown")),
            is_navigation_request=bool(
                _read_member(request, "is_navigation_request", False)
            ),
        )

    def on_response(response: Any) -> None:
        request = _read_member(response, "request")
        request_id = request_ids.get(id(request))
        if request_id is None:
            return
        callbacks.on_response(
            request_id=request_id,
            status=int(_read_member(response, "status", 0)),
            status_text=str(_read_member(response, "status_text", "")),
            headers=_header_items(_all_headers(response)),
            body=_response_body_bytes(response),
        )

    def on_request_failed(request: Any) -> None:
        request_id = request_ids.get(id(request))
        if request_id is None:
            return
        failure = _read_member(request, "failure", {})
        if isinstance(failure, dict):
            reason = str(failure.get("errorText") or failure.get("error") or "request_failed")
        else:
            reason = str(failure or "request_failed")
        callbacks.on_request_failed(request_id=request_id, reason=reason)

    def on_frame_navigated(frame: Any) -> None:
        main_frame = _read_member(page, "main_frame")
        if main_frame is not None and frame != main_frame:
            return
        callbacks.on_navigation(
            url=str(_read_member(frame, "url", "")),
            title=_safe_page_title(page),
        )

    def on_download(download: Any) -> None:
        callbacks.on_download(
            transfer_id=next_transfer_id("download"),
            file_name=str(_read_member(download, "suggested_filename", "download.bin")),
            related_request_id=None,
        )

    def on_filechooser(_file_chooser: Any) -> None:
        callbacks.on_upload(
            transfer_id=next_transfer_id("upload"),
            file_name="manual-upload",
            related_request_id=None,
        )

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_request_failed)
    page.on("framenavigated", on_frame_navigated)
    page.on("download", on_download)
    page.on("filechooser", on_filechooser)


def _capture_browser_snapshot(*, context: BrowserContext, page: Page) -> dict[str, Any]:
    storage_state = context.storage_state()
    cookies = storage_state.get("cookies", []) or []
    cookie_domains = sorted(
        {
            str(cookie.get("domain"))
            for cookie in cookies
            if cookie.get("domain")
        }
    )

    page_state = _capture_page_storage(page)
    current_url = str(_read_member(page, "url", ""))
    netloc = urlparse(current_url).netloc
    login_sites = cookie_domains or ([netloc] if netloc else [])

    return {
        "currentUrl": current_url,
        "pageTitle": _safe_page_title(page),
        "cookieSummary": {
            "count": str(len(cookies)),
            "domains": ",".join(cookie_domains),
        },
        "storageSummary": page_state,
        "loginSiteSummaries": login_sites,
    }


def _capture_page_storage(page: Page) -> dict[str, dict[str, str]]:
    try:
        result = page.evaluate(
            """
            () => ({
              localStorage: { itemCount: String(window.localStorage.length) },
              sessionStorage: { itemCount: String(window.sessionStorage.length) },
            })
            """
        )
    except Exception:
        return {}

    if not isinstance(result, dict):
        return {}

    payload: dict[str, dict[str, str]] = {}
    for key, value in result.items():
        if isinstance(value, dict):
            payload[str(key)] = {
                str(inner_key): str(inner_value)
                for inner_key, inner_value in value.items()
            }
    return payload


def _all_headers(obj: Any) -> Any:
    headers_method = getattr(obj, "all_headers", None)
    if callable(headers_method):
        try:
            return headers_method()
        except Exception:
            pass
    return _read_member(obj, "headers", {})


def _header_items(value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, dict):
        return []
    return [(str(key), str(item)) for key, item in value.items()]


def _request_body_bytes(request: Any) -> bytes | None:
    payload = _read_member(request, "post_data_buffer")
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    payload = _read_member(request, "post_data")
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return None


def _response_body_bytes(response: Any) -> bytes | None:
    payload = _read_member(response, "body")
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    return None


def _safe_page_title(page: Page) -> str | None:
    try:
        return page.title()
    except Exception:
        return None


def _read_member(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return default
        except Exception:
            return default
    return value
