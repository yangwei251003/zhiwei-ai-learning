# A3 - 基于大模型的个性化资源生成与学习多智能体系统

> 第十五届“中国软件杯”大学生软件设计大赛 · A3 赛道作品
> 队伍：知微智学 ｜ IP形象：小智析析

## 技术栈

- **前端**: Vue 3 + Vite + Element Plus + Pinia + SSE 流式通信
- **后端**: FastAPI + Python 3.12 + SQLAlchemy + PostgreSQL
- **智能体**: LangGraph 多智能体编排
- **大模型**: 讯飞星火 Spark API（赛道要求）+ DeepSeek/Qwen（可选补充）
- **向量库**: ChromaDB（本地）
- **知识库**: 课程文档 → Embedding → 向量检索

## 项目结构

```
A3-multi-agent-learning/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 配置、安全、数据库
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── agents/       # LangGraph 多智能体
│   │   ├── schemas/      # Pydantic 模型
│   │   └── knowledge_base/  # 知识库工具
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/        # 页面
│   │   ├── components/   # 组件
│   │   ├── api/          # API 请求
│   │   ├── store/        # Pinia 状态
│   │   └── router/       # 路由
│   └── package.json
├── documents/            # 提交文档
└── README.md
```

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env  # 配置讯飞 API Key
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```
