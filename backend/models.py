"""
缺陷管理系统 - 数据模型定义
使用 SQLAlchemy ORM 映射数据库表
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import hashlib

# Python 3.12+ 兼容：使用 timezone-aware datetime
def utcnow():
    return datetime.now(timezone.utc)

db = SQLAlchemy()


class Role(db.Model):
    """角色表"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    role_code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=utcnow)

    users = db.relationship('User', backref='role', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'role_name': self.role_name,
            'role_code': self.role_code,
            'description': self.description,
            'permissions': self.permissions
        }


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # SHA256 hash
    real_name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    created_bugs = db.relationship('Bug', foreign_keys='Bug.created_by', backref='creator', lazy=True)
    assigned_bugs = db.relationship('Bug', foreign_keys='Bug.assigned_to', backref='assignee', lazy=True)
    resolved_bugs = db.relationship('Bug', foreign_keys='Bug.resolved_by', backref='resolver', lazy=True)

    @staticmethod
    def hash_password(password):
        """SHA256 密码加密"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """验证密码"""
        return self.password == self.hash_password(password)

    def to_dict(self, include_password=False):
        data = {
            'id': self.id,
            'username': self.username,
            'real_name': self.real_name,
            'email': self.email,
            'phone': self.phone,
            'role_id': self.role_id,
            'role_name': self.role.role_name if self.role else None,
            'role_code': self.role.role_code if self.role else None,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
        if include_password:
            data['password'] = self.password
        return data


class Project(db.Model):
    """项目表"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_name = db.Column(db.String(100), nullable=False)
    project_code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_projects')
    modules = db.relationship('Module', backref='project', lazy=True, cascade='all, delete-orphan')
    bugs = db.relationship('Bug', backref='project', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'project_name': self.project_name,
            'project_code': self.project_code,
            'description': self.description,
            'manager_id': self.manager_id,
            'manager_name': self.manager.real_name if self.manager else None,
            'status': self.status,
            'bug_count': len(self.bugs) if self.bugs else 0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Module(db.Model):
    """模块表"""
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)

    bugs = db.relationship('Bug', backref='module', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'module_name': self.module_name,
            'project_id': self.project_id,
            'description': self.description,
            'bug_count': len(self.bugs) if self.bugs else 0
        }


class Bug(db.Model):
    """Bug缺陷表"""
    __tablename__ = 'bugs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bug_title = db.Column(db.String(255), nullable=False)
    bug_no = db.Column(db.String(50), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))

    severity = db.Column(db.Enum('1-致命', '2-严重', '3-一般', '4-轻微', '5-建议'), default='3-一般')
    priority = db.Column(db.Enum('1-紧急', '2-高', '3-中', '4-低'), default='3-中')
    bug_type = db.Column(db.Enum('功能缺陷', '界面问题', '性能问题', '安全问题', '兼容性问题', '文档问题', '其他'), default='功能缺陷')

    status = db.Column(db.Enum('Active', 'Assigned', 'Resolved', 'Verified', 'Closed', 'Reopened'), default='Active')
    resolution = db.Column(db.Enum('Fixed', 'Duplicated', 'NotABug', 'WontFix', 'Later', 'WorksForMe', 'External', 'Unresolved'))

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    description = db.Column(db.Text)
    steps_to_reproduce = db.Column(db.Text)
    environment_info = db.Column(db.String(500))
    attachment_path = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    logs = db.relationship('BugLog', backref='bug', lazy=True, cascade='all, delete-orphan', order_by='BugLog.created_at.desc()')
    comments = db.relationship('BugComment', backref='bug', lazy=True, cascade='all, delete-orphan', order_by='BugComment.created_at.asc()')

    # Status flow definition: from status -> allowed next statuses
    STATUS_FLOW = {
        'Active': ['Assigned', 'Closed'],
        'Assigned': ['Resolved', 'Active'],
        'Resolved': ['Verified', 'Assigned'],
        'Verified': ['Closed', 'Assigned'],
        'Closed': ['Reopened'],
        'Reopened': ['Assigned']
    }

    @classmethod
    def can_change_status(cls, from_status, to_status):
        """检查状态流转是否合法"""
        return to_status in cls.STATUS_FLOW.get(from_status, [])

    def to_dict(self):
        return {
            'id': self.id,
            'bug_title': self.bug_title,
            'bug_no': self.bug_no,
            'project_id': self.project_id,
            'project_name': self.project.project_name if self.project else None,
            'module_id': self.module_id,
            'module_name': self.module.module_name if self.module else None,
            'severity': self.severity,
            'priority': self.priority,
            'bug_type': self.bug_type,
            'status': self.status,
            'resolution': self.resolution,
            'created_by': self.created_by,
            'creator_name': self.creator.real_name if self.creator else None,
            'assigned_to': self.assigned_to,
            'assignee_name': self.assignee.real_name if self.assignee else None,
            'resolved_by': self.resolved_by,
            'resolver_name': self.resolver.real_name if self.resolver else None,
            'verified_by': self.verified_by,
            'description': self.description,
            'steps_to_reproduce': self.steps_to_reproduce,
            'environment_info': self.environment_info,
            'attachment_path': self.attachment_path,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if self.resolved_at else None,
            'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None,
            'comments_count': len(self.comments) if self.comments else 0
        }


class BugLog(db.Model):
    """Bug操作日志表"""
    __tablename__ = 'bug_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bug_id = db.Column(db.Integer, db.ForeignKey('bugs.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'bug_id': self.bug_id,
            'user_id': self.user_id,
            'user_name': self.user.real_name if self.user else None,
            'action_type': self.action_type,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'comment': self.comment,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class BugComment(db.Model):
    """Bug评论表"""
    __tablename__ = 'bug_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bug_id = db.Column(db.Integer, db.ForeignKey('bugs.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'bug_id': self.bug_id,
            'user_id': self.user_id,
            'user_name': self.user.real_name if self.user else None,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
