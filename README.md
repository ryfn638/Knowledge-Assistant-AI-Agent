# Knowledge Assistant Study AI Agent
Simple pdf analysis AI agent that can answer basic queries about pdf documents that uses OpenOnion
This works best with pdf files that are completely text and dont contain scanned images as content.

## Some other features
- If you request it to it can create notes on specific tasks which are stored in extras/notes.html
- Similarly it can create multiple choice quizzes with an answer sheet included separately which are also stored in the extras folders

---

If you want to use this agent you will need to provide your own Google Gemini API key via the inclusion of a .env folder which has the following structure
GOOGLE_API_KEY=yourapikeyhere

If you want to change the model to use your paid GPT-5 API key, then in agent.py replace the `model = "gemini-2.5-flash"` with whatever model you want to use as shown.

```python
agent = Agent(
    name="knowledge-assistant", 
    system_prompt=Path(__file__).parent / "prompt.md", # you can also pass a markdown file like system_prompt="path/to/your_markdown_file.md"
    tools=pdf_tools, # tools can be python classes or functions
    model="YOURMODELNAMEHERE",
    api_key=None  # Will read from GOOGLE_API_KEY environment variable or .env file
)```

 Similarly in pdf_automation you will also have to do this with applications of `llm_do()`
 there will be a `model = gemini-2.5-flash` which you can replace with your own LLM API key.

 For more information on your specific LLM refer to OpenOnion Documentation
