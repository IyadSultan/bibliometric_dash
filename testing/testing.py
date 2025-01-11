import sqlite3
import pandas as pd

def analyze_khcc_papers_db():
    # Connect to the SQLite database
    conn = sqlite3.connect('khcc_papers.sqlite')
    cursor = conn.cursor()
    
    # Get schema for papers table
    print("\nPapers Table Schema:")
    cursor.execute("PRAGMA table_info(papers);")
    papers_columns = cursor.fetchall()
    for col in papers_columns:
        print(f"- {col[1]}: {col[2]}")
        
    # Get schema for khcc_authors table
    print("\nKHCC_Authors Table Schema:")
    cursor.execute("PRAGMA table_info(khcc_authors);")
    authors_columns = cursor.fetchall()
    for col in authors_columns:
        print(f"- {col[1]}: {col[2]}")
    
    # Get sample data from both tables
    print("\nSample row from papers:")
    papers_df = pd.read_sql_query("SELECT * FROM papers LIMIT 1", conn)
    print(papers_df.columns.tolist())
    
    print("\nSample row from khcc_authors:")
    authors_df = pd.read_sql_query("SELECT * FROM khcc_authors LIMIT 1", conn)
    print(authors_df.columns.tolist())
    
    conn.close()

if __name__ == "__main__":
    analyze_khcc_papers_db()
