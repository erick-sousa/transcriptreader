import streamlit as st
from bs4 import BeautifulSoup
import requests
import json
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Transcript Extractor", layout="wide")

st.title("🎙️ Transcript Extractor from HTML (Descript)")

st.markdown("Paste a Descript Publish **URL** and either press Enter or click Submit:")

# URL input triggers rerun on Enter
url = st.text_input("Descript Publish URL", placeholder="https://example.com/transcript.html", key="url_input")

# Use a session state flag to avoid reprocessing unnecessarily
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# Form-style behavior: Trigger on Enter or on Submit button click
submit_clicked = st.button("Submit")

# Trigger parsing if either:
# - Submit button clicked
# - URL was entered and Enter was pressed (i.e., url is set but not yet submitted)
if (submit_clicked or (url and not st.session_state.submitted)) and url:
    st.session_state.submitted = True  # prevent auto re-runs
    with st.spinner("Fetching and processing transcript..."):
        try:
            response = requests.get(url)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            doc_json_tag = soup.find("script", {"id": "document", "type": "application/json"})
            if not doc_json_tag:
                raise ValueError("No <script id='document'> JSON block found.")
            doc_json = json.loads(doc_json_tag.string)
        except Exception as e:
            st.error(f"Failed to load transcript:\n{e}")
            st.stop()

        # Parse transcript
        try:
            alignment = doc_json["mediaLibrary"]["mediaRefs"][0]["voiceover"]["metadata"]["alignment"]
            voices = doc_json.get("voices", [])
            speaker_names = {v["id"]: v["name"] for v in voices}

            output_lines = []
            current_speaker_id = None
            current_line = []

            for word_obj in alignment:
                word = word_obj.get("word", "")
                speaker_id = word_obj.get("speaker", {}).get("speakerId", "")

                if speaker_id != current_speaker_id:
                    if current_line:
                        output_lines.append(" ".join(current_line))
                        current_line = []
                    speaker_name = speaker_names.get(speaker_id, f"Speaker {speaker_id[:6]}")
                    output_lines.append("")  # blank line before speaker name
                    output_lines.append(speaker_name)
                    current_speaker_id = speaker_id
                current_line.append(word)

            if current_line:
                output_lines.append(" ".join(current_line))

            transcript = "\n".join(output_lines)
            st.success("Transcript loaded successfully!")

            # Export options
            

            doc = Document()
            for line in transcript.split("\n"):
                if line.strip() == "":
                    doc.add_paragraph("")
                elif line.strip().istitle() or line.strip().isupper():
                    p = doc.add_paragraph()
                    run = p.add_run(line.strip())
                    run.bold = True
                else:
                    doc.add_paragraph(line.strip())

            doc_io = BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)
            
            st.download_button("⬇️ Download as DOCX", doc_io, file_name="transcript.docx")
            st.download_button("⬇️ Download as TXT", transcript, file_name="transcript.txt")

            # Preview area
            st.markdown("### Transcript Preview")
            st.text_area("Preview", transcript, height=400, disabled=True)

        except Exception as e:
            st.error(f"Error parsing transcript:\n{e}")
