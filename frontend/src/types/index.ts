// 项目
export interface Project {
  id: number
  name: string
  description: string
  status: 'active' | 'archived'
  createdAt: string
  updatedAt: string
}

// 功能点
export interface Feature {
  id: number
  projectId: number
  name: string
  description: string
  status: 'pending' | 'in_progress' | 'done'
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  createdAt: string
  updatedAt: string
}

// 测试用例步骤
export interface TestStep {
  id: number
  order: number
  action: string
  expected: string
}

// 测试用例
export interface TestCase {
  id: number
  featureId: number
  title: string
  precondition: string
  steps: TestStep[]
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: 'draft' | 'ready' | 'obsolete'
  createdAt: string
  updatedAt: string
}

// 执行记录
export interface Execution {
  id: number
  projectId: number
  triggerType: 'manual' | 'scheduled'
  status: 'pending' | 'running' | 'passed' | 'failed' | 'error'
  totalCases: number
  passedCases: number
  failedCases: number
  startedAt: string
  finishedAt: string | null
  createdAt: string
}

// 执行结果详情
export interface ExecutionResult {
  id: number
  executionId: number
  testCaseId: string
  testCaseTitle: string
  status: 'passed' | 'failed' | 'error' | 'skipped'
  duration: number
  errorMessage: string | null
}

// 报告统计
export interface ReportStats {
  totalFeatures: number
  coveredFeatures: number
  coverageRate: number
  totalCases: number
  passedCases: number
  failedCases: number
  passRate: number
}

// 趋势数据
export interface TrendPoint {
  date: string
  passRate: number
  coverageRate: number
}

// 通用分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}
