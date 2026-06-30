-- ============================================
-- 缺陷管理系统（类 BugFree）数据库初始化脚本
-- 适配鲲鹏 ARM 架构 MySQL
-- ============================================

CREATE DATABASE IF NOT EXISTS bug_manager DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bug_manager;

-- ----------------------------
-- 1. 角色表 (roles)
-- ----------------------------
DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `role_name` VARCHAR(50) NOT NULL UNIQUE COMMENT '角色名称：系统管理员/项目经理/开发工程师/测试工程师',
  `role_code` VARCHAR(30) NOT NULL UNIQUE COMMENT '角色编码：admin/manager/developer/tester',
  `description` VARCHAR(255) DEFAULT NULL COMMENT '角色描述',
  `permissions` TEXT COMMENT '权限列表JSON',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 初始化角色数据
INSERT INTO `roles` (`role_name`, `role_code`, `description`, `permissions`) VALUES
('系统管理员', 'admin', '拥有系统全部权限，可管理用户、项目、Bug', '{"user":["create","read","update","delete"],"project":["create","read","update","delete"],"bug":["create","read","update","delete","assign","close"],"system":["manage"]}'),
('项目经理', 'manager', '可管理项目和Bug，查看报表', '{"user":["read"],"project":["create","read","update"],"bug":["create","read","update","delete","assign","close"],"system":[]}'),
('开发工程师', 'developer', '可查看和修复指派给自己的Bug', '{"user":["read"],"project":["read"],"bug":["read","update"],"system":[]}'),
('测试工程师', 'tester', '可提交Bug，验证已修复Bug', '{"user":["read"],"project":["read"],"bug":["create","read","update"],"system":[]}');

-- ----------------------------
-- 2. 用户表 (users)
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（SHA256加密存储）',
  `real_name` VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
  `role_id` INT NOT NULL COMMENT '角色ID',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`role_id`) REFERENCES `roles`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 初始化用户数据（密码均为 123456 的SHA256值）
INSERT INTO `users` (`username`, `password`, `real_name`, `email`, `role_id`) VALUES
('admin', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '系统管理员', 'admin@bugmanager.com', 1),
('manager', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '项目经理', 'manager@bugmanager.com', 2),
('developer', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '开发工程师', 'dev@bugmanager.com', 3),
('tester', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '测试工程师', 'tester@bugmanager.com', 4);

-- ----------------------------
-- 3. 项目模块表 (projects)
-- ----------------------------
DROP TABLE IF EXISTS `projects`;
CREATE TABLE `projects` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `project_name` VARCHAR(100) NOT NULL COMMENT '项目名称',
  `project_code` VARCHAR(50) NOT NULL UNIQUE COMMENT '项目编码',
  `description` TEXT COMMENT '项目描述',
  `manager_id` INT DEFAULT NULL COMMENT '项目经理ID',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1-进行中，0-已关闭',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`manager_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目模块表';

-- ----------------------------
-- 4. 模块表 (modules)
-- ----------------------------
DROP TABLE IF EXISTS `modules`;
CREATE TABLE `modules` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `module_name` VARCHAR(100) NOT NULL COMMENT '模块名称',
  `project_id` INT NOT NULL COMMENT '所属项目ID',
  `description` VARCHAR(255) DEFAULT NULL COMMENT '模块描述',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目模块表';

-- ----------------------------
-- 5. Bug缺陷表 (bugs)
-- ----------------------------
DROP TABLE IF EXISTS `bugs`;
CREATE TABLE `bugs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `bug_title` VARCHAR(255) NOT NULL COMMENT 'Bug标题',
  `bug_no` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Bug编号（如BUG-20260624-001）',
  `project_id` INT NOT NULL COMMENT '所属项目ID',
  `module_id` INT DEFAULT NULL COMMENT '所属模块ID',

  -- Bug分类
  `severity` ENUM('1-致命','2-严重','3-一般','4-轻微','5-建议') NOT NULL DEFAULT '3-一般' COMMENT '严重程度',
  `priority` ENUM('1-紧急','2-高','3-中','4-低') NOT NULL DEFAULT '3-中' COMMENT '优先级',
  `bug_type` ENUM('功能缺陷','界面问题','性能问题','安全问题','兼容性问题','文档问题','其他') DEFAULT '功能缺陷' COMMENT 'Bug类型',

  -- Bug状态流转
  `status` ENUM('Active','Assigned','Resolved','Verified','Closed','Reopened') NOT NULL DEFAULT 'Active' COMMENT 'Bug状态',
  `resolution` ENUM('Fixed','Duplicated','NotABug','WontFix','Later','WorksForMe','External','Unresolved') DEFAULT NULL COMMENT '解决方案',

  -- 人员指派
  `created_by` INT NOT NULL COMMENT '创建人ID',
  `assigned_to` INT DEFAULT NULL COMMENT '指派给谁',
  `resolved_by` INT DEFAULT NULL COMMENT '解决人ID',
  `verified_by` INT DEFAULT NULL COMMENT '验证人ID',

  -- 描述信息
  `description` TEXT COMMENT 'Bug详细描述',
  `steps_to_reproduce` TEXT COMMENT '复现步骤',
  `environment_info` VARCHAR(500) COMMENT '环境信息（OS/浏览器/版本等）',

  -- 附件信息
  `attachment_path` VARCHAR(500) DEFAULT NULL COMMENT '附件路径',

  -- 时间信息
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `resolved_at` TIMESTAMP NULL DEFAULT NULL COMMENT '解决时间',
  `closed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '关闭时间',

  FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`module_id`) REFERENCES `modules`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`created_by`) REFERENCES `users`(`id`),
  FOREIGN KEY (`assigned_to`) REFERENCES `users`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`resolved_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`verified_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Bug缺陷表';

-- ----------------------------
-- 6. Bug操作日志表 (bug_logs)
-- ----------------------------
DROP TABLE IF EXISTS `bug_logs`;
CREATE TABLE `bug_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `bug_id` INT NOT NULL COMMENT '关联Bug ID',
  `user_id` INT NOT NULL COMMENT '操作人ID',
  `action_type` VARCHAR(50) NOT NULL COMMENT '操作类型：create/update/assign/resolve/verify/close/reopen/comment',
  `old_value` TEXT COMMENT '旧值（JSON格式）',
  `new_value` TEXT COMMENT '新值（JSON格式）',
  `comment` TEXT COMMENT '备注/评论',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`bug_id`) REFERENCES `bugs`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Bug操作日志表';

-- ----------------------------
-- 7. Bug评论表 (bug_comments)
-- ----------------------------
DROP TABLE IF EXISTS `bug_comments`;
CREATE TABLE `bug_comments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `bug_id` INT NOT NULL COMMENT '关联Bug ID',
  `user_id` INT NOT NULL COMMENT '评论人ID',
  `content` TEXT NOT NULL COMMENT '评论内容',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`bug_id`) REFERENCES `bugs`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Bug评论表';

-- ----------------------------
-- 索引优化
-- ----------------------------
CREATE INDEX idx_bugs_status ON bugs(status);
CREATE INDEX idx_bugs_severity ON bugs(severity);
CREATE INDEX idx_bugs_project ON bugs(project_id);
CREATE INDEX idx_bugs_assigned ON bugs(assigned_to);
CREATE INDEX idx_bugs_created ON bugs(created_by);
CREATE INDEX idx_bugs_created_at ON bugs(created_at);
CREATE INDEX idx_bug_logs_bug ON bug_logs(bug_id);
CREATE INDEX idx_bug_comments_bug ON bug_comments(bug_id);
