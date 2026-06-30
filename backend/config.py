"""
缺陷管理系统 - 配置文件
基于 FusionCompute + Docker 容器部署，适配鲲鹏 ARM 架构
"""

import os

# ============================================
# 基础配置
# ============================================
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'bug-manager-secret-key-2024-kunpeng')

# ============================================
# 数据库配置
# 生产环境: MySQL（Docker Compose 部署，适配鲲鹏 ARM）
# 开发环境: SQLite（本地调试，无需安装 MySQL）
# ============================================
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite')  # sqlite / mysql

if DB_ENGINE == 'mysql':
    DB_HOST = os.environ.get('DB_HOST', 'mysql')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'buguser')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'BugManager@2024')
    DB_NAME = os.environ.get('DB_NAME', 'bug_manager')
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
else:
    # 本地开发使用 SQLite，零配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bug_manager.db')

SQLALCHEMY_TRACK_MODIFICATIONS = False

# ============================================
# 文件上传配置
# ============================================
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf', 'txt', 'zip', 'rar', 'doc', 'docx', 'xls', 'xlsx'}

# ============================================
# 分页配置
# ============================================
ITEMS_PER_PAGE = 15

# ============================================
# 日志配置
# ============================================
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
