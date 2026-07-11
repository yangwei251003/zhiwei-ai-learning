# A3 项目 · 直接复制发给 Codex 的提示词集合

> 当前项目状态：阶段 0（调研）+ 阶段 1（环境搭建）已完成。
> 下面从「修复依赖」开始，按顺序逐阶段发。

---

## 【修复任务 1】替换 sparkai 为 HTTP API

> 原因：sparkai 在 Python 3.13 下安装失败。改用讯飞原生 HTTP API。

**直接复制这段发新对话：**

```text
sparkai 在 Python 3.13 下无法安装。请做以下替换：

在 backend/app/core/ 下新建 llm.py，用 HTTP API 替代 sparkai SDK。

实现一个 SparkHTTP 类：
- chat() 方法：POST https://spark-api-open.xf-yun.com/v1/chat/completions
- 认证方式：Authorization: Bearer + API Key
- 超时 30 秒
- 失败抛异常，不返回模拟文本
- get_llm(level) 函数：high→Spark4.0, medium→Spark3.5, low→SparkLite

写 tests/test_spark_http.py 验证：调用 chat("你好")，确认返回真实内容。

如果 URL 不对，去 https://www.xfyun.cn/doc/spark/Web.html 查最新地址。
```

---

## 【修复任务 2】用 FAISS 替代 chromadb

> 原因：chromadb 在 Windows 下需编译。改用免编译的 FAISS。

**接着上一个对话继续发：**

```text
chromadb 在 Windows 下装不上。改用 FAISS：

pip install faiss-cpu sentence-transformers numpy

在 backend/app/creative/vector_store.py 中实现 VectorStore 类：
- add_documents(texts)：向量化并存入索引
- search(query, top_k=5)：返回关联片段和相似度分数
- 使用 paraphrase-multilingual-MiniLM-L12-v2（中文支持好）

写 tests/test_vector.py 验证。
```

---

## 【阶段 1→2 过渡】clone 参考项目 + 写借鉴要点

**发新对话：**

```text
项目现状：
- 后端 http://localhost:8000
- 前端 http://localhost:5173
- 5 个 P0 缺陷已修复
- 讯飞 API 改用 HTTP 方式（app/core/llm.py）
- 向量库用 FAISS（app/creative/vector_store.py）

请做以下事情（先不写业务代码）：

## 1. clone 3 个项目到 research/
- https://github.com/langchain-ai/langgraph（MIT）
- https://github.com/user-attachments/Tutor-AI（Apache-2.0，如果链接不对请搜索）
- https://github.com/vbenjs/vue-vben-admin（MIT）

## 2. 写 documents/借鉴要点.md，回答：
- LangGraph 的 State 怎么定义？节点怎么传数据？
- Tutor-AI 的对话→画像→推荐流程怎么走的？
- Vben Admin 的路由/权限/暗色模式怎么实现的？

## 3. 只学思路不复制代码
- MaxKB：RAG 交互流程
- Multi-Agent Study Assistant：Agent 分工

写完后告诉我。
```

---

## 【阶段 2】后端核心 + 创意模块

> 前置条件：修复任务 1+2 已完成，借鉴要点已写好。

**发新对话：**

```text
项目现状：
- 后端 /backend/，前端 /frontend/
- 端口 8000/5173
- 讯飞：app/core/llm.py（HTTP 方式）
- 向量：app/creative/vector_store.py（FAISS）
- IP：小智析析，队伍：知微智学
- 参考项目：research/ 目录
- 借鉴要点：documents/借鉴要点.md

开 Goal 模式。目标：完成后端全部功能。

## 1. 多智能体编排（用 langgraph.StateGraph）
节点：intent_classifier、profile_agent、resource_agent、path_agent、tutor_agent、response_agent、memory_node

## 2. 5 类资源并行生成（asyncio.gather + 前端检索 RAG）
讲解文档（Markdown）/ 思维导图（Mermaid mindmap）/ 练习题（5题+答案+解析）/ 视频脚本（分镜表）/ 代码案例（可运行）

## 3. 知识库 RAG（FAISS）
上传→切片→向量化→检索。支持 PDF/Word/TXT/Markdown。

## 4. SSE 流式对话 /api/chat/stream
事件：token（逐字）/ resource（资源卡片）/ profile_update（画像更新）/ thinking（思考中）/ done（结束）

## 5. 创意模块（选做 2 个）
- 知识图谱（概念+关系数据）
- 成就徽章系统（首次对话/生成5资源/连续3天学习 等）
- 学习 Streak
- 每日学习挑战

## 6. API 清单
/auth/*、/resources/*、/knowledge/*、/path/*、/agents/status、/creative/*

## 7. 模型等级
high→Spark4.0（画像/路径/辅导/代码）
medium→Spark3.5（文档/题目/导图/视频/对话）
low→SparkLite（意图识别/摘要/Embedding）

验收：全部 API 在 Swagger 可用，5 类资源能生成，SSE 流式正常，创意模块 2 个以上工作。
完成后告诉我「阶段 2 完成」。
```

---

## 【阶段 3】设计系统 + AI 生图

**发新对话：**

```text
项目现状：后端全部完成。前端框架已初始化。IP：小智析析。

先 Plan 模式：在 documents/design-system.md 写完整设计规范。
- 色彩：主色 #6366F1，9 阶阶梯，暗色模式完整
- 字体：中文 PingFang，英文 Inter，代码 JetBrains Mono
- 间距/圆角/阴影：4px 基准、12px 卡片、5 级阴影
- 动效：12 个 CSS @keyframes（fadeInUp/shimmer/float/pulseGlow 等）
- 3 层视觉深度：背景渐变/粒子 + glass morphism 表面 + 内容层

我确认后，再用 image2 生成以下素材存到 frontend/public/assets/：

mascot-logo.png / mascot-hero.png / mascot-chat.png
mascot-thinking.png / mascot-celebrate.png / mascot-empty.png / mascot-error.png
icon-document.svg / icon-mindmap.svg / icon-quiz.svg / icon-video.svg / icon-code.svg
bg-login.jpg / bg-hero.jpg

完成后告诉我。
```

---

## 【阶段 4】前端页面

### 4.1 全局框架 + 登录注册

```text
项目状态：后端 8000，前端 5173。素材在 frontend/public/assets/。设计在 design-system.md。

开 Goal 模式。先搭全局框架和登录页：

全局：Vue Router（7 路由）+ Pinia（3 store）+ Axios（Token 拦截器）+ Element Plus 按需 + 暗色模式 + 动画

Login 页：左右分栏，glass morphism，IP头像，表单验证，shake 动画
Register 页：同风格 + 专业选择 + 学习风格

完成后截图。
```

### 4.2 首页

```text
三段滚动：Hero（100vh，大字+count-up+浮动IP+粒子背景）+ 功能亮点（3列卡片+stagger入场）+ 时间轴动态
```

### 4.3 对话页（核心）

```text
三栏布局（左240px+中自适应+右320px）：
左栏：对话历史列表
中栏：SSE流式对话，Markdown渲染，代码块复制，资源卡片
右栏：画像面板6维实时更新

SSE事件：token / resource / profile_update / thinking / done
```

### 4.4-4.7 剩余页面（可发1个对话或分2个并行）

**资源库页：** 网格卡片 + 分类 + 搜索 + Mermaid + 代码高亮 + 弹窗详情
**学习路径页：** 时间轴 + 步骤状态 + 进度环 + 完成庆祝
**辅导页：** 左右分栏 + 3 Tab（文字/图解Mermaid/视频预留）+ 快捷标签
**管理后台：** 3 Tab（知识库上传+用户列表+系统配置）

---

## 【阶段 5】联调测试

```text
走完完整流程：注册→登录→对话→画像→资源生成→路径完成→辅导→后台

异常测试：空输入/超长/断网/Token过期/API失败/空知识库
视觉走查：1920px/1366px/暗色模式/动画

结果存 documents/测试报告.md
```

---

## 【阶段 6】文档生成

```text
生成 7 份文档到 documents/：
需求分析.docx / 系统设计.docx / 测试报告.docx / 部署说明.docx / 产品说明书.docx（配截图） / 演示PPT.pptx（12-15页） / 演示视频脚本.docx（7分钟分镜头）
```

---

## 【阶段 7】打包

```text
清理（删 research/、__pycache__、node_modules、确认 .env 不在包内）
前端 build、更新 README、打 zip

最终检查：后端启动？前端 build？.env.example？7 份文档？无硬编码密钥？开源引用标注？
```
