import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse
import pandas as pd
from typing import Optional, Dict, List
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
        self.views = [
            'dbo.vw_bibliometric_author_productivity',
            'dbo.vw_bibliometric_collaborating_institutions',
            'dbo.vw_bibliometric_collaborations',
            'dbo.vw_bibliometric_department_metrics',
            'dbo.vw_bibliometric_journal_metrics',
            'dbo.vw_bibliometric_khcc_authors',
            'dbo.vw_bibliometric_papers_summary',
            'dbo.vw_bibliometric_research_topics',
            'dbo.vw_bibliometric_topic_network'
        ]
    
    def execute_query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn, params=params or {})
    
    def get_view_schema(self, view_name: str) -> List[Dict]:
        """Get schema information for a specific view"""
        query = """
        SELECT 
            c.name as column_name,
            t.name as data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable
        FROM sys.columns c
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        INNER JOIN sys.objects o ON c.object_id = o.object_id
        WHERE o.name = :view_name
        ORDER BY c.column_id
        """
        # Extract view name without schema
        view_name_only = view_name.split('.')[-1]
        return self.execute_query(query, {'view_name': view_name_only}).to_dict('records')

    def analyze_all_views(self) -> Dict[str, List[Dict]]:
        """Analyze schema for all bibliometric views"""
        schemas = {}
        for view in self.views:
            print(f"Analyzing schema for {view}...")
            schemas[view] = self.get_view_schema(view)
        return schemas

    def print_schema_analysis(self, schemas: Dict[str, List[Dict]]):
        """Print formatted schema analysis with sample data"""
        for view_name, columns in schemas.items():
            print(f"\n{'=' * 100}")
            print(f"Schema for: {view_name}")
            print(f"{'=' * 100}")
            
            # Print schema information
            print("\nSCHEMA DETAILS:")
            print(f"{'Column Name':<30} {'Data Type':<15} {'Nullable':<10} {'Length/Precision':<15}")
            print(f"{'-' * 80}")
            
            for col in columns:
                length_info = str(col['max_length']) if col['max_length'] != -1 else ''
                if col['data_type'] in ('decimal', 'numeric'):
                    length_info = f"{col['precision']},{col['scale']}"
                    
                print(f"{col['column_name']:<30} "
                      f"{col['data_type']:<15} "
                      f"{'YES' if col['is_nullable'] else 'NO':<10} "
                      f"{length_info:<15}")
            
            # Get and print sample data
            try:
                query = f"SELECT TOP 2 * FROM {view_name}"
                sample_data = self.execute_query(query)
                
                if not sample_data.empty:
                    print(f"\nSAMPLE DATA (First 2 rows):")
                    print(f"{'-' * 100}")
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', None)
                    pd.set_option('display.max_colwidth', 30)
                    print(sample_data.to_string())
                    print()
            except Exception as e:
                print(f"\nError getting sample data: {str(e)}")
            
            print(f"\n{'=' * 100}")

    def save_schema_analysis(self, schemas: Dict[str, List[Dict]], filename: Optional[str] = None):
        """Save schema analysis to a CSV file"""
        all_schemas = []
        for view_name, columns in schemas.items():
            for col in columns:
                all_schemas.append({
                    'view_name': view_name,
                    'column_name': col['column_name'],
                    'data_type': col['data_type'],
                    'is_nullable': col['is_nullable'],
                    'max_length': col['max_length'],
                    'precision': col['precision'],
                    'scale': col['scale']
                })
        
        df = pd.DataFrame(all_schemas)
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'schema_analysis_{timestamp}.csv'
        
        df.to_csv(filename, index=False)
        print(f"\nSchema analysis saved to {filename}")

    # [Previous methods remain unchanged]
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
        
        # Test schema analysis
        print("\nAnalyzing database schemas...")
        schemas = biblio.analyze_all_views()
        biblio.print_schema_analysis(schemas)
        biblio.save_schema_analysis(schemas)
        
        # Previous tests remain unchanged
        print("\n1. Testing KHCC authors query...")
        authors = biblio.get_khcc_authors(limit=5)
        print(f"Retrieved {len(authors)} authors")
        print(authors[['author_name', 'paper_id', 'citations']].head())
        
        print("\n2. Testing author metrics query...")
        metrics = biblio.get_author_metrics()
        print(f"Retrieved metrics for {len(metrics)} authors")
        print(metrics[['author_name', 'total_papers', 'total_citations']].head())
        
        print("\n3. Testing journal metrics query...")
        journals = biblio.get_journal_metrics()
        print(f"Retrieved metrics for {len(journals)} journals")
        
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