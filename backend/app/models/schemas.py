"""backend/app/models/schemas.py — Pydantic V2 数据模型

按设计文档 design/L1-TASK-001-整体架构.md 第4节定义。
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from enum import Enum

# 项目管理的工作项编号，如 FLEET-12
PM_ITEM_KEY_PATTERN = r"^[A-Z][A-Z0-9_]*-[0-9]+$"


# === 枚举 ===
class FeatureStatus(str, Enum):
    pending = "pending"
    partial = "partial"
    covered = "covered"


class CasePriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"





class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"
    completed = "completed"


# === 项目 ===
class ProjectImport(BaseModel):
    """从项目管理导入项目：只给项目标识，名称和描述从项目管理取"""
    pm_project_key: str = Field(..., alias="pmProjectKey", pattern=r"^[A-Z][A-Z0-9]{1,9}$")
    repo_url: str | None = Field(None, alias="repoUrl")
    model_config = {"populate_by_name": True}


class ProjectUpdate(BaseModel):
    """名称、描述以项目管理为准，这里只能改仓库地址"""
    repo_url: str | None = Field(None, alias="repoUrl")
    model_config = {"populate_by_name": True}


class ProjectOut(BaseModel):
    id: str
    name: str
    repo_url: str | None = Field(None, alias="repoUrl")
    description: str | None
    pm_project_key: str | None = Field(None, alias="pmProjectKey")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    model_config = {"populate_by_name": True}


# === 功能点 ===
class FeatureCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    source: str | None = None
    pm_item_key: str | None = Field(None, alias="pmItemKey", pattern=PM_ITEM_KEY_PATTERN)
    model_config = {"populate_by_name": True}


class FeatureUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    status: FeatureStatus | None = None
    # 不传 = 不改；传空串 = 解除关联；传编号 = 关联到这个需求
    pm_item_key: str | None = Field(None, alias="pmItemKey", pattern=PM_ITEM_KEY_PATTERN + "|^$")
    model_config = {"populate_by_name": True}


class FeatureOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    title: str
    description: str | None
    source: str | None
    pm_item_key: str | None = Field(None, alias="pmItemKey")
    status: FeatureStatus
    case_count: int = Field(0, alias="caseCount")
    created_at: str = Field(alias="createdAt")
    model_config = {"populate_by_name": True}


# === 测试用例 ===
class CaseCreate(BaseModel):
    feature_id: str = Field(..., alias="featureId")
    title: str = Field(..., min_length=1, max_length=200)
    steps: list[str] = Field(..., min_length=1, description="测试步骤数组，每步一条")
    expected_result: str = Field(..., alias="expectedResult", min_length=1, description="预期结果")
    priority: CasePriority = CasePriority.medium
    midscene_script: str = Field(..., alias="midsceneScript", min_length=1, description="Playwright 脚本")
    smoke: bool = Field(False, description="冒烟用例：项目管理登记部署后自动执行")
    model_config = {"populate_by_name": True}


class CaseUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    steps: list[str] | None = None
    expected_result: str | None = Field(None, alias="expectedResult")
    priority: CasePriority | None = None
    midscene_script: str | None = Field(None, alias="midsceneScript")
    smoke: bool | None = None
    model_config = {"populate_by_name": True}


class CaseOut(BaseModel):
    id: str
    feature_id: str = Field(alias="featureId")
    title: str
    steps: list[str] = Field(default_factory=list)
    expected_result: str | None = Field(None, alias="expectedResult")
    priority: CasePriority
    midscene_script: str | None = Field(None, alias="midsceneScript")
    smoke: bool = False
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    model_config = {"populate_by_name": True}


# === 执行 ===
class RunCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    case_ids: list[str] = Field(default_factory=list, alias="caseIds")
    feature_ids: list[str] = Field(default_factory=list, alias="featureIds")
    timeout: int = Field(default=60, ge=5, le=300)
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
    pm_bug_key: str | None = Field(None, alias="pmBugKey")
    regression_pending: bool = Field(False, alias="regressionPending")
    model_config = {"populate_by_name": True}


class BugDraft(BaseModel):
    """失败用例转缺陷：预览返回草稿，测试人员确认（可改标题和严重程度）后再提交"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    severity: str = Field("normal", pattern=r"^(major|normal|minor)$")
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
