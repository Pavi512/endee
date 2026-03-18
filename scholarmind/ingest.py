import os
import glob
from data_loader import process_document
from endee_client import vector_store

def main():
    sample_docs_dir = os.path.join(os.path.dirname(__file__), "sample_docs")
    files = glob.glob(os.path.join(sample_docs_dir, "*.*"))
    
    total_chunks = 0
    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"Loading {filename}...")
        records = process_document(filepath, category="ai_ml", filename=filename)
        if records:
            count = vector_store.upsert_chunks(records)
            print(f"Successfully indexed {count} chunks for {filename}.\n")
            total_chunks += count
            
    print(f"Ingestion complete. Total chunks in vector database: {total_chunks}")
    print(vector_store.get_stats())

if __name__ == "__main__":
    # Ensure index exists before inserting
    vector_store.ensure_index()
    main()
