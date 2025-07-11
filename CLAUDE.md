# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScioScribe is an AI-powered research workflow management system for scientific experiment design and data analysis. It uses a multi-agent AI architecture built with LangGraph and FastAPI backend with React frontend.

## Common Development Commands

### Frontend (run from `apps/web/`)
```bash
npm run dev          # Start development server on port 5173
npm run build        # Build for production
npm run typecheck    # Run TypeScript type checking
npm run lint         # Run ESLint
npm run preview      # Preview production build
```

### Backend (run from `server/`)
```bash
python main.py       # Start FastAPI server on port 8000
pytest               # Run all tests
pytest tests/test_specific.py::test_name  # Run single test
pytest --cov=. --cov-report=html  # Run tests with coverage report
black .              # Format Python code
flake8               # Run Python linting
isort .              # Sort Python imports
mypy .               # Run Python type checking
```

## Architecture Overview

### Multi-Agent System
The core AI functionality is built using LangGraph with specialized agents:
- **Planning Agents** (`server/agents/planning/`): Handle research methodology and experiment design
- **Data Cleaning Agents** (`server/agents/dataclean/`): Process and validate data quality
- **Analysis Agents** (`server/agents/analysis/`): Generate visualizations and statistical insights

Each agent system follows a human-in-the-loop pattern with approval workflows at key decision points.

### Frontend-Backend Communication
- REST API endpoints in `server/api/` for standard CRUD operations
- WebSocket connections for real-time agent interactions and progress updates
- Message handlers in `apps/web/src/handlers/` process WebSocket messages

### State Management
- Frontend uses Zustand stores (`apps/web/src/stores/`) for global state
- Backend maintains agent state through LangGraph's state persistence
- SQLite database for persistent data storage with SQLAlchemy ORM

### Key Integration Points
1. **Agent Invocation**: Frontend sends requests to `/api/agent/{agent_type}` endpoints
2. **WebSocket Flow**: Real-time updates flow through `ws://localhost:8000/ws/{session_id}`
3. **File Handling**: Uploads processed through `/api/upload` with EasyOCR for text extraction
4. **Visualization**: Plotly graphs generated server-side and rendered in React

## Development Guidelines

### Adding New Agents
1. Create agent module in `server/agents/{agent_name}/`
2. Define state schema inheriting from `BaseAgentState`
3. Implement agent functions with `@agent_node` decorator
4. Register transitions in the agent graph
5. Add corresponding API endpoint in `server/api/`
6. Create frontend handler in `apps/web/src/handlers/`

### Working with Components
- UI components use shadcn/ui patterns - check existing components before creating new ones
- All components should have TypeScript interfaces for props
- Use Tailwind classes for styling, avoid inline styles

### Testing Agents
- Mock LLM responses using `server/agents/testing/mock_llm.py`
- Test state transitions separately from LLM logic
- Use `pytest` fixtures for common agent test setups

### Environment Setup
Backend requires `.env` file with:
- `OPENAI_API_KEY` for GPT-4 access
- `REDIS_URL` for Celery task queue (optional)
- `DATABASE_URL` for SQLAlchemy connection (defaults to SQLite)