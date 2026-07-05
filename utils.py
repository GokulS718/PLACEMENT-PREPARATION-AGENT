import io
import logging
from typing import List, Dict, Any, Tuple
import PyPDF2

logger = logging.getLogger("Utils")

def parse_resume(file_bytes: bytes, filename: str) -> str:
    """
    Parses PDF or text files to extract resume contents.
    """
    text = ""
    filename_lower = filename.lower()
    try:
        if filename_lower.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        elif filename_lower.endswith(".txt"):
            text = file_bytes.decode("utf-8")
        else:
            logger.warning(f"Unsupported file format: {filename}")
    except Exception as e:
        logger.error(f"Error parsing resume {filename}: {e}")
    return text.strip()

def adjust_difficulty(current_difficulty: str, consecutive_high: int, consecutive_low: int) -> Tuple[str, int, int]:
    """
    Determines next interview difficulty based on scoring history.
    - Upward shift if user scores >= 75% on 2 consecutive questions.
    - Downward shift if user scores < 60% on 2 consecutive questions.
    Returns: (new_difficulty, updated_consec_high, updated_consec_low)
    """
    new_diff = current_difficulty
    
    if consecutive_high >= 2:
        if current_difficulty == "Easy":
            new_diff = "Medium"
        elif current_difficulty == "Medium":
            new_diff = "Hard"
        consecutive_high = 0 # reset counters after scaling
        consecutive_low = 0
    elif consecutive_low >= 2:
        if current_difficulty == "Hard":
            new_diff = "Medium"
        elif current_difficulty == "Medium":
            new_diff = "Easy"
        consecutive_high = 0
        consecutive_low = 0
        
    return new_diff, consecutive_high, consecutive_low

def generate_grading_rubric(question_text: str, expected_points: str) -> str:
    """
    Generates standard structured rubrics used by the LLM Evaluator Node.
    """
    rubric = (
        f"You are grading a candidate's answer for the following question:\n"
        f"Question: {question_text}\n"
        f"Ideal Answer Rubrics: {expected_points}\n\n"
        f"Grade the candidate's answer according to these criteria:\n"
        f"1. Accuracy and correctness (40% weight)\n"
        f"2. Core logic, edge cases, and runtime/space complexity mentions (35% weight)\n"
        f"3. Technical expression and clarity of explanation (25% weight)\n\n"
        f"Provide a numerical score between 0 and 100, and a concise summary feedback with 2-3 specific improvement recommendations."
    )
    return rubric
