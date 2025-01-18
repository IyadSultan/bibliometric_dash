import os
from sqlalchemy import create_engine, text
import urllib.parse
import pandas as pd
from dotenv import load_dotenv

def test_connection():
    print("Testing database connection and queries...")
    
    # Load environment variables
    load_dotenv()
    
    # Create connection string
    params = urllib.parse.quote_plus(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={os.getenv("DB_SERVER")};'
        f'DATABASE={os.getenv("DB_NAME")};'
        f'UID={os.getenv("DB_USERNAME")};'
        f'PWD={os.getenv("DB_PASSWORD")};'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
    )
    
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    try:
        with engine.connect() as conn:
            # Test 1: KHCC authors
            print("1. Testing KHCC authors query...")
            query = text("""
                SELECT author_name, paper_id, citations
                FROM dbo.vw_bibliometric_khcc_authors
                ORDER BY citations DESC
            """)
            df = pd.read_sql(query, conn)
            print(f"Retrieved {len(df)} authors")
            print(df.head())
            
            # Test 2: Author metrics
            print("\n2. Testing author metrics query...")
            query = text("""
                SELECT author_name, total_papers, total_citations 
                FROM dbo.vw_bibliometric_author_productivity
                ORDER BY total_papers DESC
            """)
            df = pd.read_sql(query, conn)
            print(f"Retrieved metrics for {len(df)} authors")
            print(df.head())
            
            # Test 3: Journal metrics
            print("\n3. Testing journal metrics query...")
            query = text("""
                SELECT COUNT(*) as journal_count 
                FROM dbo.vw_bibliometric_journal_metrics
            """)
            result = conn.execute(query).fetchone()
            print(f"Retrieved metrics for {result[0]} journals")
            
            # Test 4: Search functionality
            print("\n4. Testing search functionality...")
            search_term = '%cancer%'
            query = text("""
                SELECT p.title, p.journal_name, p.publication_year, p.citations
                FROM dbo.vw_bibliometric_papers_summary p
                LEFT JOIN dbo.vw_bibliometric_khcc_authors a
                    ON p.paper_id = a.paper_id
                WHERE
                    p.title LIKE :search_term OR
                    a.author_name LIKE :search_term OR
                    p.journal_name LIKE :search_term
            """)
            df = pd.read_sql(query, conn, params={'search_term': search_term})
            print(f"Found {len(df)} papers matching 'cancer'")
            print(df.head())
            
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    test_connection()