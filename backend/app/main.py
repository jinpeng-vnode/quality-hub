"""backend/app/main.py — FastAPI 应用入口"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.database import init_db
from app.routers import projects, features, cases, runs, reports
from app.utils.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    yield


app = FastAPI(title="Quality Hub API", version="0.1.0", lifespan=lifespan)

# 注册统一异常处理
register_exception_handlers(app)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(projects.router, prefix="/api")
app.include_router(features.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
