"""backend/app/models/schemas.py — Pydantic V2 数据模型"""
from __future__ import annotations

from pydantic import BaseModel, Field


# === 项目 ===
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: str = Field(alias="createdAt", default="")

    model_config = {"populate_by_name": True}


# === 功能点 ===
class FeatureCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")

    model_config = {"populate_by_name": True}


class FeatureOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    name: str
    description: str
    status: str
    created_at: str = Field(alias="createdAt", default="")

    model_config = {"populate_by_name": True}


# === 测试用例 ===
class CaseCreate(BaseModel):
    feature_id: str = Field(..., alias="featureId")
    title: str = Field(..., min_length=1, max_length=300)
    steps: list[str] = Field(default_factory=list)
    expected: str = Field(default="")
    priority: str = Field(default="medium")

    model_config = {"populate_by_name": True}


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    steps: list[str] | None = None
    expected: str | None = None
    priority: str | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


class CaseOut(BaseModel):
    id: str
    feature_id: str = Field(alias="featureId")
    title: str
    steps: list[str]
    expected: str
    priority: str
    status: str
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")

    model_config = {"populate_by_name": True}


# === 执行 ===
class RunCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    case_ids: list[str] = Field(default_factory=list, alias="caseIds")

    model_config = {"populate_by_name": True}


class RunResultOut(BaseModel):
    id: str
    case_id: str = Field(alias="caseId")
    status: str
    error_message: str = Field(alias="errorMessage", default="")
    duration_ms: int = Field(alias="durationMs", default=0)

    model_config = {"populate_by_name": True}


class RunOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    status: str
    total: int
    passed: int
    failed: int
    skipped: int
    started_at: str | None = Field(alias="startedAt", default=None)
    finished_at: str | None = Field(alias="finishedAt", default=None)
    created_at: str = Field(alias="createdAt", default="")

    model_config = {"populate_by_name": True}


class RunReportOut(BaseModel):
    run: RunOut
    results: list[RunResultOut]


# === 看板 ===
class DashboardOut(BaseModel):
    total_projects: int = Field(alias="totalProjects")
    total_features: int = Field(alias="totalFeatures")
    total_cases: int = Field(alias="totalCases")
    total_runs: int = Field(alias="totalRuns")
    pass_rate: float = Field(alias="passRate")
    recent_runs: list[RunOut] = Field(alias="recentRuns")

    model_config = {"populate_by_name": True}
