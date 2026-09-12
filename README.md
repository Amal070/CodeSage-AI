<div align="center">

# 🧠 CodeSage AI

### **AI-Powered Code Intelligence Platform**

**Understand • Search • Analyze • Chat with Your Codebase**

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
</p>

<p>
  <img src="https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=for-the-badge" />
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-0467DF?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Ollama-Local_AI-black?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Tree--sitter-Code_Parsing-orange?style=for-the-badge" />
</p>

<p>
  <a href="#-overview">Overview</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

</div>

---

## 🚀 Overview

**CodeSage AI** is a full-stack AI-powered platform that helps developers **understand, explore, search, analyze, and interact with software codebases using natural language**.

Large software projects can be difficult to understand because developers need to navigate hundreds or thousands of files, identify dependencies, trace authentication flows, and manually locate relevant implementations.

CodeSage AI addresses this problem by combining:

**Code Parsing + Embeddings + Vector Search + RAG + Local LLMs**

into a unified developer experience.

### 💡 The Core Idea

Instead of searching a codebase like this:

```text
Ctrl + F → keyword → inspect files → follow dependencies → understand code
```

CodeSage AI enables developers to ask:

```text
"Where is authentication implemented?"

"Explain how the login process works."

"Which files are responsible for database operations?"

"How does this function interact with the rest of the application?"

"Show me the code related to JWT authentication."
```

The platform retrieves relevant code and uses an AI model to generate a contextual explanation.

---

# 🎯 What Problem Does CodeSage AI Solve?

Modern applications often contain:

* Hundreds of source files
* Multiple programming languages
* Complex dependencies
* Unfamiliar architectures
* Legacy code
* Difficult-to-trace workflows

Understanding such systems manually is time-consuming.

### Traditional Approach

```text
Developer
   │
   ├── Browse folders
   ├── Search keywords
   ├── Open multiple files
   ├── Trace imports
   ├── Understand dependencies
   └── Build mental model
```

### CodeSage AI Approach

```text
Developer
   │
   ▼
Ask a natural-language question
   │
   ▼
Semantic Code Search
   │
   ▼
Retrieve relevant code
   │
   ▼
RAG + AI reasoning
   │
   ▼
Context-aware explanation
```

---

# ✨ Features

<table>
<tr>
<td width="50%">

### 📁 Project Intelligence

Upload a software project and automatically process its source files and project structure.

</td>
<td width="50%">

### 🔎 Semantic Code Search

Find relevant code using natural language rather than relying only on exact keywords.

</td>
</tr>

<tr>
<td>

### 🧠 AI Code Understanding

Ask questions about functions, modules, authentication, databases, and application workflows.

</td>
<td>

### 💬 AI Project Chat

Interact conversationally with your entire indexed codebase.

</td>
</tr>

<tr>
<td>

### 🔗 Dependency Analysis

Explore relationships between project components and understand how different parts interact.

</td>
<td>

### 🌳 Intelligent Code Parsing

Parse source code into meaningful structures before indexing and retrieval.

</td>
</tr>

<tr>
<td>

### 🔐 Authentication

Secure registration, login, password hashing, JWT authentication, and protected routes.

</td>
<td>

### 🤖 Local AI

Use locally hosted AI models through Ollama for privacy-conscious code analysis.

</td>
</tr>
</table>

---

# 🧠 AI Capabilities

CodeSage AI is designed around four major capabilities:

```text
        ┌────────────────────────────┐
        │       CODE INTELLIGENCE    │
        └─────────────┬──────────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   UNDERSTAND       SEARCH         ANALYZE
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
                    CHAT
```

### 1. Understand

Understand what a function, class, module, or workflow does.

### 2. Search

Find semantically related code using natural-language queries.

### 3. Analyze

Analyze project structure, dependencies, and relationships.

### 4. Chat

Interact with the codebase through an AI-powered conversational interface.

---

# 🏗️ Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                         USER                              │
└──────────────────────────┬────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────┐
│                    REACT FRONTEND                         │
│                                                           │
│  Dashboard │ Upload │ Explorer │ Search │ Analysis │ Chat │
└──────────────────────────┬────────────────────────────────┘
                           │
                        REST API
                           │
                           ▼
┌───────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                        │
│                                                           │
│ Authentication │ Projects │ Parser │ Search │ AI │ RAG   │
└───────────────┬───────────┬───────────┬───────────────────┘
                │           │           │
                ▼           ▼           ▼
         ┌───────────┐ ┌───────────┐ ┌──────────────┐
         │PostgreSQL │ │Tree-sitter│ │Project Store │
         └───────────┘ └─────┬─────┘ └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │Code Chunks   │
                      └──────┬───────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Nomic Embeddings│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      FAISS      │
                    │  Vector Search  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    LangChain    │
                    │   RAG Pipeline  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Ollama      │
                    │   Local LLM     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ AI Response     │
                    └─────────────────┘
```

---

# 🔄 End-to-End AI Pipeline

The core intelligence pipeline follows this process:

```text
             PROJECT UPLOAD
                    │
                    ▼
             FILE EXTRACTION
                    │
                    ▼
             CODE DISCOVERY
                    │
                    ▼
             TREE-SITTER PARSING
                    │
                    ▼
              CODE CHUNKING
                    │
                    ▼
           NOMIC EMBEDDINGS
                    │
                    ▼
              FAISS INDEX
                    │
                    │
          ┌─────────▼─────────┐
          │   USER QUESTION   │
          └─────────┬─────────┘
                    │
                    ▼
            QUERY EMBEDDING
                    │
                    ▼
          SEMANTIC RETRIEVAL
                    │
                    ▼
           RELEVANT CODE
                    │
                    ▼
             RAG CONTEXT
                    │
                    ▼
             LANGCHAIN
                    │
                    ▼
               OLLAMA
                    │
                    ▼
          CONTEXTUAL ANSWER
```

---

# 🔍 Semantic Search

Traditional search depends heavily on exact keywords.

For example:

```text
authentication
```

CodeSage AI allows queries based on **intent and meaning**.

Example:

```text
"Where does the application verify a user's identity?"
```

The system:

```text
Question
   ↓
Embedding
   ↓
FAISS similarity search
   ↓
Relevant code chunks
   ↓
Ranked results
```

This makes code discovery more natural and useful for unfamiliar codebases.

---

# 💬 AI Code Chat

Users can ask questions directly about their project.

### Example

**User**

```text
How does authentication work in this project?
```

**CodeSage AI**

```text
The authentication flow begins with the login endpoint,
which validates the user's credentials and generates a JWT
token. The token is then used to access protected routes...
```

Another example:

```text
Explain the database architecture.

Where is the JWT token generated?

Which files handle user registration?

How does the frontend communicate with the backend?

What happens when a project is uploaded?
```

---

# 🔐 Security Architecture

Authentication is implemented using industry-standard concepts:

```text
                 USER
                   │
                   ▼
              REGISTER
                   │
                   ▼
            PASSWORD HASHING
                   │
                   ▼
              DATABASE
                   │
                   ▼
                LOGIN
                   │
                   ▼
             JWT TOKEN
                   │
                   ▼
          PROTECTED ROUTES
```

### Security Components

* 🔑 Password hashing
* 🎫 JWT authentication
* 🛡️ Protected API routes
* 🔒 Environment-based secrets
* 🗄️ Secure database access

Sensitive configuration should be stored in environment variables rather than committed to source control.

---

# 🛠️ Technology Stack

| Category                   | Technology       |
| -------------------------- | ---------------- |
| **Frontend**               | React            |
| **Build Tool**             | Vite             |
| **Backend**                | FastAPI          |
| **Language**               | Python           |
| **Database**               | PostgreSQL       |
| **ORM**                    | SQLAlchemy       |
| **Migrations**             | Alembic          |
| **Authentication**         | JWT              |
| **Password Security**      | Password Hashing |
| **Code Parsing**           | Tree-sitter      |
| **Embeddings**             | Nomic Embed Text |
| **Vector Database/Search** | FAISS            |
| **AI Framework**           | LangChain        |
| **LLM Runtime**            | Ollama           |
| **LLM**                    | Gemma            |
| **Testing**                | Pytest           |
| **API Style**              | REST             |

---

# 📂 Project Structure

```text
CodeSage-AI/
│
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── ...
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_ai_chat.py
│   │   ├── test_code_indexing.py
│   │   ├── test_code_parser.py
│   │   ├── test_dependency_analysis.py
│   │   ├── test_embedding_generation.py
│   │   ├── test_faiss_retrieval.py
│   │   ├── test_file_explorer.py
│   │   ├── test_ollama_ai.py
│   │   ├── test_project_analysis.py
│   │   ├── test_project_upload.py
│   │   └── test_rag_pipeline.py
│   │
│   └── storage/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── AiTest.jsx
│   │   │   ├── DashboardLayout.jsx
│   │   │   ├── DashboardOverview.jsx
│   │   │   ├── LandingPage.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── ProjectAnalysis.jsx
│   │   │   ├── ProjectChat.jsx
│   │   │   ├── ProjectDependencies.jsx
│   │   │   ├── ProjectExplorer.jsx
│   │   │   ├── ProjectRag.jsx
│   │   │   ├── ProjectSearch.jsx
│   │   │   ├── ProjectUpload.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── Register.jsx
│   │   │   └── Sidebar.jsx
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   │
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

---

# ⚙️ Installation

## Prerequisites

Make sure the following are installed:

* Python 3.10+
* Node.js
* npm
* PostgreSQL
* Git
* Ollama

---

## 1. Clone the Repository

```bash
git clone https://github.com/Amal070/CodeSage-AI.git
cd CodeSage-AI
```

---

# 🐍 Backend Setup

### Activate the environment

```bash
conda activate codesage
```

### Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

# 🗄️ Database Configuration

Create a PostgreSQL database for CodeSage AI.

Configure the required environment variables.

Example:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/codesage
SECRET_KEY=your-secret-key
```

> ⚠️ Never commit your `.env` file or real credentials to GitHub.

---

# 🧱 Database Migrations

If Alembic is configured:

```bash
alembic upgrade head
```

---

# ▶️ Start Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# ⚛️ Frontend Setup

Open a second terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🤖 Ollama Setup

Install Ollama and download the required model.

Example:

```bash
ollama pull gemma
```

Run Ollama:

```bash
ollama serve
```

CodeSage AI can then communicate with the locally running model.

---

# 🧪 Testing

The backend contains tests for major system components.

Run the complete test suite:

```bash
pytest
```

Testing areas include:

```text
Authentication
       │
Project Upload
       │
Code Parsing
       │
Project Analysis
       │
Dependency Analysis
       │
Embedding Generation
       │
FAISS Retrieval
       │
Ollama AI
       │
RAG Pipeline
       │
AI Chat
```

---

# 📸 Application Preview

> Replace the placeholders below with actual screenshots after completing the UI.

## 🏠 Landing Page

<p align="center">
  <img src="docs/screenshots/landing-page.png" width="900" alt="CodeSage AI Landing Page">
</p>

---

## 📊 Dashboard

<p align="center">
  <img src="docs/screenshots/dashboard.png" width="900" alt="CodeSage AI Dashboard">
</p>

---

## 📁 Project Upload

<p align="center">
  <img src="docs/screenshots/project-upload.png" width="900" alt="Project Upload">
</p>

---

## 🔎 Semantic Search

<p align="center">
  <img src="docs/screenshots/semantic-search.png" width="900" alt="Semantic Code Search">
</p>

---

## 💬 AI Code Chat

<p align="center">
  <img src="docs/screenshots/ai-chat.png" width="900" alt="AI Code Chat">
</p>

---

## 📈 Project Analysis

<p align="center">
  <img src="docs/screenshots/project-analysis.png" width="900" alt="Project Analysis">
</p>

---

# 📊 Project Workflow

```text
┌──────────────────┐
│ Upload Project   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Extract Files    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Parse Source     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Generate         │
│ Embeddings       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Build FAISS      │
│ Index            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Project Ready    │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────┐
│                                │
│ Search │ Analyze │ Explore │ AI Chat │
│                                │
└────────────────────────────────┘
```

---

# 🎯 Use Cases

### 👨‍💻 Developers

Understand unfamiliar repositories quickly.

### 🏢 Software Teams

Reduce onboarding time for new developers.

### 🎓 Students

Learn how real-world projects are structured.

### 🔧 Maintenance

Locate relevant implementations in large codebases.

### 📚 Documentation

Use AI to understand and explain existing code.

### 🔍 Code Investigation

Find implementations and dependencies using natural language.

---

# 🌟 What Makes CodeSage AI Different?

CodeSage AI combines multiple developer-intelligence capabilities into one platform.

```text
        ┌─────────────────────┐
        │     CODEBASE        │
        └──────────┬──────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
       ▼           ▼           ▼
   Explorer     Search      Analysis
       │           │           │
       └───────────┼───────────┘
                   │
                   ▼
              AI CHAT
                   │
                   ▼
          CODE INTELLIGENCE
```

The goal is not simply to generate AI answers.

The goal is to make the **entire codebase understandable**.

---

# 🗺️ Roadmap

### ✅ Completed

* [x] FastAPI backend
* [x] React frontend
* [x] PostgreSQL integration
* [x] Authentication
* [x] JWT authorization
* [x] Project upload
* [x] Code parsing
* [x] Project analysis
* [x] Dependency analysis
* [x] Embedding generation
* [x] FAISS semantic retrieval
* [x] Ollama integration
* [x] LangChain RAG pipeline
* [x] AI project chat
* [x] Automated backend tests

### 🔜 Future

* [ ] GitHub repository integration
* [ ] Automatic documentation generation
* [ ] Advanced dependency visualization
* [ ] Code quality analysis
* [ ] Security vulnerability detection
* [ ] AI refactoring suggestions
* [ ] Pull request analysis
* [ ] Code change impact analysis
* [ ] Multi-user collaboration
* [ ] Cloud deployment
* [ ] Streaming AI responses
* [ ] Advanced multi-language support

---

# 📈 Future Vision

The long-term goal of CodeSage AI is to evolve into an **AI development companion that understands an entire software system**.

```text
             CODEBASE
                │
                ▼
       ┌──────────────────┐
       │ CODE UNDERSTANDING│
       └────────┬─────────┘
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
   Search    Analysis   Chat
      │         │         │
      └─────────┼─────────┘
                │
                ▼
       Developer Intelligence
```

Future versions can move beyond code search toward:

**Understand → Reason → Explain → Recommend → Assist**

---

# 📚 Learning & Engineering Concepts

This project brings together several important software engineering and AI concepts:

* REST API development
* Full-stack architecture
* Authentication & authorization
* Database design
* ORM
* Database migrations
* Syntax-aware parsing
* Vector embeddings
* Similarity search
* Retrieval-Augmented Generation
* Local Large Language Models
* AI application architecture
* Automated testing
* Modular software design

---

# 🧩 Development Philosophy

CodeSage AI follows a modular architecture so that individual components can evolve independently.

```text
Frontend
   ↓
API Layer
   ↓
Business Logic
   ↓
Data Layer
   ↓
AI / Retrieval Layer
```

This separation makes the system easier to:

* Maintain
* Test
* Extend
* Debug
* Deploy

---

# 📜 License

This project is currently intended for **educational, portfolio, and development purposes**.

A formal open-source license can be added as the project evolves.

---

# 👨‍💻 Author

<div align="center">

## **Amal Shaji**

Full-Stack Developer • AI Enthusiast

<a href="https://github.com/Amal070">
  <img src="https://img.shields.io/badge/GitHub-Amal070-181717?style=for-the-badge&logo=github" />
</a>

</div>

---

# ⭐ Support the Project

If you find **CodeSage AI** interesting, useful, or helpful for learning:

**⭐ Star the repository**

**🍴 Fork the project**

**🐛 Report issues**

**💡 Suggest improvements**

---

<div align="center">

### 🧠 CodeSage AI

**Understand your codebase. Search your codebase. Talk to your codebase.**

Built with ❤️ using **Python • FastAPI • React • PostgreSQL • FAISS • LangChain • Ollama**

</div>
