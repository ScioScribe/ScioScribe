# Master PRD: ScioScribe - AI Research Co-pilot
Version: 1.1
Status: In Development

## 1. Introduction & Vision
ScioScribe is an open-source, AI-powered workspace designed to unify the entire research lifecycle for scientists, academics, and data analysts. In a world where researchers juggle a dozen disjointed tools for planning, data collection, and analysis, ScioScribe provides a single, intelligent co-pilot to streamline this process. Our vision is to accelerate scientific discovery by automating tedious tasks and allowing researchers to focus on what matters: generating insights.

## 2. The Problem
The modern research workflow is fundamentally broken and inefficient, characterized by:
Disjointed Toolchains: Data is collected in one system (e.g., SurveyMonkey), managed in another (Google Drive), and analyzed in a third (SPSS, R), creating bottlenecks and hindering reproducibility.
Manual, Error-Prone Data Handling: Researchers spend an inordinate amount of time on manual data entry, cleaning inconsistent values, and formatting spreadsheets.
High Barrier to Complex Analysis: Performing sophisticated data analysis and creating compelling visualizations requires specialized coding skills, limiting the ability of many researchers to explore their data fully.
Context Loss: Critical context about experiment design and data collection is often lost by the time the analysis phase begins, leading to misinterpretations.

## 3. User Personas
Dr. Anya Sharma (Academic Researcher): A university professor managing multiple research projects with her team of grad students. She is tech-savvy but time-poor. She needs a tool that can help her students follow a rigorous methodology and allow her to quickly oversee progress without getting bogged down in spreadsheet errors.
Ben Carter (PhD Student): Deep in his dissertation research, Ben works with large, messy datasets. He has some coding knowledge but struggles with advanced statistical analysis in R. He needs a tool that can help him clean data faster and explore it visually without having to write complex scripts from scratch.
Chloe Davis (UX Researcher): A UX researcher at a tech company. She conducts frequent user interviews and surveys. She needs a tool to help her synthesize qualitative notes with quantitative survey data efficiently and generate reports for stakeholders who are not data experts.

## 4. High-Level Features & Epics
ScioScribe will be built around three core, integrated modules:
Epic 1: The Experiment Planner: A conversational agent that guides researchers through the process of defining a robust experiment, from hypothesis to methodology and instrument creation.
Epic 2: The Data Steward: A suite of tools for intelligent data ingestion, cleaning, and management. It supports uploads, voice/image-to-data conversion, and automated cleaning to ensure data is analysis-ready.
Epic 3: The Analysis Co-pilot: An interactive agent that allows researchers to "talk to their data." Users can ask for statistical summaries, generate complex visualizations, and create comprehensive reports using natural language.

## 5. Design & UX Principles
Clarity and Simplicity: The UI should be clean, intuitive, and never overwhelm the user. The focus should always be on the user's task, not on the complexity of the tool.
Trust Through Transparency: The AI's suggestions (e.g., for data cleaning) should always be presented for user verification. The user is the final authority.
Guided, Not Prescriptive: The agent should feel like a helpful co-pilot, offering suggestions and automating steps, but never locking the user into a rigid workflow.
Seamless Flow: The transition between planning, data ingestion, and analysis should feel like a natural progression within a single application.

## 6. Goals & Success Metrics
Our primary goal is to create a seamless workflow that demonstrably saves researchers time and effort.

## 7. What's Out of Scope (for this MVP)
Real-time Collaboration: Multiple users editing the same project simultaneously will not be supported in the initial version.
Direct Integration with External Tools: We will not build direct API integrations with SurveyMonkey, SPSS, etc. The focus is on providing a superior, unified alternative.
Advanced User/Permission Management: The MVP will assume a single-user-per-project model.
Mobile-Specific Application: The application will be designed for desktop use, which is the primary environment for this type of work.

## 8. Technology Stack
Frontend: React, Vite, TailwindCSS, Shadcn
Backend: Python, FastAPI
AI Agent Framework: LangGraph
Database/Storage: Firestore
Vector Store: ChromaDB (for RAG capabilities)
Deployment: Firebase 

## 9. File Structure 

ai-lab-assistant/                               # ← git repo root
│
├─ apps/                                        # ── FRONT END ───────────────
│   └─ web/                                     #  Vite + React 18 + TS
│       ├─ public/                              #    static - index.html, icons
│       ├─ src/
│       │   ├─ components/                      #    UI atoms / molecules
│       │   ├─ pages/                           #    routed screens
│       │   ├─ hooks/                           #    custom hooks
│       │   ├─ lib/                             #    ⇢ tiny SDK for API calls
│       │   └─ styles/                          #    Tailwind / global CSS
│       ├─ vite.config.ts
│       ├─ tsconfig.json
│       └─ package.json
│
└─ server/                                      # ── BACK END (Python) ───────
    ├─ agents/                                  #  PURE LangGraph graphs
    │   ├─ planning/
    │   │   ├─ __init__.py
    │   │   ├─ graph.py                         #    create_planning_graph()
    │   │   └─ tests/
    │   ├─ dataclean/
    │   │   ├─ __init__.py
    │   │   └─ graph.py
    │   └─ analysis/
    │       ├─ __init__.py
    │       └─ graph.py
    │
    ├─ api/                                     #  FASTAPI APPLICATION
    │   ├─ __init__.py
    │   └─ main.py                              #  FastAPI() + 3 routers
    │
    ├─ functions/                               #  FIREBASE ENTRY-POINTS
    │   ├─ __init__.py                          #  shared middleware / utils
    │   ├─ planning_fn.py                       #  ASGI→GCF adapter
    │   ├─ dataclean_fn.py
    │   └─ analysis_fn.py
    │
    ├─ requirements.txt                         #  fastapi, langgraph, vellox…
    └─ runtimeconfig.json                       #  env vars for emulator / prod
│
├─ infra/                                       # IaC & local-dev helpers
│   ├─ firebase.json                            #  Hosting + Functions targets
│   ├─ .firebaserc                              #  project aliases (staging/prod)
│   └─ docker-compose.yml                       #  optional Postgres/Redis for LG-Lite
│
├─ docs/                                        # architecture notes, ADRs, API md
│
├─ .github/
│   └─ workflows/                               #  CI: lint, test, deploy preview
│
├─ npm-workspace.yaml                          #  JS workspaces (front-end only)
├─ .gitignore
└─ README.md                                    #  quick-start & dev commands