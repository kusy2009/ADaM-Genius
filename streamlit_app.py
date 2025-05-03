import streamlit as st
import os
import sys
import subprocess
from dotenv import load_dotenv

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

try:
    from adamai import extract_adam_variable, generate_natural_response
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error("Please check your project setup and import paths.")
    sys.exit(1)

# Load environment variables
load_dotenv()

def main():
    st.title("ADaM Genius")
    
    # Sidebar for instructions
    st.sidebar.header("How to Use")
    st.sidebar.info(
        "Ask a natural language question about an ADaM variable. "
        "Press Enter to get details."
    )
    
    # Main input area
    query = st.text_input("What would you like to know about an ADaM variable?", 
                          placeholder="e.g., Tell me about patient age in clinical trials", 
                          key="query_input")
    
    # Process Query Automatically on Enter
    if query:
        # Extract variable
        variable = extract_adam_variable(query)
        
        if variable:
            # Display extracted variable
            st.success(f"Extracted Variable: {variable}")
            
            # Run adam_genius.py to get metadata
            try:
                result = subprocess.run(
                    ['python', 'adam_genius.py', variable], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                metadata = result.stdout
                
                # Display raw metadata
                st.subheader("Variable Metadata")
                st.code(metadata)
                
                # Generate conversational explanation
                explanation = generate_natural_response(variable, metadata)
                st.subheader("Explanation")
                st.write(explanation)
            
            except subprocess.CalledProcessError as e:
                st.error(f"Error running adam_genius.py: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
        else:
            st.warning("Could not extract a valid ADaM variable from the query.")

if __name__ == "__main__":
    main()
