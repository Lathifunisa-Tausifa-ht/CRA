import stomp, os, time

# Connect to ActiveMQ broker
conn = stomp.Connection([("localhost", 61613)])
conn.connect(wait=True)

# Folder containing your sample PDFs
pdf_folder = "sample_pdfs"

# Loop through all PDFs in the folder
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        filepath = os.path.join(pdf_folder, filename)
        with open(filepath, "rb") as f:
            pdf_bytes = f.read()

        # Send PDF as message
        conn.send(body=pdf_bytes,
                  destination="/queue/regulation.incoming",
                  headers={"filename": filename, "content-type": "application/pdf"})
        print(f"Sent {filename} to queue.")

        # Wait 10 seconds before sending the next file
        time.sleep(10)

conn.disconnect()