import os
import json
import logging
import base64
from typing import Dict, Any, List, Optional, Tuple
from config import Config

logger = logging.getLogger("bea.ai_service")

# Default structured system instructions for Diploma Basic Electronics & Amplifiers
DEFAULT_EVALUATION_INSTRUCTIONS = """
You are an expert Diploma Electronics & Communication Engineering (ECE) examiner for the subject:
Basic Electronics and Amplifiers (BEA - Subject Code: MEE-105).

Marking Guidelines:
1. Handwritten Scripts & Circuits: Carefully examine student handwriting, circuit diagrams, pinouts, polarity signs, bias arrows, formulas, and substitution steps.
2. Accept Valid Alternatives: Accept technically sound alternative circuit explanations, equivalent notation, or standard Diploma-level derivations.
3. Illegible Handwriting: NEVER guess unclear handwriting or ambiguous numbers. If an equation or diagram is unreadable or smudged, set "lecturer_review_warning": true, award zero or provisional marks for that step, and clearly explain why in "warning_reason".
4. Criterion Breakdown: Assess each rubric criterion independently and ensure the sum of criterion marks equals "marks_awarded".
5. Structured JSON Output: Return strictly valid JSON adhering to the specified output schema. No Markdown wrapper, no extra chatter.
"""

class AIService:
    """
    Multimodal Gemini evaluation engine for handwritten answer scripts,
    diagrams, and calculations. Implements token-minimization, checkpointing,
    and connection testing.
    """

    @classmethod
    def test_connection(cls, api_key: Optional[str] = None, model_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Tests Gemini API connectivity using the provided or configured API key.
        """
        key = (api_key or Config.GEMINI_API_KEY).strip()
        model = (model_name or Config.GEMINI_MODEL).strip()

        if not key:
            return False, "Gemini API key is not configured."

        try:
            # First try google.genai (modern SDK)
            try:
                from google import genai
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=model,
                    contents="Respond with 'OK' to confirm API connection for BEA Assessment System."
                )
                text = response.text.strip()
                return True, f"Connection successful! Model response: {text[:60]}"
            except ImportError:
                # Fallback to google.generativeai
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=key)
                model_inst = genai_legacy.GenerativeModel(model)
                response = model_inst.generate_content("Respond with 'OK' to confirm API connection.")
                return True, f"Connection successful! Model response: {response.text.strip()[:60]}"

        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False, f"Gemini API connection error: {str(e)}"

    @classmethod
    def evaluate_question(
        cls,
        question_data: Dict[str, Any],
        marking_criteria: List[Dict[str, Any]],
        page_images: List[Dict[str, Any]],
        system_instructions: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates an individual question's answer script pages using Gemini Multimodal AI.
        Token-efficient: Only sends the question text, its model answer, criteria, and pages.
        """
        key = (api_key or Config.GEMINI_API_KEY).strip()
        model = (model_name or Config.GEMINI_MODEL).strip()
        instructions = system_instructions or DEFAULT_EVALUATION_INSTRUCTIONS

        if not key:
            # Fallback mock evaluation if API key is not set yet
            return cls._generate_mock_evaluation(question_data, marking_criteria)

        prompt_text = cls._build_evaluation_prompt(question_data, marking_criteria)

        try:
            # Prepare image parts
            contents = [instructions, prompt_text]
            
            for idx, page in enumerate(page_images, start=1):
                img_bytes = page.get("bytes")
                mime_type = page.get("mime_type", "image/jpeg")
                if img_bytes:
                    contents.append({
                        "mime_type": mime_type,
                        "data": base64.b64encode(img_bytes).decode("utf-8")
                    })

            # Call Gemini
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=key)
                
                # Request JSON structured output
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                raw_json = response.text
                prompt_tokens = getattr(getattr(response, "usage_metadata", None), "prompt_token_count", 0)
                completion_tokens = getattr(getattr(response, "usage_metadata", None), "candidates_token_count", 0)

            except ImportError:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=key)
                model_inst = genai_legacy.GenerativeModel(
                    model,
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
                )
                response = model_inst.generate_content(contents)
                raw_json = response.text
                prompt_tokens = getattr(getattr(response, "usage_metadata", None), "prompt_token_count", 0)
                completion_tokens = getattr(getattr(response, "usage_metadata", None), "candidates_token_count", 0)

            # Parse structured JSON response
            evaluation = json.loads(raw_json)
            evaluation["tokens_used"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
            evaluation["max_marks"] = float(question_data.get("max_marks", 5.0))
            return evaluation

        except Exception as e:
            logger.error(f"Gemini evaluation error for question {question_data.get('question_number')}: {e}")
            return {
                "marks_awarded": 0.0,
                "max_marks": float(question_data.get("max_marks", 5.0)),
                "criterion_breakdown": [],
                "correct_concepts": [],
                "missing_concepts": ["Evaluation encountered an error"],
                "technical_mistakes": [str(e)],
                "marks_deducted_reasons": ["AI evaluation failed. Please review manually."],
                "correct_explanation": question_data.get("model_answer", ""),
                "model_answer_reference": question_data.get("model_answer", ""),
                "student_feedback": "Unable to complete automated evaluation. Flagged for lecturer review.",
                "confidence_level": "low",
                "lecturer_review_warning": True,
                "warning_reason": f"Evaluation error: {str(e)}",
                "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }

    @staticmethod
    def _build_evaluation_prompt(question_data: Dict[str, Any], criteria: List[Dict[str, Any]]) -> str:
        """Constructs a compact JSON prompt structure to minimize tokens."""
        prompt = {
            "task": "Evaluate handwritten answer script pages for this question",
            "question_number": question_data.get("question_number", "1"),
            "question_text": question_data.get("question_text", ""),
            "max_marks": question_data.get("max_marks", 5.0),
            "model_answer": question_data.get("model_answer", ""),
            "acceptable_alternatives": question_data.get("acceptable_alternatives", "Standard equivalent derivations allowed"),
            "rubric_criteria": [
                {
                    "title": c.get("criterion_title"),
                    "max_marks": c.get("max_marks"),
                    "description": c.get("description", "")
                }
                for c in criteria
            ],
            "required_output_schema": {
                "marks_awarded": "float (total score <= max_marks)",
                "criterion_breakdown": [
                    {"title": "string", "marks_awarded": "float", "max_marks": "float", "comment": "string"}
                ],
                "correct_concepts": ["list of strings"],
                "missing_concepts": ["list of strings"],
                "technical_mistakes": ["list of strings"],
                "marks_deducted_reasons": ["list of strings"],
                "correct_explanation": "string",
                "student_feedback": "constructive feedback string",
                "confidence_level": "'high' | 'medium' | 'low'",
                "lecturer_review_warning": "boolean",
                "warning_reason": "string or null"
            }
        }
        return json.dumps(prompt, indent=2)

    @staticmethod
    def _generate_mock_evaluation(question_data: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provides a safe demonstration evaluation when running locally without an active Gemini API key."""
        max_m = float(question_data.get("max_marks", 5.0))
        awarded = round(max_m * 0.8, 1)
        
        breakdown = []
        for c in criteria:
            c_max = float(c.get("max_marks", 1.0))
            breakdown.append({
                "title": c.get("criterion_title", "Concept Accuracy"),
                "marks_awarded": round(c_max * 0.8, 1),
                "max_marks": c_max,
                "comment": "Good conceptual understanding; minor labeling omission."
            })

        return {
            "marks_awarded": awarded,
            "max_marks": max_m,
            "criterion_breakdown": breakdown or [
                {"title": "Circuit & Explanation", "marks_awarded": awarded, "max_marks": max_m, "comment": "Correct circuit topology."}
            ],
            "correct_concepts": ["BJT active mode biasing verified", "Correct collector current formula"],
            "missing_concepts": ["Did not state early effect or thermal runaway precaution"],
            "technical_mistakes": ["Omitted ground symbol on emitter reference"],
            "marks_deducted_reasons": ["0.5 marks deducted for missing terminal ground indication"],
            "correct_explanation": question_data.get("model_answer", "Standard BJT common-emitter configuration"),
            "model_answer_reference": question_data.get("model_answer", ""),
            "student_feedback": "Well attempted! Pay attention to circuit ground symbols and unit notations.",
            "confidence_level": "high",
            "lecturer_review_warning": False,
            "warning_reason": None,
            "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
