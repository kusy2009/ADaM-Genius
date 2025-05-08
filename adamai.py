import os
import sys
import re
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_adam_variable(query):
    """
    Use GPT to extract ADaM variable from natural language query
    
    Args:
        query (str): Natural language query about an ADaM variable
    
    Returns:
        str: Extracted ADaM variable name
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in extracting ADaM variable names from natural language queries. Always return ONLY the variable name in uppercase."},
                {"role": "user", "content": f"Extract the ADaM variable name from this query: {query}"}
            ],
            max_tokens=10
        )
        variable = response.choices[0].message.content.strip().upper()
        
        # Validate variable (must be uppercase letters)
        if re.match(r'^[A-Z]+$', variable):
            return variable
        else:
            print(f"Could not extract a valid ADaM variable from: {query}")
            return None
    
    except Exception as e:
        print(f"Error extracting variable: {e}")
        return None

def generate_natural_response(variable, query, metadata):
    """
    Use GPT to generate a conversational response based on metadata and the user query.
    
    Args:
        variable (str): ADaM variable name
        query (str): User's query about the variable
        metadata (str): Metadata retrieved for the variable
    
    Returns:
        str: Conversational explanation
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are an expert in explaining ADaM variable metadata in a friendly, "
                    "conversational manner. Your task is to read the user query and the metadata, "
                    "and then generate a response based on the metadata you fetched for the variable." 
                )},
                {"role": "user", "content": (
                    f"Here is the user's query about the ADaM variable {variable}: '{query}'\n"
                    f"Here is the metadata for the variable {variable}: {metadata}\n"
                    "Based on this information, provide a clear, very short in 2 lines, easy-to-understand answer and provide actual full {metadata} for reference"
                )}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error generating response: {e}")
        return metadata


def main():
    # Check if query is provided
    if len(sys.argv) < 2:
        print("Please provide a natural language query about an ADaM variable.")
        sys.exit(1)
    
    # Combine all arguments into a single query
    query = " ".join(sys.argv[1:])
    
    # Extract variable
    variable = extract_adam_variable(query)
    
    if not variable:
        print("Could not extract a valid ADaM variable from your query.")
        sys.exit(1)
    
    # Run adam_genius.py to get metadata
    try:
        result = subprocess.run(
            ['python', 'adam_genius.py', variable], 
            capture_output=True, 
            text=True, 
            check=True
        )
        metadata = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running adam_genius.py: {e}")
        sys.exit(1)
    
    # Generate conversational response
    conversational_response = generate_natural_response(variable, query, metadata)
    
    print("\n🤖 AI Explanation:")
    print(conversational_response)

if __name__ == "__main__":
    main()
