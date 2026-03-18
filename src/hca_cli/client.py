from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib import error, parse, request


USER_AGENT = "hca-cli/0.1"


class NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None

    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    http_error_302 = http_error_303 = http_error_307 = http_error_308 = http_error_301


@dataclass(frozen=True)
class ApiResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str

    def json(self) -> Any | None:
        if not self.body:
            return None
        content_type = self.headers.get("Content-Type", "")
        if "json" in content_type.lower():
            return json.loads(self.body.decode("utf-8"))
        stripped = self.body.lstrip()
        if stripped.startswith((b"{", b"[")):
            return json.loads(self.body.decode("utf-8"))
        return None

    def text(self) -> str | None:
        if not self.body:
            return None
        return self.body.decode("utf-8", errors="replace")


class ApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str | None = None,
        timeout: float = 60.0,
        follow_redirects: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.bearer_token = bearer_token
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    def request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        path_params = path_params or {}
        query = query or {}
        headers = headers or {}

        rendered_path = path
        for key, value in path_params.items():
            rendered_path = rendered_path.replace("{" + key + "}", parse.quote(str(value), safe=""))

        prepared_query = self._prepare_query(query)
        url = parse.urljoin(self.base_url, rendered_path.lstrip("/"))
        if prepared_query:
            url += "?" + parse.urlencode(prepared_query, doseq=True)

        data = None
        request_headers = {
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
            "User-Agent": USER_AGENT,
            **headers,
        }
        if self.bearer_token:
            request_headers["Authorization"] = f"Bearer {self.bearer_token}"
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        http_request = request.Request(url, method=method.upper(), data=data, headers=request_headers)
        opener = request.build_opener() if self.follow_redirects else request.build_opener(NoRedirectHandler)
        try:
            with opener.open(http_request, timeout=self.timeout) as response:
                return ApiResponse(
                    status=getattr(response, "status", response.getcode()),
                    headers=dict(response.headers.items()),
                    body=response.read(),
                    url=response.geturl(),
                )
        except error.HTTPError as exc:
            return ApiResponse(
                status=exc.code,
                headers=dict(exc.headers.items()),
                body=exc.read(),
                url=exc.geturl(),
            )

    @staticmethod
    def _prepare_query(query: dict[str, Any]) -> dict[str, Any]:
        prepared: dict[str, Any] = {}
        for key, value in query.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                prepared[key] = json.dumps(value, separators=(",", ":"))
            else:
                prepared[key] = value
        return prepared
