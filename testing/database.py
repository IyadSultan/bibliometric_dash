import pyodbc
import pandas as pd
import logging
from datetime import datetime
import json

def create_khcc_authors_table(conn):
    """Create the khcc_authors table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[khcc_authors]') AND type in (N'U'))
    BEGIN
        CREATE TABLE khcc_authors (
            id INT IDENTITY(1,1) PRIMARY KEY,
            paper_id NVARCHAR(255),  -- Full OpenAlex URL format
            author_id NVARCHAR(255), -- Full OpenAlex URL format
            author_name NVARCHAR(255),
            author_position NVARCHAR(50),
            is_corresponding BIT,
            CONSTRAINT UC_Paper_Author UNIQUE(paper_id, author_id)
        )
    END
    ''')
    conn.commit()

def extract_khcc_authors(conn):
    """Extract authors from KHCC and insert them into khcc_authors table."""
    cursor = conn.cursor()
    
    # Get all papers and their authorships
    cursor.execute('SELECT paper_id, authorships FROM papers')
    papers = cursor.fetchall()
    
    # Prepare insert statement
    insert_query = '''
    MERGE khcc_authors AS target
    USING (VALUES (?, ?, ?, ?, ?)) AS source (paper_id, author_id, author_name, author_position, is_corresponding)
    ON target.paper_id = source.paper_id AND target.author_id = source.author_id
    WHEN MATCHED THEN
        UPDATE SET 
            author_name = source.author_name,
            author_position = source.author_position,
            is_corresponding = source.is_corresponding
    WHEN NOT MATCHED THEN
        INSERT (paper_id, author_id, author_name, author_position, is_corresponding)
        VALUES (source.paper_id, source.author_id, source.author_name, source.author_position, source.is_corresponding);
    '''
    
    authors_count = 0
    for paper_id, authorships in papers:
        # Ensure paper_id has full URL format
        if not paper_id.startswith('https://openalex.org/'):
            paper_id = f'https://openalex.org/{paper_id}'
            
        # Parse authorships JSON
        try:
            authors_list = json.loads(authorships)
            
            for author in authors_list:
                # Check if author is from KHCC
                institutions = author.get('institutions', [])
                is_khcc = any(
                    inst.get('id') == 'https://openalex.org/I2799468983' 
                    for inst in institutions
                )
                
                if is_khcc:
                    # Extract author information
                    author_info = author.get('author', {})
                    author_id = author_info.get('id', '')
                    author_name = author_info.get('display_name', '')
                    author_position = author.get('author_position', '')
                    is_corresponding = author.get('is_corresponding', False)
                    
                    # Insert into database using MERGE
                    cursor.execute(insert_query, (
                        paper_id,
                        author_id,
                        author_name,
                        author_position,
                        is_corresponding
                    ))
                    authors_count += 1
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON for paper {paper_id}: {e}")
            continue
    
    conn.commit()
    return authors_count

class BibliometricData:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.logger = logging.getLogger('bibliometric_database')
        
        # Configure logging if not already configured
        if not self.logger.handlers:
            handler = logging.FileHandler(f'database_{datetime.now().strftime("%Y%m%d")}.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_connection(self):
        """Create and return a database connection"""
        try:
            return pyodbc.connect(self.connection_string)
        except pyodbc.Error as e:
            self.logger.error(f"Database connection error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise

    def get_papers_summary(self):
        """Get summary data for all papers"""
        try:
            conn = self.get_connection()
            papers_df = pd.read_sql_query("""
                SELECT 
                    paper_id,
                    title,
                    journal_name as journal,
                    impact_factor,
                    quartile,
                    citations,
                    open_access,
                    authorships,
                    abstract,
                    abstract_summary,
                    REPLACE(pdf_url, '@', '') as pdf_url,
                    type,
                    pmid,
                    publication_date,
                    keywords,
                    concepts,
                    topics,
                    YEAR(publication_date) as publication_year,
                    MONTH(publication_date) as publication_month
                FROM papers WITH (NOLOCK)
            """, conn)
            conn.close()
            return papers_df
        except Exception as e:
            self.logger.error(f"Error getting papers summary: {str(e)}")
            return pd.DataFrame()

    def get_khcc_authors(self):
        """Get data for KHCC authors"""
        try:
            conn = self.get_connection()
            authors_df = pd.read_sql_query("""
                SELECT 
                    ka.*,
                    p.citations,
                    YEAR(p.publication_date) as publication_year,
                    p.journal_name,
                    p.quartile,
                    p.open_access,
                    p.impact_factor
                FROM khcc_authors ka WITH (NOLOCK)
                JOIN papers p WITH (NOLOCK) ON ka.paper_id = p.paper_id
            """, conn)
            conn.close()
            return authors_df
        except Exception as e:
            self.logger.error(f"Error getting KHCC authors: {str(e)}")
            return pd.DataFrame()

def main():
    # Use Azure SQL connection string
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=your-server.database.windows.net;"
        "Database=your-database;"
        "UID=your-username;"
        "PWD=your-password;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )
    
    try:
        conn = pyodbc.connect(connection_string)
        
        # Create table and extract data
        create_khcc_authors_table(conn)
        authors_count = extract_khcc_authors(conn)
        
        print(f"\nSuccessfully saved {authors_count} KHCC authors to khcc_authors table")
        
        # Display sample of results
        cursor = conn.cursor()
        cursor.execute('''
        SELECT TOP 5 * FROM khcc_authors 
        ORDER BY 
            paper_id,
            CASE author_position
                WHEN 'first' THEN 1
                WHEN 'middle' THEN 2
                WHEN 'last' THEN 3
                ELSE 4
            END
        ''')
        
        print("\nSample of saved records:")
        print("ID | Paper ID | Author ID | Name | Position | Corresponding")
        print("-" * 80)
        for row in cursor.fetchall():
            print(" | ".join(str(x) for x in row))
            
    except Exception as e:
        print(f"An error occurred: {e}")
        if 'conn' in locals():
            conn.rollback()
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()