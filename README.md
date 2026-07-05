# PlacementAI — Agentic Campus Placement Coach

An intelligent, full-stack placement preparation assistant designed to help students prepare for technical campus placements (FAANG, startups, MNCs). The system orchestrates a multi-node state machine in **LangGraph**, integrates **Pinecone RAG** hybrid question retrieval, and maintains state logs in **PostgreSQL** with **Redis** caching.

---

## 🏗️ Architecture Design & Files

The project has been modularized as follows:

- **`models.py`**: SQLAlchemy relational mappings for User profiles, Session workflow states, candidate PerformanceLogs, and Resource Recommendations. Supports PostgreSQL and SQLite.
- **`pinecone_client.py`**: Pinecone index controller. Integrates OpenAI Text Embeddings and custom hybrid metadata search, boosting questions targeting student weaknesses or goals.
- **`utils.py`**: Helpers for parsing PDF resumes, setting standard rubric templates, and shifting difficulty scale levels.
- **`graph.py`**: Defines the LangGraph workflow orchestrator. Combines 7 specialized nodes in a compiled routing layout.
- **`main.py`**: FastAPI server exposing endpoints for starting sessions, retrieving questions, evaluating candidate responses, and progress analytics.
- **`test_session.py`**: Testing suite simulating a complete student prep session from resume analysis to questionnaire grading loops.

---

## ⚙️ Environment Variables

Create a `.env` file in the root workspace folder:

```env
# API Keys (For Live Production)
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=placement-questions

# Database connections
DATABASE_URL=postgresql://postgres:password@localhost:5432/placement_prep
REDIS_URL=redis://localhost:6379/0
```

---

## 🛠️ Getting Started

### 1. Install local Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run simulation test script
Verify the entire state machine pipeline and database logs:
```bash
python test_session.py
```

### 3. Launch Docker containers (PostgreSQL + Redis + FastAPI)
```bash
docker-compose up --build
```
The backend API server will start on `http://localhost:8000`.

---

## 🔌 API Documentation

### 1. Start Assessment
* **Endpoint**: `POST /assessment/start`
* **Payload**:
  ```json
  {
    "user_id": "student_01",
    "name": "Rahul Kumar",
    "skills": "Python, SQL",
    "goals": "Amazon SDE",
    "weak_areas": "System Design",
    "prep_level": "intermediate"
  }
  ```

### 2. Retrieve Question
* **Endpoint**: `GET /question/next?user_id=student_01`
* **Response**:
  ```json
  {
    "id": "q-1",
    "question": "Implement a URL shortener...",
    "topic": "System Design",
    "difficulty": "Medium"
  }
  ```

### 3. Submit Response
* **Endpoint**: `POST /answer/submit`
* **Payload**:
  ```json
  {
    "user_id": "student_01",
    "answer": "We can build base62 encoded short links..."
  }
  ```
* **Response**:
  ```json
  {
    "evaluation": {
      "score": 85.0,
      "feedback": "Excellent outline of base62 redirects..."
    },
    "next_step": "next_question",
    "difficulty": "Medium"
  }
  ```

### 4. Fetch Progress Summary
* **Endpoint**: `GET /progress/{user_id}`
* **Response**: Returns readiness levels, placement probabilities, full logs, and resource recommendations.

### 5. Fetch Weakness Analytics
* **Endpoint**: `GET /weakness/{user_id}`
* **Response**: Returns attempt counts and mastery statuses categorized by topic.

### 6. Reset Session / Start Mock Interview
* **Endpoint**: `POST /mock/start` (Clears historical metrics to initiate a clean mock session).
