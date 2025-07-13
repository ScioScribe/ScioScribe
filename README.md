# ScioScribe
> AI-Powered Research Co-pilot for Scientific Experiment Design and Data Analysis

**ScioScribe** is a sophisticated research workflow management system that combines cutting-edge AI orchestration with real-time collaboration tools. It provides an intelligent interface for experiment planning, data cleaning, and analysis through multi-agent AI systems powered by LangGraph and OpenAI GPT-4.

![ScioScribe Interface](https://img.shields.io/badge/React-19.1.0-blue?logo=react) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi) ![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple) ![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue?logo=typescript)

![License](https://img.shields.io/badge/License-MIT-green.svg)

## Table of Contents
- [Features](#-features)
- [Live Demo](#-live-demo)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [Development](#-development)
- [API Reference](#-api-reference)
- [Security & Configuration](#-security--configuration)
- [Contributing](#-contributing)
- [License](#-license)

## **ScioScribe**

![ScioScribe Landing Page](documents/scioscribe-media/ScioScribe-landing.gif)



## Features

### **AI-Powered Experiment Planning**
- **Multi-agent planning system** with specialized AI teams
- **Human-in-the-loop approval workflows** for each planning stage
- **Real-time collaboration** via WebSocket connections
- **Interactive refinement** conversations with domain experts

###  **Intelligent Data Cleaning**
- **Conversational interface** for natural language data processing
- **AI-powered quality assessment** with automatic suggestions
- **Custom transformation pipeline** with preview capabilities
- **Multi-format support:** CSV, Excel, images with OCR
- **Version control** with undo/redo functionality

###  **Automated Analysis & Visualization**
- **Specialized agent team** for comprehensive analysis
- **Plotly visualization generation** with responsive HTML output
- **Real-time progress tracking** through analysis stages
- **Statistical profiling** and chart recommendations
- **Interactive visualizations** with full Plotly features

### **Modern Architecture**
- **Real-time WebSocket communication** with connection pooling
- **Responsive three-column layout** optimized for research workflows
- **Dark/light theme support** with accessible components
- **Auto-save functionality** with optimistic updates
- **Session persistence** across page reloads

## Architecture

### Frontend Stack
- **React 19.1.0** with TypeScript for type-safe component development
- **Vite** for fast development and optimized builds
- **Zustand** for centralized state management
- **TailwindCSS + shadcn/ui** for modern, accessible design system
- **Radix UI** primitives for accessibility compliance

### Backend Stack
- **FastAPI** with async/await for high-performance API
- **LangGraph** for sophisticated multi-agent AI orchestration
- **OpenAI GPT-4** integration via LangChain
- **SQLite + SQLAlchemy** for persistent data storage
- **EasyOCR** for image text extraction
- **WebSockets** for real-time bidirectional communication

### AI Agent Teams
1. **Planning Agents:** Research methodology, experimental design, and protocol development
2. **Data Cleaning Agents:** Quality assessment, transformation, and validation
3. **Analysis Agents:** Statistical profiling, visualization design, and scientific communication

## Getting Started

### Prerequisites

- **Node.js 18+** for frontend development
- **Python 3.9+** for backend services
- **OpenAI API Key** for AI functionality

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/scioscribe.git
cd scioscribe

# Setup backend
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend
cd ../apps/web
npm install
```

### Environment Configuration

Create a `.env` file in the server directory:

```bash
# Copy the example environment file
cp .env.bak .env
```

**Required Environment Variables:**
```bash
# Essential configuration
OPENAI_API_KEY=your-openai-api-key-here
APP_ENVIRONMENT=development
DATABASE_URL=sqlite:///./database/scioscribe.db

# Optional (recommended for production)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=ScioScribe
```

### Running the Application

1. **Start the backend server:**
```bash
cd server
python main.py
```
The API will be available at `http://localhost:8000`

2. **Start the frontend development server:**
```bash
cd apps/web
npm run dev
```
The application will be available at `http://localhost:5173`

3. **Access the application:**
   - **Frontend:** http://localhost:5173
   - **API Documentation:** http://localhost:8000/docs
   - **Alternative Docs:** http://localhost:8000/redoc

## Usage

### 1. Experiment Planning
```bash
# Start a new planning session
curl -X POST "http://localhost:8000/api/planning/start" \
  -H "Content-Type: application/json" \
  -d '{"research_query": "Effects of caffeine on cognitive performance"}'

# Connect via WebSocket for real-time collaboration
ws://localhost:8000/api/planning/ws/{session_id}
```

### 2. Data Cleaning
```bash
# Upload and process CSV files
curl -X POST "http://localhost:8000/api/dataclean/upload-file" \
  -F "file=@your-data.csv"

# Start conversational cleaning
ws://localhost:8000/api/dataclean/conversation/ws/{session_id}
```

### 3. Data Analysis
```bash
# Generate visualizations
curl -X POST "http://localhost:8000/api/analysis/generate-visualization" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a scatter plot", "plan": "...", "csv": "..."}'

# Real-time analysis with progress updates
ws://localhost:8000/api/analysis/ws/{session_id}
```

##  Development

### Project Structure
```
ScioScribe/
├── apps/web/                   # React frontend application
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── stores/            # Zustand state management
│   │   ├── api/               # API integration layer
│   │   └── handlers/          # WebSocket message handlers
├── server/                     # FastAPI backend
│   ├── api/                   # REST API endpoints
│   ├── agents/                # AI agent systems
│   │   ├── planning/          # Experiment planning agents
│   │   ├── dataclean/         # Data cleaning agents
│   │   └── analysis/          # Analysis and visualization agents
│   ├── database/              # Database models and migrations
│   └── config.py              # Application configuration
└── docs/                      # Documentation
```

### Building for Production

**Frontend:**
```bash
cd apps/web
npm run build
```

**Backend:**
```bash
cd server
# Production server with Gunicorn
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### Testing

**Frontend Tests:**
```bash
cd apps/web
npm run test
npm run test:coverage
```

**Backend Tests:**
```bash
cd server
pytest
pytest --cov=. --cov-report=html
```

## API Reference

### Core Endpoints

| Module | Endpoint | Purpose |
|--------|----------|---------|
| **Database** | `/api/database/*` | Experiment CRUD operations |
| **Planning** | `/api/planning/*` | Human-in-the-loop experiment planning |
| **DataClean** | `/api/dataclean/*` | Conversational data cleaning |
| **Analysis** | `/api/analysis/*` | AI-powered analysis and visualization |

### WebSocket Endpoints

| Path | Purpose |
|------|---------|
| `/api/planning/ws/{session_id}` | Real-time planning with approval workflows |
| `/api/dataclean/conversation/ws/{session_id}` | Interactive data cleaning sessions |
| `/api/analysis/ws/{session_id}` | Streaming analysis with progress updates |

For detailed API documentation, visit: http://localhost:8000/docs

## Security & Configuration

### Security Features
- **CORS protection** with configurable origins
- **SQL injection prevention** via SQLAlchemy ORM
- **Input sanitization** for all user-provided data
- **File upload validation** with type and size restrictions

### Production Configuration
- Update CORS origins in production
- Implement proper authentication/authorization
- Configure rate limiting for API endpoints
- Use environment variables for all sensitive data
- Enable HTTPS with proper SSL certificates

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository** and create a feature branch
2. **Follow the coding standards:**
   - TypeScript for frontend with strict type checking
   - Python with type hints and docstrings
   - Consistent formatting with ESLint and Black
3. **Write tests** for new functionality
4. **Submit a pull request** with a clear description

### Development Guidelines
- Use conventional commit messages
- Maintain test coverage above 80%
- Update documentation for new features
- Follow the existing architectural patterns

## Links

- **Project Homepage:** [https://github.com/your-username/scioscribe](https://github.com/your-username/scioscribe)
- **Issue Tracker:** [https://github.com/your-username/scioscribe/issues](https://github.com/your-username/scioscribe/issues)
- **Documentation:** [https://scioscribe.readthedocs.io](https://scioscribe.readthedocs.io)
- **API Documentation:** http://localhost:8000/docs (when running locally)

### Related Projects
- **LangGraph:** [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **FastAPI:** [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **React:** [https://react.dev/](https://react.dev/)
- **Plotly:** [https://plotly.com/javascript/](https://plotly.com/javascript/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ by the ScioScribe Team**

*Empowering researchers with intelligent automation and collaborative workflows*