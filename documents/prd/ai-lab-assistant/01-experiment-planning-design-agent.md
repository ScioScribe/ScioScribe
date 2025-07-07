# Sub-PRD 1: Experiment Planning & Design Agent

**Owner:** Developer 1 (The Architect)  
**Epic:** The Experiment Planner  
**Goal:** To create a conversational AI that guides a user from a vague idea to a structured, actionable research plan.

## 1. Feature Overview

This module provides a conversational interface where a researcher interacts with an AI agent to build out a complete experiment plan. The agent will proactively ask questions to ensure the plan is well-defined, methodologically sound, and ready for data collection.

## 2. User Stories

- **As a researcher,** I want to start a new "Experiment Plan" so that I can begin defining my study.
- **As a researcher,** I want the AI to ask me clarifying questions about my core hypothesis, variables (independent/dependent), and control groups so that my experimental design is robust.
- **As a researcher,** I want the AI to suggest appropriate research methodologies (e.g., A/B test, longitudinal study, qualitative interview) based on my stated goals.
- **As a researcher,** I want the AI to help me draft a survey or questionnaire based on my plan, suggesting unbiased and validated question formats.
- **As a researcher,** I want the final plan to be saved and exported as a structured document (`ExperimentPlan.json`) that can be used in later stages of the application.

## 3. Functional Requirements

- A dedicated UI section for "New Experiment Plan."
- A chat-like interface for the conversation between the user and the agent.
- The agent must maintain the state of the conversation, building up the plan incrementally.
- The agent must be able to call different tools or sub-agents (e.g., one for methodology, one for question generation).
- A "Finish & Save" button that finalizes the plan and stores it in Firestore.

## 4. Technical Considerations

- **Frontend:** Build reusable React components for the chat interface. Use a state management library (like Zustand or React Context) to handle the live state of the `ExperimentPlan` object as it's being built.
- **Backend (LangGraph):** Design a LangGraph state machine where each node represents a piece of the plan (e.g., `get_hypothesis`, `define_variables`, `suggest_methodology`). The state object will be the `ExperimentPlan` itself.
- **API Contract:** The final output must conform to the `ExperimentPlan.json` structure agreed upon by the team.

```json
// Example Structure
{
  "experimentId": "uuid-1234",
  "title": "Effect of Caffeine on Code Quality",
  "hypothesis": "Developers who consume caffeine will produce code with 20% fewer bugs.",
  "variables": {
    "independent": "Caffeine intake (mg)",
    "dependent": "Bug count per 100 lines of code"
  },
  "methodology": "A/B Test",
  "dataCollectionPlan": {
    "type": "Survey",
    "questions": [...]
  }
}
```

## 5. Acceptance Criteria

- A user can successfully navigate the entire conversation and generate a complete `ExperimentPlan.json`.
- The generated plan is saved correctly to the user's account in Firestore.
- The conversation feels natural and guides the user effectively without getting stuck in loops.