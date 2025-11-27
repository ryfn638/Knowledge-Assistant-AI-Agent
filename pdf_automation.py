import PyPDF2
from connectonion import xray, llm_do
import search_strategy
from pydantic import BaseModel
from utils import generate_keywords

class QuizContent(BaseModel):
    """Model for quiz output with separate questions and answers HTML."""
    questions: str
    answers: str

class PDFAutomation:
    """
        Simple Interface for performing all needed operations for scanning different pages
        This includes:
        - Scanning pages for present keywords and gathering relevant content
        - If not sufficient then traverse to the next page
        - flip the page in the opposite direction if needed
        - Generating keywords based off the question

        Use tools from this function should the user provide a pdf and NOT a link to a website
    """

    def __init__(self):
        self.pdf_reader = None;
        self.current_page = 0;
        self.page = None;

        self.question = None;
        self.keywords = None;
        self.relevantPages = [];

    def ask_pdf_question(self) -> str:
        """
        Tool: Prompt the user for a question about the PDF document.
        """
        self.question = input(f"Ask question revolving around the document\n");
        if (self.question.lower() == "exit"):
            return "return Exit"
        else :
            return self.question

    def load_pdf(self, pdf_path: str = None) -> str:
        """
        Tool: Load a PDF document from a file path. If no path is provided, prompts the user.
        """
        if not pdf_path:
            pdf_path = input(f"Please provide a valid pdf filepath: ")

        try:
            self.pdf_reader = PyPDF2.PdfReader(pdf_path)
            self.current_page = 0
            return "PDF successfully loaded"
        except Exception as e:
            return f"Invalid PDF filepath: {e}"


    def get_page(self) -> str:
        """
        Tool: Load the current page from the PDF into memory.
        """
        self.page = self.pdf_reader.pages[self.current_page]
        return f"Loaded page {self.current_page}"

    def flip_page(self) -> str:
        """
        Tool: Move to the next page in the PDF document.
        """
        if self.current_page < len(self.pdf_reader.pages) - 1:
            self.current_page += 1
            self.page = self.pdf_reader.pages[self.current_page]
            return f"Moved to page {self.current_page}"
        else:
            return "Already on last page"

    def reverse_flip_page(self) -> str:
        """
        Tool: Move to the previous page in the PDF document.
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.page = self.pdf_reader.pages[self.current_page]
            return f"Moved to page {self.current_page}"
        else:
            return "Already on first page"

    def get_text(self) -> str:
        """
        Tool: Extract all text content from the currently loaded page.
        """
        if not self.page:
            return "No page loaded. Call get_page() first."
        return self.page.extract_text()

    def generate_pdf_keywords(self) -> str:
        """
        Tool: Generate search keywords from the user's question for PDF scanning.
        """
        self.keywords = generate_keywords(self.question)

        return f"Generated keywords: {', '.join(self.keywords) if self.keywords else 'None'}"

    def scan_page(self) -> str:
        """
        Tool: Search the current page for an answer to the user's question using keywords.
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
        Tool: Jump directly to a specific page number (0-indexed) in the PDF.
        """
        if page_number < 0 or page_number >= len(self.pdf_reader.pages):
            return f"Invalid page number. Document has {len(self.pdf_reader.pages)} pages (0-{len(self.pdf_reader.pages)-1})"
        self.current_page = page_number
        self.page = self.pdf_reader.pages[self.current_page]

        self.relevantPages = [self.current_page]

        return f"Jumped to page {self.current_page}"

    def get_total_pages(self) -> int:
        """
        Tool: Get the total number of pages in the loaded PDF document.
        """
        return len(self.pdf_reader.pages)

    def extract_text_range(self, start_page: int, end_page: int) -> str:
        """
        Tool: Extract and concatenate text from a range of pages (inclusive).
        Updates relevantPages for use in notes/quiz generation.
        """
        if start_page < 0 or end_page >= len(self.pdf_reader.pages) or start_page > end_page:
            return f"Invalid page range. Document has {len(self.pdf_reader.pages)} pages (0-{len(self.pdf_reader.pages)-1})"
        
        text_parts = []
        for page_num in range(start_page, end_page + 1):
            page = self.pdf_reader.pages[page_num]
            text = page.extract_text()
            text_parts.append(f"--- Page {page_num} ---\n{text}\n")
        
        ## update relevantPages if a html is going to be made
        self.relevantPages = [page_num for page_num in range(start_page, end_page+1)]
        return "\n".join(text_parts)

    def search_entire_document(self) -> str:
        """
        Tool: Search the entire PDF for an answer by scanning all pages efficiently.
        Optimized to reduce API calls by batching pages and requiring multiple keyword matches.
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
            keyword_matches = sum(1 for kw in self.keywords if kw.lower() in page_text.lower())
            if keyword_matches >= 2:  # Require at least 2 unique keyword matches
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
            result = llm_do(f"""
            Search the following pages for an answer to the question: {self.question}

            Pages to search:
            {batch_text}

            If you find a satisfactory answer, provide it. If the answer is unsatisfactory or lacking enough context, return:
            answer="No answer found on these pages", reason="Insufficient information"
            """, 
            output=search_strategy.SearchStrategy, model="gemini-2.5-flash")
            
            if result.answer != "No answer found on these pages" and result.answer != "No answer found on the page":
                self.relevantPages = page_numbers # Save the Relevant Pages
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
        Tool: Get the current page number (0-indexed) in the PDF.
        """
        return self.current_page


    def createNotes(self) -> str:
        """
        Tool: Generate comprehensive HTML study notes from relevant PDF pages.
        Requires search_entire_document() or extract_text_range() to have run first.
        Saves notes to extras/notes.html.
        """

        if len(self.relevantPages) == 0:
            return "No relevant pages in the pdf to form notes, run search_entire_document()"

        # Extract text from relevant pages
        pages_text = ""
        for page_num in self.relevantPages:
            page = self.pdf_reader.pages[page_num]
            page_text = page.extract_text()
            pages_text += f"\n\n--- Page {page_num} ---\n{page_text}"
        
        # Generate HTML notes using LLM
        html_content = llm_do(f"""
            Based on the question: {self.question}
            
            Create comprehensive study notes in HTML format from the following pages:
            {pages_text}
            
            Format the notes as a complete, well-structured HTML document with:
            - Proper HTML structure (html, head, body tags)
            - Title and headings
            - Organized sections
            - Good formatting and styling
            - Return ONLY the HTML code, nothing else
            """, 
            model="gemini-2.5-flash")
        
        # Save HTML string to notes.html file
        with open('extras/notes.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return f"Notes successfully saved to notes.html using pages {self.relevantPages}"

    def quizNotes(self) -> str:
        """
        Tool: Generate a multiple-choice quiz and answer key from relevant PDF pages.
        Requires search_entire_document(), extract_text_range(), or jump_to_page() to have run first.
        Saves quiz to extras/quiz.html and answers to extras/answers.html.
        """

        if len(self.relevantPages) == 0:
            return "No relevant pages in the pdf to form notes, run search_entire_document()"

        # Extract text from relevant pages
        pages_text = ""
        for page_num in self.relevantPages:
            page = self.pdf_reader.pages[page_num]
            page_text = page.extract_text()
            pages_text += f"\n\n--- Page {page_num} ---\n{page_text}"

        # Generate quiz HTML using LLM with structured output
        quiz_content = llm_do(f"""
            Based on the query: {self.question}
            
            Create a comprehensive quiz in HTML format using the following page text as a reference:
            {pages_text}. Assume that the quiz is multiple choice UNLESS specified otherwise.
            
            You must return two separate HTML documents:
            1. questions: A complete, well-structured HTML document containing the quiz questions with:
               - Proper HTML structure (html, head, body tags)
               - Title and headings
               - Multiple choice questions with options (A, B, C, D, etc.)
               - Good formatting and styling
               - Do NOT include the answers in this document
            
            2. answers: A complete, well-structured HTML document containing the answer key with:
               - Proper HTML structure (html, head, body tags)
               - Title and headings
               - Clear answer key showing which option is correct for each question
               - Good formatting and styling
            """, 
            model="gemini-2.5-flash",
            output=QuizContent)

        # Save HTML strings to separate files
        with open('extras/quiz.html', 'w', encoding='utf-8') as f:
            f.write(quiz_content.questions)
        
        with open('extras/answers.html', 'w', encoding='utf-8') as f:
            f.write(quiz_content.answers)
        
        return f"Quiz successfully saved to extras/quiz.html and extras/answers.html using pages {self.relevantPages}"


    def clearKeywords(self) -> str:
        """
        Tool: Clear cached keywords and relevant pages when switching to a new topic.
        Use when the user asks an unrelated question to reset the search state.
        """
        self.relevantPages = []
        self.keywords = None
        return "Keywords and relevant pages cleared"







