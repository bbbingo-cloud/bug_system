#!/bin/bash
# ============================================
# 缺陷管理系统 - 一键部署脚本
# 在 FusionCompute 鲲鹏 ARM 虚拟机上执行
# ============================================

set -e

echo "============================================"
echo "  缺陷管理系统 - 容器化部署脚本"
echo "  Platform: FusionCompute + Docker"
echo "  Arch: Kunpeng ARM (aarch64)"
echo "============================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查系统架构
echo "[INFO] 检查系统架构..."
ARCH=$(uname -m)
echo "  当前架构: $ARCH"
if [[ "$ARCH" != "aarch64" ]] && [[ "$ARCH" != "arm64" ]] && [[ "$ARCH" != "armv7l" ]]; then
    echo -e "${YELLOW}[WARN] 非ARM架构，但可继续使用Docker部署${NC}"
fi

# 检查 Docker 是否安装
echo ""
echo "[INFO] 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker 未安装！${NC}"
    echo "请先安装 Docker（适配鲲鹏 ARM）："
    echo "  CentOS/OpenEuler: yum install -y docker-ce"
    echo "  Ubuntu: apt-get install -y docker.io"
    exit 1
fi
echo -e "${GREEN}  Docker 版本: $(docker --version)${NC}"

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose 未安装！${NC}"
    echo "请先安装 Docker Compose"
    exit 1
fi
echo -e "${GREEN}  Docker Compose 已就绪${NC}"

# 检查 Docker 服务状态
if ! docker info &> /dev/null; then
    echo -e "${RED}[ERROR] Docker 服务未运行，请启动 Docker 服务${NC}"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
echo ""
echo "[INFO] 项目目录: $PROJECT_DIR"

cd "$PROJECT_DIR"

# 停止并清理已有容器（如果存在）
echo ""
echo "[INFO] 清理已有容器..."
docker compose -f docker/docker-compose.yml down 2>/dev/null || true
echo -e "${GREEN}  清理完成${NC}"

# 构建镜像
echo ""
echo "[INFO] 开始构建 Docker 镜像..."
echo "  （首次构建可能需要几分钟，请耐心等待）"
docker compose -f docker/docker-compose.yml build --no-cache
echo -e "${GREEN}  镜像构建完成${NC}"

# 启动容器
echo ""
echo "[INFO] 启动容器服务..."
docker compose -f docker/docker-compose.yml up -d
echo -e "${GREEN}  容器启动完成${NC}"

# 等待服务就绪
echo ""
echo "[INFO] 等待服务就绪..."
sleep 10

# 检查 MySQL 容器状态
if docker ps --format '{{.Names}}' | grep -q "bug-mysql"; then
    echo -e "${GREEN}  MySQL 容器运行中${NC}"
else
    echo -e "${RED}[ERROR] MySQL 容器启动失败${NC}"
    docker logs bug-mysql --tail 20
    exit 1
fi

# 检查 Web 容器状态
if docker ps --format '{{.Names}}' | grep -q "bug-web"; then
    echo -e "${GREEN}  Web 容器运行中${NC}"
else
    echo -e "${RED}[ERROR] Web 容器启动失败${NC}"
    docker logs bug-web --tail 20
    exit 1
fi

# 健康检查
echo ""
echo "[INFO] 执行健康检查..."
sleep 5
HEALTH_CHECK=$(curl -s http://localhost:5000/api/health 2>/dev/null || echo "{}")
if echo "$HEALTH_CHECK" | grep -q "running"; then
    echo -e "${GREEN}  服务健康检查通过！${NC}"
else
    echo -e "${YELLOW}[WARN] 健康检查未通过，请检查日志${NC}"
fi

# 输出部署信息
echo ""
echo "============================================"
echo -e "${GREEN}  部署完成！${NC}"
echo "============================================"
echo ""
echo "  访问地址:"
echo "    Bug管理系统:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):5000"
echo "    MySQL数据库:  $(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):3306"
echo ""
echo "  测试账号:"
echo "    管理员:  admin / 123456"
echo "    项目经理: manager / 123456"
echo "    开发工程师: developer / 123456"
echo "    测试工程师: tester / 123456"
echo ""
echo "  常用命令:"
echo "    查看容器状态:  docker compose -f docker/docker-compose.yml ps"
echo "    查看Web日志:   docker logs -f bug-web"
echo "    查看MySQL日志: docker logs -f bug-mysql"
echo "    停止服务:      docker compose -f docker/docker-compose.yml down"
echo "    重启服务:      docker compose -f docker/docker-compose.yml restart"
echo "    进入Web容器:   docker exec -it bug-web /bin/bash"
echo ""
echo "============================================"
