/**
 * Jenkinsfile — quality-hub 部署 pipeline
 *
 * 假设条件：
 * 1. 在 Mac Mini (192.168.3.9) 本地 Jenkins agent 上执行
 * 2. agent 有 docker / docker compose 命令可用
 * 3. 工作目录为仓库 checkout 目录（Jenkins SCM 自动 checkout）
 * 4. 外部 Traefik 已配置 quality-hub.todonot.com → localhost:5400
 * 5. 如果 .env 文件不存在，pipeline 会从 .env.example 复制一份（默认值足够启动）
 */

pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = 'quality-hub'
        HEALTH_URL = 'http://localhost:5400/health'
        PUBLIC_URL = 'https://quality-hub.todonot.com/'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '📥 拉取 dev 分支最新代码...'
                checkout scm
            }
        }

        stage('Prepare Env') {
            steps {
                echo '⚙️ 检查环境配置文件...'
                script {
                    if (!fileExists('.env')) {
                        echo '.env 不存在，从 .env.example 复制默认配置'
                        sh 'cp .env.example .env'
                    } else {
                        echo '.env 已存在，跳过'
                    }
                }
            }
        }

        stage('Build Images') {
            steps {
                echo '🔨 构建前后端 Docker 镜像...'
                sh 'docker compose build --no-cache'
            }
        }

        stage('Deploy') {
            steps {
                echo '🚀 停止旧容器并启动新容器...'
                sh 'docker compose down --remove-orphans || true'
                sh 'docker compose up -d'
                echo '⏳ 等待服务启动（15秒）...'
                sh 'sleep 15'
            }
        }

        stage('Health Check') {
            steps {
                echo '🏥 执行健康检查...'
                // 检查本地网关端口
                sh """
                    echo "检查本地网关 (localhost:5400)..."
                    curl -f --retry 3 --retry-delay 5 --max-time 10 ${HEALTH_URL}
                    echo ""
                    echo "✅ 本地健康检查通过"
                """
                // 检查公网域名（Traefik 反代）
                sh """
                    echo "检查公网域名 (quality-hub.todonot.com)..."
                    curl -f --retry 3 --retry-delay 5 --max-time 10 ${PUBLIC_URL}
                    echo ""
                    echo "✅ 公网访问正常"
                """
            }
        }

        stage('Verify Containers') {
            steps {
                echo '📋 确认容器运行状态...'
                sh 'docker compose ps'
                sh 'docker compose logs --tail=20'
            }
        }
    }

    post {
        success {
            echo '''
            ✅ 部署成功！
            - 本地访问: http://localhost:5400
            - 公网访问: https://quality-hub.todonot.com/
            - 后端 API 文档: https://quality-hub.todonot.com/docs
            - 健康检查: https://quality-hub.todonot.com/health
            '''
        }
        failure {
            echo '❌ 部署失败，打印容器日志用于排查...'
            sh 'docker compose logs --tail=50 || true'
            sh 'docker compose ps || true'
        }
        always {
            echo "Pipeline 执行完毕，时间: ${new Date()}"
        }
    }
}
