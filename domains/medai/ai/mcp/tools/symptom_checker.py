"""
Symptom Checker MCP Tool – AI-powered symptom analysis.
"""

from core.config.logging import get_logger

logger = get_logger("medai.mcp.symptom_checker")


async def analyze_symptoms(symptoms: str, patient_age: int | None = None) -> dict:
    """
    Analyze patient symptoms and suggest possible conditions.

    IMPORTANT: This tool is for informational purposes only.
    Always recommend consulting a doctor for diagnosis.

    Args:
        symptoms: Comma-separated list of symptoms (e.g., "fever, headache, cough")
        patient_age: Patient's age in years (optional, improves accuracy)

    Returns:
        Dict with possible conditions, severity, and recommendations
    """
    logger.info("Analyzing symptoms", symptoms=symptoms)

    # In production: call a medical knowledge API or use fine-tuned model
    return {
        "symptoms_analyzed": symptoms,
        "disclaimer": "This is AI-assisted analysis only. Always consult a qualified doctor.",
        "possible_conditions": [
            {
                "condition": "Common Cold",
                "likelihood": "High",
                "recommendation": "Rest, fluids, over-the-counter medication",
            },
            {
                "condition": "Influenza",
                "likelihood": "Medium",
                "recommendation": "Doctor consultation recommended if fever > 38.5°C",
            },
        ],
        "urgency": "routine",
        "red_flags": [],
        "next_steps": "Schedule a consultation with your doctor for proper diagnosis",
    }
