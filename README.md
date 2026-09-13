<div align="center">

# 🚀 CodeSage AI

### **AI-Powered Code Intelligence & Understanding Platform**

**Understand • Search • Analyze • Chat with Real-World Codebases**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Vite-8.1-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FAISS-FlatIP-0467DF?style=for-the-badge&logo=meta&logoColor=white" alt="FAISS" />
  <img src="https://img.shields.io/badge/Nomic--Embed--Text-768_dim-7B1FA2?style=for-the-badge" alt="Nomic Embeddings" />
  <img src="https://img.shields.io/badge/LangChain-LCEL_RAG-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/Ollama-Gemma_2B-black?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama / Gemma" />
  <img src="https://img.shields.io/badge/Tree--sitter-AST_Parsing-E65100?style=for-the-badge" alt="Tree-sitter" />
  <img src="https://img.shields.io/badge/Pytest-100%25_Passing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
</p>

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-supported-project-types">Supported Projects</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-security-architecture">Security</a> •
  <a href="#-testing">Testing</a>
</p>

</div>

---

## 📖 Overview

**CodeSage AI** is a production-grade, full-stack developer intelligence platform designed to help software engineers, technical leads, and students **explore, comprehend, search, and converse with unfamiliar codebases using natural language**.

Navigating complex software repositories often demands hours of manual effort: tracking through directory trees, untangling imports, locating authentication flows, and piecing together database models. CodeSage AI transforms this experience by integrating:

$$\text{AST Code Parsing} \longrightarrow \text{Dense Embeddings} \longrightarrow \text{FAISS Vector Search} \longrightarrow \text{File-Level Context Retrieval} \longrightarrow \text{LangChain RAG} \longrightarrow \text{Local Gemma LLM}$$

Developers can upload complete project ZIP archives and immediately interrogate their codebase with questions like:
* *"Where is user authentication implemented?"*
* *"Explain how the login view validates tokens and updates state."*
* *"How does the React frontend communicate with the backend API endpoints?"*
* *"Which service classes handle data pipeline batch processing?"*

Every response is strictly grounded in verified source code, citing exact file paths and line ranges with comprehensive hallucination defense.

---

## ✨ Key Features

### 🔐 Multi-Tenant Authentication & Security
- **Bcrypt Password Hashing**: Passwords salt-hashed before database persistence.
- **Signed JWT Bearer Tokens**: Stateless session authentication with configurable expiration.
- **Tenant Isolation**: Projects, file trees, vector indexes, and chat sessions are strictly partitioned per authenticated user; cross-tenant access returns HTTP 404.

### 📦 Safe Project Ingestion & Extraction
- **Multipart ZIP Upload**: Validates MIME types, magic bytes, and file size limits (up to 100MB).
- **Zip Slip Mitigation**: Path normalization guarantees extracted entries remain strictly confined within the project directory.
- **Metadata Persistence**: File counts, line counts, and storage locations tracked in PostgreSQL.

### 📁 Interactive Code Explorer & Viewer
- **Recursive Tree Navigation**: Folder structure navigation supporting nested applications and packages.
- **Safe Code Inspection**: Robust text preview with automatic encoding fallbacks (UTF-8, UTF-8-SIG, Latin-1) and binary file detection.

### 🔍 Syntax-Aware Code & Dependency Analysis
- **Tree-sitter AST Parsing**: Grammars for Python, JavaScript, JSX, and Java extract functions, classes, methods, parameters, and imports.
- **Dependency Detection**: Manifest parsing from `requirements.txt` (Python/Django) and `package.json` (Node/React).
- **Cross-File Relationship Graph**: Differentiates internal project module dependencies from external third-party packages.

### 🧠 Semantic Search & Code Indexing
- **AST-Aligned Chunking**: Source files divided into semantic code chunks preserving function/class boundaries, symbol names, and parent scopes.
- **Nomic Embed Text v1.5**: 768-dimensional dense vector embeddings generated with task-specific prefixes and L2 normalization.
- **FAISS Vector Indexing**: Separate `IndexFlatIP` vector index built and persisted per project for rapid cosine similarity search.

### 🎯 File-Level Context Retrieval (Day 17)
- **Explainable File Relevance Scoring**: Combines peak chunk similarity with supporting chunk bonuses:
  $$\text{file\_score} = 0.65 \times \text{best\_chunk} + 0.25 \times \text{top3\_mean} + \text{supporting\_bonus}$$
- **Duplicate Chunk Resistance**: Prevents repetitive boilerplate chunks from outranking high-relevance source files.
- **Relevant File Badges**: Frontend displays top-ranked file badges linked directly to the Code Explorer.

### 💬 Grounded AI Chat & Conversation History (Days 15–16)
- **LangChain LCEL Pipeline**: Connects local Ollama (`gemma:2b`) with retrieved project context.
- **Prompt Injection Defense**: Untrusted project source code is treated strictly as passive data.
- **Multi-Turn Contextual Follow-up**: Enriches referential follow-up questions (*"Where is that implemented?"*, *"Which function handles it?"*) with bounded conversation history.
- **Strict Hallucination Defense**: Model explicitly rejects questions about nonexistent features (e.g., Redis caching or GraphQL when absent) rather than inventing code.

---

## 🧩 Supported Project Types

CodeSage AI uses a unified pipeline tested and validated against diverse project paradigms:

| Project Type | Architecture / Framework | Verified Pipeline Capabilities | Status |
| :--- | :--- | :--- | :---: |
| **Python** | Standalone modules, data pipelines, utilities | Functions, classes, imports, `requirements.txt`, semantic search, RAG | ✅ **Full Support** |
| **Django** | Full-stack web framework | Models, views, URLs, serializers, admin, settings, cross-file flows | ✅ **Full Support** |
| **React** | SPA, Vite, Functional Components, JSX | Functional components, Hooks, Axios services, `package.json`, JSX chunking | ✅ **Full Support** |
| **JavaScript** | Node.js / Vanilla JS | ES6 classes, async functions, arrow functions, CommonJS/ESM imports | ✅ **Full Support** |
| **Java** | OOP Classes, Methods, Packages | Tree-sitter AST parsing for classes, methods, and package imports | ⚠️ **Syntax Parsing** |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (React 19 + Vite)"]
        UI[Landing Page / Dashboard]
        UploadUI[Project Upload]
        ExplorerUI[Code Explorer]
        ChatUI[AI Project Chat]
    end

    subgraph API["Backend API Layer (FastAPI)"]
        AuthRouter["/api/auth (JWT & Bcrypt)"]
        ProjectRouter["/api/projects (CRUD & Files)"]
        AnalysisRouter["/api/projects/{id}/analysis"]
        IndexRouter["/api/projects/{id}/index"]
        ContextRouter["/api/projects/{id}/context/retrieve"]
        ChatRouter["/api/projects/{id}/chat"]
    end

    subgraph Data["Storage & Database Layer"]
        PG[(PostgreSQL Database)]
        FS[Disk Storage / Extracted Files]
    end

    subgraph Processing["Processing & Intelligence Pipeline"]
        TS[Tree-sitter AST Parser]
        Chunker[Structural Code Chunker]
        Nomic[Nomic Embed Text v1.5]
        FAISS[(FAISS IndexFlatIP Store)]
        Retriever[File-Level Context Retriever]
    end

    subgraph LLM["Local AI Inference (Ollama)"]
        LangChain[LangChain LCEL RAG Chain]
        Gemma[Google Gemma 2B]
    end

    UI --> AuthRouter
    UploadUI --> ProjectRouter
    ExplorerUI --> ProjectRouter
    ChatUI --> ChatRouter

    ProjectRouter --> FS
    ProjectRouter --> PG
    AnalysisRouter --> TS
    IndexRouter --> Chunker
    Chunker --> Nomic
    Nomic --> PG
    Nomic --> FAISS

    ChatRouter --> ContextRouter
    ContextRouter --> FAISS
    ContextRouter --> Retriever
    Retriever --> LangChain
    LangChain --> Gemma
    Gemma --> ChatRouter
    ChatRouter --> PG
```

---

## 🔄 End-to-End Processing Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant DB as PostgreSQL
    participant AI as Local AI Engine (Nomic + FAISS + Gemma)

    Dev->>FE: Upload project (.zip archive)
    FE->>BE: POST /api/projects/upload (multipart)
    BE->>BE: Validate ZIP & Extract (Zip Slip Defense)
    BE->>DB: Store project & file records
    BE-->>FE: Project ready (Status: uploaded)

    Dev->>FE: Trigger Indexing
    FE->>BE: POST /api/projects/{id}/index
    BE->>BE: Tree-sitter AST parse & Chunk code
    BE->>AI: Generate Nomic embeddings (768-dim)
    AI->>DB: Persist vectors & hashes
    BE->>AI: Build FAISS IndexFlatIP
    BE-->>FE: Indexing & Vector Space completed

    Dev->>FE: Ask: "Where is authentication implemented?"
    FE->>BE: POST /api/projects/{id}/chat
    BE->>AI: FAISS semantic search + Context Retriever
    AI-->>BE: Top matching files & structured chunks
    BE->>AI: Format Grounded Prompt + History -> Gemma 2B
    AI-->>BE: Synthesized answer with file/line citations
    BE->>DB: Save ChatHistory turn
    BE-->>FE: Return answer, relevant files, and source citations
    FE-->>Dev: Render response with clickable file badges
```

---

## 🛠️ Technology Stack

| Domain | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | `^0.100.0` | High-performance asynchronous REST API |
| **Application Server** | **Uvicorn** | `^0.22.0` | ASGI production server |
| **Language** | **Python** | `3.10+` | Backend runtime |
| **Database** | **PostgreSQL** | `15+` | Relational store for users, projects, files, chunks, chat |
| **ORM** | **SQLAlchemy** | `^2.0.0` | Object relational mapping & transactional sessions |
| **Schema Validation** | **Pydantic** | `^2.0.0` | Request/response validation & serialization |
| **AST Parsing** | **Tree-sitter** | `^0.22.0` | Grammars for Python, JavaScript, Java |
| **Embeddings** | **Nomic Embed Text** | `v1.5` | 768-dimensional local text/code embeddings |
| **Embedding Engine** | **SentenceTransformers** | `^3.0.0` | Model inference on CPU/CUDA |
| **Vector Search** | **FAISS** | `faiss-cpu` | In-memory & persisted inner-product index |
| **RAG Orchestration** | **LangChain** | `^0.3.0` | Prompt templates, output parsers, LCEL pipelines |
| **Local LLM Runtime**| **Ollama** | `Latest` | Local container/daemon for open weights |
| **Foundation Model** | **Gemma 2B** | `gemma:2b` | Code reasoning and question answering |
| **Frontend Library** | **React** | `^19.2.7` | Reactive single page application |
| **Build System** | **Vite** | `^8.1.1` | Fast HMR development and production bundling |
| **Routing** | **React Router** | `^7.18.3` | Client-side routing with route guards |
| **Testing** | **Pytest** | `^9.1.1` | Comprehensive backend test automation |

---

## 📡 API Reference

All endpoints (except `/api/auth/register` and `/api/auth/login`) require a valid JWT Bearer token:
`Authorization: Bearer <access_token>`.

### Authentication Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/auth/register` | Register new user account with hashed password | No |
| `POST` | `/api/auth/login` | Authenticate user credentials and issue signed JWT | No |
| `GET` | `/api/auth/me` | Retrieve profile of the currently authenticated user | **Yes** |

### Project & File Explorer Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/projects/upload` | Upload and safely unpack project ZIP archive | **Yes** |
| `GET` | `/api/projects` | List all projects belonging to authenticated user | **Yes** |
| `GET` | `/api/projects/{id}` | Retrieve specific project metadata by ID | **Yes** |
| `GET` | `/api/projects/{id}/files` | Retrieve hierarchical file tree of extracted project | **Yes** |
| `GET` | `/api/projects/{id}/file` | Read preview contents of a specific file (`?path=...`) | **Yes** |

### Code Analysis & AST Parsing Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/projects/{id}/analysis` | Compute language distribution and directory metrics | **Yes** |
| `GET` | `/api/projects/{id}/dependencies` | Detect manifest packages and cross-file import relationships | **Yes** |
| `GET` | `/api/projects/{id}/parse` | Tree-sitter AST parse file for functions, classes, imports | **Yes** |

### Code Indexing & Semantic Vector Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/projects/{id}/index` | Chunk source code files and persist metadata | **Yes** |
| `GET` | `/api/projects/{id}/index/status` | Read code indexing completion status | **Yes** |
| `GET` | `/api/projects/{id}/chunks` | Retrieve indexed chunks with symbol metadata | **Yes** |
| `POST` | `/api/projects/{id}/embeddings` | Generate 768-dim Nomic embeddings for indexed chunks | **Yes** |
| `GET` | `/api/projects/{id}/embeddings/status`| Read embedding generation status | **Yes** |
| `POST` | `/api/projects/{id}/vector-index` | Build and persist FAISS `IndexFlatIP` vector index | **Yes** |
| `GET` | `/api/projects/{id}/vector-index/status` | Read FAISS vector index readiness status | **Yes** |
| `POST` | `/api/projects/{id}/search` | Semantic vector search query across code chunks | **Yes** |

### Context Retrieval & AI Chat Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/projects/{id}/context/retrieve` | Day 17 file-level context retrieval with relevance scoring | **Yes** |
| `POST` | `/api/projects/{id}/rag` | Single-turn Question-Answering RAG pipeline | **Yes** |
| `POST` | `/api/projects/{id}/chat` | Multi-turn conversational chat with follow-up awareness | **Yes** |
| `GET` | `/api/projects/{id}/chat` | Retrieve chronological chat history for project | **Yes** |
| `DELETE` | `/api/projects/{id}/chat` | Clear chat history for project or conversation | **Yes** |
| `GET` | `/api/ai/health` | Check local Ollama daemon and Gemma model reachability | **Yes** |
| `POST` | `/api/ai/test` | Diagnostic prompt test with local Ollama runtime | **Yes** |

---

## ⚡ Quick Start

### Prerequisites
1. **Python 3.10+** (Conda environment recommended: `codesage`)
2. **Node.js 18+** & **npm**
3. **PostgreSQL 14+** running locally
4. **Ollama** installed with `gemma:2b` model pulled

---

### 1. Clone the Repository
```bash
git clone https://github.com/Amal070/CodeSage-AI.git
cd CodeSage-AI
```

---

### 2. Backend Setup

#### Activate Conda Environment & Install Dependencies
```bash
conda activate codesage
cd backend
pip install -r requirements.txt
```

#### Configure Environment Variables
Copy the example template and verify database credentials:
```bash
cp .env.example .env
```
*(Ensure `DATABASE_URL` matches your local PostgreSQL instance).*

#### Run Database Migrations
```bash
alembic upgrade head
```

#### Start FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```
Backend API will be live at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

---

### 3. Frontend Setup

In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend development server will be live at `http://localhost:5173`.

---

### 4. Local AI Setup (Ollama)

Start Ollama and verify Gemma 2B is pulled:
```bash
ollama serve
ollama pull gemma:2b
```

---

## ⚙️ Environment Configuration

Configuration is managed via `backend/app/core/config.py` reading from `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/codesage_db` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | *(Set securely in `.env`)* | Secret signing key for JWT tokens |
| `JWT_ALGORITHM` | `HS256` | Cryptographic algorithm for JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime before expiration |
| `MAX_UPLOAD_SIZE_MB` | `100` | Maximum project ZIP archive upload size |
| `MAX_VIEWABLE_FILE_SIZE_MB` | `5` | Maximum file size viewable in code explorer |
| `STORAGE_DIR` | `storage` | Directory for extracted project files |
| `INDEXES_DIR` | `storage/indexes` | Directory for saved FAISS vector indexes |
| `EMBEDDING_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | HuggingFace embedding model name |
| `EMBEDDING_BATCH_SIZE` | `32` | Batch size for embedding inference |
| `EMBEDDING_DEVICE` | `auto` | Execution device (`auto`, `cuda`, or `cpu`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL of local Ollama runtime |
| `OLLAMA_MODEL` | `gemma:2b` | Model name pulled in Ollama |
| `MAX_RAG_TOP_K` | `10` | Maximum chunks retrieved per RAG query |
| `MAX_CONTEXT_CHARACTERS` | `12000` | Token character budget for LLM context |
| `CHAT_HISTORY_LIMIT` | `10` | Number of previous chat turns passed to LLM |
| `RETRIEVAL_TOP_FILES` | `5` | Default number of top matching files surfaced |
| `RETRIEVAL_CHUNKS_PER_FILE` | `3` | Maximum chunks extracted per top file |

---

## 🛡️ Security Architecture

1. **Zip Slip Protection**:
   All ZIP member file destinations are resolved against the absolute project extraction root. If an archive entry attempts directory traversal via `../`, extraction halts and returns an HTTP 400 error.
2. **Strict Path Traversal Guard**:
   File viewing endpoints disallow leading slashes, drive specifications (`C:`), and `..` parent segments.
3. **Multi-User Tenancy Isolation**:
   Every database query filters by `user_id == current_user.id`. Attempts by User B to query, index, browse, or chat with User A's project return HTTP 404.
4. **Prompt Injection Defense**:
   All retrieved source code chunks are wrapped within `=== PROJECT CONTEXT ===` XML/markdown blocks marked as passive data. System instructions forbid executing prompt overrides found inside user code.
5. **Hallucination Rejection**:
   Strict prompt rules prohibit the LLM from inventing files, endpoints, or technologies (such as claiming REST/Axios is GraphQL, or inventing Redis when absent).

---

## 🧪 Testing & Verification

CodeSage AI includes an extensive, production-grade automated test suite in `backend/tests/`:

```powershell
# Run the complete test suite
pytest -v

# Run project pipeline tests (Day 18 validation)
pytest tests/test_day18_django_pipeline.py -v
pytest tests/test_day18_react_pipeline.py -v
pytest tests/test_day18_python_pipeline.py -v

# Run cross-project & multi-user isolation tests
pytest tests/test_day18_cross_project_isolation.py -v

# Run context retrieval and RAG regression tests
pytest tests/test_day17_context_retrieval.py -v
pytest tests/test_day16_ai_responses.py -v
```

### Verified Test Areas
* ✅ Authentication, registration, and JWT expiration
* ✅ ZIP extraction, magic byte validation, and Zip Slip defense
* ✅ File explorer tree traversal and encoding fallback
* ✅ Tree-sitter AST parsing across Python, JavaScript, JSX, and Java
* ✅ Dependency manifest extraction (`requirements.txt`, `package.json`)
* ✅ Code indexing, AST symbol capture, and deterministic hashing
* ✅ 768-dim Nomic embedding generation and PostgreSQL storage
* ✅ FAISS index build, disk persistence, and reload
* ✅ Day 17 context retrieval file ranking and duplicate resistance
* ✅ Multi-turn conversation history and referential follow-up queries
* ✅ Cross-project isolation and multi-user tenancy boundary defense
* ✅ Grounding integrity, source citation accuracy, and hallucination rejection

---

## 📂 Project Structure

```text
CodeSage-AI/
├── backend/
│   ├── alembic/                      # Database migrations
│   ├── app/
│   │   ├── api/                      # FastAPI route controllers
│   │   │   ├── auth.py               # Registration, login, /me
│   │   │   ├── project.py            # Upload, files, analysis, index, search, chat
│   │   │   └── ai.py                 # Health check and diagnostic endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Centralized settings from .env
│   │   │   └── security.py           # Bcrypt hashing & JWT utilities
│   │   ├── models/                   # SQLAlchemy database models
│   │   │   ├── user.py               # Users table
│   │   │   ├── project.py            # Projects & UploadedFiles tables
│   │   │   ├── code_chunk.py         # CodeChunks table with embeddings
│   │   │   └── chat_history.py       # ChatHistory table with conversation_id
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── auth.py, project.py, code_parser.py, code_index.py
│   │   │   ├── project_analysis.py, dependency_analysis.py, embedding.py
│   │   │   ├── semantic_search.py, rag.py, chat.py, context_retrieval.py
│   │   ├── services/                 # Core business & AI logic
│   │   │   ├── auth_service.py       # User credentials & JWT
│   │   │   ├── project_service.py    # ZIP extraction & file explorer
│   │   │   ├── code_parser.py        # Tree-sitter AST parser
│   │   │   ├── project_analyzer.py   # Languages & structure analysis
│   │   │   ├── dependency_analyzer.py# Manifest & import relationships
│   │   │   ├── code_indexer.py       # AST chunker & hash generator
│   │   │   ├── embedding_service.py  # Nomic Embed Text v1.5
│   │   │   ├── faiss_service.py      # FAISS IndexFlatIP vector index
│   │   │   ├── context_retriever.py  # File-level relevance scoring (Day 17)
│   │   │   ├── rag_service.py        # LangChain LCEL RAG pipeline
│   │   │   ├── ollama_service.py     # Local Gemma LLM runtime
│   │   │   ├── chat_service.py       # Multi-turn chat & sessions
│   │   │   └── prompts.py            # Centralized prompt templates & safety
│   │   ├── database.py               # Engine & sessionmaker
│   │   └── main.py                   # FastAPI app factory & CORS
│   ├── storage/                      # Extracted projects & FAISS indexes
│   ├── tests/                        # Comprehensive test suite (Days 1–18)
│   ├── .env.example                  # Environment configuration template
│   ├── alembic.ini                   # Alembic configuration
│   ├── pytest.ini                    # Pytest configuration
│   └── requirements.txt              # Backend dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/               # React UI components
│   │   │   ├── LandingPage.jsx       # Public marketing page
│   │   │   ├── Login.jsx, Register.jsx # Authentication forms
│   │   │   ├── DashboardLayout.jsx   # Shell with navigation sidebar
│   │   │   ├── DashboardOverview.jsx # Project cards & metrics
│   │   │   ├── ProjectUpload.jsx     # Drag-and-drop ZIP upload
│   │   │   ├── ProjectExplorer.jsx   # Code tree & syntax viewer
│   │   │   ├── ProjectAnalysis.jsx   # Language charts & file stats
│   │   │   ├── ProjectDependencies.jsx# Dependency list & graph
│   │   │   ├── ProjectSearch.jsx     # Semantic vector search UI
│   │   │   ├── ProjectRag.jsx        # Single-turn RAG question UI
│   │   │   ├── ProjectChat.jsx       # Multi-turn chat & file badges
│   │   │   └── AiTest.jsx            # Ollama health diagnostic
│   │   ├── context/                  # AuthContext for JWT state
│   │   ├── services/                 # Fetch API client services
│   │   ├── App.jsx                   # Route declarations
│   │   └── index.css                 # Custom design tokens & layout
│   ├── package.json
│   └── vite.config.js
│
└── README.md                         # Project documentation
```

---

## 📈 Development Milestones (Days 1–18)

- [x] **Day 1**: FastAPI backend setup, React frontend initialization, PostgreSQL connection.
- [x] **Day 2**: SQLAlchemy database models, Alembic migrations, database schema design.
- [x] **Day 3**: Secure user registration, password hashing with bcrypt, JWT authentication.
- [x] **Day 4**: Protected dashboard layout, responsive sidebar navigation, user logout.
- [x] **Day 5**: ZIP project upload, Zip Slip defense, project metadata storage.
- [x] **Day 6**: Interactive File Explorer, recursive directory tree, safe file viewing.
- [x] **Day 7**: Tree-sitter AST parsing for Python, JavaScript, and Java.
- [x] **Day 8**: Project structure analysis, language distribution calculation.
- [x] **Day 9**: Dependency detection, manifest parsing (`requirements.txt`, `package.json`).
- [x] **Day 10**: Syntax-aware code indexing, AST chunking, deterministic hashing.
- [x] **Day 11**: Nomic Embed Text v1.5 integration, 768-dim embeddings generation.
- [x] **Day 12**: FAISS `IndexFlatIP` vector index creation, persistence, and semantic search.
- [x] **Day 13**: Ollama runtime integration, local Google Gemma 2B model execution.
- [x] **Day 14**: LangChain RAG pipeline, context construction, and source grounding.
- [x] **Day 15**: AI Project Chat interface, conversational question answering.
- [x] **Day 16**: Prompt engineering, prompt injection defenses, structured conversation history.
- [x] **Day 17**: File-level context retrieval, relevance scoring, and top matching file badges.
- [x] **Day 18**: Comprehensive validation across Django, React, and Python projects with multi-tenant isolation.
- [x] **Day 19**: Professional production-grade repository documentation.

---

## 🗺️ Roadmap & Future Enhancements

- [ ] Direct GitHub / GitLab repository URL importing
- [ ] Automatic API documentation and README generation from indexed code
- [ ] Interactive dependency relationship graph visualization (Cytoscape / D3.js)
- [ ] Real-time token streaming for AI chat responses
- [ ] Cloud deployment templates (Docker Compose, Kubernetes Helm chart)
- [ ] Automated security vulnerability scanning in project dependencies

---

## 📜 License & Acknowledgments

This project is created for **educational, portfolio, and code intelligence development**.

* **Author**: [Amal Shaji](https://github.com/Amal070)
* **Built With**: FastAPI, React, PostgreSQL, Tree-sitter, FAISS, LangChain, Nomic AI, and Ollama.

---

<div align="center">

**CodeSage AI — Understand your codebase. Search your codebase. Talk to your codebase.**

</div>
