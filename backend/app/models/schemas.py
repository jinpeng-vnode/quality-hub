"""backend/app/models/schemas.py — Pydantic V2 数据模型

按设计文档 design/L1-TASK-001-整体架构.md 第4节定义。
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from enum import Enum


# === 枚举 ===
class FeatureStatus(str, Enum):
    pending = "pending"
    partial = "partial"
    covered = "covered"


class CasePriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CaseType(str, Enum):
    manual = "manual"
    e2e = "e2e"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"
    completed = "completed"


# === 项目 ===
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    repo_url: str | None = Field(None, alias="repoUrl")
    description: str | None = None
    model_config = {"populate_by_name": True}


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    repo_url: str | None = Field(None, alias="repoUrl")
    description: str | None = None
    model_config = {"populate_by_name": True}


class ProjectOut(BaseModel):
    id: str
    name: str
    repo_url: str | None = Field(None, alias="repoUrl")
    description: str | None
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    model_config = {"populate_by_name": True}


# === 功能点 ===
class FeatureCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    source: str | None = None
    model_config = {"populate_by_name": True}


class FeatureUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    status: FeatureStatus | None = None
    model_config = {"populate_by_name": True}


class FeatureOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    title: str
    description: str | None
    source: str | None
    status: FeatureStatus
    case_count: int = Field(0, alias="caseCount")
    created_at: str = Field(alias="createdAt")
    model_config = {"populate_by_name": True}


# === 测试用例 ===
class CaseCreate(BaseModel):
    feature_id: str = Field(..., alias="featureId")
    title: str = Field(..., min_length=1, max_length=200)
    steps: str | None = None
    expected_result: str | None = Field(None, alias="expectedResult")
    priority: CasePriority = CasePriority.medium
    case_type: CaseType = Field(CaseType.manual, alias="caseType")
    midscene_script: str | None = Field(None, alias="midsceneScript")
    model_config = {"populate_by_name": True}


class CaseUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    steps: str | None = None
    expected_result: str | None = Field(None, alias="expectedResult")
    priority: CasePriority | None = None
    case_type: CaseType | None = Field(None, alias="caseType")
    midscene_script: str | None = Field(None, alias="midsceneScript")
    model_config = {"populate_by_name": True}


class CaseOut(BaseModel):
    id: str
    feature_id: str = Field(alias="featureId")
    title: str
    steps: str | None
    expected_result: str | None = Field(None, alias="expectedResult")
    priority: CasePriority
    case_type: CaseType = Field(alias="caseType")
    midscene_script: str | None = Field(None, alias="midsceneScript")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    model_config = {"populate_by_name": True}


# === 执行 ===
class RunCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    case_ids: list[str] = Field(default_factory=list, alias="caseIds")
    feature_ids: list[str] = Field(default_factory=list, alias="featureIds")
    mode: str = Field(default="manual")  # "manual" | "script"
    timeout: int = Field(default=60, ge=5, le=300)  # 单条用例超时秒数，默认60s
    model_config = {"populate_by_name": True}


class RunResultUpdate(BaseModel):
    """手动标记单条结果"""
    status: str = Field(...)  # "passed" | "failed" | "skipped"
    error_message: str = Field(default="", alias="errorMessage")
    duration_ms: int = Field(default=0, alias="durationMs")
    model_config = {"populate_by_name": True}


class RunOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    status: RunStatus
    mode: str = Field(default="manual")
    total: int
    passed: int
    failed: int
    skipped: int = Field(default=0)
    started_at: str | None = Field(None, alias="startedAt")
    finished_at: str | None = Field(None, alias="finishedAt")
    created_at: str = Field(alias="createdAt")
    model_config = {"populate_by_name": True}


class RunResultOut(BaseModel):
    id: str
    run_id: str = Field(alias="runId")
    case_id: str = Field(alias="caseId")
    case_title: str = Field(default="", alias="caseTitle")
    feature_id: str = Field(default="", alias="featureId")
    feature_title: str = Field(default="", alias="featureTitle")
    status: RunStatus
    error_message: str | None = Field(None, alias="errorMessage")
    duration_ms: int | None = Field(None, alias="durationMs")
    log: str = Field(default="")
    screenshots: list[str] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


# === 报告 ===
class TrendPoint(BaseModel):
    date: str
    pass_rate: float = Field(alias="passRate")
    total_cases: int = Field(alias="totalCases")
    model_config = {"populate_by_name": True}


class CoverageReport(BaseModel):
    project_id: str = Field(alias="projectId")
    total_features: int = Field(alias="totalFeatures")
    covered_features: int = Field(alias="coveredFeatures")
    coverage_rate: float = Field(alias="coverageRate")
    model_config = {"populate_by_name": True}


class PassRateReport(BaseModel):
    project_id: str = Field(alias="projectId")
    total_runs: int = Field(alias="totalRuns")
    passed_runs: int = Field(alias="passedRuns")
    pass_rate: float = Field(alias="passRate")
    model_config = {"populate_by_name": True}


class DashboardOut(BaseModel):
    coverage: CoverageReport
    pass_rate: PassRateReport = Field(alias="passRate")
    trend: list[TrendPoint]
    model_config = {"populate_by_name": True}
