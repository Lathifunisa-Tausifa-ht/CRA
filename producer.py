import sys, stomp, base64

filepath = sys.argv[1]
filename = filepath.split("/")[-1]

conn = stomp.Connection([("localhost", 61613)])
conn.connect(wait=True)

with open(filepath, "rb") as f:
    pdf_bytes = f.read()

pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

conn.send(body=pdf_b64,
          destination="/queue/regulation.incoming",
          headers={"filename": filename, "content-type": "application/pdf"})
conn.disconnect()

print(f"Sent {filename} to queue.")