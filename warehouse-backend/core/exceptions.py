from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """HTTP error carrying the application's stable code and safe message."""
    def __init__(self, status_code: int, code: str, message: str):
        """Initialize a structured domain error response."""
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent domain, validation and unexpected error handlers."""
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        """Render an application error without changing its code or message."""
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Render Pydantic validation failures using the standard error envelope."""
        errors = exc.errors()
        messages = [str(item.get("ctx", {}).get("error", item.get("msg", "Invalid request data"))) for item in errors]
        code = "INVALID_INSPECTION_QUANTITY" if any("INVALID_INSPECTION_QUANTITY" in message for message in messages) else "VALIDATION_ERROR"
        return JSONResponse(status_code=400, content={"detail": {"code": code, "message": "; ".join(messages)}})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Log unexpected failures and return a safe generic error envelope."""
        request.app.state.logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )
