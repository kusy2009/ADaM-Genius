# ADaM Variable AI Assistant

## Project Overview
This project provides an AI-powered tool for exploring and understanding ADaM (Analysis Data Model) variables in clinical trials. It offers multiple interfaces to interact with variable metadata and explanations.

## Prerequisites
- Python 3.8+
- OpenAI API Key

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/kusy2009/adam-genius.git
cd adam-genius
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
CDISC_API_KEY=your_cdisc_api_key_here
```

## Project Components

### 1. Command-Line Interface (`adamai.py`)
Allows extracting and explaining ADaM variables directly from the terminal.

#### Usage
```bash
python adamai.py "Fetch vairbale metsdata for APHASE?"
```

#### Features
- Extracts ADaM variable names from natural language queries
- Generates conversational explanations
- Runs `adam_genius.py` to retrieve variable metadata

### 2. Streamlit Web Interface (`streamlit_app.py`)
An interactive web application for exploring ADaM variables.

#### Usage
```bash
streamlit run streamlit_app.py
```

#### Features
- Natural language query input
- Automatic variable extraction
- Metadata display
- Conversational explanations

### 3. Metadata Extraction (`adam_genius.py`)
Retrieves and formats metadata for specific ADaM variables.

#### Usage
```bash
python adam_genius.py ASTDTF
```

## Workflow Examples

### Scenario 1: Command-Line Variable Extraction
```bash
# Extract variable and get metadata
python adamai.py "Tell me about DTYPE variable and its associated codelists"
```

### Scenario 2: Web Interface Exploration
```bash
# Start the Streamlit web app
streamlit run streamlit_app.py

# In the web interface:
# 1. Enter a natural language query
# 2. Press Enter
# 3. View extracted variable, metadata, and explanation
```

### Scenario 3: Direct Metadata Retrieval
```bash
# Get metadata for a specific variable
python adam_genius.py ABLFL
```

## Troubleshooting
- Ensure OpenAI API key is correctly set in `.env`
- Check internet connection
- Verify Python and pip are up to date

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

