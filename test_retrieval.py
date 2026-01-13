"""
Test script to validate RAG system with sample queries.
Run this after Phase 2 completes to verify the RAG system works.
"""

import lancedb
from sentence_transformers import SentenceTransformer
import pandas as pd

# Configuration
DB_PATH = "./data/index"
TABLE_NAME = "docs"
MODEL_NAME = "BAAI/bge-large-en-v1.5"

def test_retrieval():
    print("=" * 60)
    print("🧪 Testing RAG Retrieval System")
    print("=" * 60)
    
    # 1. Load model
    print("\n🔧 Loading embedding model...")
    try:
        model = SentenceTransformer(MODEL_NAME, device='mps')
        print("✅ Model loaded on Metal GPU")
    except:
        model = SentenceTransformer(MODEL_NAME, device='cpu')
        print("✅ Model loaded on CPU")
    
    # 2. Connect to database
    print("🔧 Connecting to LanceDB...")
    db = lancedb.connect(DB_PATH)
    
    try:
        table = db.open_table(TABLE_NAME)
        print(f"✅ Connected to table: {TABLE_NAME}")
    except Exception as e:
        print(f"❌ Error: Could not open table '{TABLE_NAME}'")
        print(f"   Make sure Phase 2 has completed successfully.")
        return
    
    # 3. Get table stats
    print("\n📊 Database Statistics:")
    try:
        count = table.count_rows()
        print(f"   - Total chunks in database: {count:,}")
        
        # Sample a few records to see structure
        sample = table.to_pandas().head(3)
        print(f"   - Columns: {list(sample.columns)}")
        if 'page_number' in sample.columns:
            print(f"   - Sample page numbers: {sample['page_number'].tolist()}")
        if 'file_name' in sample.columns:
            files = sample['file_name'].unique().tolist()
            print(f"   - Sample files: {files}")
    except Exception as e:
        print(f"   Error getting stats: {e}")
    
    # 4. Test queries
    test_queries = [
        "What is the main topic of the document?",
        "Summarize the key points",
        "Tell me about the important concepts",
        "What are the main themes discussed?",
        "Describe the key information"
    ]
    
    print("\n🔍 Testing Sample Queries:\n")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: \"{query}\"")
        print("-" * 60)
        
        try:
            # Generate query embedding
            query_embedding = model.encode([query], normalize_embeddings=True)[0]
            
            # Search
            results = table.search(query_embedding).limit(3).to_pandas()
            
            # Display results
            if len(results) > 0:
                for idx, row in results.iterrows():
                    distance = row.get('_distance', 'N/A')
                    page = row.get('page_number', 'N/A')
                    chunk = row.get('chunk_index', 'N/A')
                    text = row.get('text', '')
                    
                    # Truncate text for display
                    text_preview = text[:200] + "..." if len(text) > 200 else text
                    
                    print(f"\n   Result {idx + 1}:")
                    print(f"   - Page: {page}, Chunk: {chunk}")
                    print(f"   - Distance: {distance}")
                    print(f"   - Text: {text_preview}")
            else:
                print("   ⚠️  No results found")
        
        except Exception as e:
            print(f"   ❌ Error during search: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Start the RAG server: uvicorn app.main:app --reload --port 8000")
    print("   2. Open browser: http://localhost:8000")
    print("   3. Ensure LM Studio is running with a model loaded")

if __name__ == "__main__":
    test_retrieval()
