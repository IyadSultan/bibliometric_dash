import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse
import pandas as pd
from typing import Optional
from datetime import datetime

class DatabaseConnection:
    """Handles database connection using environment variables"""
    
    def __init__(self):
        load_dotenv()
        
        # Database connection parameters
        self.server = os.getenv('DB_SERVER', 'aidi-db-server.database.windows.net')
        self.name = os.getenv('DB_NAME', 'IRN-DB')
        self.user = os.getenv('DB_USERNAME', 'aidiadmin')
        self.password = os.getenv('DB_PASSWORD')
        
        if not self.password:
            raise ValueError("DB_PASSWORD not found in environment variables")
        
        # Create connection string
        params = urllib.parse.quote_plus(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={self.server};'
            f'DATABASE={self.name};'
            f'UID={self.user};'
            f'PWD={self.password};'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )
        
        # Create SQLAlchemy engine
        self.engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    
    def get_connection(self):
        """Returns a database connection from the engine"""
        return self.engine.connect()

class BibliometricData:
    """Handles all bibliometric data queries"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def execute_query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn, params=params or {})
    
    def get_khcc_authors(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Get KHCC authors from the view"""
        query = f"""
        SELECT {f'TOP {limit}' if limit else ''} * 
        FROM dbo.vw_bibliometric_khcc_authors
        ORDER BY 
            paper_id,
            CASE author_position
                WHEN 'first' THEN 1
                WHEN 'middle' THEN 2
                WHEN 'last' THEN 3
                ELSE 4
            END
        """
        return self.execute_query(query)

    def get_author_metrics(self) -> pd.DataFrame:
        """Get author productivity metrics"""
        query = """
        SELECT * 
        FROM dbo.vw_bibliometric_author_productivity
        ORDER BY total_citations DESC
        """
        return self.execute_query(query)

    def get_journal_metrics(self) -> pd.DataFrame:
        """Get journal metrics"""
        query = """
        SELECT * 
        FROM dbo.vw_bibliometric_journal_metrics
        ORDER BY publication_count DESC
        """
        return self.execute_query(query)

    def get_research_topics(self) -> pd.DataFrame:
        """Get research topics analysis"""
        query = """
        SELECT * 
        FROM dbo.vw_bibliometric_research_topics
        ORDER BY papers_count DESC
        """
        return self.execute_query(query)

    def get_collaborating_institutions(self) -> pd.DataFrame:
        """Get collaborating institutions"""
        query = """
        SELECT * 
        FROM dbo.vw_bibliometric_collaborating_institutions
        ORDER BY collaboration_count DESC
        """
        return self.execute_query(query)

    def get_papers_summary(self, year: Optional[int] = None) -> pd.DataFrame:
        """Get papers summary with optional year filter"""
        query = """
        SELECT * 
        FROM dbo.vw_bibliometric_papers_summary
        """
        params = {}
        
        if year:
            query += "\nWHERE publication_year = :year"
            params['year'] = year
        
        query += "\nORDER BY publication_date DESC"
        return self.execute_query(query, params)

    def search_papers(self, search_term: str) -> pd.DataFrame:
        """Search papers by title, author, or journal"""
        query = """
        SELECT p.* 
        FROM dbo.vw_bibliometric_papers_summary p
        LEFT JOIN dbo.vw_bibliometric_khcc_authors a 
            ON p.paper_id = a.paper_id
        WHERE 
            p.title LIKE :pattern OR
            a.author_name LIKE :pattern OR
            p.journal LIKE :pattern
        """
        return self.execute_query(query, {'pattern': f'%{search_term}%'})

def test_database():
    """Test all database functionalities"""
    try:
        print("\nTesting database connection and queries...")
        biblio = BibliometricData()
        
        # Test 1: KHCC Authors
        print("\n1. Testing KHCC authors query...")
        authors = biblio.get_khcc_authors(limit=5)
        print(f"Retrieved {len(authors)} authors")
        print(authors[['author_name', 'paper_id', 'citations']].head())
        
        # Test 2: Author Metrics
        print("\n2. Testing author metrics query...")
        metrics = biblio.get_author_metrics()
        print(f"Retrieved metrics for {len(metrics)} authors")
        print(metrics[['author_name', 'total_papers', 'total_citations']].head())
        
        # Test 3: Journal Metrics
        print("\n3. Testing journal metrics query...")
        journals = biblio.get_journal_metrics()
        print(f"Retrieved metrics for {len(journals)} journals")
        
        # Test 4: Search Functionality
        print("\n4. Testing search functionality...")
        search_results = biblio.search_papers("cancer")
        print(f"Found {len(search_results)} papers matching 'cancer'")
        
        print("\nAll tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        return False

if __name__ == "__main__":
    # Ensure environment variables are set up
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("""
# Database Configuration
DB_SERVER=aidi-db-server.database.windows.net
DB_NAME=IRN-DB
DB_USERNAME=aidiadmin
DB_PASSWORD=your_password_here
            """.strip())
        print("Created .env file - please update with your database password")
    
    # Run tests
    test_database()


