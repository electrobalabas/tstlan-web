from datetime import timedelta
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from tstlan.auth.service import resolve_session

SESSION_COOKIE = "tstlan_session"
CSRF_HEADER = "X-CSRF-Token"
LOGIN_PATH = "/auth/login"

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
SAFE_METHODS = frozenset({"GET", "HEAD"})


class AuthCsrfMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        ttl: timedelta,
        refresh_after: timedelta,
        allowed_origins: list[str],
        cookie_secure: bool,
    ) -> None:
        super().__init__(app)
        self._sessionmaker = sessionmaker
        self._ttl = ttl
        self._refresh_after = refresh_after
        self._allowed_origins = frozenset(allowed_origins)
        self._cookie_secure = cookie_secure

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.user = None
        request.state.csrf_token = None
        csrf_token: str | None = None

        token = request.cookies.get(SESSION_COOKIE)
        if token:
            async with self._sessionmaker() as db:
                session = await resolve_session(
                    db, token, ttl=self._ttl, refresh_after=self._refresh_after
                )
                if session is not None:
                    request.state.user = session.user
                    request.state.csrf_token = session.csrf_token
                    csrf_token = session.csrf_token

        denied = self._reject_csrf(request, csrf_token)
        if denied is not None:
            return denied

        response = await call_next(request)
        if token and csrf_token is not None and request.method in SAFE_METHODS:
            self._set_session_cookie(response, token)
        return response

    def _reject_csrf(self, request: Request, csrf_token: str | None) -> Response | None:
        if request.method not in UNSAFE_METHODS:
            return None
        if request.url.path == LOGIN_PATH:
            if not self._origin_allowed(request):
                return _forbidden("origin not allowed")
            return None
        if csrf_token is None:
            return None
        if not self._origin_allowed(request):
            return _forbidden("origin not allowed")
        if request.headers.get(CSRF_HEADER) != csrf_token:
            return _forbidden("csrf token mismatch")
        return None

    def _origin_allowed(self, request: Request) -> bool:
        origin = request.headers.get("origin")
        if origin is None:
            referer = request.headers.get("referer")
            origin = _origin_of(referer) if referer else None
        return origin in self._allowed_origins

    def _set_session_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=int(self._ttl.total_seconds()),
            httponly=True,
            samesite="lax",
            secure=self._cookie_secure,
            path="/",
        )


def _forbidden(detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=403)


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"
