import logging
from collections.abc import Callable

from todo_api.error import AppError, AuthenticationError, InternalError
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse
from todo_api.http_layer.middleware import GetResponse
from todo_api.http_layer.router import Router

logger = logging.getLogger(__name__)


class App:
    def __init__(
        self,
        router: Router,
        middlewares: tuple[Callable[[GetResponse], GetResponse], ...] = (),
    ) -> None:
        self._router = router
        handler: GetResponse = self._dispatch
        for middleware in reversed(middlewares):
            handler = middleware(handler)
        self._handler = handler

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self._handler(request)

    def _dispatch(self, request: HttpRequest) -> HttpResponse:
        try:
            route, params = self._router.resolve(request.method, request.path)
            if request.user_id is None:
                raise AuthenticationError
            return route.action(request, params)
        except AppError as error:
            return HttpResponse.error(error)
        except Exception:
            logger.exception("Unexpected error while handling request")
            return HttpResponse.error(InternalError())
