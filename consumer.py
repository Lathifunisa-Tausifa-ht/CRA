# import stomp, os, base64, time

# class PDFConsumer(stomp.ConnectionListener):
#     def on_message(self, frame):
#         filename = frame.headers.get("filename", "unknown.pdf")
#         os.makedirs("mock_folder", exist_ok=True)
#         filepath = os.path.join("mock_folder", filename)

#         pdf_bytes = base64.b64decode(frame.body)
#         with open(filepath, "wb") as f:
#             f.write(pdf_bytes)

#         print(f"Saved: {filepath}")

# conn = stomp.Connection([("localhost", 61613)])
# conn.set_listener("", PDFConsumer())
# conn.connect(wait=True)
# conn.subscribe(destination="/queue/regulation.incoming", id=1, ack="auto")

# print("Listening... Press Ctrl+C to stop.")

# # Keep alive
# while True:
#     time.sleep(1)


import stomp, os, base64, time
from PyPDF2 import PdfReader   # parser library

class PDFConsumer(stomp.ConnectionListener):
    def on_message(self, frame):
        filename = frame.headers.get("filename", "unknown.pdf")
        os.makedirs("mock_folder", exist_ok=True)
        filepath = os.path.join("mock_folder", filename)

        # Save PDF
        pdf_bytes = base64.b64decode(frame.body)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        print(f"Saved: {filepath}")

        # Parse PDF immediately
        try:
            reader = PdfReader(filepath)
            text = "\n".join(
                page.extract_text() for page in reader.pages if page.extract_text()
            )
            print(f"Extracted text preview from {filename}:\n{text[:500]}...\n")
            print(f"Completed parsing {filename}........\n")
            print("COmplete Text Below", text)
        except Exception as e:
            print(f"Error parsing {filename}: {e}")

# Connect and subscribe
conn = stomp.Connection([("localhost", 61613)])
conn.set_listener("", PDFConsumer())
conn.connect(wait=True)
conn.subscribe(destination="/queue/regulation.incoming", id=1, ack="auto")

print("Listening... Press Ctrl+C to stop.")

# Keep alive
while True:
    time.sleep(1)
    