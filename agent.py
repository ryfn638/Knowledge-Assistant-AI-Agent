"""Minimal ConnectOnion agent with a simple calculator tool."""

from connectonion import Agent
from pathlib import Path
from pdf_automation import PDFAutomation
from dotenv import load_dotenv
from website_automation import WebsiteAutomation
from utils import InfoTools
# Load environment variables from .env file
load_dotenv()

# Sample pdf which has all of the subject matter for uni subject, this should be a good test case
pdf_path = Path(__file__).parent / "pdfs" / "CAB202LectureNotes.pdf"

print(f"Type exit as an input to close the program")

# Create agent with calculator tool
agent = Agent(
    name="knowledge-assistant", 
    system_prompt=Path(__file__).parent / "prompt.md", # you can also pass a markdown file like system_prompt="path/to/your_markdown_file.md"
    tools=[PDFAutomation(), WebsiteAutomation(), InfoTools()], # tools can be python classes or functions
    model="gemini-2.5-flash", # Using Gemini model - requires GOOGLE_API_KEY in .env file
    api_key=None  # Will read from GOOGLE_API_KEY environment variable or .env file
)


# Run the agent, maybe could attach this to a web server and just compute with AWS and would be sick to expand upon this more
# Make like a full on study app with quizzes and whatnot, but thats for another time.
if __name__ == "__main__":
    question = "None"
    result = agent.input(f"""
        1. Prompt the user to provide a document, this can be a website or a pdf document. Run the function fetch_info_type() here
        2. Once the location is found then use the corresponding Automation() class to answer any prompts the user may make
        3. If the user has provided a pdf but no path, then request a path from the user, using fetch_info_type() again for this
        4. Ask the user for a request surrounding the document, and then answer their prompt
        5. If the user requests exit, then return "Exit" as an output.
        """)

    print(result)

    while (question.lower() != "exit"):
        
        result = agent.input(f"""
        1. Ask the user for a request surrounding the document, and then answer their prompt
        2. If the user wants to change the document run the following process (
            1. Once the location is found then use the corresponding Automation() class to answer any prompts the user may make
            2. If the user has provided a pdf but no path, then request a path from the user, using fetch_info_type() again for this
            3. Ask the user for a request surrounding the document, and then answer their prompt
        )
        3. If the user requests exit, then return "Exit" as an output.
        """)

        print(result)
        
        question = result

    print("Thanks for using the Study Agent")