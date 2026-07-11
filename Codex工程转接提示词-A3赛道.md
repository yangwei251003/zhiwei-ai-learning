# Codex 工程转接提示词 - A3 赛道 v3（最终版）

> 将这个提示词完整复制发给 Codex。Codex 会自行调研最适合本项目的 Skills、MCP、GitHub 开源项目，然后从零到交付完成整个作品。

---

## 完整提示词（复制以下全部给 Codex）

```text
注意：收到这条消息后，不要马上写代码。先完整读完，再按顺序执行。

---

## 0. 竞争情报验证（必须先做这一步）

你要开发的这个项目属于一场正式比赛。在你动手之前，请访问大赛官网确认你没有搞错比赛和赛道：

官网：https://www.cnsoftbei.com
赛道页面：https://www.cnsoftbei.com/content-3-1286-1.html

你需要在回复中明确告诉我：

- 比赛全称是什么？
- 这是第几届？
- A3 赛道的全称是什么？
- 出题企业是谁？
- 参赛组别是哪一个？
- 提交截止日期是什么时候？

我确认无误后，你再继续往下。这一步不能跳过——大赛信息一旦搞错，所有代码白写。

---

## 1. 项目现状

我要参加的比赛、赛道、技术栈都已经定了。项目骨架也搭好了，后端核心代码（FastAPI + LangGraph 多智能体 + 讯飞星火）已经写了一版，前端（Vue3）还没开始。

你接手后的工作：
1. 先依托现有骨架把后端跑通、补完
2. 从零搭建前端
3. 把整个系统做成一个能拿去比赛演示、冲击奖项的完整作品

项目根目录在：A3-multi-agent-learning/

现有代码你自己进去看，了解现在的进度。

---

## 2. 你的第一个独立任务：自己调研适合本项目的工具和开源项目

### 2.1 你要自己调研并安装 Skills

不要用我预设的 Skill 清单。你的第一项工作是：

- 去 https://github.com/openai/skills 和 https://github.com/ComposioHQ/awesome-codex-skills 浏览可用的 Skills
- 筛选出对本项目有用的 Skill（参考标准：能提升前端 UI 质量、能写更好的测试、能优化多智能体代码架构、能生成更高质量的文档和 PPT）
- 把筛选结果列出来，告诉我每个 Skill 是什么、为什么适合本项目、怎么安装
- 等我确认后，你再安装

### 2.2 你要自己调研并安装 MCP

- 思考本项目开发过程中需要访问哪些外部服务（GitHub 搜索代码？查 API 文档？）
- 去了解 Codex 可用哪些 MCP Server
- 筛选出对本项目有用的，列出来告诉我
- 等我确认后配置

### 2.3 你要自己调研 GitHub 开源项目并做迁移

- 用 GitHub 搜索（关键词参考：LangGraph multi-agent education、personalized learning agent、AI tutoring system、knowledge graph RAG、中文知识库问答）
- 找出 3-5 个最相关的开源仓库
- 对于每个仓库，告诉我：仓库名、Star 数、核心技术栈、哪些模块可以借鉴移植、开源协议是否允许商用
- 等我确认后，把确认的项目 clone 到 research/ 目录，读完源码，写一份"借鉴要点清单"

---

## 3. 赛道核心要求（技术栈已定，不要改）

### 3.1 技术栈

后端：Python 3.12 + FastAPI + LangGraph（多智能体）
前端：Vue 3 + Vite + Element Plus + Pinia
大模型：讯飞星火 Spark API（赛道强制要求）+ 可选 DeepSeek/Qwen
向量库：ChromaDB（本地）
数据库：SQLite（开发） / PostgreSQL（可选）
渲染：Markdown + Mermaid.js + SSE 流式

### 3.2 必须实现的功能（缺一个就直接淘汰）

1. 对话式学生画像：至少 6 个维度（知识基础、认知风格、易错点、学习目标、专业、兴趣），支持自然语言对话采集和动态更新
2. 多智能体协同：不同角色的 Agent 协作完成 5 类资源生成
   - 讲解文档（Markdown）
   - 思维导图（Mermaid.js）
   - 练习题（含答案和解析）
   - 多模态视频/动画脚本（分镜表）
   - 代码实操案例（可运行的 Python 代码）
3. 个性化学习路径：根据学生画像规划学习顺序，推送对应资源
4. 智能辅导（加分）：多模态答疑（文字 + 图解 + 视频脚本）
5. 学习效果评估（加分）：跟踪行为、分析薄弱点、动态调整策略

### 3.3 评分权重

创新与实用 35% + 功能与技术 45% + 文档 10% + 演示/PPT 10%

### 3.4 非功能要求

界面美观（现代 AI 产品风格），有防幻觉机制，流式输出避免白屏，开发过程中使用的 AI 辅助工具必须包含科大讯飞相关工具

---

## 4. 项目结构（已经存在的文件，在此基础开发）

```
A3-multi-agent-learning/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/                 # auth.py / chat.py(SSE流式) / agents.py / resources.py / knowledge.py
│   │   ├── agents/              # orchestrator.py(总调度+SparkLLM) / profile_agent.py / resource_agent.py / tutor_agent.py / path_agent.py
│   │   ├── models/              # SQLAlchemy: User, StudentProfile, LearningResource, LearningPath, Conversation
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── core/                # 配置(settings) + 数据库连接
│   │   └── knowledge_base/      # 文件上传目录
│   ├── requirements.txt         # 含 sparkai, langgraph, fastapi 等
│   └── .env.example             # 需要填讯飞 API Key
├── frontend/                    # 空目录，从零搭建 Vue3 + Vite
├── documents/                   # 空目录，放提交文档
└── README.md
```

---

## 5. 开发执行计划

### 阶段一：准备和验证（每步做完告诉我结果，不要跳步）

**Step 1** - 完成上面第 2 节的三项独立调研（Skills / MCP / GitHub 项目），把调研结果发给我确认

**Step 2** - 我确认后，安装 Skills、配置 MCP、clone 确认的 GitHub 项目到 research/

**Step 3** - 后端环境：
```bash
cd backend && pip install -r requirements.txt
```
如果 sparkai 安装失败，试 pip install sparkai==1.1.3。把 `.env.example` 复制为 `.env`，告诉我去 https://xinghuo.xfyun.cn/ 注册后需要填哪几个值。新用户有 200 万 tokens 免费额度。

**Step 4** - 前端初始化：
```bash
cd frontend
npm create vite@latest . -- --template vue
npm install element-plus @element-plus/icons-vue pinia vue-router axios markdown-it mermaid
npm install -D sass
```
Vite 配置代理：/api 转发到 http://localhost:8000

**Step 5** - 验证连通性：
```bash
cd backend && uvicorn app.main:app --reload
# 访问 http://localhost:8000/health 确认返回 {"status":"ok"}
```
```bash
cd frontend && npm run dev
# 访问 http://localhost:5173 确认页面正常
```

**全部通过后，告诉我准备就绪，然后我们进入阶段二。**

---

### 阶段二：核心开发

现在开启 Goal 模式，目标如下：

**成品定义**：一个完整的 Web 应用，学生登录后可以和 AI 对话构建画像、一键生成 5 类学习资源、按学习路径学习、向 AI 提问。加上管理员后台，加上全套比赛文档和演示视频脚本。

**前端页面（全部要完成）**

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录/注册 | /login /register | 背景图 + 表单 + JWT Token 本地存储 |
| 首页 | / | 问候语 + 快捷入口 + 学习概览卡片 |
| 对话学习 | /chat | 左侧历史 + 中间 SSE 流式对话 + 右侧画像面板 |
| 资源库 | /resources | 网格卡片 + 分类筛选（文档/导图/题/视频/代码） |
| 学习路径 | /path | 步骤条/时间轴 + 进度 + 资源跳转 |
| 智能辅导 | /tutor | 提问 + Mermaid 图渲染区 |
| 管理后台 | /admin | 知识库管理 + 用户列表 + 系统配置 |

**后端 API 检查清单**
- [ ] /api/auth/register  /login  /me
- [ ] /api/chat/stream（SSE 流式对话，核心接口）
- [ ] /api/agents/status
- [ ] /api/resources/（CRUD）
- [ ] /api/knowledge/upload  /list

**5 类资源 Agent 验证**
- 文档 Agent → 结构化 Markdown 讲解文档（有标题、小节、例子）
- 导图 Agent → 能被 Mermaid.js 渲染的 mindmap 代码
- 题目 Agent → 至少 5 道题，每题有答案和解析
- 视频 Agent → 5-8 镜头分镜脚本
- 代码 Agent → 可运行的 Python 示例代码

**设计风格**

- 主色：#4F46E5（靛蓝），辅色：#10B981（翠绿）、#F59E0B（琥珀）
- 布局：侧边栏 + 主内容区，响应式
- 组件：圆角卡片（12px）、微阴影、过渡动画
- 支持暗色模式

**AI 生图**（你用 Codex 内置 image2 生成，存到 frontend/public/assets/）

- mascot-logo.png / mascot-hero.png / mascot-chat.png / mascot-empty.png — 平台 IP 形象"小智析析"（AI 学习助手吉祥物，小灯泡/小机器人，戴学士帽，蓝紫渐变）
- icon-document.svg / icon-mindmap.svg / icon-quiz.svg / icon-video.svg / icon-code.svg — 5 个资源类型图标
- bg-login.jpg / bg-hero.jpg — 登录和首页背景

**视频嵌入**（豆包视频模型单独生成，你留好占位）

首页 Hero 区、资源渲染页、登录页留 `<video>` 标签，用 VideoPlayer.vue 组件封装

**最终交付物**

1. 演示 PPT（10-15 页）.pptx
2. 需求分析文档 .docx
3. 系统设计文档 .docx（含架构图、数据模型、Agent 设计）
4. 测试报告 .docx
5. 部署说明 .docx
6. 产品说明书 .docx
7. 7 分钟演示视频脚本 .docx（分镜头）
8. 打包压缩包（源码 + build）

---

## 6. 三个红线

1. 代码里必须有 sparkai 调用，不能全是 OpenAI/DeepSeek。赛道要求科大讯飞工具。
2. 每次 LLM 回复前先检索知识库。不确定的回答要明确说"我不确定，建议查看教材"。
3. 借鉴开源项目必须在注释和文档里标明出处和协议。

---

现在从阶段一 Step1 开始——先做 Skills、MCP、GitHub 项目的独立调研，把结果发给我确认。
```

---

## 使用说明

1. 打开这个文件，把代码块里的内容完整复制发给 Codex
2. Codex 会先访问大赛官网确认比赛信息
3. 确认无误后，Codex 自己调研 Skills / MCP / GitHub 项目
4. 你审核确认后，Codex 开始搭建环境和开发
5. 最后开启 Goal 模式一口气完成到交付
