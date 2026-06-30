"""
缺陷管理系统 - Flask 主应用
Bug Management System (类 BugFree) 后端 API
基于 FusionCompute 鲲鹏架构 + Docker 容器部署
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify, session, send_from_directory, g
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import *
from models import db, User, Role, Project, Module, Bug, BugLog, BugComment


app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(__name__)
CORS(app, supports_credentials=True)

# 数据库初始化
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

db.init_app(app)

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================
# SQLite 本地开发：自动建表和初始化数据
# ============================================
def init_sqlite_db():
    """SQLite 模式下自动创建表并插入初始数据"""
    with app.app_context():
        db.create_all()
        # 初始化角色
        if Role.query.count() == 0:
            roles = [
                Role(role_name='系统管理员', role_code='admin', description='拥有系统全部权限',
                     permissions='{"user":["create","read","update","delete"],"project":["create","read","update","delete"],"bug":["create","read","update","delete","assign","close"],"system":["manage"]}'),
                Role(role_name='项目经理', role_code='manager', description='可管理项目和Bug',
                     permissions='{"user":["read"],"project":["create","read","update"],"bug":["create","read","update","delete","assign","close"],"system":[]}'),
                Role(role_name='开发工程师', role_code='developer', description='可查看和修复Bug',
                     permissions='{"user":["read"],"project":["read"],"bug":["read","update"],"system":[]}'),
                Role(role_name='测试工程师', role_code='tester', description='可提交和验证Bug',
                     permissions='{"user":["read"],"project":["read"],"bug":["create","read","update"],"system":[]}'),
            ]
            db.session.add_all(roles)
            db.session.flush()

            users = [
                User(username='admin', password=User.hash_password('123456'), real_name='系统管理员',
                     email='admin@bugmanager.com', role_id=roles[0].id, status=1),
                User(username='manager', password=User.hash_password('123456'), real_name='项目经理',
                     email='manager@bugmanager.com', role_id=roles[1].id, status=1),
                User(username='developer', password=User.hash_password('123456'), real_name='开发工程师',
                     email='dev@bugmanager.com', role_id=roles[2].id, status=1),
                User(username='tester', password=User.hash_password('123456'), real_name='测试工程师',
                     email='tester@bugmanager.com', role_id=roles[3].id, status=1),
            ]
            db.session.add_all(users)
            db.session.commit()
            print('[INIT] SQLite 数据库初始化完成（4个角色、4个用户）')


# ============================================
# 辅助函数
# ============================================

def generate_bug_no(project_id):
    """生成Bug编号：BUG-YYYYMMDD-XXX"""
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    count = Bug.query.filter(
        Bug.bug_no.like(f'BUG-{today}-%')
    ).count()
    return f'BUG-{today}-{count + 1:03d}'


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'code': 401, 'message': '请先登录'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.status == 0:
            session.clear()
            return jsonify({'code': 401, 'message': '用户不存在或已禁用'}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def permission_required(module, action):
    """权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'code': 401, 'message': '请先登录'}), 401
            user = User.query.get(session['user_id'])
            if not user:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
            permissions = json.loads(user.role.permissions) if user.role and user.role.permissions else {}
            allowed_actions = permissions.get(module, [])
            if action not in allowed_actions:
                return jsonify({'code': 403, 'message': f'权限不足：需要 {module}.{action} 权限'}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================
# 静态文件服务（前端页面）
# ============================================

@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/<path:path>')
def static_files(path):
    return app.send_static_file(path)


# ============================================
# 用户认证 API
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    if not user.check_password(password):
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    if user.status == 0:
        return jsonify({'code': 403, 'message': '账号已被禁用，请联系管理员'})

    session['user_id'] = user.id
    session['username'] = user.username
    session['role_code'] = user.role.role_code if user.role else None

    # 记录登录日志
    user_info = user.to_dict()
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': user_info
    })


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'code': 200, 'message': '已退出登录'})


@app.route('/api/auth/current_user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    return jsonify({
        'code': 200,
        'data': g.current_user.to_dict()
    })


@app.route('/api/auth/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not g.current_user.check_password(old_password):
        return jsonify({'code': 400, 'message': '原密码错误'})

    if len(new_password) < 6:
        return jsonify({'code': 400, 'message': '新密码长度不能少于6位'})

    g.current_user.password = User.hash_password(new_password)
    db.session.commit()

    return jsonify({'code': 200, 'message': '密码修改成功'})


# ============================================
# 用户管理 API
# ============================================

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """获取用户列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', ITEMS_PER_PAGE, type=int)
    keyword = request.args.get('keyword', '').strip()

    query = User.query
    if keyword:
        query = query.filter(
            db.or_(
                User.username.like(f'%{keyword}%'),
                User.real_name.like(f'%{keyword}%'),
                User.email.like(f'%{keyword}%')
            )
        )

    pagination = query.order_by(User.id.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'code': 200,
        'data': {
            'users': [u.to_dict() for u in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


@app.route('/api/users', methods=['POST'])
@permission_required('user', 'create')
def create_user():
    """创建用户"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '123456')
    real_name = data.get('real_name', '').strip()
    email = data.get('email', '').strip()
    role_id = data.get('role_id')

    if not username or not role_id:
        return jsonify({'code': 400, 'message': '用户名和角色为必填项'})

    if User.query.filter_by(username=username).first():
        return jsonify({'code': 400, 'message': '用户名已存在'})

    user = User(
        username=username,
        password=User.hash_password(password),
        real_name=real_name,
        email=email,
        role_id=role_id,
        status=1
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '用户创建成功',
        'data': user.to_dict()
    })


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@permission_required('user', 'update')
def update_user(user_id):
    """更新用户信息"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'})

    data = request.get_json()
    if 'real_name' in data:
        user.real_name = data['real_name']
    if 'email' in data:
        user.email = data['email']
    if 'phone' in data:
        user.phone = data['phone']
    if 'role_id' in data:
        user.role_id = data['role_id']
    if 'status' in data:
        user.status = data['status']
    if 'password' in data and data['password']:
        user.password = User.hash_password(data['password'])

    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '用户更新成功',
        'data': user.to_dict()
    })


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@permission_required('user', 'delete')
def delete_user(user_id):
    """删除用户"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'})

    # 检查用户是否有关联的Bug
    has_bugs = Bug.query.filter(
        (Bug.created_by == user_id) |
        (Bug.assigned_to == user_id) |
        (Bug.resolved_by == user_id) |
        (Bug.verified_by == user_id)
    ).first()

    if has_bugs:
        return jsonify({'code': 400, 'message': '该用户有关联的Bug记录，无法删除'})

    db.session.delete(user)
    db.session.commit()

    return jsonify({'code': 200, 'message': '用户已删除'})


# ============================================
# 角色管理 API
# ============================================

@app.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    """获取角色列表"""
    roles = Role.query.all()
    return jsonify({
        'code': 200,
        'data': [r.to_dict() for r in roles]
    })


# ============================================
# 项目管理 API
# ============================================

@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    """获取项目列表"""
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', type=int)

    query = Project.query
    if keyword:
        query = query.filter(
            db.or_(
                Project.project_name.like(f'%{keyword}%'),
                Project.project_code.like(f'%{keyword}%')
            )
        )
    if status is not None:
        query = query.filter(Project.status == status)

    projects = query.order_by(Project.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'data': [p.to_dict() for p in projects]
    })


@app.route('/api/projects', methods=['POST'])
@permission_required('project', 'create')
def create_project():
    """创建项目"""
    data = request.get_json()
    project_name = data.get('project_name', '').strip()
    project_code = data.get('project_code', '').strip()
    description = data.get('description', '')
    manager_id = data.get('manager_id')

    if not project_name or not project_code:
        return jsonify({'code': 400, 'message': '项目名称和编码为必填项'})

    if Project.query.filter_by(project_code=project_code).first():
        return jsonify({'code': 400, 'message': '项目编码已存在'})

    project = Project(
        project_name=project_name,
        project_code=project_code,
        description=description,
        manager_id=manager_id,
        status=1
    )
    db.session.add(project)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '项目创建成功',
        'data': project.to_dict()
    })


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@permission_required('project', 'update')
def update_project(project_id):
    """更新项目"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'code': 404, 'message': '项目不存在'})

    data = request.get_json()
    if 'project_name' in data:
        project.project_name = data['project_name']
    if 'description' in data:
        project.description = data['description']
    if 'manager_id' in data:
        project.manager_id = data['manager_id']
    if 'status' in data:
        project.status = data['status']

    db.session.commit()
    return jsonify({
        'code': 200,
        'message': '项目更新成功',
        'data': project.to_dict()
    })


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@permission_required('project', 'delete')
def delete_project(project_id):
    """删除项目"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'code': 404, 'message': '项目不存在'})

    if project.bugs and len(project.bugs) > 0:
        return jsonify({'code': 400, 'message': f'该项目下还有 {len(project.bugs)} 个Bug，无法删除'})

    db.session.delete(project)
    db.session.commit()
    return jsonify({'code': 200, 'message': '项目已删除'})


# ============================================
# 模块管理 API
# ============================================

@app.route('/api/projects/<int:project_id>/modules', methods=['GET'])
@login_required
def get_modules(project_id):
    """获取项目模块列表"""
    modules = Module.query.filter_by(project_id=project_id).order_by(Module.id.asc()).all()
    return jsonify({
        'code': 200,
        'data': [m.to_dict() for m in modules]
    })


@app.route('/api/projects/<int:project_id>/modules', methods=['POST'])
@login_required
def create_module(project_id):
    """创建模块"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'code': 404, 'message': '项目不存在'})

    data = request.get_json()
    module_name = data.get('module_name', '').strip()
    description = data.get('description', '')

    if not module_name:
        return jsonify({'code': 400, 'message': '模块名称不能为空'})

    module = Module(
        module_name=module_name,
        project_id=project_id,
        description=description
    )
    db.session.add(module)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '模块创建成功',
        'data': module.to_dict()
    })


# ============================================
# Bug 管理 API（核心功能）
# ============================================

@app.route('/api/bugs', methods=['GET'])
@login_required
def get_bugs():
    """获取Bug列表（支持多条件筛选和分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', ITEMS_PER_PAGE, type=int)

    # 筛选条件
    project_id = request.args.get('project_id', type=int)
    module_id = request.args.get('module_id', type=int)
    status = request.args.get('status')
    severity = request.args.get('severity')
    priority = request.args.get('priority')
    bug_type = request.args.get('bug_type')
    assigned_to = request.args.get('assigned_to', type=int)
    created_by = request.args.get('created_by', type=int)
    keyword = request.args.get('keyword', '').strip()

    query = Bug.query

    if project_id:
        query = query.filter(Bug.project_id == project_id)
    if module_id:
        query = query.filter(Bug.module_id == module_id)
    if status:
        query = query.filter(Bug.status == status)
    if severity:
        query = query.filter(Bug.severity == severity)
    if priority:
        query = query.filter(Bug.priority == priority)
    if bug_type:
        query = query.filter(Bug.bug_type == bug_type)
    if assigned_to:
        query = query.filter(Bug.assigned_to == assigned_to)
    if created_by:
        query = query.filter(Bug.created_by == created_by)
    if keyword:
        query = query.filter(
            db.or_(
                Bug.bug_title.like(f'%{keyword}%'),
                Bug.bug_no.like(f'%{keyword}%'),
                Bug.description.like(f'%{keyword}%')
            )
        )

    pagination = query.order_by(Bug.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'code': 200,
        'data': {
            'bugs': [b.to_dict() for b in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


@app.route('/api/bugs/<int:bug_id>', methods=['GET'])
@login_required
def get_bug_detail(bug_id):
    """获取Bug详情（含操作日志和评论）"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    return jsonify({
        'code': 200,
        'data': {
            'bug': bug.to_dict(),
            'logs': [log.to_dict() for log in bug.logs],
            'comments': [c.to_dict() for c in bug.comments]
        }
    })


@app.route('/api/bugs', methods=['POST'])
@permission_required('bug', 'create')
def create_bug():
    """创建Bug"""
    data = request.get_json()

    bug_title = data.get('bug_title', '').strip()
    project_id = data.get('project_id')
    module_id = data.get('module_id')

    if not bug_title or not project_id:
        return jsonify({'code': 400, 'message': 'Bug标题和所属项目为必填项'})

    # 检查项目是否存在
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'code': 404, 'message': '项目不存在'})

    bug_no = generate_bug_no(project_id)

    bug = Bug(
        bug_title=bug_title,
        bug_no=bug_no,
        project_id=project_id,
        module_id=module_id,
        severity=data.get('severity', '3-一般'),
        priority=data.get('priority', '3-中'),
        bug_type=data.get('bug_type', '功能缺陷'),
        status='Active',
        created_by=g.current_user.id,
        assigned_to=data.get('assigned_to'),
        description=data.get('description', ''),
        steps_to_reproduce=data.get('steps_to_reproduce', ''),
        environment_info=data.get('environment_info', '')
    )
    db.session.add(bug)
    db.session.flush()  # 获取 bug.id

    # 记录操作日志
    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='create',
        new_value=json.dumps({'bug_title': bug_title, 'bug_no': bug_no}, ensure_ascii=False),
        comment=f'创建了Bug {bug_no}'
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': 'Bug创建成功',
        'data': bug.to_dict()
    })


@app.route('/api/bugs/<int:bug_id>', methods=['PUT'])
@permission_required('bug', 'update')
def update_bug(bug_id):
    """更新Bug信息"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()
    old_values = json.dumps({
        'bug_title': bug.bug_title,
        'severity': bug.severity,
        'priority': bug.priority,
        'bug_type': bug.bug_type,
        'status': bug.status,
        'assigned_to': bug.assigned_to
    }, ensure_ascii=False)

    changes = []
    if 'bug_title' in data:
        changes.append(f"标题: {bug.bug_title} → {data['bug_title']}")
        bug.bug_title = data['bug_title']
    if 'severity' in data and data['severity'] != bug.severity:
        changes.append(f"严重程度: {bug.severity} → {data['severity']}")
        bug.severity = data['severity']
    if 'priority' in data and data['priority'] != bug.priority:
        changes.append(f"优先级: {bug.priority} → {data['priority']}")
        bug.priority = data['priority']
    if 'bug_type' in data:
        bug.bug_type = data['bug_type']
    if 'description' in data:
        bug.description = data['description']
    if 'steps_to_reproduce' in data:
        bug.steps_to_reproduce = data['steps_to_reproduce']
    if 'environment_info' in data:
        bug.environment_info = data['environment_info']
    if 'module_id' in data:
        bug.module_id = data['module_id']
    if 'assigned_to' in data:
        changes.append(f"指派: {bug.assigned_to} → {data['assigned_to']}")
        bug.assigned_to = data['assigned_to']
    if 'resolution' in data:
        bug.resolution = data['resolution']

    # 状态流转处理
    if 'status' in data and data['status'] != bug.status:
        new_status = data['status']
        if not Bug.can_change_status(bug.status, new_status):
            return jsonify({
                'code': 400,
                'message': f'不允许从 {bug.status} 流转到 {new_status}'
            })

        changes.append(f"状态: {bug.status} → {new_status}")
        bug.status = new_status

        # 根据状态变化更新时间和人员
        if new_status == 'Assigned':
            if not bug.assigned_to:
                return jsonify({'code': 400, 'message': '指派Bug时请选择指派人'})
        elif new_status == 'Resolved':
            bug.resolved_by = g.current_user.id
            bug.resolved_at = datetime.now(timezone.utc)
            if not bug.resolution:
                bug.resolution = 'Fixed'
        elif new_status == 'Verified':
            bug.verified_by = g.current_user.id
        elif new_status == 'Closed':
            bug.closed_at = datetime.now(timezone.utc)

    # 记录操作日志
    new_values = json.dumps({
        'bug_title': bug.bug_title,
        'severity': bug.severity,
        'priority': bug.priority,
        'bug_type': bug.bug_type,
        'status': bug.status,
        'assigned_to': bug.assigned_to
    }, ensure_ascii=False)

    comment_text = data.get('comment', '')
    if changes:
        comment_text = '; '.join(changes) + (f' | 备注: {data.get("comment", "")}' if data.get('comment') else '')

    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='update',
        old_value=old_values,
        new_value=new_values,
        comment=comment_text
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': 'Bug更新成功',
        'data': bug.to_dict()
    })


@app.route('/api/bugs/<int:bug_id>', methods=['DELETE'])
@permission_required('bug', 'delete')
def delete_bug(bug_id):
    """删除Bug"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    db.session.delete(bug)
    db.session.commit()
    return jsonify({'code': 200, 'message': 'Bug已删除'})


# ============================================
# Bug 状态流转 API
# ============================================

@app.route('/api/bugs/<int:bug_id>/assign', methods=['POST'])
@permission_required('bug', 'assign')
def assign_bug(bug_id):
    """指派Bug"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()
    assigned_to = data.get('assigned_to')

    if not assigned_to:
        return jsonify({'code': 400, 'message': '请选择指派人'})

    if not Bug.can_change_status(bug.status, 'Assigned'):
        return jsonify({'code': 400, 'message': f'当前状态 {bug.status} 不允许指派'})

    old_status = bug.status
    bug.status = 'Assigned'
    bug.assigned_to = assigned_to

    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='assign',
        old_value=json.dumps({'status': old_status, 'assigned_to': None}, ensure_ascii=False),
        new_value=json.dumps({'status': 'Assigned', 'assigned_to': assigned_to}, ensure_ascii=False),
        comment=data.get('comment', f'Bug已指派给用户{assigned_to}')
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': 'Bug指派成功', 'data': bug.to_dict()})


@app.route('/api/bugs/<int:bug_id>/resolve', methods=['POST'])
@permission_required('bug', 'update')
def resolve_bug(bug_id):
    """解决Bug"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()
    resolution = data.get('resolution', 'Fixed')

    if not Bug.can_change_status(bug.status, 'Resolved'):
        return jsonify({'code': 400, 'message': f'当前状态 {bug.status} 不允许设为已解决'})

    old_status = bug.status
    bug.status = 'Resolved'
    bug.resolution = resolution
    bug.resolved_by = g.current_user.id
    bug.resolved_at = datetime.now(timezone.utc)

    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='resolve',
        old_value=json.dumps({'status': old_status, 'resolution': None}, ensure_ascii=False),
        new_value=json.dumps({'status': 'Resolved', 'resolution': resolution}, ensure_ascii=False),
        comment=data.get('comment', f'Bug已解决：{resolution}')
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': 'Bug已标记为已解决', 'data': bug.to_dict()})


@app.route('/api/bugs/<int:bug_id>/close', methods=['POST'])
@permission_required('bug', 'close')
def close_bug(bug_id):
    """关闭Bug"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()

    if not Bug.can_change_status(bug.status, 'Closed'):
        return jsonify({'code': 400, 'message': f'当前状态 {bug.status} 不允许关闭'})

    old_status = bug.status
    bug.status = 'Closed'
    bug.closed_at = datetime.now(timezone.utc)

    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='close',
        old_value=json.dumps({'status': old_status}, ensure_ascii=False),
        new_value=json.dumps({'status': 'Closed'}, ensure_ascii=False),
        comment=data.get('comment', 'Bug已关闭')
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': 'Bug已关闭', 'data': bug.to_dict()})


@app.route('/api/bugs/<int:bug_id>/reopen', methods=['POST'])
@permission_required('bug', 'update')
def reopen_bug(bug_id):
    """重新打开Bug"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()

    if not Bug.can_change_status(bug.status, 'Reopened'):
        return jsonify({'code': 400, 'message': f'当前状态 {bug.status} 不允许重新打开'})

    old_status = bug.status
    bug.status = 'Reopened'

    log = BugLog(
        bug_id=bug.id,
        user_id=g.current_user.id,
        action_type='reopen',
        old_value=json.dumps({'status': old_status}, ensure_ascii=False),
        new_value=json.dumps({'status': 'Reopened'}, ensure_ascii=False),
        comment=data.get('comment', 'Bug已重新打开')
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': 'Bug已重新打开', 'data': bug.to_dict()})


# ============================================
# Bug 评论 API
# ============================================

@app.route('/api/bugs/<int:bug_id>/comments', methods=['POST'])
@login_required
def add_comment(bug_id):
    """添加Bug评论"""
    bug = Bug.query.get(bug_id)
    if not bug:
        return jsonify({'code': 404, 'message': 'Bug不存在'})

    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'code': 400, 'message': '评论内容不能为空'})

    comment = BugComment(
        bug_id=bug_id,
        user_id=g.current_user.id,
        content=content
    )
    db.session.add(comment)

    # 同时记录操作日志
    log = BugLog(
        bug_id=bug_id,
        user_id=g.current_user.id,
        action_type='comment',
        comment=f'添加了评论: {content[:100]}'
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '评论添加成功',
        'data': comment.to_dict()
    })


# ============================================
# 文件上传 API
# ============================================

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """上传附件"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请选择文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 400, 'message': '请选择文件'})

    if not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': f'不支持的文件类型，允许：{",".join(ALLOWED_EXTENSIONS)}'})

    filename = secure_filename(file.filename)
    # 添加UUID前缀避免文件名冲突
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    return jsonify({
        'code': 200,
        'message': '文件上传成功',
        'data': {
            'filename': filename,
            'unique_filename': unique_filename,
            'path': f'/uploads/{unique_filename}',
            'size': os.path.getsize(file_path)
        }
    })


@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    """下载附件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================
# 数据统计 API
# ============================================

@app.route('/api/statistics/overview', methods=['GET'])
@login_required
def get_statistics():
    """获取系统概览统计数据"""
    total_bugs = Bug.query.count()
    total_projects = Project.query.count()
    total_users = User.query.count()

    # 按状态统计
    status_stats = db.session.query(
        Bug.status, db.func.count(Bug.id)
    ).group_by(Bug.status).all()
    status_data = {s: c for s, c in status_stats}

    # 按严重程度统计
    severity_stats = db.session.query(
        Bug.severity, db.func.count(Bug.id)
    ).group_by(Bug.severity).all()
    severity_data = {s: c for s, c in severity_stats}

    # 按优先级统计
    priority_stats = db.session.query(
        Bug.priority, db.func.count(Bug.id)
    ).group_by(Bug.priority).all()
    priority_data = {p: c for p, c in priority_stats}

    # 按项目统计
    project_stats = db.session.query(
        Project.project_name, db.func.count(Bug.id)
    ).outerjoin(Bug).group_by(Project.id).all()
    project_data = [{'name': name, 'count': count} for name, count in project_stats]

    return jsonify({
        'code': 200,
        'data': {
            'total_bugs': total_bugs,
            'total_projects': total_projects,
            'total_users': total_users,
            'status_stats': status_data,
            'severity_stats': severity_data,
            'priority_stats': priority_data,
            'project_stats': project_data
        }
    })


@app.route('/api/statistics/bugs', methods=['GET'])
@login_required
def get_bug_statistics():
    """获取Bug详细统计"""
    project_id = request.args.get('project_id', type=int)

    base_query = Bug.query
    if project_id:
        base_query = base_query.filter(Bug.project_id == project_id)

    bugs = base_query.all()

    # 按类型统计
    type_stats = {}
    for bug in bugs:
        bug_type = bug.bug_type or '未分类'
        type_stats[bug_type] = type_stats.get(bug_type, 0) + 1

    # 按指派人统计
    assignee_stats = db.session.query(
        User.real_name, db.func.count(Bug.id)
    ).join(Bug, Bug.assigned_to == User.id).filter(
        Bug.project_id == project_id if project_id else True
    ).group_by(User.id).all()

    return jsonify({
        'code': 200,
        'data': {
            'total': len(bugs),
            'type_stats': type_stats,
            'assignee_stats': [{'name': name, 'count': count} for name, count in assignee_stats]
        }
    })


# ============================================
# 健康检查 API（Docker 容器探活）
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """容器健康检查接口"""
    try:
        # 测试数据库连接
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'

    return jsonify({
        'status': 'running',
        'service': 'Bug Management System',
        'version': '1.0.0',
        'platform': 'FusionCompute + Docker',
        'architecture': 'Kunpeng ARM',
        'database': db_status,
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    })


# ============================================
# 应用启动
# ============================================

if __name__ == '__main__':
    # SQLite 模式自动初始化
    if DB_ENGINE == 'sqlite':
        init_sqlite_db()

    # 开发环境使用 debug 模式
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
