# Knowledge Assistant Study AI Agent
Simple pdf analysis AI agent that can answer basic queries about pdf documents
This works best with pdf files that are completely text and dont contain scanned images as content.

Some other features
- If you request it to it can create notes on specific tasks which are stored in extras/notes.html
- Similarly it can create multiple choice quizzes with an answer sheet included separately which are also stored in the extras folders

---

If you want to use this agent you will need to provide your own Google Gemini API key via the inclusion of a .env folder which has the following structure
GOOGLE_API_KEY=yourapikeyhere
