import os
import json
import logging
import threading
from typing import Dict, Any, List, Optional, TypedDict
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Project imports
from pinecone_client import pinecone_rag
from utils import adjust_difficulty, generate_grading_rubric

logger = logging.getLogger("GraphEngine")

# Initialize Gemini Chat Model using langchain_google_genai
gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
llm = None

if gemini_key:
    try:
        _model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        llm = ChatGoogleGenerativeAI(
            model=_model_name,
            google_api_key=gemini_key,
            temperature=0.2,
            request_timeout=15,      # Increased timeout to 15s to prevent 400 errors
            max_retries=2
        )
        logger.info(f"ChatGoogleGenerativeAI ({_model_name}) active.")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Model: {e}")

class AgentState(TypedDict):
    user_id: str
    current_stage: str
    resume_data: Dict[str, Any]
    performance_history: List[Dict[str, Any]]
    weak_areas: List[str]
    resume_rating: Optional[int]
    resume_rating_label: Optional[str]
    resume_feedback: Optional[str]
    confidence_score: float
    next_action: str
    
    # Internal parameters
    current_difficulty: str
    consecutive_high_scores: int
    consecutive_low_scores: int
    current_question: Optional[Dict[str, Any]]
    current_answer: Optional[str]
    latest_score: float
    recommended_resources: List[Dict[str, Any]]

class PlacementGraphWorkflow:
    def __init__(self):
        self.workflow = self._build_graph()

    # --- Node 1: Resume Analyzer ---
    def resume_analyzer(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: resume_analyzer")
        resume = state.get("resume_data", {})
        skills = resume.get("skills", "")
        goals = ", ".join(resume.get("companies", [])) if isinstance(resume.get("companies"), list) else resume.get("companies", "")
        resume_text = resume.get("resume_text", "")
        
        gaps = []
        feedback = ""
        rating = 3
        rating_label = "Average"

        if llm:
            try:
                prompt = (
                    f"Analyze the following student resume targeting {goals} roles. "
                    "1. Extract their top 3 weak areas or missing critical skills. "
                    "2. Rate the resume on a scale of 1 to 5. "
                    "   (1=Worst, 2-3=Average, 4=Better, 5=Best) based on standard industry expectations. "
                    "3. Provide a very brief 1-sentence feedback explaining the rating.\n"
                    f"Skills: {skills}\n"
                    f"Resume Text:\n{resume_text}\n\n"
                    "Respond ONLY in valid JSON format exactly like this:\n"
                    '{\n  "weaknesses": ["skill1", "skill2"],\n  "rating": 4,\n  "rating_label": "Better",\n  "feedback": "Strong project experience but missing cloud deployment skills."\n}'
                )

                response = llm.invoke([HumanMessage(content=prompt)])
                text_content = response.content.replace("```json", "").replace("```", "").strip()
                data = json.loads(text_content)
                
                gaps = data.get("weaknesses", [])
                rating = data.get("rating", 3)
                rating_label = data.get("rating_label", "Average")
                feedback = data.get("feedback", "No specific feedback provided.")
                logger.info(f"Resume Analysis Complete: Rating={rating} ({rating_label})")
                
            except Exception as e:
                logger.error(f"Resume analysis LLM failed: {e}")
                gaps, feedback = self._fallback_resume_analysis(skills, goals)
        else:
            gaps, feedback = self._fallback_resume_analysis(skills, goals)

        new_weak = list(state.get("weak_areas", []))
        for skill in gaps:
            if skill not in new_weak:
                new_weak.append(skill)

        history = list(state.get("performance_history", []))
        history.append({
            "stage": "resume_analysis",
            "feedback": f"[{rating_label} - {rating}/5] {feedback}",
            "skills_missing": gaps
        })

        return {
            "weak_areas": new_weak,
            "resume_rating": rating,
            "resume_rating_label": rating_label,
            "resume_feedback": feedback,
            "performance_history": history,
            "current_stage": "resume_analysis",
            "next_action": "generate_question"
        }

    def _fallback_resume_analysis(self, skills: str, goals: str) -> (List[str], str):
        skills_lower = [s.strip().lower() for s in skills.split(",") if s.strip()]
        missing = []
        if "dsa" not in skills_lower and "algorithms" not in skills_lower:
            missing.append("Data Structures & Algorithms")
        if "system design" not in skills_lower and "architecture" not in skills_lower:
            missing.append("System Design")
            
        feedback = f"Analyzed skills profile targeting SDE roles at '{goals}'. Focus on vector caching and data hierarchies."
        return missing, feedback

    # --- Node 2: Question Generator (RAG) ---
    def question_generator(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: question_generator")
        resume = state.get("resume_data", {})
        goals = ", ".join(resume.get("companies", [])) if isinstance(resume.get("companies"), list) else resume.get("companies", "")
        skills = resume.get("skills", "")
        difficulty = state.get("current_difficulty", "Easy")
        
        companies = state.get("resume_data", {}).get("companies", [])
        weak_topics = state.get("weak_areas", [])
        subject = state.get("resume_data", {}).get("subject", "Coding")
        
        # Extract topic from subject if it's not generic 'Coding'
        rag_topic = None
        if subject and subject.lower() not in ["coding", "all"]:
            rag_topic = subject

        # Build search query based on selected companies
        if companies:
            search_query = f"Coding interview questions relevant to these companies: {', '.join(companies)}. If no exact match exists, use closest matching company category."
        else:
            search_query = "Coding interview questions for general software engineering."
            
        if skills:
            search_query += f" using {skills}"
        if weak_topics:
            search_query += f" on topics: {', '.join(weak_topics[:2])}"

        # Retrieve questions from RAG (Pinecone or local fallback)
        logger.info(f"[GRAPH ENGINE] Calling query_questions() with: companies={companies}, difficulty={difficulty}, topic={rag_topic}")
        questions = pinecone_rag.query_questions(
            query_text=search_query,
            companies=companies,
            difficulty=difficulty,
            topic=rag_topic,
            weak_areas=weak_topics,
            limit=5
        )
        logger.info(f"[GRAPH ENGINE] query_questions() returned question IDs: {[q['id'] for q in questions]}")

        asked_ids = {h.get("question_id") for h in state.get("performance_history", []) if h.get("question_id")}
        selected = None
        for q in questions:
            if q["id"] not in asked_ids:
                selected = q
                break
        
        if not selected and questions:
            selected = questions[0]
        elif not selected:
            # Empty state handling
            selected = {
                "id": "fallback-empty",
                "question": f"No questions found for selected companies ({', '.join(companies)}), topic ({subject}), or difficulty ({difficulty}). Please adjust your filters in the Preparation Settings.",
                "expected_answer": "Adjust filters to continue.",
                "topic": subject or "System Message",
                "difficulty": difficulty,
                "company": ", ".join(companies) if companies else "System",
                "type": "System"
            }

        return {
            "current_question": selected,
            "current_stage": "questioning",
            "next_action": "wait_for_answer"
        }

    # --- Batch Question Generator (for Coding Tab) ---
    def question_generator_batch(self, state: AgentState) -> List[Dict[str, Any]]:
        logger.info("Function: question_generator_batch")
        resume = state.get("resume_data", {})
        companies = resume.get("companies", [])
        skills = resume.get("skills", "")
        difficulty = state.get("current_difficulty", "Easy")
        weak_topics = state.get("weak_areas", [])
        subject = resume.get("subject", "Coding")
        
        rag_topic = subject if subject and subject.lower() not in ["coding", "all"] else None

        search_query = f"Coding interview questions relevant to these companies: {', '.join(companies)}." if companies else "Coding interview questions."
        if skills: search_query += f" using {skills}"
        if weak_topics: search_query += f" on topics: {', '.join(weak_topics[:2])}"

        questions = pinecone_rag.query_questions(
            query_text=search_query,
            companies=companies,
            difficulty=difficulty,
            topic=rag_topic,
            weak_areas=weak_topics,
            limit=10
        )
        
        for q in questions:
            q["is_ai_generated"] = False

        if llm and len(questions) < 10:
            needed = 10 - len(questions)
            try:
                prompt = (
                    f"Generate {needed} unique coding interview questions for {', '.join(companies) or 'general software engineering'}. "
                    f"Difficulty: {difficulty}. Topic: {rag_topic or 'Data Structures and Algorithms'}. "
                    "Return ONLY a JSON array of objects. Each object must have: 'id' (string, e.g. 'gen-1'), 'question' (string, the problem statement), 'expected_answer' (string, optimal approach), 'topic' (string), 'difficulty' (string), 'company' (string), 'type' (string: 'Coding')."
                )
                res = llm.invoke([HumanMessage(content=prompt)])
                text = res.content.strip("`").replace("json\n", "").strip()
                generated = json.loads(text)
                for g in generated:
                    g["is_ai_generated"] = True
                    questions.append(g)
            except Exception as e:
                logger.error(f"Failed to generate batch questions: {e}")

        if not questions:
            questions.append({
                "id": "fallback-empty",
                "question": f"No questions found for selected parameters.",
                "expected_answer": "Adjust filters to continue.",
                "topic": subject or "System",
                "difficulty": difficulty,
                "company": ", ".join(companies) if companies else "System",
                "type": "System",
                "is_ai_generated": False
            })

        return questions[:10]

    # --- ATS Resume Analyzer (for Behavioral Tab) ---
    def analyze_resume_ats(self, text: str) -> Dict[str, Any]:
        if not llm or not text.strip():
            return {"ats_score": 50, "best_points": ["Valid document format"], "improvement_areas": ["Add more keywords", "Highlight impact metrics"]}
        
        try:
            prompt = (
                "Analyze the following resume text for ATS (Applicant Tracking System) friendliness. "
                "1. Provide an overall ATS score from 0 to 100. "
                "2. Extract 2-3 'best points' (strengths). "
                "3. Provide 2-3 'improvement areas' (weaknesses). "
                f"Resume Text:\n{text}\n\n"
                "Respond ONLY in valid JSON format like: {\"ats_score\": 85, \"best_points\": [\"...\"], \"improvement_areas\": [\"...\"]}"
            )
            res = llm.invoke([HumanMessage(content=prompt)])
            data = json.loads(res.content.strip("`").replace("json\n", "").strip())
            return {
                "ats_score": data.get("ats_score", 50),
                "best_points": data.get("best_points", []),
                "improvement_areas": data.get("improvement_areas", [])
            }
        except Exception as e:
            logger.error(f"ATS analysis failed: {e}")
            return {"ats_score": 60, "best_points": ["Document parsed"], "improvement_areas": ["Standardize formatting for ATS"]}

    # --- Node 3: Answer Evaluator ---
    def answer_evaluator(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: answer_evaluator")
        q = state.get("current_question")
        ans = state.get("current_answer", "")
        
        if not q:
            return {"latest_score": 0.0}

        score = 0.0
        feedback = ""
        expected = q.get("expected_answer", "")
        
        # Rubric setup
        rubric = generate_grading_rubric(q["question"], expected)

        if llm:
            try:
                prompt = (
                    f"{rubric}\n\n"
                    f"Candidate Answer: {ans}\n\n"
                    f"Evaluate and output raw JSON format with keys 'score' (int) and 'feedback' (string with critique)."
                )
                res = llm.invoke([
                    SystemMessage(content="You are a placement examiner. Output raw JSON format only."),
                    HumanMessage(content=prompt)
                ])
                content_text = res.content.strip("`").replace("json\n", "").strip()
                data = json.loads(content_text)
                score = float(data.get("score", 0))
                feedback = data.get("feedback", "")
            except Exception as e:
                logger.error(f"Answer evaluation LLM failed: {e}")
                score, feedback = self._fallback_evaluation(ans, expected)
        else:
            score, feedback = self._fallback_evaluation(ans, expected)

        high = state.get("consecutive_high_scores", 0)
        low = state.get("consecutive_low_scores", 0)
        curr_diff = state.get("current_difficulty", "Easy")

        if score >= 75:
            high += 1
            low = 0
        elif score < 60:
            low += 1
            high = 0
        else:
            high = 0
            low = 0

        next_diff, new_high, new_low = adjust_difficulty(curr_diff, high, low)

        history = list(state.get("performance_history", []))
        history.append({
            "stage": "evaluation",
            "question_id": q["id"],
            "topic": q["topic"],
            "score": score,
            "feedback": feedback,
            "answer": ans
        })

        return {
            "latest_score": score,
            "current_difficulty": next_diff,
            "consecutive_high_scores": new_high,
            "consecutive_low_scores": new_low,
            "performance_history": history,
            "current_stage": "evaluating",
            "next_action": "analyze_weakness"
        }

    def _fallback_evaluation(self, answer: str, expected: str) -> (float, str):
        if not answer or len(answer.strip()) < 10:
            return 10.0, "The answer lacks logic details. Explain more thoroughly."
        ans_lower = answer.lower()
        key_terms = [t.strip(",.()").lower() for t in expected.split() if len(t) > 4]
        matches = sum(1 for t in key_terms if t in ans_lower)
        
        match_ratio = matches / len(key_terms) if key_terms else 1.0
        score = min(30.0 + (match_ratio * 70.0), 100.0)
        
        feedback = f"Your answer matched key metrics with {int(match_ratio * 100)}% keyword logic."
        return score, feedback

    # --- Node 4: Weakness Analyzer ---
    def weakness_analyzer(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: weakness_analyzer")
        score = state.get("latest_score", 0.0)
        q = state.get("current_question", {})
        topic = q.get("topic", "General")
        
        weaks = list(state.get("weak_areas", []))
        if score < 60:
            if topic not in weaks:
                weaks.append(topic)
        elif score >= 85:
            if topic in weaks:
                weaks.remove(topic)

        next_act = "next_question"
        if score < 60:
            next_act = "concept_review"
        elif weaks:
            next_act = "resource_recommender"

        evals_done = sum(1 for h in state.get("performance_history", []) if h.get("stage") == "evaluation")
        if evals_done >= 3:
            next_act = "track_progress"

        return {
            "weak_areas": weaks,
            "current_stage": "reviewing",
            "next_action": next_act
        }

    # --- Node 5: Resource Recommender ---
    def resource_recommender(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: resource_recommender")
        weaks = state.get("weak_areas", [])
        recs = list(state.get("recommended_resources", []))

        if weaks:
            latest_weak = weaks[-1]
            if not any(r.get("topic") == latest_weak for r in recs):
                resources = self._get_resources(latest_weak)
                recs.append({
                    "topic": latest_weak,
                    "resources": resources
                })

        return {
            "recommended_resources": recs,
            "current_stage": "recommendation",
            "next_action": "generate_question"
        }

    def _get_resources(self, topic: str) -> List[Dict[str, str]]:
        repo = {
            "Array": [
                {"name": "LeetCode Array Problems", "url": "https://leetcode.com/tag/array/", "type": "Practice"},
                {"name": "GFG Array Tutorial", "url": "https://www.geeksforgeeks.org/array-data-structure/", "type": "Article"}
            ],
            "Linked List": [
                {"name": "LeetCode Linked List Cycle", "url": "https://leetcode.com/problems/linked-list-cycle/", "type": "Practice"}
            ],
            "System Design": [
                {"name": "System Design Primer - GitHub", "url": "https://github.com/donnemartin/system-design-primer", "type": "Article"}
            ]
        }
        return repo.get(topic, [
            {"name": f"GeeksforGeeks - {topic}", "url": f"https://www.geeksforgeeks.org/search?q={topic}", "type": "Article"}
        ])

    # --- Node 6: Mock Interviewer ---
    def mock_interviewer(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: mock_interviewer")
        return {
            "current_stage": "complete",
            "next_action": "track_progress"
        }

    # --- Node 7: Progress Tracker ---
    def progress_tracker(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Node: progress_tracker")
        history = state.get("performance_history", [])
        scores = [h["score"] for h in history if h.get("stage") == "evaluation"]
        
        avg_score = sum(scores) / len(scores) if scores else 50.0
        prep_level = state.get("resume_data", {}).get("prep_level", "intermediate")
        mult = 1.15 if prep_level == "advanced" else (1.0 if prep_level == "intermediate" else 0.8)
        confidence = min(avg_score * mult, 100.0)

        return {
            "confidence_score": round(confidence, 2),
            "current_stage": "complete",
            "next_action": "end"
        }

    # --- Conditional Router ---
    def _route_decision(self, state: AgentState) -> str:
        action = state.get("next_action")
        if action == "concept_review":
            return "concept_review"
        elif action == "resource_recommender":
            return "resource_recommender"
        elif action == "track_progress":
            return "track_progress"
        else:
            return "next_question"

    def _build_graph(self):
        builder = StateGraph(AgentState)
        
        builder.add_node("resume_analyzer", self.resume_analyzer)
        builder.add_node("question_generator", self.question_generator)
        builder.add_node("answer_evaluator", self.answer_evaluator)
        builder.add_node("weakness_analyzer", self.weakness_analyzer)
        builder.add_node("resource_recommender", self.resource_recommender)
        builder.add_node("mock_interviewer", self.mock_interviewer)
        builder.add_node("progress_tracker", self.progress_tracker)
        
        builder.set_entry_point("resume_analyzer")
        
        builder.add_edge("resume_analyzer", "question_generator")
        builder.add_edge("question_generator", "answer_evaluator")
        builder.add_edge("answer_evaluator", "weakness_analyzer")
        
        builder.add_conditional_edges(
            "weakness_analyzer",
            self._route_decision,
            {
                "concept_review": "question_generator",
                "resource_recommender": "resource_recommender",
                "track_progress": "progress_tracker",
                "next_question": "question_generator"
            }
        )
        
        builder.add_edge("resource_recommender", "question_generator")
        builder.add_edge("progress_tracker", END)
        
        return builder.compile()

placement_graph = PlacementGraphWorkflow()
