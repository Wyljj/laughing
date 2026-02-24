# 环保咨询助手（内部 Web 应用 MVP）

本项目已从“纯聊天脚本”升级为**可部署的内部 Web 应用**，面向环保咨询交付场景：

- 文件上传
- 知识库检索（条款级引用）
- 项目隔离与权限（简化 RBAC）
- 审计日志
- 危废问诊式合规建议
- 结构化咨询评估

## 架构（Docker Compose）

当前 MVP 服务：

1. **Web/API（FastAPI）**：聊天、Gap 评估、上传、审计接口
2. **规则与检索内核**：`eco_assistant.py`
3. **文件存储**：本地 `uploads/`（后续可替换 MinIO）
4. **审计日志**：`audit_log.jsonl`（后续可替换 PostgreSQL）

> 说明：按你的建议，目标架构是前端 + API + 检索 + 对象存储 + 异步任务。MVP 已先落地 Web 入口与核心流程，便于后续接 Redis/Celery、pgvector/MinIO。

## 主要模块（对应咨询交付流程）

- 对话工作台（强制引用模板）
- 标准/法规库（全国 + 地方更严）
- 项目资料库（按项目上传文件）
- 质控与风险边界提示
- 导出/证据包（当前先输出结构化文本）

## 运行

### 方式1：本地 Python

```bash
pip install -r requirements.txt
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

打开 `http://localhost:8000`。

### 方式2：Docker Compose

```bash
docker compose up --build
```

## 默认测试 Token（演示）

- `admin-token`
- `consultant-token`
- `viewer-token`

## API 摘要

- `POST /api/chat`：法规问答（固定模板 + 引用 + 风险提示）
- `POST /api/gap`：危废 5 场景 Gap 清单与整改计划
- `POST /api/upload`：项目文件上传（consultant/admin）
- `GET /api/audit?token=admin-token`：审计日志（admin）

## 质量与风控硬规则

1. 无引用不下结论（最小引用数 >= 2）
2. 仅给“依据 + 一般要求 + 建议动作”，不做法律裁决
3. 涉及停产整治/重大违法/刑责边界，强提示法务/第三方复核

## 测试

```bash
pytest -q
```
