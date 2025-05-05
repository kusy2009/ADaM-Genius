#!/usr/bin/env python3
import argparse
import dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

def build_index(data_dir: str = "data") -> VectorStoreIndex:
    """
    Load documents from `data_dir` and build an index.
    """
    dotenv.load_dotenv()
    documents = SimpleDirectoryReader(data_dir).load_data()
    return VectorStoreIndex.from_documents(documents)

def main():
    parser = argparse.ArgumentParser(
        description="Query a LlamaIndex RAG index from the command line"
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="The question you want to ask the index (wrap multi-word queries in quotes)"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to the directory containing your documents (default: data)"
    )
    args = parser.parse_args()

    # Join the list of words into a single query string
    query_text = " ".join(args.query)

    # Build the index and run the query
    index = build_index(data_dir=args.data_dir)
    query_engine = index.as_query_engine()
    response = query_engine.query(query_text)

    # Print out the response
    print(response)

if __name__ == "__main__":
    main()
