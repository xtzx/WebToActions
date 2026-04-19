from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import uuid4

PLAYWRIGHT_IMPORT_ERROR: Exception | None = None

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local environment
    PLAYWRIGHT_IMPORT_ERROR = exc
    PlaywrightError = Exception  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from playwright.sync_api import Request
    from playwright.sync_api import Response
else:
    Page = Request = Response = Any


LOGGER = logging.getLogger("webtoactions.spike.browser_recording")
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".webtoactions" / "spikes" / "recordings"
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-csrf-token",
    "x-xsrf-token",
}


@dataclass
class PocConfig:
    url: str
    headed: bool
    capture_wait_ms: int
    hold_open_ms: int
    timeout_ms: int
    output_dir: Path
    ignore_https_errors: bool
    browser_channel: str | None
    browser_path: Path | None


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a minimal Playwright browser session summary for stage 0 Spike.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Target URL to open.",
    )
    parser.add_argument(
        "--url",
        dest="url_option",
        help="Target URL to open. Optional alias for the positional url.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Launch a visible browser window instead of the default headless mode.",
    )
    parser.add_argument(
        "--browser-channel",
        choices=[
            "chromium",
            "chrome",
            "chrome-beta",
            "chrome-dev",
            "chrome-canary",
            "msedge",
            "msedge-beta",
            "msedge-dev",
            "msedge-canary",
        ],
        help=(
            "Use an installed browser channel instead of Playwright managed Chromium, "
            "for example: chrome or msedge."
        ),
    )
    parser.add_argument(
        "--browser-path",
        type=Path,
        help="Use a custom browser executable path.",
    )
    parser.add_argument(
        "--capture-wait-ms",
        type=int,
        default=2000,
        help="Extra wait after page load for late network requests to settle.",
    )
    parser.add_argument(
        "--hold-open-ms",
        type=int,
        default=0,
        help="Keep the page open for manual interaction before final capture.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30000,
        help="Navigation and page load timeout in milliseconds.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory used to store JSON recording outputs.",
    )
    parser.add_argument(
        "--ignore-https-errors",
        action="store_true",
        help="Ignore HTTPS certificate errors inside the browser context.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity for the PoC script.",
    )
    return parser


def parse_args() -> tuple[PocConfig, str]:
    parser = build_argument_parser()
    args = parser.parse_args()

    url = args.url_option or args.url
    if not url:
        parser.error("A target URL is required. Use positional url or --url.")

    if args.browser_channel and args.browser_path:
        parser.error("Use either --browser-channel or --browser-path, not both.")

    return (
        PocConfig(
            url=url,
            headed=args.headed,
            capture_wait_ms=args.capture_wait_ms,
            hold_open_ms=args.hold_open_ms,
            timeout_ms=args.timeout_ms,
            output_dir=args.output_dir,
            ignore_https_errors=args.ignore_https_errors,
            browser_channel=args.browser_channel,
            browser_path=args.browser_path,
        ),
        args.log_level,
    )


def main() -> int:
    config, log_level = parse_args()
    configure_logging(log_level)
    recording, output_path = run_capture(config)
    print(f"Recording saved to {output_path}")
    return 0 if recording["status"] == "ok" else 1


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def run_capture(config: PocConfig) -> tuple[dict[str, Any], Path]:
    output_dir = resolve_output_dir(config.output_dir)
    recording_id = uuid4().hex
    output_path = build_output_path(output_dir, config.url, recording_id)

    recording: dict[str, Any] = {
        "recordingId": recording_id,
        "stage": "spike",
        "recordingType": "browser_recording_poc",
        "status": "running",
        "targetUrl": config.url,
        "startedAt": utc_now(),
        "finishedAt": None,
        "artifactPath": str(output_path),
        "browserContext": {
            "browser": determine_browser_label(config),
            "headless": not config.headed,
            "isolation": "browser.new_context()",
            "ignoreHttpsErrors": config.ignore_https_errors,
            "launchChannel": config.browser_channel,
            "executablePath": (
                str(resolve_browser_path(config.browser_path))
                if config.browser_path is not None
                else None
            ),
        },
        "input": {
            "captureWaitMs": config.capture_wait_ms,
            "holdOpenMs": config.hold_open_ms,
            "timeoutMs": config.timeout_ms,
        },
        "navigation": {
            "initialResponse": None,
            "events": [],
            "finalPage": None,
        },
        "network": {
            "requestCount": 0,
            "responseCount": 0,
            "failedRequestCount": 0,
            "resourceTypes": [],
            "statusGroups": [],
            "entries": [],
        },
        "sessionState": {
            "cookies": {},
            "localStorage": {},
            "sessionStorage": {},
            "currentPage": {},
        },
        "runtime": {
            "pythonVersion": sys.version.split()[0],
            "engine": "playwright",
        },
        "error": None,
    }

    if sync_playwright is None:
        recording["status"] = "error"
        recording["finishedAt"] = utc_now()
        recording["error"] = {
            "type": "ModuleNotFoundError",
            "message": (
                "Playwright Python is not installed. Run "
                "\"python3 -m pip install -e './backend[dev]'\" from repo root. "
                "If you want the default bundled browser, also run "
                "\"./.venv/bin/playwright install chromium\"."
            ),
        }
        write_recording(recording, output_path)
        return recording, output_path

    network_entries: list[dict[str, Any]] = []
    entries_by_request_id: dict[int, dict[str, Any]] = {}
    navigation_events: list[dict[str, Any]] = []

    browser = None
    context = None
    page = None

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(
                    **build_launch_kwargs(config),
                )
                context = browser.new_context(
                    ignore_https_errors=config.ignore_https_errors,
                )
                page = context.new_page()
                page.set_default_timeout(config.timeout_ms)

                register_page_observers(
                    page=page,
                    network_entries=network_entries,
                    entries_by_request_id=entries_by_request_id,
                    navigation_events=navigation_events,
                )

                initial_response = page.goto(
                    config.url,
                    wait_until="domcontentloaded",
                    timeout=config.timeout_ms,
                )

                if initial_response is not None:
                    recording["navigation"]["initialResponse"] = summarize_response(
                        initial_response,
                    )

                page.wait_for_load_state("load", timeout=config.timeout_ms)

                if config.capture_wait_ms > 0:
                    page.wait_for_timeout(config.capture_wait_ms)

                if config.hold_open_ms > 0:
                    LOGGER.info(
                        "Holding browser open for %s ms for manual interaction.",
                        config.hold_open_ms,
                    )
                    page.wait_for_timeout(config.hold_open_ms)

                recording["status"] = "ok"
            except PlaywrightError as exc:
                recording["status"] = "error"
                recording["error"] = {
                    "type": exc.__class__.__name__,
                    "message": explain_playwright_error(exc, config),
                }
            except Exception as exc:  # pragma: no cover - runtime-only path
                recording["status"] = "error"
                recording["error"] = {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                }
            finally:
                recording["finishedAt"] = utc_now()
                recording["navigation"]["events"] = navigation_events
                recording["network"] = build_network_summary(network_entries)

                if page is not None:
                    recording["navigation"]["finalPage"] = summarize_page(page)
                    current_page_state = capture_current_page_state(page)
                    recording["sessionState"]["currentPage"] = current_page_state
                    recording["sessionState"]["sessionStorage"] = current_page_state.get(
                        "sessionStorage",
                        {},
                    )

                if context is not None:
                    try:
                        storage_state = context.storage_state()
                    except Exception as exc:  # pragma: no cover - runtime-only path
                        recording["sessionState"]["cookies"] = {
                            "error": {
                                "type": exc.__class__.__name__,
                                "message": str(exc),
                            }
                        }
                        recording["sessionState"]["localStorage"] = {
                            "error": {
                                "type": exc.__class__.__name__,
                                "message": str(exc),
                            }
                        }
                    else:
                        cookies = storage_state.get("cookies", []) or []
                        origins = storage_state.get("origins", []) or []
                        recording["sessionState"]["cookies"] = summarize_cookies(cookies)
                        recording["sessionState"]["localStorage"] = summarize_local_storage(
                            origins,
                        )

                    try:
                        context.close()
                    except Exception as exc:  # pragma: no cover - cleanup-only path
                        LOGGER.warning("Failed to close browser context cleanly: %s", exc)

                if browser is not None:
                    try:
                        browser.close()
                    except Exception as exc:  # pragma: no cover - cleanup-only path
                        LOGGER.warning("Failed to close browser cleanly: %s", exc)
    except Exception as exc:  # pragma: no cover - unexpected startup path
        recording["status"] = "error"
        if recording["finishedAt"] is None:
            recording["finishedAt"] = utc_now()
        if recording["error"] is None:
            recording["error"] = {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }

    write_recording(recording, output_path)
    return recording, output_path


def register_page_observers(
    *,
    page: Page,
    network_entries: list[dict[str, Any]],
    entries_by_request_id: dict[int, dict[str, Any]],
    navigation_events: list[dict[str, Any]],
) -> None:
    def on_request(request: Request) -> None:
        entry = summarize_request(
            request=request,
            request_id=f"req-{len(network_entries) + 1:04d}",
        )
        network_entries.append(entry)
        entries_by_request_id[id(request)] = entry

    def on_response(response: Response) -> None:
        request = read_member(response, "request")
        entry = entries_by_request_id.get(id(request))
        if entry is None:
            return
        entry["response"] = summarize_response(response)

    def on_request_failed(request: Request) -> None:
        entry = entries_by_request_id.get(id(request))
        if entry is None:
            return
        entry["failure"] = summarize_failure(request)

    def on_frame_navigated(frame: Any) -> None:
        main_frame = read_member(page, "main_frame")
        if main_frame is not None and frame != main_frame:
            return
        navigation_events.append(
            {
                "url": read_member(frame, "url"),
                "name": read_member(frame, "name"),
                "observedAt": utc_now(),
            }
        )

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_request_failed)
    page.on("framenavigated", on_frame_navigated)


def build_launch_kwargs(config: PocConfig) -> dict[str, Any]:
    launch_kwargs: dict[str, Any] = {
        "headless": not config.headed,
    }

    if config.browser_channel is not None:
        launch_kwargs["channel"] = config.browser_channel

    if config.browser_path is not None:
        launch_kwargs["executable_path"] = str(resolve_browser_path(config.browser_path))

    return launch_kwargs


def determine_browser_label(config: PocConfig) -> str:
    if config.browser_path is not None:
        return "custom-browser"

    if config.browser_channel is not None:
        return config.browser_channel

    return "chromium"


def explain_playwright_error(exc: Exception, config: PocConfig) -> str:
    message = str(exc)

    if "Executable doesn't exist" in message and config.browser_channel is None and config.browser_path is None:
        return (
            f"{message}\n\n"
            "Default Playwright Chromium is not installed. Run "
            "\"./.venv/bin/playwright install chromium\", or use "
            "\"--browser-channel chrome\" to launch your locally installed Chrome."
        )

    return message


def summarize_request(*, request: Request, request_id: str) -> dict[str, Any]:
    return {
        "id": request_id,
        "url": read_member(request, "url"),
        "method": read_member(request, "method"),
        "resourceType": read_member(request, "resource_type"),
        "isNavigationRequest": bool(read_member(request, "is_navigation_request", False)),
        "requestHeaderKeys": sanitize_header_keys(read_member(request, "headers", {})),
        "postDataBytes": compute_post_data_bytes(read_member(request, "post_data")),
        "observedAt": utc_now(),
        "response": None,
        "failure": None,
    }


def summarize_response(response: Response) -> dict[str, Any]:
    return {
        "url": read_member(response, "url"),
        "status": read_member(response, "status"),
        "statusText": read_member(response, "status_text"),
        "ok": bool(read_member(response, "ok", False)),
        "fromServiceWorker": bool(read_member(response, "from_service_worker", False)),
        "responseHeaderKeys": sanitize_header_keys(read_member(response, "headers", {})),
        "observedAt": utc_now(),
    }


def summarize_failure(request: Request) -> dict[str, Any]:
    failure_value = read_member(request, "failure")

    if isinstance(failure_value, dict):
        message = (
            failure_value.get("errorText")
            or failure_value.get("error")
            or json.dumps(failure_value, ensure_ascii=False, sort_keys=True)
        )
    elif failure_value:
        message = str(failure_value)
    else:
        message = "requestfailed event without failure details"

    return {
        "message": message,
        "observedAt": utc_now(),
    }


def build_network_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    resource_type_counts = Counter(entry.get("resourceType") or "unknown" for entry in entries)
    status_groups = Counter(
        status_group(entry.get("response", {}).get("status"))
        for entry in entries
        if isinstance(entry.get("response"), dict)
    )

    return {
        "requestCount": len(entries),
        "responseCount": sum(1 for entry in entries if entry.get("response")),
        "failedRequestCount": sum(1 for entry in entries if entry.get("failure")),
        "resourceTypes": [
            {"resourceType": resource_type, "count": count}
            for resource_type, count in resource_type_counts.most_common()
        ],
        "statusGroups": [
            {"group": group_name, "count": count}
            for group_name, count in status_groups.most_common()
        ],
        "entries": entries,
    }


def summarize_page(page: Page) -> dict[str, Any]:
    url = read_member(page, "url")
    parsed_url = urlparse(url or "")

    try:
        title = page.title()
    except Exception as exc:  # pragma: no cover - runtime-only path
        title = f"<unavailable: {exc}>"

    origin = None
    if parsed_url.scheme and parsed_url.netloc:
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    return {
        "url": url,
        "origin": origin,
        "title": title,
    }


def capture_current_page_state(page: Page) -> dict[str, Any]:
    snapshot_script = """
    () => {
      const summarizeStorage = (storage) => {
        const items = [];
        for (let index = 0; index < storage.length; index += 1) {
          const key = storage.key(index);
          if (key === null) {
            continue;
          }

          const value = storage.getItem(key) ?? "";
          items.push({
            key,
            valueBytes: value.length,
          });
        }

        return {
          itemCount: storage.length,
          items,
        };
      };

      return {
        url: window.location.href,
        origin: window.location.origin,
        title: document.title,
        localStorage: summarizeStorage(window.localStorage),
        sessionStorage: summarizeStorage(window.sessionStorage),
      };
    }
    """

    try:
        snapshot = page.evaluate(snapshot_script)
    except Exception as exc:  # pragma: no cover - runtime-only path
        return {
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }
        }

    if not isinstance(snapshot, dict):
        return {
            "error": {
                "type": "SnapshotError",
                "message": "Page storage snapshot is not an object.",
            }
        }

    return snapshot


def summarize_cookies(cookies: list[dict[str, Any]]) -> dict[str, Any]:
    domain_counts = Counter(cookie.get("domain") or "<unknown>" for cookie in cookies)
    return {
        "count": len(cookies),
        "domains": [
            {"domain": domain, "count": count}
            for domain, count in domain_counts.most_common()
        ],
        "items": [
            {
                "name": cookie.get("name"),
                "domain": cookie.get("domain"),
                "path": cookie.get("path"),
                "secure": cookie.get("secure"),
                "httpOnly": cookie.get("httpOnly"),
                "sameSite": cookie.get("sameSite"),
                "expires": cookie.get("expires"),
                "valueBytes": len(str(cookie.get("value", ""))),
            }
            for cookie in cookies
        ],
    }


def summarize_local_storage(origins: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "originCount": len(origins),
        "origins": [
            {
                "origin": origin_entry.get("origin"),
                "itemCount": len(origin_entry.get("localStorage", []) or []),
                "items": [
                    {
                        "key": item.get("name"),
                        "valueBytes": len(str(item.get("value", ""))),
                    }
                    for item in (origin_entry.get("localStorage", []) or [])
                ],
            }
            for origin_entry in origins
        ],
    }


def sanitize_header_keys(headers: Any) -> list[str]:
    if not isinstance(headers, dict):
        return []
    return sorted(
        key
        for key in headers.keys()
        if str(key).lower() not in SENSITIVE_HEADERS
    )


def compute_post_data_bytes(post_data: Any) -> int:
    if post_data is None:
        return 0
    if isinstance(post_data, str):
        return len(post_data.encode("utf-8"))
    if isinstance(post_data, (bytes, bytearray)):
        return len(post_data)
    return len(str(post_data).encode("utf-8"))


def read_member(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except TypeError:
            return default
    return value


def status_group(status: Any) -> str:
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        return "unknown"
    return f"{status_code // 100}xx"


def build_output_path(output_dir: Path, url: str, recording_id: str) -> Path:
    host = sanitize_fragment(urlparse(url).netloc or "browser")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output_dir / f"{timestamp}-{host}-{recording_id[:8]}.json"


def sanitize_fragment(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return sanitized or "recording"


def resolve_output_dir(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return (Path.cwd() / expanded).resolve()


def resolve_browser_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return (Path.cwd() / expanded).resolve()


def write_recording(recording: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(recording, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
