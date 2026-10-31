class ErrorCode:
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


class AppError(Exception):
    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
    ):
        self.code = error_code.code
        self.message = message if message is not None else error_code.message
        super().__init__(self.message)


class NotFoundError(AppError):
    ERROR = ErrorCode("not_found", "Not Found")

    def __init__(self, message: str | None = None):
        super().__init__(NotFoundError.ERROR, message)


class TodoNotFoundError(AppError):
    ERROR = ErrorCode("todo_not_found", "Todo Not Found")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class ValidationError(AppError):
    ERROR = ErrorCode("validation_error", "Invalid Value")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class InvalidRequestError(AppError):
    ERROR = ErrorCode("invalid_request", "Invalid Request")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class MethodNotAllowedError(AppError):
    ERROR = ErrorCode("method_not_allowed", "Method Not Allowed")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class InvalidJsonError(AppError):
    ERROR = ErrorCode("invalid_json", "Invalid JSON")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class InternalError(AppError):
    ERROR = ErrorCode("internal_error", "Internal Error")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class PayloadTooLargeError(AppError):
    ERROR = ErrorCode("payload_too_large", "Request Body Too Large")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class UnsupportedMediaTypeError(AppError):
    ERROR = ErrorCode("unsupported_media_type", "Unsupported Media Type Header")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)


class AuthenticationError(AppError):
    ERROR = ErrorCode("authentication_error", "Authentication Error")

    def __init__(self, message: str | None = None):
        super().__init__(self.ERROR, message)
