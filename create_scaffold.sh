#!/usr/bin/env bash
set -euo pipefail

echo "Creating scaffold files..."

# Create directories
mkdir -p frontend/app frontend/components frontend/services frontend/types frontend/tests
mkdir -p backend/app/api/v1 backend/app/core backend/app/db backend/app/models backend/app/schemas backend/app/repositories backend/app/services backend/app/security backend/app/middleware backend/app/tests
mkdir -p ai/llm/providers agents/common/tests agents/common/protocols agents/concierge/prompts agents/concierge/tools agents/concierge/schemas agents/concierge/services agents/concierge/tests agents/reservation/tools agents/reservation/schemas agents/reservation/services agents/reservation/tests agents/recommendation agents/recommendation/tests agents/feedback agents/feedback/tests database/seeds/demo_fixtures docs/architecture docs/agents docs/ai docs/security docs/responsible-ai docs/analytics docs/development docs/decisions .github/workflows tools/mcp/servers tools/internal retrieval/embeddings retrieval/vectorstore scripts infrastructure/docker knowledge_base/documents knowledge_base/processed

# Root Files
cat > README.md <<'INNER'
# SMARTSTAY-AI0.1
Initial repository placeholder for the SmartStay AI project.
INNER

cat > .gitignore <<'INNER'
.venv/
__pycache__/
.env
.env.*
node_modules/
dist/
.next/
.vscode/
.DS_Store
coverage/
*.pyc
*.pyo
*.pyd
*.db
*.sqlite
.idea/
Thumbs.db
secrets.yml
INNER

cat > .env.example <<'INNER'
APP_ENV=development
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
DATABASE_URL=postgresql://postgres:password@localhost:5432/smartstay_dev
PGVECTOR_ENABLED=true
LLM_PROVIDER=openai
OPENAI_API_KEY=
LLM_MODEL=gpt-4o
JWT_SECRET=changeme
ANALYTICS_WRITE_KEY=
INNER

cat > docker-compose.yml <<'INNER'
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: smartstay_dev
    ports:
      - "5432:5432"
INNER

cat > backend/app/main.py <<'INNER'
from fastapi import FastAPI
app = FastAPI(title='SmartStay AI — Backend')

@app.get('/health')
async def health():
    return {'status': 'ok'}
INNER

cat > backend/requirements.txt <<'INNER'
fastapi
uvicorn[standard]
pydantic
pytest
INNER

cat > agents/common/base_agent.py <<'INNER'
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def handle_message(self, context, message):
        raise NotImplementedError
INNER

# Add .gitkeep to empty directories
find . -type d -empty -not -path './.git*' -exec touch {}/.gitkeep \;

echo "Scaffold files created successfully."
