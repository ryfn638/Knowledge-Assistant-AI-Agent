"""Minimal ConnectOnion agent with a simple calculator tool."""

from connectonion import Agent
from pathlib import Path
from pdf_automation import PDFAutomation
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def calculator(expression: str) -> float:
    """Simple calculator that evaluates arithmetic expressions.

    Args:
        expression: A mathematical expression (e.g., "5*5", "10+20")

    Returns:
        The result of the calculation
    """
    # Note: eval() is used for simplicity. For production, use a safer parser.
    return eval(expression)

# Sample pdf which has all of the subject matter for uni subject, this should be a good test case
pdf_path = Path(__file__).parent / "CAB202LectureNotes.pdf"

question = input(f"Ask question revolving around the document\n")
pdf_tools = PDFAutomation(pdf_path, question)

# Create agent with calculator tool
agent = Agent(
    name="knowledge-assistant", 
    system_prompt=Path(__file__).parent / "prompt.md", # you can also pass a markdown file like system_prompt="path/to/your_markdown_file.md"
    tools=pdf_tools, # tools can be python classes or functions
    model="gemini-2.5-flash", # Using Gemini model - requires GOOGLE_API_KEY in .env file
    api_key=None  # Will read from GOOGLE_API_KEY environment variable or .env file
)



# Run the agent
if __name__ == "__main__":
    result = agent.input(f"Answer the question : {question}")

    print(result)
