from http import HTTPStatus


class ErrorCode:
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


class AppError(Exception):
    STATUS = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.code = error_code.code
        self.message = message if message is not None else error_code.message
        self.headers = headers or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    ERROR = ErrorCode("not_found", "Not Found")
    STATUS = HTTPStatus.NOT_FOUND

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(NotFoundError.ERROR, message, headers)


class TodoNotFoundError(AppError):
    ERROR = ErrorCode("todo_not_found", "Todo Not Found")
    STATUS = HTTPStatus.NOT_FOUND

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class ValidationError(AppError):
    ERROR = ErrorCode("validation_error", "Invalid Value")
    STATUS = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class InvalidRequestError(AppError):
    ERROR = ErrorCode("invalid_request", "Invalid Request")
    STATUS = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class MethodNotAllowedError(AppError):
    ERROR = ErrorCode("method_not_allowed", "Method Not Allowed")
    STATUS = HTTPStatus.METHOD_NOT_ALLOWED

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class InvalidJsonError(AppError):
    ERROR = ErrorCode("invalid_json", "Invalid JSON")
    STATUS = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class InternalError(AppError):
    ERROR = ErrorCode("internal_error", "Internal Error")
    STATUS = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class PayloadTooLargeError(AppError):
    ERROR = ErrorCode("payload_too_large", "Request Body Too Large")
    STATUS = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class UnsupportedMediaTypeError(AppError):
    ERROR = ErrorCode("unsupported_media_type", "Unsupported Media Type Header")
    STATUS = HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(self.ERROR, message, headers)


class AuthenticationError(AppError):
    ERROR = ErrorCode("authentication_error", "Authentication Error")
    STATUS = HTTPStatus.UNAUTHORIZED

    def __init__(self, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(
            self.ERROR,
            message,
            headers={**(headers or {}), "WWW-Authenticate": "Bearer"},
        )
