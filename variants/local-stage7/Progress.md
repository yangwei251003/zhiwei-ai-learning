# Progress.md — 小智析析阶段 4–5 → 阶段 6 交接

更新时间：2026-07-15（Asia/Shanghai）

## 当前结论

阶段 0–5 已完成。阶段 4 的 Vue 3 八页应用与阶段 5 的真实联调、安全管理员、会话历史、资源/路径/Tutor/Admin 完整闭环均已通过 fresh 自动门禁和真实浏览器门禁。

阶段 5 开始时星火仍返回 `AppIdNoAuthError`，但外部授权状态在 2026-07-15 当天发生变化。最终测试已观察到真实星火普通回答、五类资源、学习路径和 Tutor 三种呈现成功；后续文档必须采用这一最新事实，不得继续写“星火仍未授权”，也不得把历史错误截图当最终成功证据。

详细依据：

- `research/stage-4-research.md`
- `research/stage-4-verification.md`
- `research/stage-5-research.md`
- `research/stage-5-verification.md`
- `research/stage-status.json`

## 阶段 4–5 已验证交付

### 阶段 4：Vue 前端与设计系统

- Vue 3.5 + Vite 8 + Element Plus + Pinia 3 + Vue Router 5，依赖锁定于 `frontend/package-lock.json`。
- 8 页完成：Login、Register、Home、Chat、Resources、Path、Tutor、Admin。
- AppShell、JWT API 层、Pinia stores、双主题、本地原创 IP/背景/Phosphor 图标、Markdown 与 Mermaid strict 渲染、360/1024/1440 响应式均已实现。
- POST SSE 使用 `fetch + ReadableStream + TextDecoder + AbortController`，不改回无法携带 POST body 的 EventSource。

### 阶段 5：真实闭环与安全边界

- 安全管理员 bootstrap：`backend/scripts/bootstrap_admin.py`；注册 API 永不接受 `is_admin`；密码不通过 CLI 参数或日志传递。
- 会话历史：`GET /api/chat/conversations` 与 `GET /api/chat/conversations/{id}`，按所有权隔离；Chat 左栏使用真实后端历史与详情。
- SSE：非 2xx、非 event-stream、显式 error、用户取消、异常断流、EOF 缺 done 均有不同语义。
- 上传：PDF/DOCX/TXT/Markdown 扩展名、MIME、magic、空文件、DOCX ZIP bomb/加密/NUL 等门禁；失败清理半成品。
- Windows FAISS Unicode 路径通过 ASCII staging + Python Unicode 原子替换解决；真实 TXT → BGE embedding → SQLite/FAISS → UI 已通过。
- 五类资源并行生成；mindmap/code 必须通过真实格式契约，不合格最多一次真实星火重试，连续不合格返回真实错误且不持久化。
- Tutor 必须包含三段文字、简单安全 Mermaid 与视频分镜表；HTML/花括号公式等不安全 Mermaid 会被真实重试，不交给前端冒充成功。
- Mermaid 前端只提取真实响应中的第一段 fenced Mermaid；普通正文不会被当图执行。
- Resources/Tutor tabs 支持 roving tabindex、ArrowLeft/ArrowRight、Home/End、ARIA tab/tabpanel 关联。
- Playwright 1.61.1 + Edge 使用每次独立随机 SQLite、FAISS、上传目录和真实 bootstrap；没有 route/HAR/mock 成功。

## Fresh 验证证据

### 后端

```powershell
cd <USER_HOME>\Desktop\小智析析\backend
.\.venv\Scripts\ruff.exe format --check app tests scripts
.\.venv\Scripts\ruff.exe check app tests scripts
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
.\.venv\Scripts\python.exe -m compileall -q app scripts
```

观察结果：62 files already formatted；Ruff clean；80 tests passed；app coverage 93%；compileall exit 0。

### 前端

```powershell
cd <USER_HOME>\Desktop\小智析析\frontend
npm run test:coverage
npm run build
npm run test:e2e
```

观察结果：7 files / 27 tests passed；statements 52.82%、lines 60.15%、SSE statements 94%；Vite build 成功（4731 modules）；最终 Playwright 6 passed（9.0m）。

### 数据库与扫描

```text
全新 SQLite alembic upgrade head：通过
alembic check：No new upgrade operations detected
current / heads：唯一 7c8784b6bba6 (head)
backend/.env：被 .gitignore 命中且未跟踪
secret scan：SECRET_SCAN_OK
production mock scan：PRODUCTION_MOCK_SCAN_OK
E2E route mock scan：E2E_ROUTE_MOCK_SCAN_OK
```

最终浏览器状态：`output/playwright/stage-5/test-results/.last-run.json` 为 `passed`，`failedTests` 为空。

## 阶段 5 真实浏览器证据

截图位于 `output/playwright/stage-5/`：

- `home-1440-light.png`
- `chat-real-spark-result-1440.png`
- `path-real-result.png`
- `tutor-real-three-presentations.png`
- `resources-real-five-types.png`
- `admin-1440.png`
- `chat-1024-light.png`
- `chat-360-light.png`
- `chat-1440-dark.png`
- `home-reduced-motion.png`

覆盖的真实故事：注册/登录/首页、Chat SSE/画像/历史、路径生成/进度、Tutor 三种呈现、五类资源与 Mermaid/Python、管理员上传/用户/配置、八页 axe A/AA、键盘、双主题、360/1024/1440 与 reduced-motion。

## 不可重新发明的决策

- `SPEC.md` 是产品权威；每项任务前读取 `research/skills-map.md` 并运行 Guardian preflight。
- 所有行为变化继续用 Superpowers TDD；跨层故障按浏览器 → API → 数据/FAISS/星火 → UI 定位首个坏边界。
- 真实失败不得被 mock、静态样例或前端补造内容掩盖。
- 每次 LLM 回复前必须检索知识库；弱证据需明确表达不确定性。
- 星火模型 high/medium/low 仍映射为 `generalv3.5` / `generalv3` / `lite`；超时由 `SPARK_TIMEOUT_SECONDS` 控制，默认 180 秒。
- Vue POST SSE 不能改成 EventSource；Mermaid 保持 `securityLevel:'strict'`，Markdown 保持 `html:false`。
- 正式数据库结构只由 Alembic 管理，`AUTO_CREATE_TABLES` 默认 false。
- 运行时素材只用 `frontend/public/assets/`，图标统一 Phosphor。
- `backend/.env` 只供本地运行；任何文档、截图、日志、压缩包、提交和交接不得显示、复制或包含其中的值。

## Git 与工作区

- 分支：`develop/full-build`
- 当前基线提交：`ae7b091 docs: hand off stages 2 and 3`
- 阶段 4 与阶段 5 都尚未提交，工作树保持 dirty；包含完整前端、阶段 4–5 研究/验证、后端联调修复、E2E 与截图。
- 本窗口没有执行 reset、checkout 覆盖、clean、commit 或 push。
- 新窗口必须保留所有未提交成果。未经用户明确授权，不得自动 commit/push。
- `output/` 含大量 E2E 临时数据库/FAISS/test-results；阶段 6 应只引用最终 10 张截图和验证结论，不把临时账户或运行数据写入交付文档。清理动作仍需用户授权且不得在阶段 6 擅自进行。

## 已知风险与外部约束

1. 星火输出具有非确定性；后端格式验证与最多一次真实重试是刻意的安全边界。连续不合格返回真实错误属于正确行为。
2. 本机未配置 HF token，首次加载 embedding 会出现 Hugging Face 未认证限流提示；最终真实上传仍为 201。若部署需要 token，只在本地/部署 secret 中配置，不写仓库。
3. E2E 的 Chat/路径/Tutor 等待预算为 210 秒，资源为 330 秒；这是对齐后端 180 秒星火上限与持久化余量，不代表忽略错误，测试仍要求 alert=0 和真实内容/数据库/UI。
4. 前端 coverage 为 52.82%，高于阶段 4 基线 46.43%，核心 SSE/安全工具覆盖较高；阶段 6 是文档阶段，不要为了数字无意义改业务。

## 下一阶段：阶段 6 文档

阶段 6 尚未开始，也尚未创建 `research/stage-6-research.md`。下一窗口的第一项工作是联网调研当前比赛材料规范、优秀获奖文档/PPT/7 分钟演示结构、DOCX/PPTX 可访问性与许可证，写研究文档后运行 stage 6 Guardian preflight。

依据 `SPEC.md`，阶段 6 需产出 7 份文档：

1. 需求分析.docx
2. 系统设计.docx（含架构图、Agent 协作图、ER 图、API 清单）
3. 测试报告.docx
4. 部署说明.docx
5. 产品说明书.docx（使用阶段 5 真实截图）
6. PPT.pptx（12–15 页、深色背景、大量真实截图）
7. 演示视频脚本.docx（约 7 分钟分镜）

最终交付清单还要求 `< 7 分钟` 的演示视频 MP4；阶段 6 研究需明确录制、旁白、字幕、压缩与验收方案，阶段 7 再做最终打包。

优先加载的 Skills：

- `$guard-xiaozhixixi-development`
- `web-access`（阶段 6 最新资料与比赛规范调研）
- `documents:documents`
- `presentations:Presentations`
- `pdf:pdf`（DOCX/PPTX 导出后视觉复核）
- `playwright`（需要补录真实页面或视频时）
- `Verification Before Completion`

不要直接开始写文档，先盘点当前窗口实际可用的 Skills/插件、写 `research/stage-6-research.md`、更新 `research/skills-map.md`（如发现更合适且官方维护/Windows 兼容/许可合适的工具），再 preflight。

## 新窗口必须提供

- 仓库：`<USER_HOME>\Desktop\小智析析`
- 必读：`SPEC.md`、`Progress.md`、`PRODUCT.md`、`DESIGN.md`
- 阶段依据：`research/skills-map.md`、`research/stage-5-research.md`、`research/stage-5-verification.md`、`research/stage-status.json`
- 说明：阶段 4–5 尚未提交，工作树 dirty；`backend/.env` 存在但不得读取输出、复制或提交其值。

## 可直接粘贴的新窗口提示词

```text
请在 <USER_HOME>\Desktop\小智析析 继续开发“小智析析”阶段 6。阶段 4–5 已完成但尚未提交，必须保留当前 dirty 工作树，禁止 reset、checkout 覆盖或 clean，也不要未经我授权自动 commit/push。

开始后完整阅读 SPEC.md、Progress.md、PRODUCT.md、DESIGN.md、research/skills-map.md、research/stage-5-research.md、research/stage-5-verification.md 和 research/stage-status.json；先运行 git status --short --branch，核对阶段 5 最终证据与 output/playwright/stage-5/ 的 10 张真实截图。不得显示、复制或提交 backend/.env 的任何值。

先盘点本窗口实际可用的插件和 Skills，优先检查 $guard-xiaozhixixi-development、web-access、documents:documents、presentations:Presentations、pdf:pdf、playwright 和 Verification Before Completion。随后联网调研最新比赛文档/PPT/7 分钟演示规范、优秀获奖结构、DOCX/PPTX 可访问性与许可证，创建 research/stage-6-research.md；如需更新工具选择，先说明理由并更新 research/skills-map.md。研究完成后运行 Guardian stage 6 preflight，未通过不得制作交付物。

按 SPEC.md 产出需求分析.docx、系统设计.docx、测试报告.docx、部署说明.docx、产品说明书.docx、12–15 页 PPT.pptx、约 7 分钟演示视频脚本.docx，并为最终 <7 分钟 MP4 制定和验证录制方案。所有内容只使用真实代码、真实测试数字和阶段 5 真实截图；不得沿用“星火仍 AppIdNoAuthError”的过期结论，不得使用 mock/假界面/假结果。完成阶段 6 后按 Guardian 记录证据并停止，不要直接进入阶段 7。
```
