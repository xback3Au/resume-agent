# 简历定制AI工具

这是一个使用 Python 构建的原型项目：
- 首次运行：一次性将你的个人信息，项目报告、实习笔记等私有文档入库，所有txt文件的内容都会直接作为大模型的上下文，其他格式如pdf,docx等文件的内容会被构建为RAG
- 日常使用：启动本地网页，粘贴岗位 JD，自动生成定制中文简历
- 不满意可继续改写：基于当前版本输入改写指令，生成新版本
- 支持下载：将当前版本导出为 TXT / DOCX / PDF

## 1. 功能概览

- 私有文档读取：支持 `pdf / docx / txt / md`
- 智能检索：根据 JD 从私有资料中召回最相关片段
- 定制生成：调用 DeepSeek API 生成中文简历文本
- 版本迭代：基于上一版简历进行连续改写
- 文件导出：下载当前版本为 TXT / DOCX / PDF（支持照片位置）

## 2. 技术栈

- 后端：FastAPI
- Agent/RAG：LangChain
- 模型：DeepSeek（OpenAI 兼容接口）
- 向量库：Chroma（本地持久化）
- 向量模型：Sentence Transformers（默认多语言模型）

## 3. 目录结构

```text
app/
  api/                 # HTTP 路由
  adapters/            # DeepSeek 与向量库适配层
  core/                # 配置、日志、安全工具
  prompts/             # 提示词模板（中文）
  services/            # 入库、生成、改写、导出逻辑
scripts/
  ingest.py            # 一次性入库脚本
web/
  index.html           # 本地网页
data/
  raw/                 # 原始语料目录（建议放 个人信息/技能/实习/项目）
  index/               # 向量索引
  sessions/            # 会话与版本数据
  uploads/             # 导出时使用的照片文件
tests/                 # 最小测试样例
```

## 4. 环境准备

1) 安装依赖：

```bash
pip install -r requirements.txt
```

说明：本项目的 `requirements.txt` 使用“版本区间”而不是全部精确版本，目的是在保证兼容性的同时，降低 Windows/conda 环境下的安装冲突概率。

2) 复制环境变量模板并填写：

```bash
copy .env.example .env
```

请在 `.env` 中至少配置：
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）
- `DEEPSEEK_MODEL`（默认 `deepseek-reasoner`效果更好，也可改为`deepseek-chat`更省token）

## 5. 一次性入库（只需首次执行）

将你的私有文档放在 `data/raw`（建议只保留 `简历/实习/项目` 三类目录），然后执行：

```bash
python scripts/ingest.py --input_dir "data/raw"
```

成功后会输出文档数与切分块数，索引写入 `data/index`。

## 6. 启动本地服务与网页

启动服务：

```bash
uvicorn app.main:app --reload
```

打开浏览器访问：
- `http://127.0.0.1:8000/`

使用方式：
1. 粘贴 JD，点击“生成首版简历”
2. 输入改写指令，点击“基于当前版本改写”
3. 使用导出接口下载 TXT / DOCX / PDF

## 7. 接口说明

- `POST /api/generate`
  - 入参：`{ "jd_text": "..." }`
  - 出参：`session_id`, `version_id`, `resume_text`, `sources`

- `POST /api/rewrite`
  - 入参：`{ "session_id": "...", "version_id": "...", "instruction": "..." }`
  - 出参：新 `version_id` 与 `resume_text`

- `GET /api/export?session_id=...&version_id=...&format=txt`
  - 下载 TXT 文件

- `GET /api/export?session_id=...&version_id=...&format=docx`
  - 下载一页版 DOCX（右上角预留照片位置）

- `GET /api/export?session_id=...&version_id=...&format=pdf`
  - 下载一页版 PDF（超过一页时自动压缩一次）

- `GET /api/export?session_id=...&version_id=...&format=pdf&photo_file=me.jpg`
  - 指定照片文件名，照片需放在 `data/uploads/me.jpg`

- `GET /health`
  - 健康检查

## 8. 隐私与安全建议

- API Key 仅放在 `.env`，不要写入代码或前端
- 日志默认不记录 JD 与简历全文
- 仅在本机保存索引与会话数据，避免上传到第三方存储
- 输入 JD 会做基础清洗与长度限制

## 9. 运行测试

```bash
pytest -q
```

## 10. 常见问题

- 问：为什么依赖没有全部写死为 `==`？
  - 答：`==` 能保证最强复现性，但容易与新环境产生解析冲突；版本区间（如 `>=x,<y`）在主版本不变前提下更灵活，通常更容易安装成功。

- 问：安装时如果不写版本号会怎样？
  - 答：`pip` 会安装“当前最新版本”，短期可能可用，但未来上游 API 变更后可能导致代码报错或行为变化，因此生产/长期项目不建议完全不限制版本。

- 问：提示“索引不存在”怎么办？
  - 答：先执行一次 `scripts/ingest.py` 完成入库

- 问：生成效果不满意怎么办？
  - 答：使用“改写指令”反复迭代，例如“突出分布式系统项目并压缩到一页”

- 问：Windows 中文路径会有影响吗？
  - 答：建议使用 UTF-8 编码环境；若个别文档解析失败，可先转成 txt/md 再入库
