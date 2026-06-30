# 缺陷管理系统 (Bug Management System)

## 项目简介

基于 FusionCompute + Docker 容器部署的类 BugFree 缺陷管理系统，适配鲲鹏 ARM 架构。

## 技术栈

- **虚拟化平台**: FusionCompute（华为鲲鹏 ARM）
- **后端**: Python Flask + SQLAlchemy ORM
- **前端**: HTML5 + JavaScript + Bootstrap 5 + Chart.js
- **数据库**: MySQL 8.0
- **容器**: Docker + Docker Compose

## 项目结构

```
bug-management-system/
├── backend/                  # 后端代码
│   ├── app.py               # Flask 主应用 (API 路由)
│   ├── config.py            # 配置文件
│   ├── models.py            # 数据模型 (SQLAlchemy)
│   └── requirements.txt     # Python 依赖
├── frontend/                # 前端代码
│   ├── index.html           # 主页面 (SPA)
│   ├── css/style.css        # 自定义样式
│   └── js/app.js            # 前端逻辑
├── database/
│   └── init.sql             # 数据库初始化脚本
├── docker/
│   ├── Dockerfile           # 镜像构建文件
│   └── docker-compose.yml   # 容器编排文件
└── deploy/
    └── deploy.sh            # 一键部署脚本
```

## 快速启动

### 前置要求

- Docker & Docker Compose（ARM64 版本）
- FusionCompute 虚拟机（鲲鹏 ARM 架构）

### 一键部署

```bash
cd bug-management-system
bash deploy/deploy.sh
```

### 手动部署

```bash
# 1. 构建并启动
docker compose -f docker/docker-compose.yml up -d

# 2. 等待服务就绪
sleep 30

# 3. 访问系统
# http://<虚拟机IP>:5000
```

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 系统管理员 | admin | 123456 |
| 项目经理 | manager | 123456 |
| 开发工程师 | developer | 123456 |
| 测试工程师 | tester | 123456 |

## API 文档

| 模块 | 路径 | 方法 | 说明 |
|------|------|------|------|
| 认证 | /api/auth/login | POST | 用户登录 |
| 认证 | /api/auth/logout | POST | 用户登出 |
| 认证 | /api/auth/current_user | GET | 获取当前用户 |
| 用户 | /api/users | GET/POST | 用户列表/创建 |
| 用户 | /api/users/{id} | PUT/DELETE | 用户更新/删除 |
| 角色 | /api/roles | GET | 角色列表 |
| 项目 | /api/projects | GET/POST | 项目列表/创建 |
| 项目 | /api/projects/{id} | PUT/DELETE | 项目更新/删除 |
| 模块 | /api/projects/{id}/modules | GET/POST | 模块列表/创建 |
| Bug | /api/bugs | GET/POST | Bug列表(筛选)/创建 |
| Bug | /api/bugs/{id} | GET/PUT/DELETE | Bug详情/更新/删除 |
| Bug | /api/bugs/{id}/assign | POST | 指派Bug |
| Bug | /api/bugs/{id}/resolve | POST | 解决Bug |
| Bug | /api/bugs/{id}/close | POST | 关闭Bug |
| Bug | /api/bugs/{id}/reopen | POST | 重新打开Bug |
| Bug | /api/bugs/{id}/comments | POST | 添加评论 |
| 统计 | /api/statistics/overview | GET | 系统概览统计 |
| 健康 | /api/health | GET | 服务健康检查 |

## Bug 状态流转

```
Active → Assigned → Resolved → Verified → Closed
  ↑        ↑  │        ↑  │       ↑  │      │
  │        └──┘        └──┘       └──┘      │
  └──────────────────────────────────────────┘
                    Reopened ←─────────────────┘
```

## 常用命令

```bash
# 查看容器状态
docker compose -f docker/docker-compose.yml ps

# 查看日志
docker logs -f bug-web
docker logs -f bug-mysql

# 停止服务
docker compose -f docker/docker-compose.yml down

# 重启服务
docker compose -f docker/docker-compose.yml restart

# 进入容器
docker exec -it bug-web /bin/bash
```
