from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
import logging

logger = logging.getLogger("agrishield_api")

def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP Exception: {exc.detail} on path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation Exception on path {request.url.path}: {exc.errors()}")
        errors_list = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            msg = error.get("msg", "Validation error")
            errors_list.append(f"{loc}: {msg}")
        
        message = "; ".join(errors_list) if errors_list else "Validation failed"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "details": exc.errors()
                }
            }
        )

    @app.exception_handler(IntegrityError)
    async def db_integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database Integrity Error: {str(exc)} on path {request.url.path}")
        # Map integrity errors (like unique constraint or foreign key violations) to user-friendly messages
        message = "A database integrity constraint was violated. (e.g. duplicate SKU/email, or invalid references)"
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "INTEGRITY_ERROR",
                    "message": message
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception on path {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact system administrator."
                }
            }
        )
