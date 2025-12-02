import streamlit as st
import pandas as pd
import PyPDF2
from mistralai import Mistral
import os
from io import BytesIO
import json
import re


# --------------------------------------
# CONFIGURATION
# --------------------------------------

API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = "mistral-small-2501"


# --------------------------------------
# FUNCTIONS
# --------------------------------------

def extract_pdf_text(file):
    """Extract text from PDF."""
    text = ""
    reader = PyPDF2.PdfReader(file)
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text.strip()


def clean_llm_output(output):
    """Remove markdown, comments, and extract only JSON."""
    
    # Remove code block markers
    output = output.replace("```json", "").replace("```", "").strip()

    # Extract the first JSON array using regex
    match = re.search(r"\[.*\]", output, re.DOTALL)
    if match:
        output = match.group(0)

    # Fix trailing commas
    output = re.sub(r",\s*]", "]", output)
    output = re.sub(r",\s*}", "}", output)

    return output


def call_mistral_for_kvc(text):
    """Call Mistral LLM and extract structured JSON."""
    client = Mistral(api_key=API_KEY)

    prompt = f"""
    You are an expert data extraction AI.

    OUTPUT STRICTLY JSON — NO TEXT OUTSIDE JSON.

    Format:
    [
      {{"Key": "Field Name", "Value": "Extracted Value", "Comments": "Additional context"}},
      ...
    ]

    Requirements:
    - Only output JSON.
    - the "Key" :"Field Name" should cantain this parameter First Name
    Last Name
    Date of Birth
    Birth City
    Birth State
    Age
    Blood Group
    Nationality
    Joining Date of first professional role
    Designation of first professional role
    Salary of first professional role
    Salary currency of first professional role
    Current Organization
    Current Joining Date
    Current Designation
    Current Salary
    Current Salary Currency
    Previous Organization
    Previous Joining Date
    Previous end year
    Previous Starting Designation
    High School
    12th standard pass out year
    12th overall board score
    Undergraduate degree
    Undergraduate college
    Undergraduate year
    Undergraduate CGPA
    Graduation degree
    Graduation college
    Graduation year
    Graduation CGPA
    Certifications 1
    Certifications 2
    Certifications 3
    Certifications 4
    Technical Proficiency
    - and "Value": "Extracted Value", "Comments": "Additional context" have filled information accroding to "Key": "Field Name" parameter
    - no explanations.
    - No markdown.
    - give commentary.

    Text to extract from:
    {text}
    """

    response = client.chat.complete(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content.strip()
    cleaned = clean_llm_output(raw)
    return cleaned


def convert_json_to_excel(json_text):
    """Convert JSON to Excel safely."""

    try:
        data = json.loads(json_text)
    except Exception as e:
        st.error("❌ Still invalid JSON after cleaning.\n\nJSON Returned:\n" + json_text)
        return None, None

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return df, output


# --------------------------------------
# STREAMLIT UI
# --------------------------------------

st.set_page_config(page_title="PDF → Excel Extractor", page_icon="📄", layout="centered")

st.title("📄 PDF → Excel Data Extractor ")
st.write("Upload a PDF → Extract Key–Value–Comment → Download Excel")


uploaded_pdf = st.file_uploader("📤 Upload PDF File", type=["pdf"])


if uploaded_pdf:

    if st.button("🚀 Start Processing"):
        
        with st.spinner("Extracting PDF text..."):
            pdf_text = extract_pdf_text(uploaded_pdf)

        st.success("PDF Extracted!")
        st.text_area("PDF Extracted Text (Preview)", pdf_text[:2000], height=250)

        with st.spinner("Sending to Mistral LLM..."):
            llm_json = call_mistral_for_kvc(pdf_text)

        st.success("LLM Output Received!")
        st.text_area("RAW + CLEANED JSON OUTPUT", llm_json, height=250)

        df, excel_file = convert_json_to_excel(llm_json)

        if excel_file:
            st.write("### Extracted Data Preview")
            st.dataframe(df)

            st.download_button(
                label="💾 Download Excel",
                data=excel_file,
                file_name="output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("👆 Upload a PDF to begin.")

st.markdown("---")
st.caption("Built with ❤️ using Streamlit + Mistral AI")
