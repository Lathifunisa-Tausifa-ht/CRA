import os, time, base64, stomp, json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent  # ✅ Correct import
from langchain.tools import tool
 
load_dotenv()
 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
 
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0.2
)
 
@tool
def parse_pdf_tool(filepath: str) -> str:
    """Tool that parses a PDF file and returns structured JSON."""
    reader = PdfReader(filepath)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
 
    result = {
        "regulation_id": os.path.basename(filepath),
        "title": os.path.basename(filepath).replace(".pdf", ""),
        "raw_text": text
    }
    # ✅ Return JSON string, not dict
    return json.dumps(result)
 
agent = create_agent(
    model=llm,
    tools=[parse_pdf_tool],
    system_prompt="You are the Regulation Monitor Agent. "
        "When given a PDF filepath, call parse_pdf_tool with that filepath. "
        "Then, generate a concise summary of the parsed content based on the 'raw_text' and 'sections'. "
        "Return a JSON object that includes both the parsed output and the summary."
    )
 
class RegulationConsumer(stomp.ConnectionListener):
    def __init__(self, agent, output_folder="mock_folder"):
        self.agent = agent
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)
 
    def on_message(self, frame):
        raw_filename = frame.headers.get("filename", "unknown.pdf")
        filename = os.path.basename(raw_filename)
        filepath = os.path.join(self.output_folder, filename)
 
        pdf_bytes = base64.b64decode(frame.body)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        print(f"[Monitor] Saved regulation: {filepath}")
 
        try:
            result = self.agent.invoke({
                "messages": [
                    {"role": "user", "content": f"Parse this regulation PDF: {filepath}"}
                ]
            })
 
            # ✅ Extract content - handle different response types
            if isinstance(result, dict):
                # If result is a dict with 'messages' key
                if "messages" in result:
                    raw_response = result["messages"][-1].content
                else:
                    raw_response = result.get("content", "")
            else:
                # If result is an AIMessage object directly
                raw_response = result.content
 
            try:
                parsed_output = json.loads(raw_response)
            except Exception as e:
                print(f"[Monitor] Failed to parse JSON: {e}")
                parsed_output = {"response": str(raw_response)}
 
            print(f"[Monitor] Agent output:\n{json.dumps(parsed_output, indent=2)}\n")
 
        except Exception as e:
            print(f"[Monitor] Error processing {filename}: {e}")
 
conn = stomp.Connection([("localhost", 61613)])
consumer = RegulationConsumer(agent=agent)
conn.set_listener("", consumer)
conn.connect(wait=True)
conn.subscribe(destination="/queue/regulation.incoming", id=1, ack="auto")
 
print("[Monitor Agent] Listening for new regulations... Press Ctrl+C to stop.")
 
while True:
    time.sleep(1)