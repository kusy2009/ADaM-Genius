# ADaM Genius: AI Assistant for CDISC ADaM

## Project Overview
This project provides an AI-powered toolkit for exploring and understanding the CDISC Analysis Data Model (ADaM) used in clinical trials. It offers multiple ways to interact with ADaM information, combining direct CDISC Library API access for precise metadata with Retrieval-Augmented Generation (RAG) for broader questions based on the ADaM Implementation Guide (ADaMIG) document.

**Two Main Components:**

1.  **API-Based Metadata Assistant (`adamai.py`, `adam_genius.py`, `streamlit_app.py`):**
    *   Uses natural language queries to fetch specific ADaM variable metadata (label, type, codelist, etc.) directly from the official CDISC Library API.
    *   Leverages AI (OpenAI) to interpret queries and format the authoritative API results into user-friendly explanations.
    *   Accessible via command-line (`adamai.py`) or a Streamlit web interface (`streamlit_app.py`).

2.  **RAG-Based Document Q&A (`adamrag.py`):**
    *   Answers natural language questions about ADaM principles, implementation guidance, and examples based on the content of a local ADaMIG PDF document.
    *   Uses LlamaIndex and RAG to retrieve relevant text sections from the document and synthesize answers.
    *   Accessible via command-line (`adamrag.py`).

This combination allows users to get both precise, live metadata via the API and contextual understanding from the official guidance document.

## Prerequisites

*   Python 3.8+
*   OpenAI API Key
*   CDISC Library API Key (for API-based features)
*   ADaM Implementation Guide PDF (e.g., `ADaMIG_v1.3.pdf`) (for RAG-based features)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/kusy2009/ADaM-Genius.git
cd ADaM-Genius
```

### 2. Create a Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
Install requirements for both the API assistant and the RAG component:
```bash
# pip install -r requirements_rag.txt 
```
*(Note: You may need to adjust the requirements file(s) based on the specific libraries used by `adamrag.py` and its dependencies.)*

### 4. Set Up Environment Variables
Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
CDISC_API_KEY=your_cdisc_api_key_here
```

### 5. Prepare Data for RAG
Create a directory (e.g., `data`) in the project root and place your ADaMIG PDF file inside it.
```bash
mkdir data
cp /path/to/your/ADaMIG_v1.3.pdf data/
```

## Usage

### 1. API-Based Metadata Assistant

**Command-Line (`adamai.py`):**
Ask about specific variable metadata.
```bash
python adamai.py "Tell me about DTYPE variable and its associated codelists"
python adamai.py "What is the definition of ABLFL?"
```

**Streamlit Web Interface (`streamlit_app.py`):**
Start the interactive web app.
```bash
streamlit run streamlit_app.py
```
Navigate to the provided URL in your browser, type your query about variable metadata, and view the results.

**Direct Metadata Retrieval (`adam_genius.py`):**
Get raw metadata for a specific variable (used internally by `adamai.py`).
```bash
python adam_genius.py ABLFL
```

### 2. RAG-Based Document Q&A (`adamrag.py`)

Ask questions about the content of the ADaMIG PDF.
```bash
# Ensure ADaMIG PDF is in the 'data' directory (or specify --data-dir)
python adamrag.py "Explain the purpose of ADSL"
python adamrag.py --data-dir /path/to/pdf/folder "What are fundamental principles of adam standard"
```

## Workflow Examples

*   **Need specific codelist for DTYPE?** Use `adamai.py` or the Streamlit app: `python adamai.py "Get codelist for DTYPE"`
*   **Need to understand the difference between ADSL and BDS?** Use `adamrag.py`: `python adamrag.py "Explain the difference between ADSL and BDS structures"`
*   **Need the definition and data type of PARAMCD?** Use `adamai.py` or the Streamlit app: `streamlit run streamlit_app.py` (then query `PARAMCD`)
*   **Need guidance on implementing population flags?** Use `adamrag.py`: `python adamrag.py "How should population flags be implemented?"`

## Troubleshooting

*   Ensure API keys (`OPENAI_API_KEY`, `CDISC_API_KEY`) are correctly set in `.env`.
*   Verify the ADaMIG PDF is in the correct directory (`data` by default) for `adamrag.py`.
*   Check internet connection (required for OpenAI and CDISC API calls).
*   Ensure all dependencies from `requirements.txt` (and any RAG requirements) are installed in your virtual environment.
*   Verify Python and pip are up to date.

## Contributing

1.  Fork the repository
2.  Create a feature branch
3.  Commit your changes
4.  Push to the branch
5.  Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

