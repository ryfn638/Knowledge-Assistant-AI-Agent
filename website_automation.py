import os
from connectonion import xray, llm_do
import search_strategy
from pydantic import BaseModel
from pdf_automation import QuizContent
from utils import generate_keywords

import requests
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class WebsiteAutomation():
    """
    Interface for accessing and processing content from websites and YouTube videos.
    Use tools from this class when the user provides a website URL or YouTube link (not a PDF).
    Supports: articles, blogs, documentation, and YouTube video metadata.
    """

    def __init__(self):
        self.keywords = None;
        self.website_text = None;
        self.question = None;
        self.website = None;
        api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube_client = build("youtube", "v3", developerKey=api_key) if api_key else None

    def ask_website_question(self) -> str:
        """
        Tool: Prompt the user for a question about the website or YouTube video.
        """
        self.question = input(f"Ask question revolving around the document\n");

        if (self.question.lower() == "exit"):
            return "return Exit"
        else :
            return self.question

    def load_website(self, url: str) -> str:
        """
        Tool: Fetch a web page (articles, blogs, docs) and cache its HTML content for scanning.
        Automatically adds https:// if scheme is missing and includes browser headers to avoid bot detection.
        """
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            return f"Invalid website: {exc}"

        self.website = resp
        self.website_text = resp.text

        return "Website successfully loaded"

    def load_website_text(self) -> str:
        """
        Tool: Refresh the cached website text from the stored response object.
        Use this if the website content has been updated or you need to re-extract text.
        """
        if not self.website:
            return "No website loaded. Call load_website() first."
        self.website_text = self.website.text
        return "Text successfully extracted"

    def _extract_youtube_id(self, url: str):
        """
        Private helper: Extract YouTube video ID from various URL formats.
        Supports youtube.com/watch?v=ID and youtu.be/ID formats.
        """
        parsed = urlparse(url)
        if parsed.hostname in ("youtu.be", "www.youtu.be"):
            return parsed.path.lstrip("/")
        if parsed.hostname and "youtube.com" in parsed.hostname:
            query = parse_qs(parsed.query)
            return query.get("v", [None])[0]
        return None

    def load_youtube_video(self, url: str) -> str:
        """
        Tool: Load YouTube video metadata (title, channel, description) via YouTube Data API.
        Requires YOUTUBE_API_KEY environment variable to be set. Caches text content for searching.
        """
        if not self.youtube_client:
            return "YouTube API not configured. Set YOUTUBE_API_KEY environment variable."

        video_id = self._extract_youtube_id(url)
        if not video_id:
            return "Invalid YouTube URL."

        try:
            response = (
                self.youtube_client.videos()
                .list(part="snippet", id=video_id)
                .execute()
            )
        except HttpError as exc:
            return f"Failed to load video: {exc}"

        items = response.get("items")
        if not items:
            return "Video not found."

        snippet = items[0].get("snippet", {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        channel = snippet.get("channelTitle", "")

        text_chunks = [title, channel, description]
        self.website_text = "\n".join(chunk for chunk in text_chunks if chunk)
        self.website = {"video_id": video_id, "snippet": snippet}

        return "YouTube video details loaded"
    
    def generate_web_keywords(self, question: str) -> str:
        """
        Tool: Generate search keywords from the user's question for website/YouTube content scanning.
        Keywords help identify relevant sections before running the full LLM search.
        """
        self.question = question
        self.keywords = generate_keywords(question)
        return f"Generated keywords: {', '.join(self.keywords) if self.keywords else 'None'}"

    def search_website(self) -> str:
        """
        Tool: Search the cached website/YouTube content to answer the user's question.
        Requires keywords to be generated first via generate_web_keywords().
        Filters out HTML tags and focuses on visible content text.
        """
        if not self.website_text:
            return "No website content loaded. Call load_website() or load_youtube_video() first."
        
        if not self.keywords:
            return "No keywords generated. Call generate_web_keywords() first."
        
        page_text = self.website_text
        keyword_matches = sum(1 for kw in self.keywords if kw.lower() in page_text.lower())
        
        if keyword_matches < 1:
            return "No answer found. Insufficient keywords in the content."

        # Truncate very long pages to reduce token usage
        truncated_text = page_text[:5000] + "..." if len(page_text) > 5000 else page_text

        result = llm_do(f"""
        Search the following website content for an answer to the question: {self.question}

        Content:
        {truncated_text}

        Note: This may contain HTML tags - ignore them and focus only on visible text content.

        If you find a satisfactory answer, provide it. If the answer is unsatisfactory or lacking enough context, return:
        answer="No answer found on these pages", reason="Insufficient information"
        """, 
        output=search_strategy.SearchStrategy, model="gemini-2.5-flash")
        
        if result.answer != "No answer found on these pages" and result.answer != "No answer found on the page":
            return result.answer
        else:
            return "No answer found in the searched content."

    def clear_web_keywords(self) -> str:
        """
        Tool: Clear cached keywords when switching to a new topic or question.
        Use when the user asks an unrelated question to reset the search state.
        """
        self.keywords = None
        self.question = None
        return "Keywords and question cleared"



