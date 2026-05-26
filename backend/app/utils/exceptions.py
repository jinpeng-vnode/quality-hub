"""backend/app/utils/exceptions.py — 统一异常定义与处理中间件

统一错误响应格式: {"code": "NOT_FOUND", "message": "...", "detail": null}
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger


class AppException(Exception):
    """应用统一异常基类"""

    def __init__(self, code: str, message: str, status_code: int = 400, detail: str | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class ConflictException(AppException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(code="CONFLICT", message=message, status_code=409)


class ForbiddenException(AppException):
    def __init__(self, message: str = "操作被禁止"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "参数校验失败", "detail": str(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"未处理异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "detail": None},
        )
