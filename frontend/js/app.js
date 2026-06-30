/**
 * 缺陷管理系统 - 前端主逻辑
 * Bug Management System (类 BugFree)
 * FusionCompute + Docker 容器部署 | 鲲鹏 ARM 架构
 */

// ============================================
// 全局状态
// ============================================
const API_BASE = '/api';
let currentUser = null;
let currentPage = 'dashboard';
let bugsPageNum = 1;
let debounceTimer = null;

// ============================================
// 初始化
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // 登录表单事件
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    // 检查是否已登录
    checkAuth();
});

// ============================================
// 认证相关
// ============================================
async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/auth/current_user`);
        if (res.ok) {
            const data = await res.json();
            if (data.code === 200) {
                currentUser = data.data;
                showMainPage();
                return;
            }
        }
    } catch (e) {}
    showLoginPage();
}

function showLoginPage() {
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('loginError').style.display = 'none';
}

function showMainPage() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('mainPage').style.display = 'block';
    document.getElementById('currentUserName').textContent = currentUser.real_name || currentUser.username;
    document.getElementById('currentUserRole').textContent = currentUser.role_name || '';
    // 只有管理员显示用户管理
    if (currentUser.role_code === 'admin') {
        document.getElementById('userMgmtNav').style.display = '';
    }
    switchPage('dashboard');
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (data.code === 200) {
            currentUser = data.data;
            showMainPage();
        } else {
            showLoginError(data.message);
        }
    } catch (e) {
        showLoginError('网络连接失败，请检查服务器是否正常运行');
    }
}

function showLoginError(msg) {
    const el = document.getElementById('loginError');
    el.textContent = msg;
    el.style.display = 'block';
}

async function logout() {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    currentUser = null;
    showLoginPage();
}

// ============================================
// 页面切换
// ============================================
function switchPage(page) {
    currentPage = page;
    document.querySelectorAll('.page-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));

    const pageEl = document.getElementById(page + 'Page');
    if (pageEl) pageEl.style.display = '';

    // 根据页面更新导航高亮
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('onclick')?.includes(`'${page}'`)) {
            link.classList.add('active');
        }
    });

    // 加载页面数据
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'bugs': loadBugs(); loadProjectFilter(); break;
        case 'projects': loadProjects(); break;
        case 'users': loadUsers(); break;
    }
}

// ============================================
// 仪表盘
// ============================================
async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/statistics/overview`);
        const data = await res.json();
        if (data.code !== 200) return;

        const stats = data.data;
        document.getElementById('statTotalBugs').textContent = stats.total_bugs || 0;
        document.getElementById('statTotalProjects').textContent = stats.total_projects || 0;
        document.getElementById('statTotalUsers').textContent = stats.total_users || 0;

        // 计算未解决Bug数（非Closed状态）
        let activeBugs = 0;
        if (stats.status_stats) {
            for (const [status, count] of Object.entries(stats.status_stats)) {
                if (status !== 'Closed') activeBugs += (count || 0);
            }
        }
        document.getElementById('statActiveBugs').textContent = activeBugs;

        // 状态分布图表
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        if (window._statusChart) window._statusChart.destroy();
        window._statusChart = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Active', 'Assigned', 'Resolved', 'Verified', 'Closed', 'Reopened'],
                datasets: [{
                    data: [
                        stats.status_stats?.Active || 0,
                        stats.status_stats?.Assigned || 0,
                        stats.status_stats?.Resolved || 0,
                        stats.status_stats?.Verified || 0,
                        stats.status_stats?.Closed || 0,
                        stats.status_stats?.Reopened || 0
                    ],
                    backgroundColor: ['#0d6efd', '#6f42c1', '#198754', '#20c997', '#6c757d', '#fd7e14']
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });

        // 严重程度分布图表
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        if (window._severityChart) window._severityChart.destroy();
        window._severityChart = new Chart(severityCtx, {
            type: 'bar',
            data: {
                labels: ['致命', '严重', '一般', '轻微', '建议'],
                datasets: [{
                    label: 'Bug数量',
                    data: [
                        stats.severity_stats?.['1-致命'] || 0,
                        stats.severity_stats?.['2-严重'] || 0,
                        stats.severity_stats?.['3-一般'] || 0,
                        stats.severity_stats?.['4-轻微'] || 0,
                        stats.severity_stats?.['5-建议'] || 0
                    ],
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#0dcaf0', '#6c757d']
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    } catch (e) {
        console.error('加载仪表盘失败', e);
    }
}

// ============================================
// Bug 管理
// ============================================
async function loadProjectFilter() {
    try {
        const res = await fetch(`${API_BASE}/projects`);
        const data = await res.json();
        if (data.code === 200) {
            const sel = document.getElementById('filterProject');
            const currentVal = sel.value;
            sel.innerHTML = '<option value="">全部项目</option>';
            data.data.forEach(p => {
                sel.innerHTML += `<option value="${p.id}">${p.project_name}</option>`;
            });
            if (currentVal) sel.value = currentVal;
        }
    } catch (e) {}
}

async function loadBugs(page = 1) {
    bugsPageNum = page;
    const projectId = document.getElementById('filterProject').value;
    const status = document.getElementById('filterStatus').value;
    const severity = document.getElementById('filterSeverity').value;
    const keyword = document.getElementById('filterKeyword').value;

    const params = new URLSearchParams({ page, per_page: 15 });
    if (projectId) params.set('project_id', projectId);
    if (status) params.set('status', status);
    if (severity) params.set('severity', severity);
    if (keyword) params.set('keyword', keyword);

    try {
        const res = await fetch(`${API_BASE}/bugs?${params}`);
        const data = await res.json();
        if (data.code !== 200) return;

        const tbody = document.getElementById('bugsTableBody');
        tbody.innerHTML = data.data.bugs.map(bug => renderBugRow(bug)).join('');

        // 分页
        renderPagination('bugsPagination', data.data.page, data.data.pages, loadBugs);

        document.getElementById('bugsPage').style.display = '';
    } catch (e) {
        console.error('加载Bug列表失败', e);
    }
}

function renderBugRow(bug) {
    const statusClass = bug.status || 'Active';
    const sevCode = (bug.severity || '').replace(/[^a-zA-Z0-9一-龥]/g, '-');
    const priCode = (bug.priority || '').replace(/[^a-zA-Z0-9一-龥]/g, '-');

    return `
    <tr>
        <td><span class="text-monospace">${bug.bug_no || ''}</span></td>
        <td>
            <a href="javascript:void(0)" onclick="showBugDetail(${bug.id})" style="cursor:pointer; color:#0d6efd;">
                ${escapeHtml(bug.bug_title || '')}
            </a>
            ${bug.comments_count > 0 ? `<span class="badge bg-secondary ms-1">${bug.comments_count}</span>` : ''}
        </td>
        <td><span class="badge bg-secondary">${escapeHtml(bug.project_name || '')}</span></td>
        <td><span class="badge badge-severity-${sevCode}">${bug.severity || ''}</span></td>
        <td><span class="badge badge-priority-${priCode}">${bug.priority || ''}</span></td>
        <td><span class="badge badge-${statusClass} badge-status">${bug.status || ''}</span></td>
        <td>${escapeHtml(bug.assignee_name || '未指派')}</td>
        <td>${escapeHtml(bug.creator_name || '')}</td>
        <td>${bug.created_at || ''}</td>
        <td>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-info btn-sm" onclick="showBugDetail(${bug.id})" title="查看详情">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-outline-warning btn-sm" onclick="editBug(${bug.id})" title="编辑">
                    <i class="bi bi-pencil"></i>
                </button>
                ${renderStatusButtons(bug)}
                ${canDeleteBug() ? `<button class="btn btn-outline-danger btn-sm" onclick="deleteBug(${bug.id}, '${escapeHtml(bug.bug_no)}')" title="删除"><i class="bi bi-trash"></i></button>` : ''}
            </div>
        </td>
    </tr>`;
}

function renderStatusButtons(bug) {
    let btns = '';
    const status = bug.status;

    if (status === 'Active' || status === 'Reopened') {
        btns += `<button class="btn btn-outline-purple btn-sm" onclick="showStatusChange(${bug.id}, 'assign')" title="指派"><i class="bi bi-person-check"></i></button>`;
    }
    if (status === 'Assigned') {
        btns += `<button class="btn btn-outline-success btn-sm" onclick="showStatusChange(${bug.id}, 'resolve')" title="解决"><i class="bi bi-check-circle"></i></button>`;
    }
    if (status === 'Resolved') {
        btns += `<button class="btn btn-outline-teal btn-sm" onclick="showStatusChange(${bug.id}, 'close')" title="关闭"><i class="bi bi-check-circle-fill"></i></button>`;
    }
    if (status === 'Closed') {
        btns += `<button class="btn btn-outline-warning btn-sm" onclick="showStatusChange(${bug.id}, 'reopen')" title="重新打开"><i class="bi bi-arrow-repeat"></i></button>`;
    }

    return btns;
}

function canDeleteBug() {
    return currentUser && ['admin', 'manager'].includes(currentUser.role_code);
}

async function showBugCreateModal() {
    document.getElementById('bugModalTitle').textContent = '提交Bug';
    document.getElementById('bugForm').reset();
    document.getElementById('bugId').value = '';
    document.getElementById('bugModule').innerHTML = '<option value="">请先选择项目</option>';
    await loadProjectsForSelect('bugProject');
    await loadUsersForSelect('bugAssignedTo');
    new bootstrap.Modal(document.getElementById('bugModal')).show();
}

async function editBug(bugId) {
    try {
        const res = await fetch(`${API_BASE}/bugs/${bugId}`);
        const data = await res.json();
        if (data.code !== 200) { alert('获取Bug信息失败'); return; }

        const bug = data.data.bug;
        document.getElementById('bugModalTitle').textContent = '编辑Bug';
        document.getElementById('bugId').value = bug.id;
        document.getElementById('bugTitle').value = bug.bug_title || '';
        document.getElementById('bugSeverity').value = bug.severity || '3-一般';
        document.getElementById('bugPriority').value = bug.priority || '3-中';
        document.getElementById('bugType').value = bug.bug_type || '功能缺陷';
        document.getElementById('bugDescription').value = bug.description || '';
        document.getElementById('bugSteps').value = bug.steps_to_reproduce || '';
        document.getElementById('bugEnvironment').value = bug.environment_info || '';

        await loadProjectsForSelect('bugProject');
        document.getElementById('bugProject').value = bug.project_id || '';
        if (bug.project_id) await loadProjectModules(bug.project_id, bug.module_id);
        await loadUsersForSelect('bugAssignedTo');
        document.getElementById('bugAssignedTo').value = bug.assigned_to || '';

        new bootstrap.Modal(document.getElementById('bugModal')).show();
    } catch (e) {
        console.error(e);
        alert('获取Bug信息失败');
    }
}

async function saveBug() {
    const bugId = document.getElementById('bugId').value;
    const title = document.getElementById('bugTitle').value.trim();
    const projectId = document.getElementById('bugProject').value;

    if (!title || !projectId) {
        alert('请填写Bug标题和选择项目');
        return;
    }

    const payload = {
        bug_title: title,
        project_id: parseInt(projectId),
        module_id: document.getElementById('bugModule').value ? parseInt(document.getElementById('bugModule').value) : null,
        severity: document.getElementById('bugSeverity').value,
        priority: document.getElementById('bugPriority').value,
        bug_type: document.getElementById('bugType').value,
        assigned_to: document.getElementById('bugAssignedTo').value ? parseInt(document.getElementById('bugAssignedTo').value) : null,
        description: document.getElementById('bugDescription').value,
        steps_to_reproduce: document.getElementById('bugSteps').value,
        environment_info: document.getElementById('bugEnvironment').value
    };

    try {
        const url = bugId ? `${API_BASE}/bugs/${bugId}` : `${API_BASE}/bugs`;
        const method = bugId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.code === 200) {
            bootstrap.Modal.getInstance(document.getElementById('bugModal')).hide();
            loadBugs(bugsPageNum);
        } else {
            alert(data.message || '操作失败');
        }
    } catch (e) {
        console.error(e);
        alert('网络错误');
    }
}

async function deleteBug(bugId, bugNo) {
    if (!confirm(`确定要删除Bug ${bugNo} 吗？此操作不可恢复！`)) return;
    try {
        const res = await fetch(`${API_BASE}/bugs/${bugId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 200) {
            loadBugs(bugsPageNum);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function showBugDetail(bugId) {
    try {
        const res = await fetch(`${API_BASE}/bugs/${bugId}`);
        const data = await res.json();
        if (data.code !== 200) { alert('获取Bug详情失败'); return; }

        const bug = data.data.bug;
        const logs = data.data.logs || [];
        const comments = data.data.comments || [];
        const sevCode = (bug.severity || '').replace(/[^a-zA-Z0-9一-龥]/g, '-');
        const priCode = (bug.priority || '').replace(/[^a-zA-Z0-9一-龥]/g, '-');
        const statusClass = bug.status || 'Active';

        let html = `
        <div class="row mb-3">
            <div class="col-12">
                <h5 class="mb-0">${escapeHtml(bug.bug_no)} - ${escapeHtml(bug.bug_title)}</h5>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-md-3"><strong>项目：</strong>${escapeHtml(bug.project_name || '')}</div>
            <div class="col-md-3"><strong>模块：</strong>${escapeHtml(bug.module_name || '无')}</div>
            <div class="col-md-2"><strong>状态：</strong><span class="badge badge-${statusClass}">${bug.status}</span></div>
            <div class="col-md-2"><strong>严重：</strong><span class="badge badge-severity-${sevCode}">${bug.severity}</span></div>
            <div class="col-md-2"><strong>优先级：</strong><span class="badge badge-priority-${priCode}">${bug.priority}</span></div>
        </div>
        <div class="row mb-3">
            <div class="col-md-3"><strong>类型：</strong>${bug.bug_type || ''}</div>
            <div class="col-md-3"><strong>创建人：</strong>${escapeHtml(bug.creator_name || '')}</div>
            <div class="col-md-3"><strong>指派人：</strong>${escapeHtml(bug.assignee_name || '未指派')}</div>
            <div class="col-md-3"><strong>创建时间：</strong>${bug.created_at || ''}</div>
        </div>
        <div class="row mb-3">
            <div class="col-md-3"><strong>解决人：</strong>${escapeHtml(bug.resolver_name || '-')}</div>
            <div class="col-md-3"><strong>解决方案：</strong>${bug.resolution || '-'}</div>
            <div class="col-md-3"><strong>解决时间：</strong>${bug.resolved_at || '-'}</div>
            <div class="col-md-3"><strong>关闭时间：</strong>${bug.closed_at || '-'}</div>
        </div>
        <hr>
        <h6>详细描述</h6>
        <div class="card mb-3"><div class="card-body bg-light">${nl2br(escapeHtml(bug.description || '（无）'))}</div></div>
        <h6>复现步骤</h6>
        <div class="card mb-3"><div class="card-body bg-light">${nl2br(escapeHtml(bug.steps_to_reproduce || '（无）'))}</div></div>
        <h6>环境信息</h6>
        <div class="card mb-3"><div class="card-body bg-light">${escapeHtml(bug.environment_info || '（无）')}</div></div>
        <hr>
        <h6><i class="bi bi-chat-dots"></i> 评论 (${comments.length})</h6>
        <div class="mb-3">${comments.map(c => `
            <div class="card mb-2"><div class="card-body py-2">
                <div class="d-flex justify-content-between">
                    <strong>${escapeHtml(c.user_name || '')}</strong>
                    <small class="text-muted">${c.created_at || ''}</small>
                </div>
                <div class="mt-1">${nl2br(escapeHtml(c.content || ''))}</div>
            </div></div>
        `).join('')}</div>
        <div class="mb-3">
            <textarea id="commentInput" class="form-control form-control-sm" rows="2" placeholder="添加评论..."></textarea>
            <button class="btn btn-sm btn-outline-primary mt-1" onclick="addComment(${bug.id})">
                <i class="bi bi-send"></i> 发送评论
            </button>
        </div>
        <hr>
        <h6><i class="bi bi-activity"></i> 操作日志</h6>
        <div class="log-timeline">
        ${logs.map(l => `
            <div class="log-item">
                <div class="d-flex justify-content-between">
                    <strong>${escapeHtml(l.user_name || '')}</strong>
                    <span class="badge bg-secondary">${l.action_type || ''}</span>
                </div>
                <small class="text-muted">${l.created_at || ''}</small>
                ${l.comment ? `<div class="mt-1">${escapeHtml(l.comment)}</div>` : ''}
            </div>
        `).join('')}
        </div>`;

        document.getElementById('bugDetailContent').innerHTML = html;
        new bootstrap.Modal(document.getElementById('bugDetailModal')).show();
    } catch (e) {
        console.error(e);
        alert('获取Bug详情失败');
    }
}

function showStatusChange(bugId, action) {
    document.getElementById('statusChangeBugId').value = bugId;
    document.getElementById('statusChangeAction').value = action;
    document.getElementById('statusChangeComment').value = '';

    const assigneeDiv = document.getElementById('statusChangeAssignee');
    const resolutionDiv = document.getElementById('statusChangeResolution');

    assigneeDiv.style.display = 'none';
    resolutionDiv.style.display = 'none';

    let title = '';
    switch (action) {
        case 'assign':
            title = '指派Bug';
            assigneeDiv.style.display = '';
            loadUsersForSelect('statusChangeAssignUser');
            break;
        case 'resolve':
            title = '解决Bug';
            resolutionDiv.style.display = '';
            break;
        case 'close':
            title = '关闭Bug';
            break;
        case 'reopen':
            title = '重新打开Bug';
            break;
    }

    document.getElementById('statusChangeTitle').textContent = title;
    new bootstrap.Modal(document.getElementById('statusChangeModal')).show();
}

async function confirmStatusChange() {
    const bugId = document.getElementById('statusChangeBugId').value;
    const action = document.getElementById('statusChangeAction').value;
    const comment = document.getElementById('statusChangeComment').value;

    let url, payload = { comment };

    switch (action) {
        case 'assign':
            url = `${API_BASE}/bugs/${bugId}/assign`;
            payload.assigned_to = parseInt(document.getElementById('statusChangeAssignUser').value);
            if (!payload.assigned_to) { alert('请选择指派人'); return; }
            break;
        case 'resolve':
            url = `${API_BASE}/bugs/${bugId}/resolve`;
            payload.resolution = document.getElementById('statusChangeResType').value;
            break;
        case 'close':
            url = `${API_BASE}/bugs/${bugId}/close`;
            break;
        case 'reopen':
            url = `${API_BASE}/bugs/${bugId}/reopen`;
            break;
        default:
            return;
    }

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.code === 200) {
            bootstrap.Modal.getInstance(document.getElementById('statusChangeModal')).hide();
            loadBugs(bugsPageNum);
        } else {
            alert(data.message || '操作失败');
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function addComment(bugId) {
    const content = document.getElementById('commentInput').value.trim();
    if (!content) { alert('请输入评论内容'); return; }

    try {
        const res = await fetch(`${API_BASE}/bugs/${bugId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.code === 200) {
            bootstrap.Modal.getInstance(document.getElementById('bugDetailModal')).hide();
            showBugDetail(bugId);
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function loadProjectModules(projectId, selectedModuleId) {
    const sel = document.getElementById('bugModule');
    sel.innerHTML = '<option value="">请选择模块</option>';
    if (!projectId) return;

    try {
        const res = await fetch(`${API_BASE}/projects/${projectId}/modules`);
        const data = await res.json();
        if (data.code === 200) {
            data.data.forEach(m => {
                sel.innerHTML += `<option value="${m.id}" ${m.id === selectedModuleId ? 'selected' : ''}>${m.module_name}</option>`;
            });
        }
    } catch (e) {}
}

function resetBugFilters() {
    document.getElementById('filterProject').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterSeverity').value = '';
    document.getElementById('filterKeyword').value = '';
    loadBugs(1);
}

function debounceSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => loadBugs(1), 500);
}

// ============================================
// 项目管理
// ============================================
async function loadProjects() {
    try {
        const res = await fetch(`${API_BASE}/projects`);
        const data = await res.json();
        if (data.code !== 200) return;

        const container = document.getElementById('projectsList');
        container.innerHTML = data.data.map(p => renderProjectCard(p)).join('');
    } catch (e) {
        console.error('加载项目失败', e);
    }
}

function renderProjectCard(project) {
    return `
    <div class="col-md-4 mb-3">
        <div class="card h-100">
            <div class="card-body">
                <h5 class="card-title">
                    <i class="bi bi-folder-fill text-warning"></i>
                    ${escapeHtml(project.project_name)}
                </h5>
                <h6 class="card-subtitle mb-2 text-muted">${escapeHtml(project.project_code)}</h6>
                <p class="card-text small">${escapeHtml(project.description || '暂无描述')}</p>
                <div class="d-flex justify-content-between">
                    <span class="badge ${project.status === 1 ? 'bg-success' : 'bg-secondary'}">
                        ${project.status === 1 ? '进行中' : '已关闭'}
                    </span>
                    <small class="text-muted">
                        <i class="bi bi-bug"></i> ${project.bug_count || 0} 个Bug
                    </small>
                </div>
                <small>项目经理：${escapeHtml(project.manager_name || '未指定')}</small>
            </div>
            <div class="card-footer text-end">
                <button class="btn btn-sm btn-outline-info" onclick="editProject(${project.id})"><i class="bi bi-pencil"></i></button>
                ${currentUser.role_code === 'admin' ? `<button class="btn btn-sm btn-outline-danger" onclick="deleteProject(${project.id}, '${escapeHtml(project.project_name)}')"><i class="bi bi-trash"></i></button>` : ''}
            </div>
        </div>
    </div>`;
}

function showProjectCreateModal() {
    document.getElementById('projectModalTitle').textContent = '创建项目';
    document.getElementById('projectForm').reset();
    document.getElementById('projectId').value = '';
    loadUsersForSelect('projectManager');
    new bootstrap.Modal(document.getElementById('projectModal')).show();
}

async function editProject(projectId) {
    try {
        const res = await fetch(`${API_BASE}/projects`); // 获取所有项目
        const data = await res.json();
        const project = data.data.find(p => p.id === projectId);
        if (!project) return;

        document.getElementById('projectModalTitle').textContent = '编辑项目';
        document.getElementById('projectId').value = project.id;
        document.getElementById('projectName').value = project.project_name || '';
        document.getElementById('projectCode').value = project.project_code || '';
        document.getElementById('projectDesc').value = project.description || '';
        await loadUsersForSelect('projectManager');
        document.getElementById('projectManager').value = project.manager_id || '';

        new bootstrap.Modal(document.getElementById('projectModal')).show();
    } catch (e) {
        console.error(e);
    }
}

async function saveProject() {
    const projectId = document.getElementById('projectId').value;
    const name = document.getElementById('projectName').value.trim();
    const code = document.getElementById('projectCode').value.trim();

    if (!name || !code) { alert('请填写项目名称和编码'); return; }

    const payload = {
        project_name: name,
        project_code: code,
        description: document.getElementById('projectDesc').value,
        manager_id: document.getElementById('projectManager').value ? parseInt(document.getElementById('projectManager').value) : null
    };

    try {
        const url = projectId ? `${API_BASE}/projects/${projectId}` : `${API_BASE}/projects`;
        const method = projectId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.code === 200) {
            bootstrap.Modal.getInstance(document.getElementById('projectModal')).hide();
            loadProjects();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function deleteProject(projectId, projectName) {
    if (!confirm(`确定删除项目 "${projectName}" 吗？`)) return;
    try {
        const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 200) {
            loadProjects();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function loadProjectsForSelect(selectId) {
    const sel = document.getElementById(selectId);
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">请选择项目</option>';
    try {
        const res = await fetch(`${API_BASE}/projects`);
        const data = await res.json();
        if (data.code === 200) {
            data.data.forEach(p => {
                sel.innerHTML += `<option value="${p.id}">${p.project_name}</option>`;
            });
            if (currentVal) sel.value = currentVal;
        }
    } catch (e) {}
}

async function loadUsersForSelect(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">请选择</option>';
    try {
        const res = await fetch(`${API_BASE}/users?per_page=1000`);
        const data = await res.json();
        if (data.code === 200) {
            data.data.users.forEach(u => {
                sel.innerHTML += `<option value="${u.id}">${u.real_name || u.username} (${u.role_name || ''})</option>`;
            });
            if (currentVal) sel.value = currentVal;
        }
    } catch (e) {}
}

// ============================================
// 用户管理
// ============================================
async function loadUsers() {
    try {
        const res = await fetch(`${API_BASE}/users?per_page=1000`);
        const data = await res.json();
        if (data.code !== 200) return;

        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = data.data.users.map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${escapeHtml(u.username)}</td>
                <td>${escapeHtml(u.real_name || '-')}</td>
                <td>${escapeHtml(u.email || '-')}</td>
                <td><span class="badge bg-info">${escapeHtml(u.role_name || '')}</span></td>
                <td><span class="badge ${u.status === 1 ? 'bg-success' : 'bg-danger'}">${u.status === 1 ? '启用' : '禁用'}</span></td>
                <td>${u.created_at || ''}</td>
                <td>
                    <button class="btn btn-sm btn-outline-warning" onclick="showUserEdit(${u.id})"><i class="bi bi-pencil"></i></button>
                    ${u.id !== currentUser.id ? `<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${u.id}, '${escapeHtml(u.username)}')"><i class="bi bi-trash"></i></button>` : ''}
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('加载用户失败', e);
    }
}

function showUserCreateModal() {
    document.getElementById('userModalTitle').textContent = '创建用户';
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('userPwdHint').textContent = '(初始密码为 123456)';
    loadRolesForSelect('userRole');
    new bootstrap.Modal(document.getElementById('userModal')).show();
}

async function showUserEdit(userId) {
    try {
        const res = await fetch(`${API_BASE}/users?per_page=1000`);
        const data = await res.json();
        const user = data.data.users.find(u => u.id === userId);
        if (!user) return;

        document.getElementById('userModalTitle').textContent = '编辑用户';
        document.getElementById('userId').value = user.id;
        document.getElementById('userUsername').value = user.username || '';
        document.getElementById('userPassword').value = '';
        document.getElementById('userPwdHint').textContent = '(留空则不修改密码)';
        document.getElementById('userRealName').value = user.real_name || '';
        document.getElementById('userEmail').value = user.email || '';
        await loadRolesForSelect('userRole');
        document.getElementById('userRole').value = user.role_id || '';

        new bootstrap.Modal(document.getElementById('userModal')).show();
    } catch (e) {
        console.error(e);
    }
}

async function saveUser() {
    const userId = document.getElementById('userId').value;
    const username = document.getElementById('userUsername').value.trim();
    const password = document.getElementById('userPassword').value;
    const realName = document.getElementById('userRealName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const roleId = document.getElementById('userRole').value;

    if (!username) { alert('请输入用户名'); return; }
    if (!roleId) { alert('请选择角色'); return; }

    const payload = {
        username,
        real_name: realName,
        email,
        role_id: parseInt(roleId)
    };
    if (password) payload.password = password;

    try {
        const url = userId ? `${API_BASE}/users/${userId}` : `${API_BASE}/users`;
        const method = userId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.code === 200) {
            bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
            loadUsers();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`确定删除用户 "${username}" 吗？`)) return;
    try {
        const res = await fetch(`${API_BASE}/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 200) {
            loadUsers();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function loadRolesForSelect(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = '<option value="">请选择角色</option>';
    try {
        const res = await fetch(`${API_BASE}/roles`);
        const data = await res.json();
        if (data.code === 200) {
            data.data.forEach(r => {
                sel.innerHTML += `<option value="${r.id}">${r.role_name}</option>`;
            });
        }
    } catch (e) {}
}

// ============================================
// 工具函数
// ============================================
function renderPagination(containerId, currentPage, totalPages, callback) {
    const container = document.getElementById(containerId);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    html += `<li class="page-item ${currentPage <= 1 ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="if(${currentPage}>1)${callback.name}(${currentPage - 1})">«</a></li>`;

    for (let i = 1; i <= totalPages; i++) {
        html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
            <a class="page-link" href="javascript:void(0)" onclick="${callback.name}(${i})">${i}</a></li>`;
    }

    html += `<li class="page-item ${currentPage >= totalPages ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="if(${currentPage}<${totalPages})${callback.name}(${currentPage + 1})">»</a></li>`;

    container.innerHTML = html;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function nl2br(str) {
    if (!str) return '';
    return str.replace(/\n/g, '<br>');
}
