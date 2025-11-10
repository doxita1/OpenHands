# OpenHands 项目结构说明

## 项目概述
OpenHands（原名 OpenDevin）是一个开源的 AI 软件开发助手平台，让 AI 代理能够像人类开发者一样工作：修改代码、运行命令、浏览网页、调用 API 等。该项目旨在"写更少的代码，做更多的事情"。

## 核心模块结构

### 1. 后端核心模块 (`openhands/`)
- **agenthub/** - AI 代理中心，包含不同类型的 AI 代理实现
  - **codeact_agent/** - 代码执行代理
  - **browsing_agent/** - 网页浏览代理
  - **readonly_agent/** - 只读代理
  - **loc_agent/** - 代码行数分析代理
  - **visualbrowsing_agent/** - 可视化浏览代理
  - **dummy_agent/** - 测试用虚拟代理
- **app_server/** - 应用服务器，处理核心业务逻辑
- **controller/** - 控制器层，处理请求路由和响应
- **core/** - 核心业务逻辑和领域模型
- **critic/** - 代码审查和评估模块
- **events/** - 事件处理系统
- **integrations/** - 第三方集成（GitHub、GitLab、Jira 等）
- **llm/** - 大语言模型接口和配置
- **memory/** - 记忆管理模块
- **microagent/** - 微代理框架
- **resolver/** - 依赖解析和问题解决器
- **runtime/** - 运行时环境管理
- **security/** - 安全相关功能
- **server/** - HTTP 服务器实现
- **storage/** - 数据存储层
- **utils/** - 工具函数库

### 2. 前端模块 (`frontend/`)
- **src/** - React 前端源代码
  - **api/** - API 接口调用
  - **components/** - React 组件
  - **hooks/** - React 自定义钩子
  - **routes/** - 路由配置
  - **services/** - 服务层
  - **stores/** - 状态管理
  - **types/** - TypeScript 类型定义
  - **utils/** - 工具函数
  - **context/** - React Context 上下文
  - **ui/** - UI 组件库
- **__tests__/** - 前端测试文件
- **public/** - 静态资源文件
- **scripts/** - 构建和部署脚本
- **tests/** - 端到端测试

### 3. 企业版功能 (`enterprise/`)
- **experiments/** - A/B 测试和实验管理
- **integrations/** - 企业级集成（Bitbucket、Jira DC、Linear 等）
- **enterprise_local/** - 本地企业部署工具

### 4. 命令行工具 (`openhands-cli/`)
- CLI 工具模块，提供命令行界面

### 5. UI 组件库 (`openhands-ui/`)
- 可重用的 UI 组件库

### 6. 容器化部署 (`containers/`)
- **dev/** - 开发环境容器配置
- **runtime/** - 运行时容器配置

### 7. 评估模块 (`evaluation/`)
- 性能评估和测试框架

### 8. 微代理系统 (`microagents/`)
- 微服务架构的代理实现

### 9. 配置和脚本
- **dev_config/** - 开发环境配置
- **scripts/** - 系统脚本
- **kind/** - Kubernetes 配置
- **third_party/** - 第三方依赖

## 技术栈

### 后端技术
- **Python 3.12+** - 主要后端语言
- **Poetry** - 依赖管理
- **LiteLLM** - LLM 接口抽象层
- **OpenAI** - AI 模型接口
- **Flask/FastAPI** - Web 框架
- **SQLAlchemy** - ORM
- **Docker** - 容器化

### 前端技术
- **React** - 前端框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **Vitest** - 测试框架
- **Playwright** - 端到端测试

### 部署和运维
- **Docker Compose** - 容器编排
- **Kubernetes** - 容器编排
- **GitHub Actions** - CI/CD
- **VS Code Extension** - 集成开发环境插件

## 主要功能模块

### AI 代理系统
- 多种类型的 AI 代理实现
- 代理间通信和协作
- 任务分解和执行

### 集成系统
- 代码仓库集成（GitHub、GitLab、Bitbucket）
- 项目管理工具集成（Jira、Linear）
- 版本控制系统

### 开发工具
- 代码生成和编辑
- 问题诊断和修复
- 自动化测试
- 部署管理

### 企业功能
- 多租户支持
- 权限管理
- 审计日志
- 性能监控

## 开发流程

1. **环境设置** - 使用容器化开发环境
2. **本地开发** - 前后端分离开发
3. **测试验证** - 单元测试和集成测试
4. **部署发布** - 自动化部署流程

## 项目特点

- **模块化设计** - 高度解耦的模块架构
- **可扩展性** - 易于添加新功能和集成
- **企业就绪** - 支持大规模部署
- **开源友好** - 完整的开源生态