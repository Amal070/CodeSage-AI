"""
CodeSage AI — Day 18 Test Fixtures: Sample Projects

Provides realistic, multi-file sample project structures for:
1. Django Project (Bookstore with CustomUser, Auth views, Serializers, Models, URLs, Settings)
2. React Project (TaskFlow frontend with Components, Pages, Axios API services, Hooks, Package.json)
3. Python Project (DataPipeline with Main entrypoint, Config, Processor service, Client, Logger)
"""

import io
import json
import zipfile
from typing import Dict


# ==============================================================================
# 1. DJANGO TEST PROJECT: Bookstore API & Portal
# ==============================================================================

DJANGO_PROJECT_FILES: Dict[str, str] = {
    "requirements.txt": (
        "django>=4.2,<5.0\n"
        "djangorestframework>=3.14.0\n"
        "psycopg2-binary>=2.9.9\n"
    ),
    "manage.py": (
        "#!/usr/bin/env python\n"
        "import os\n"
        "import sys\n"
        "\n"
        "def main():\n"
        "    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore_config.settings')\n"
        "    try:\n"
        "        from django.core.management import execute_from_command_line\n"
        "    except ImportError as exc:\n"
        "        raise ImportError('Couldn\\'t import Django.') from exc\n"
        "    execute_from_command_line(sys.argv)\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ),
    "bookstore_config/settings.py": (
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "BASE_DIR = Path(__file__).resolve().parent.parent\n"
        "SECRET_KEY = 'django-insecure-test-key-for-codesage-validation'\n"
        "DEBUG = True\n"
        "ALLOWED_HOSTS = ['*']\n"
        "\n"
        "INSTALLED_APPS = [\n"
        "    'django.contrib.admin',\n"
        "    'django.contrib.auth',\n"
        "    'django.contrib.contenttypes',\n"
        "    'django.contrib.sessions',\n"
        "    'django.contrib.messages',\n"
        "    'rest_framework',\n"
        "    'accounts',\n"
        "    'books',\n"
        "]\n"
        "\n"
        "DATABASES = {\n"
        "    'default': {\n"
        "        'ENGINE': 'django.db.backends.postgresql',\n"
        "        'NAME': 'bookstore_db',\n"
        "        'USER': 'postgres',\n"
        "        'PASSWORD': 'password',\n"
        "        'HOST': 'localhost',\n"
        "        'PORT': '5432',\n"
        "    }\n"
        "}\n"
        "AUTH_USER_MODEL = 'accounts.CustomUser'\n"
    ),
    "bookstore_config/urls.py": (
        "from django.contrib import admin\n"
        "from django.urls import path, include\n"
        "\n"
        "urlpatterns = [\n"
        "    path('admin/', admin.site.urls),\n"
        "    path('api/auth/', include('accounts.urls')),\n"
        "    path('api/books/', include('books.urls')),\n"
        "]\n"
    ),
    "bookstore_config/wsgi.py": (
        "import os\n"
        "from django.core.wsgi import get_wsgi_application\n"
        "\n"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore_config.settings')\n"
        "application = get_wsgi_application()\n"
    ),
    "accounts/models.py": (
        "from django.contrib.auth.models import AbstractUser\n"
        "from django.db import models\n"
        "\n"
        "class CustomUser(AbstractUser):\n"
        "    email = models.EmailField(unique=True)\n"
        "    bio = models.TextField(blank=True, default='')\n"
        "    is_verified = models.BooleanField(default=False)\n"
        "\n"
        "    def get_display_name(self):\n"
        "        return self.username or self.email\n"
    ),
    "accounts/views.py": (
        "from rest_framework.views import APIView\n"
        "from rest_framework.response import Response\n"
        "from rest_framework import status\n"
        "from django.contrib.auth import authenticate, login\n"
        "from .serializers import UserSerializer\n"
        "\n"
        "class LoginView(APIView):\n"
        "    \"\"\"Handles user login and session authentication.\"\"\"\n"
        "    def post(self, request):\n"
        "        username = request.data.get('username')\n"
        "        password = request.data.get('password')\n"
        "        user = authenticate(request, username=username, password=password)\n"
        "        if user is not None:\n"
        "            login(request, user)\n"
        "            return Response({'message': 'Login successful', 'user': UserSerializer(user).data})\n"
        "        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)\n"
        "\n"
        "class RegisterView(APIView):\n"
        "    \"\"\"Registers a new user account.\"\"\"\n"
        "    def post(self, request):\n"
        "        serializer = UserSerializer(data=request.data)\n"
        "        if serializer.is_valid():\n"
        "            serializer.save()\n"
        "            return Response(serializer.data, status=status.HTTP_201_CREATED)\n"
        "        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)\n"
    ),
    "accounts/serializers.py": (
        "from rest_framework import serializers\n"
        "from .models import CustomUser\n"
        "\n"
        "class UserSerializer(serializers.ModelSerializer):\n"
        "    class Meta:\n"
        "        model = CustomUser\n"
        "        fields = ['id', 'username', 'email', 'bio', 'is_verified']\n"
    ),
    "accounts/urls.py": (
        "from django.urls import path\n"
        "from .views import LoginView, RegisterView\n"
        "\n"
        "urlpatterns = [\n"
        "    path('login/', LoginView.as_view(), name='login'),\n"
        "    path('register/', RegisterView.as_view(), name='register'),\n"
        "]\n"
    ),
    "accounts/admin.py": (
        "from django.contrib import admin\n"
        "from .models import CustomUser\n"
        "\n"
        "@admin.register(CustomUser)\n"
        "class CustomUserAdmin(admin.ModelAdmin):\n"
        "    list_display = ('username', 'email', 'is_verified', 'is_staff')\n"
    ),
    "books/models.py": (
        "from django.db import models\n"
        "\n"
        "class Book(models.Model):\n"
        "    title = models.CharField(max_length=200)\n"
        "    author = models.CharField(max_length=150)\n"
        "    isbn = models.CharField(max_length=13, unique=True)\n"
        "    price = models.DecimalField(max_digits=6, decimal_places=2)\n"
        "    publication_year = models.IntegerField(default=2024)\n"
        "\n"
        "    def __str__(self):\n"
        "        return self.title\n"
    ),
    "books/views.py": (
        "from rest_framework.views import APIView\n"
        "from rest_framework.response import Response\n"
        "from .models import Book\n"
        "\n"
        "class BookListView(APIView):\n"
        "    \"\"\"Lists all available books in the bookstore.\"\"\"\n"
        "    def get(self, request):\n"
        "        books = Book.objects.all()\n"
        "        data = [{'id': b.id, 'title': b.title, 'author': b.author, 'price': str(b.price)} for b in books]\n"
        "        return Response(data)\n"
    ),
    "books/urls.py": (
        "from django.urls import path\n"
        "from .views import BookListView\n"
        "\n"
        "urlpatterns = [\n"
        "    path('', BookListView.as_view(), name='book-list'),\n"
        "]\n"
    ),
    "books/admin.py": (
        "from django.contrib import admin\n"
        "from .models import Book\n"
        "\n"
        "admin.site.register(Book)\n"
    ),
    "templates/base.html": (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>Bookstore Portal</title></head>\n"
        "<body><h1>Welcome to CodeSage Bookstore</h1></body>\n"
        "</html>\n"
    ),
}


# ==============================================================================
# 2. REACT TEST PROJECT: TaskFlow Frontend
# ==============================================================================

REACT_PROJECT_FILES: Dict[str, str] = {
    "package.json": json.dumps({
        "name": "react-taskflow",
        "version": "1.0.0",
        "private": True,
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.20.0",
            "axios": "^1.6.2"
        },
        "devDependencies": {
            "vite": "^5.0.0"
        }
    }, indent=2),
    "src/main.jsx": (
        "import React from 'react';\n"
        "import ReactDOM from 'react-dom/client';\n"
        "import App from './App';\n"
        "import './index.css';\n"
        "\n"
        "ReactDOM.createRoot(document.getElementById('root')).render(\n"
        "  <React.StrictMode>\n"
        "    <App />\n"
        "  </React.StrictMode>\n"
        ");\n"
    ),
    "src/App.jsx": (
        "import React from 'react';\n"
        "import Navbar from './components/Navbar';\n"
        "import DashboardPage from './pages/DashboardPage';\n"
        "\n"
        "export default function App() {\n"
        "  return (\n"
        "    <div className=\"app-container\">\n"
        "      <Navbar title=\"TaskFlow Manager\" />\n"
        "      <main className=\"main-content\">\n"
        "        <DashboardPage />\n"
        "      </main>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    ),
    "src/components/Navbar.jsx": (
        "import React from 'react';\n"
        "import { useAuth } from '../hooks/useAuth';\n"
        "\n"
        "export default function Navbar({ title }) {\n"
        "  const { user, logout } = useAuth();\n"
        "  return (\n"
        "    <header className=\"navbar\">\n"
        "      <h2 className=\"navbar-brand\">{title}</h2>\n"
        "      {user && (\n"
        "        <div className=\"user-info\">\n"
        "          <span>Welcome, {user.name}</span>\n"
        "          <button onClick={logout}>Sign Out</button>\n"
        "        </div>\n"
        "      )}\n"
        "    </header>\n"
        "  );\n"
        "}\n"
    ),
    "src/components/TaskCard.jsx": (
        "import React from 'react';\n"
        "import { formatDueDate } from '../utils/formatters';\n"
        "\n"
        "export default function TaskCard({ task, onComplete }) {\n"
        "  return (\n"
        "    <div className=\"task-card\">\n"
        "      <h4>{task.title}</h4>\n"
        "      <p>{task.description}</p>\n"
        "      <span className=\"due-date\">Due: {formatDueDate(task.dueDate)}</span>\n"
        "      <button className=\"btn-complete\" onClick={() => onComplete(task.id)}>\n"
        "        Complete Task\n"
        "      </button>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    ),
    "src/components/LoginForm.jsx": (
        "import React, { useState } from 'react';\n"
        "import { loginUser } from '../services/api';\n"
        "\n"
        "export default function LoginForm({ onLoginSuccess }) {\n"
        "  const [email, setEmail] = useState('');\n"
        "  const [password, setPassword] = useState('');\n"
        "\n"
        "  const handleSubmit = async (e) => {\n"
        "    e.preventDefault();\n"
        "    const data = await loginUser({ email, password });\n"
        "    if (data.token) {\n"
        "      onLoginSuccess(data);\n"
        "    }\n"
        "  };\n"
        "\n"
        "  return (\n"
        "    <form onSubmit={handleSubmit} className=\"login-form\">\n"
        "      <input value={email} onChange={e => setEmail(e.target.value)} placeholder=\"Email\" />\n"
        "      <input type=\"password\" value={password} onChange={e => setPassword(e.target.value)} placeholder=\"Password\" />\n"
        "      <button type=\"submit\">Sign In</button>\n"
        "    </form>\n"
        "  );\n"
        "}\n"
    ),
    "src/pages/DashboardPage.jsx": (
        "import React, { useState, useEffect } from 'react';\n"
        "import { fetchTasks, completeTask } from '../services/api';\n"
        "import TaskCard from '../components/TaskCard';\n"
        "\n"
        "export default function DashboardPage() {\n"
        "  const [tasks, setTasks] = useState([]);\n"
        "  const [loading, setLoading] = useState(true);\n"
        "\n"
        "  useEffect(() => {\n"
        "    fetchTasks()\n"
        "      .then(data => setTasks(data))\n"
        "      .finally(() => setLoading(false));\n"
        "  }, []);\n"
        "\n"
        "  const handleComplete = async (taskId) => {\n"
        "    await completeTask(taskId);\n"
        "    setTasks(prev => prev.filter(t => t.id !== taskId));\n"
        "  };\n"
        "\n"
        "  if (loading) return <div>Loading tasks...</div>;\n"
        "\n"
        "  return (\n"
        "    <div className=\"dashboard-grid\">\n"
        "      <h3>Active Tasks ({tasks.length})</h3>\n"
        "      {tasks.map(task => (\n"
        "        <TaskCard key={task.id} task={task} onComplete={handleComplete} />\n"
        "      ))}\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    ),
    "src/services/api.js": (
        "import axios from 'axios';\n"
        "\n"
        "const apiClient = axios.create({\n"
        "  baseURL: 'https://api.taskflow.dev/v1',\n"
        "  timeout: 8000,\n"
        "});\n"
        "\n"
        "export async function fetchTasks() {\n"
        "  const response = await apiClient.get('/tasks');\n"
        "  return response.data;\n"
        "}\n"
        "\n"
        "export async function completeTask(taskId) {\n"
        "  const response = await apiClient.post(`/tasks/${taskId}/complete`);\n"
        "  return response.data;\n"
        "}\n"
        "\n"
        "export async function loginUser(credentials) {\n"
        "  const response = await apiClient.post('/auth/login', credentials);\n"
        "  return response.data;\n"
        "}\n"
    ),
    "src/hooks/useAuth.js": (
        "import { useState } from 'react';\n"
        "\n"
        "export function useAuth() {\n"
        "  const [user, setUser] = useState({ name: 'Jordan', email: 'jordan@taskflow.dev' });\n"
        "  const logout = () => setUser(null);\n"
        "  return { user, logout };\n"
        "}\n"
    ),
    "src/utils/formatters.js": (
        "export function formatDueDate(dateStr) {\n"
        "  if (!dateStr) return 'No due date';\n"
        "  return new Date(dateStr).toLocaleDateString();\n"
        "}\n"
    ),
    "src/index.css": (
        "body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; }\n"
        ".navbar { display: flex; justify-content: space-between; padding: 1rem; background: #1e1e2e; color: #fff; }\n"
    ),
}


# ==============================================================================
# 3. PYTHON TEST PROJECT: DataPipeline Engine
# ==============================================================================

PYTHON_PROJECT_FILES: Dict[str, str] = {
    "requirements.txt": (
        "pydantic>=2.5.0\n"
        "requests>=2.31.0\n"
        "pytest>=7.4.0\n"
    ),
    "main.py": (
        "import sys\n"
        "from config import load_config\n"
        "from services.processor import DataProcessor\n"
        "from utils.logger import setup_logger\n"
        "\n"
        "logger = setup_logger('data_pipeline')\n"
        "\n"
        "def main():\n"
        "    \"\"\"Main application entry point for data ingestion.\"\"\"\n"
        "    cfg = load_config()\n"
        "    logger.info('Initializing data pipeline for %s in %s mode', cfg.app_name, cfg.environment)\n"
        "    processor = DataProcessor(batch_size=cfg.batch_size)\n"
        "    sample_data = [\n"
        "        {'id': 101, 'value': 250.0, 'category': 'hardware'},\n"
        "        {'id': 102, 'value': 890.5, 'category': 'software'},\n"
        "    ]\n"
        "    processed_records = processor.process_batch(sample_data)\n"
        "    success = processor.sync_to_cloud(processed_records)\n"
        "    logger.info('Sync completed with status: %s', success)\n"
        "    return 0 if success else 1\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n"
    ),
    "config.py": (
        "import os\n"
        "from pydantic import BaseModel\n"
        "\n"
        "class AppConfig(BaseModel):\n"
        "    app_name: str = 'DataPipelineService'\n"
        "    batch_size: int = 50\n"
        "    environment: str = 'production'\n"
        "    api_timeout_seconds: int = 10\n"
        "\n"
        "def load_config() -> AppConfig:\n"
        "    \"\"\"Loads configuration settings from environment variables.\"\"\"\n"
        "    return AppConfig(\n"
        "        batch_size=int(os.getenv('BATCH_SIZE', '50')),\n"
        "        environment=os.getenv('PIPELINE_ENV', 'production'),\n"
        "        api_timeout_seconds=int(os.getenv('TIMEOUT', '10')),\n"
        "    )\n"
    ),
    "models/record.py": (
        "from pydantic import BaseModel, Field\n"
        "\n"
        "class DataRecord(BaseModel):\n"
        "    id: int\n"
        "    value: float = Field(gt=0)\n"
        "    category: str = 'general'\n"
        "    status: str = 'pending'\n"
        "\n"
        "    def calculate_tax(self, tax_rate: float = 0.18) -> float:\n"
        "        \"\"\"Calculates regional tax on the record value.\"\"\"\n"
        "        return round(self.value * tax_rate, 2)\n"
    ),
    "services/processor.py": (
        "from typing import List, Dict, Any\n"
        "from models.record import DataRecord\n"
        "from services.api_client import ExternalApiClient\n"
        "\n"
        "class DataProcessor:\n"
        "    \"\"\"Core processor for validating and transforming batch records.\"\"\"\n"
        "    def __init__(self, batch_size: int = 50):\n"
        "        self.batch_size = batch_size\n"
        "        self.api_client = ExternalApiClient()\n"
        "\n"
        "    def process_batch(self, raw_items: List[Dict[str, Any]]) -> List[DataRecord]:\n"
        "        \"\"\"Transforms raw item dictionaries into validated DataRecord objects.\"\"\"\n"
        "        records = []\n"
        "        for item in raw_items[:self.batch_size]:\n"
        "            record = DataRecord(\n"
        "                id=item['id'],\n"
        "                value=float(item['value']),\n"
        "                category=item.get('category', 'general'),\n"
        "                status='processed',\n"
        "            )\n"
        "            records.append(record)\n"
        "        return records\n"
        "\n"
        "    def sync_to_cloud(self, records: List[DataRecord]) -> bool:\n"
        "        \"\"\"Sends processed records to external cloud API.\"\"\"\n"
        "        payload = [r.model_dump() for r in records]\n"
        "        return self.api_client.post_records(payload)\n"
    ),
    "services/api_client.py": (
        "import requests\n"
        "from typing import List, Dict, Any\n"
        "\n"
        "class ExternalApiClient:\n"
        "    \"\"\"HTTP client interface for cloud synchronization.\"\"\"\n"
        "    def __init__(self, base_url: str = 'https://telemetry.pipeline.io/v1'):\n"
        "        self.base_url = base_url\n"
        "\n"
        "    def post_records(self, payload: List[Dict[str, Any]]) -> bool:\n"
        "        try:\n"
        "            resp = requests.post(f'{self.base_url}/records', json=payload, timeout=10)\n"
        "            return resp.status_code == 200\n"
        "        except Exception:\n"
        "            return False\n"
    ),
    "utils/logger.py": (
        "import logging\n"
        "\n"
        "def setup_logger(name: str) -> logging.Logger:\n"
        "    \"\"\"Configures structured logging handler.\"\"\"\n"
        "    logger = logging.getLogger(name)\n"
        "    if not logger.handlers:\n"
        "        handler = logging.StreamHandler()\n"
        "        formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')\n"
        "        handler.setFormatter(formatter)\n"
        "        logger.addHandler(handler)\n"
        "        logger.setLevel(logging.INFO)\n"
        "    return logger\n"
    ),
    "tests/test_processor.py": (
        "from services.processor import DataProcessor\n"
        "\n"
        "def test_process_batch():\n"
        "    proc = DataProcessor(batch_size=5)\n"
        "    results = proc.process_batch([{'id': 1, 'value': 99.0}])\n"
        "    assert len(results) == 1\n"
        "    assert results[0].status == 'processed'\n"
    ),
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def build_project_zip(files_dict: Dict[str, str]) -> io.BytesIO:
    """
    Constructs an in-memory ZIP archive from a dictionary of {relative_path: content}.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, content in files_dict.items():
            zf.writestr(file_path, content.encode("utf-8"))
    buffer.seek(0)
    return buffer
