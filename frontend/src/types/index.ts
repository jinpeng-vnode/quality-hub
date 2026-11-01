// 项目
export interface Project {
  id: number
  name: string
  repoUrl: string | null
  description: string | null
  pmProjectKey: string | null
  createdAt: string
  updatedAt: string
}

export interface ProjectImport { pmProjectKey: string; repoUrl?: string }

// 功能点
export type FeatureStatus = 'pending' | 'partial' | 'covered'

export interface Feature {
  id: number
  projectId: number
  title: string
  description: string | null
  source: string | null
  pmItemKey: string | null
  status: FeatureStatus
  caseCount: number
  createdAt: string
}

// 测试用例
export type CasePriority = 'high' | 'medium' | 'low'

export interface TestCase {
  id: number
  featureId: string
  title: string
  steps: string[]
  expectedResult: string | null
  priority: CasePriority
  midsceneScript: string | null
  smoke: boolean
  timeout: number | null
  createdAt: string
  updatedAt: string
}

// 执行记录
export type RunStatus = 'pending' | 'running' | 'passed' | 'failed' | 'error'

export interface TestRun {
  id: number
  projectId: number
  status: RunStatus
  mode: string
  total: number
  passed: number
  failed: number
  skipped: number
  startedAt: string | null
  finishedAt: string | null
  createdAt: string
}

// 执行结果
export interface RunResult {
  id: number
  runId: number
  caseId: number
  caseTitle: string
  featureId: string
  featureTitle: string
  status: RunStatus | 'skipped'
  errorMessage: string | null
  durationMs: number | null
  log: string
  screenshots: string[]
  pmBugKey: string | null
  regressionPending: boolean
}

export interface BugDraft { title: string; description: string; severity: 'major' | 'normal' | 'minor' }

// 报告看板
export interface DashboardData {
  coverage: { projectId: number; totalFeatures: number; coveredFeatures: number; coverageRate: number }
  passRate: { projectId: number; totalRuns: number; passedRuns: number; passRate: number }
  trend: TrendPoint[]
}

export interface TrendPoint {
  date: string
  passRate: number
  totalCases: number
}
