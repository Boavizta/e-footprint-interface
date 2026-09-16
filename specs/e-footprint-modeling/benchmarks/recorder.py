"""Small action and request recorder for browser usage-journey benchmarks."""

import csv
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import BrowserContext, Request


def utc_now() -> str:
    """Return an unambiguous timestamp suitable for correlating server logs."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class BenchmarkRecorder:
    """Record action boundaries and every browser-context request without payloads or query strings."""

    def __init__(self, context: BrowserContext, base_url: str):
        self.context = context
        self.base_url = base_url.rstrip("/")
        self.run_id = f"usage-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        self.started_at_utc = utc_now()
        self.actions: list[dict] = []
        self.requests: list[dict] = []
        self._active_action: str | None = None
        self._active_operation_id: str | None = None
        self._inflight: dict[int, tuple[float, dict]] = {}

        context.set_extra_http_headers({"X-Efootprint-Benchmark-Run": self.run_id})
        context.on("request", self._request_started)
        context.on("requestfinished", self._request_finished)
        context.on("requestfailed", self._request_failed)

    @contextmanager
    def measure(self, journey_id: str, operation_id: str, action: str):
        """Measure one complete user-visible action and retain failed observations."""
        if self._active_action is not None:
            raise RuntimeError("Benchmark actions cannot be nested")
        action_key = f"{journey_id}.{action}"
        started_perf = perf_counter()
        row = {
            "run_id": self.run_id,
            "journey_id": journey_id,
            "operation_id": operation_id,
            "action": action,
            "started_at_utc": utc_now(),
            "finished_at_utc": None,
            "duration_ms": None,
            "status": "running",
            "error": None,
        }
        self._active_action = action_key
        self._active_operation_id = operation_id
        try:
            yield
        except Exception as exc:
            row["status"] = "failed"
            row["error"] = f"{type(exc).__name__}: {exc}"
            raise
        else:
            row["status"] = "passed"
        finally:
            row["finished_at_utc"] = utc_now()
            row["duration_ms"] = round((perf_counter() - started_perf) * 1000, 3)
            self.actions.append(row)
            self._active_action = None
            self._active_operation_id = None

    def write(self, output_dir: Path) -> Path:
        """Write one lossless JSON document and flat action/request CSV files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        run_dir = output_dir / self.run_id
        run_dir.mkdir()
        finished_at_utc = utc_now()

        for _, row in self._inflight.values():
            row.update({"finished_at_utc": finished_at_utc, "status": "unfinished", "failure": None})
            self.requests.append(row)
        self._inflight.clear()

        document = {
            "schema_version": 1,
            "run": {
                "run_id": self.run_id,
                "base_url": self.base_url,
                "started_at_utc": self.started_at_utc,
                "finished_at_utc": finished_at_utc,
            },
            "actions": self.actions,
            "requests": self.requests,
        }
        (run_dir / "benchmark.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        self._write_csv(run_dir / "actions.csv", self.actions)
        self._write_csv(run_dir / "requests.csv", self.requests)
        return run_dir

    def _request_started(self, request: Request) -> None:
        parts = urlsplit(request.url)
        row = {
            "run_id": self.run_id,
            "action_key": self._active_action,
            "operation_id": self._request_operation_id(parts.path),
            "method": request.method,
            "origin": f"{parts.scheme}://{parts.netloc}",
            "path": parts.path,
            "resource_type": request.resource_type,
            "started_at_utc": utc_now(),
            "finished_at_utc": None,
            "duration_ms": None,
            "status": None,
            "failure": None,
        }
        self._inflight[id(request)] = (perf_counter(), row)

    def _request_operation_id(self, path: str) -> str | None:
        # Results opening launches attribution automatically. Keep the browser action whole while
        # retaining the canonical B5/B6 server-request boundary in the raw request dataset.
        if self._active_operation_id == "B5" and path.endswith("/sankey-diagram/"):
            return "B6"
        return self._active_operation_id

    def _request_finished(self, request: Request) -> None:
        response = request.response()
        self._finish_request(request, response.status if response is not None else None, None)

    def _request_failed(self, request: Request) -> None:
        self._finish_request(request, None, request.failure or "request failed")

    def _finish_request(self, request: Request, status: int | None, failure: str | None) -> None:
        started = self._inflight.pop(id(request), None)
        if started is None:
            return
        started_perf, row = started
        row.update(
            {
                "finished_at_utc": utc_now(),
                "duration_ms": round((perf_counter() - started_perf) * 1000, 3),
                "status": status,
                "failure": failure,
            }
        )
        self.requests.append(row)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
