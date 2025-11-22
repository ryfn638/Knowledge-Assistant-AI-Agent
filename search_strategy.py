from connectonion import xray, llm_do
from pydantic import BaseModel

class SearchStrategy(BaseModel):
    answer: str
    reason: str

def search_page(page: str, 
    keywords: list[str],
    question: str) -> SearchStrategy:

    """
        Scan the page and analyse with llm_do if there are relevant keywords on the page
    """
    answer = scan_page_linear(page, keywords, question)
    
    if (answer.answer != "No answer found on the page"):
        return answer # if a relevant answer is returned we are chungus chilin

    return SearchStrategy(answer="No answer found on the page", reason="No keywords found on the page")


def scan_page_linear(page:str, keywords: list[str], question: str) -> SearchStrategy:
    """
    Scan if there are keywords on the page before running a search.
    if there are keywords search the page for an an answer with llm_do and return the answer.
    Optimized to require multiple keyword matches to reduce false positives.
    """
    if not keywords:
        return SearchStrategy(answer="No answer found on the page", reason="No keywords provided")
    
    # Require at least 2 keyword matches to reduce false positives and API calls
    keyword_matches = sum(1 for keyword in keywords if keyword.lower() in page.lower())
    
    if keyword_matches >= 2:
        # Truncate very long pages to reduce token usage
        truncated_page = page[:2000] + "..." if len(page) > 2000 else page
        
        answer = llm_do(f"""Search the following page text for an answer to the question: {question}
        
Page text:
{truncated_page}

If you find a satisfactory answer, provide it. If the answer is unsatisfactory or lacking enough context, return:
answer="No answer found on the page", reason="Insufficient information on this page"
""", output=SearchStrategy, model="gemini-2.5-flash")
        return answer
    
    return SearchStrategy(answer="No answer found on the page", reason=f"Only {keyword_matches} keyword(s) found, need at least 2")