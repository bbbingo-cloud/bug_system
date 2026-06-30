# ============================================
# 缺陷管理系统 - Dockerfile
# 适配鲲鹏 ARM 架构（aarch64）
# 基于 FusionCompute 虚拟化平台部署
# ============================================

# 使用 ARM64 兼容的 Python 基础镜像
FROM python:3.9-slim-bullseye

LABEL maintainer="bug-manager-team"
LABEL description="Bug Management System (BugFree-Like) - FusionCompute + Docker"
LABEL platform="linux/arm64"
LABEL version="1.0.0"

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 更新源并安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件
COPY backend/requirements.txt .

# 安装 Python 依赖（使用清华源加速，适合国内鲲鹏环境）
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 复制应用代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY database/ ./database/

# 创建上传目录
RUN mkdir -p uploads && chmod 755 uploads

# 创建非root用户运行应用（安全最佳实践）
RUN useradd -m -s /bin/bash bugapp && chown -R bugapp:bugapp /app
USER bugapp

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 启动应用
CMD ["python", "backend/app.py"]
