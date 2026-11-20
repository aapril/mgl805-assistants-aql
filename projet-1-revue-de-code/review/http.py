"""Bounded client. No redirect may carry a token to another origin."""
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError


class RemoteError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base: str, headers=None, timeout: int = 30):
        parsed = urlsplit(base)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Invalid service URL")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("HTTPS is mandatory outside localhost")
        self.base = base.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.opener = build_opener(NoRedirect())

    def request(self, method, path, body=None, *, as_text=False, max_bytes=2_000_000, accept=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Invalid API path")
        headers = {"Accept": "text/plain" if as_text else "application/json", **self.headers}
        if accept is not None:
            headers["Accept"] = accept
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise RemoteError("Response too large; split the pull request.")
        except HTTPError as exc:
            raise RemoteError(f"API HTTP {exc.code}; check the URL, permissions, and availability") from None
        except (URLError, TimeoutError) as exc:
            raise RemoteError(f"API unavailable ({type(exc).__name__})") from None
        value = raw.decode("utf-8")
        return value if as_text else json.loads(value)
