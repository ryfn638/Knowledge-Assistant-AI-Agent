"""
Shared helpers for study agent flows.
"""

from typing import List, Optional
from connectonion import llm_do


def generate_keywords(question: str, *, model: str = "gemini-2.5-flash") -> List[str]:
    """
    Generate a cleaned keyword list for the provided question.
    The Gemini models cannot return structured lists reliably, so we parse a comma string.
    """
    if not question:
        return []

    keywords_str: Optional[str] = llm_do(
        f"""  
        Generate a comprehensive set of keywords based on the question: {question}.
        
        IMPORTANT: Generate BROAD, GENERALIZED keywords that capture the essence and context of the question.
        These keywords do not need to be present verbatim in the question.
        
        For each question, think about:
        1. The core concepts and topics being asked about
        2. Related terminology, synonyms, and alternative phrasings
        3. Broader conceptual categories that would contain the answer
        4. Domain-specific vocabulary that would appear in documents discussing this topic
        5. Related measurement units, scales, or technical terms (e.g., for size questions: include "size", "dimension", "measurement", "units", "length", "width", "height", "meters", "feet", "inches", "centimeters", etc.)
        6. Action words and their related forms (e.g., "describe" -> "description", "explain" -> "explanation")
        
        Examples:
        - For "how big is X?" -> include: size, dimension, measurement, units, length, width, height, area, volume, meters, feet, inches, centimeters, scale, magnitude
        - For "what is X?" -> include: definition, explanation, concept, overview, introduction, characteristics, properties
        - For "how does X work?" -> include: mechanism, process, function, operation, procedure, steps, method
        
        Be comprehensive and think about what terms a document would use when discussing this topic, even if they're not explicitly in the question.

        Return ONLY a comma-separated list, e.g. "habitat, live, environment, ecosystem, dwelling, residence".
        """,
        model="gemini-2.5-flash",
    )

    if not keywords_str:
        return []

    # Split by comma, strip whitespace, and filter out empty strings
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

class InfoTools:
    """
    Tool container for collecting document locations (PDF path or website URL).
    """

    def fetch_info_type(self) -> str:
        """
        Tool: Prompt the user for a PDF path or website link when none is provided.
        """
        return input("Please input a PDF path or a link to a website:\n")
