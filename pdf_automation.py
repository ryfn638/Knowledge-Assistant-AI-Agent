import PyPDF2
from connectonion import xray, llm_do
import search_strategy

class PDFAutomation:
    """
        Simple Interface for performing all needed operations for scanning different pages
        This includes:
        - Scanning pages for present keywords and gathering relevant content
        - If not sufficient then traverse to the next page
        - flip the page in the opposite direction if needed
        - Generating keywords based off the question
    """

    def __init__(self, pdf_path: str, question : str):
        self.pdf_reader = PyPDF2.PdfReader(pdf_path)
        self.current_page = 0;
        self.page = None;

        self.question = question;

        self.keywords = None;

    def get_page(self) -> str:
        """
        Get the Current page
        """
        self.page = self.pdf_reader.pages[self.current_page]
        return f"Loaded page {self.current_page}"

    def flip_page(self) -> str:
        """
        Traverse to the next page and assign self.page to the new page
        """
        if self.current_page < len(self.pdf_reader.pages) - 1:
            self.current_page += 1
            self.page = self.pdf_reader.pages[self.current_page]
            return f"Moved to page {self.current_page}"
        else:
            return "Already on last page"

    def reverse_flip_page(self) -> str:
        """
        Traverse to the previous page and assign self.page to the new page
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.page = self.pdf_reader.pages[self.current_page]
            return f"Moved to page {self.current_page}"
        else:
            return "Already on first page"

    def get_text(self) -> str:
        """
        Get the text of the current page
        """
        if not self.page:
            return "No page loaded. Call get_page() first."
        return self.page.extract_text()

    def generate_keywords(self) -> str:
        """
        Generate keywords based on the question
        """
        # Get keywords as a comma-separated string (Gemini doesn't support structured output for lists)
        keywords_str = llm_do(f"""
        Generate keywords based on the question: {self.question}.
        These Keywords do not have to specifically be in the question.
        For example if the question was: "Where do rabbits live", keywords can include: habitat, live, environment.
        Essentially common words that relate to the main question that you would expect to see in a pdf document addressing them.
        
        Return ONLY a comma-separated list of keywords, nothing else. For example: "habitat, live, environment, rabbits, dwelling"
        """, model="gemini-2.5-flash")

        # Parse the comma-separated string into a list
        if keywords_str:
            # Split by comma, strip whitespace, and filter out empty strings
            self.keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        else:
            self.keywords = []

        return f"Generated keywords: {', '.join(self.keywords) if self.keywords else 'None'}"

    def scan_page(self) -> str:
        """
        This is the main function that will be called to scan the page for the answer.
        This uses the search_page function in the search_strategy file
        """
        if not self.page:
            return "Page doesn't exist. Call get_page() first."

        page_text = self.get_text()

        result = search_strategy.search_page(page_text,
         self.keywords,
         self.question)

        # Convert SearchStrategy object to string format
        return f"Answer: {result.answer}\nReason: {result.reason}"

    def jump_to_page(self, page_number: int) -> str:
        """
        Jump to a specific page number (0-indexed).
        """
        if page_number < 0 or page_number >= len(self.pdf_reader.pages):
            return f"Invalid page number. Document has {len(self.pdf_reader.pages)} pages (0-{len(self.pdf_reader.pages)-1})"
        self.current_page = page_number
        self.page = self.pdf_reader.pages[self.current_page]
        return f"Jumped to page {self.current_page}"

    def get_total_pages(self) -> int:
        """
        Get the total number of pages in the PDF.
        """
        return len(self.pdf_reader.pages)

    def extract_text_range(self, start_page: int, end_page: int) -> str:
        """
        Extract text from a range of pages (inclusive).
        Returns concatenated text from all pages in the range.
        """
        if start_page < 0 or end_page >= len(self.pdf_reader.pages) or start_page > end_page:
            return f"Invalid page range. Document has {len(self.pdf_reader.pages)} pages (0-{len(self.pdf_reader.pages)-1})"
        
        text_parts = []
        for page_num in range(start_page, end_page + 1):
            page = self.pdf_reader.pages[page_num]
            text = page.extract_text()
            text_parts.append(f"--- Page {page_num} ---\n{text}\n")
        
        return "\n".join(text_parts)

    def search_entire_document(self) -> str:
        """
        Search the entire document for the answer by scanning all pages.
        Optimized to reduce API calls: batches pages together and requires multiple keyword matches.
        """
        if not self.keywords:
            return "No keywords generated. Call generate_keywords() first."
        
        total_pages = len(self.pdf_reader.pages)
        pages_to_search = min(total_pages, 50)  # Limit to 50 pages max
        answers = []
        
        # Save current page position
        original_page = self.current_page
        
        # Find pages with keywords first (cheap operation, no API calls)
        candidate_pages = []
        for page_num in range(pages_to_search):
            page = self.pdf_reader.pages[page_num]
            page_text = page.extract_text()
            
            # Check if multiple keywords are present (better signal, reduces false positives)

            ## Improvements:
            # A keyword match in a title > Keyword match in a paragraph, consider the structure of where the keyword occurs,
            # is it a Title? if so thats worth at least 3 keywords. 2 mentions in a paragraph > 1 mention as a title, even though realistically if its a title should have at least 2 mentions
            # Keyword Diversity is also important,
            # If a biology document with 100s of animals was shown then the question: Where do frogs live
            # The live Keyword will appear 100s of times, so maybe its not diversity but rather filtering out keywords that appear too much in the doc
            keyword_matches = sum(1 for kw in self.keywords if kw.lower() in page_text.lower())
            if keyword_matches >= 2:  # Require at least 2 keyword matches
                candidate_pages.append((page_num, page_text, keyword_matches))
        
        if not candidate_pages:
            self.current_page = original_page
            if original_page < total_pages:
                self.page = self.pdf_reader.pages[original_page]
            return "No answer found. No pages contained sufficient keywords."
        
        # Sort by keyword match count (highest first) - search best matches first
        candidate_pages.sort(key=lambda x: x[2], reverse=True)
        
        # Process pages in batches of 5 to reduce API calls (5 pages per call instead of 1)
        batch_size = 5
        for batch_start in range(0, min(len(candidate_pages), 20), batch_size):  # Max 20 pages = 4 API calls
            batch = candidate_pages[batch_start:batch_start + batch_size]
            
            # Build batch prompt with multiple pages
            batch_text = ""
            page_numbers = []
            for page_num, page_text, _ in batch:
                # Truncate very long pages to reduce tokens (keep first 2000 chars)
                truncated_text = page_text[:2000] + "..." if len(page_text) > 2000 else page_text
                batch_text += f"\n\n--- Page {page_num} ---\n{truncated_text}"
                page_numbers.append(page_num)
            
            # Single API call for the entire batch (5 pages at once!)
            result = llm_do(f"""Search the following pages for an answer to the question: {self.question}

Pages to search:
{batch_text}

If you find a satisfactory answer, provide it. If the answer is unsatisfactory or lacking enough context, return:
answer="No answer found on these pages", reason="Insufficient information"
""", output=search_strategy.SearchStrategy, model="gemini-2.5-flash")
            
            if result.answer != "No answer found on these pages" and result.answer != "No answer found on the page":
                answers.append(f"Found in pages {page_numbers}: {result.answer}")
                # Early stopping - found a good answer!
                break
        
        # Restore original page position
        self.current_page = original_page
        if original_page < total_pages:
            self.page = self.pdf_reader.pages[original_page]
        
        if answers:
            return "\n\n".join(answers)
        else:
            return "No answer found in the searched pages."

    def get_page_number(self) -> int:
        """
        Get the current page number (0-indexed).
        """
        return self.current_page

    ## STUFF TO DO
    # Add


