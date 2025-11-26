import os, time, base64, stomp, json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain.tools import tool

load_dotenv()

# --- Environment Variables ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# --- LLM Setup ---
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0.2
)

# --- Tool: PDF Parser ---
@tool
def parse_pdf_tool(filepath: str) -> dict:
    """
    Tool that parses a PDF file and returns structured JSON.
    """
    reader = PdfReader(filepath)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    sections = [
        {"section": f"Section {i+1}", "content": chunk.strip()}
        for i, chunk in enumerate(text.split("\n\n")) if chunk.strip()
    ]

    return {
        "regulation_id": os.path.basename(filepath),
        "title": os.path.basename(filepath).replace(".pdf", ""),
        "sections": sections,
        "raw_text": text
    }

# --- System Prompt ---
monitor_instructions = """
You are the Regulation Monitor Agent.
Your job is to ingest new regulations from the ActiveMQ queue, save them,
call the parse_pdf_tool to extract text, and output structured JSON with:
- regulation_id
- title
- sections (list of {section, content})
- raw_text

Do not return free-form text. Always output valid JSON.
"""

# --- Create Agent with Tool ---
tools = [parse_pdf_tool]
agent = create_agent(llm, tools=tools, system_prompt=monitor_instructions)

# --- Consumer Logic ---
class RegulationConsumer(stomp.ConnectionListener):
    def __init__(self, agent, output_folder="mock_folder"):
        self.agent = agent
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    def on_message(self, frame):
        raw_filename = frame.headers.get("filename", "unknown.pdf")
        filename = os.path.basename(raw_filename)
        filepath = os.path.join(self.output_folder, filename)

        # Decode and save PDF
        pdf_bytes = base64.b64decode(frame.body)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        print(f"[Monitor] Saved regulation: {filepath}")

        try:
            # Call the parsing tool. The `@tool` decorator returns a StructuredTool
            # object which may not be directly callable. Prefer `.run()` or the
            # original function available as `.func`.
            if hasattr(parse_pdf_tool, "run") and callable(getattr(parse_pdf_tool, "run")):
                result = parse_pdf_tool.run(filepath)
            elif hasattr(parse_pdf_tool, "func") and callable(getattr(parse_pdf_tool, "func")):
                result = parse_pdf_tool.func(filepath)
            else:
                raise RuntimeError("parse_pdf_tool is not callable and does not expose 'run' or 'func'.")

            # Normalize result: tool may return a dict or a JSON string
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                except Exception:
                    parsed = {"text": result}
            else:
                parsed = result

            # Print structured JSON output
            print(f"[Monitor] Parsed regulation:\n{json.dumps(parsed, indent=2)}\n")

        except Exception as e:
            print(f"[Monitor] Error processing {filename}: {e}")

# --- Connect to ActiveMQ ---
conn = stomp.Connection([("localhost", 61613)])
consumer = RegulationConsumer(agent=agent)
conn.set_listener("", consumer)
conn.connect(wait=True)
conn.subscribe(destination="/queue/regulation.incoming", id=1, ack="auto")

print("[Monitor Agent] Listening for new regulations... Press Ctrl+C to stop.")

while True:
    time.sleep(1)