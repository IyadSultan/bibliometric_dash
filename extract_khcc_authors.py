import sqlite3
import json

def create_khcc_authors_table(conn):
    """Create the khcc_authors table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS khcc_authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id TEXT,  -- Full OpenAlex URL format
        author_id TEXT, -- Full OpenAlex URL format
        author_name TEXT,
        author_position TEXT,
        is_corresponding BOOLEAN,
        UNIQUE(paper_id, author_id)
    )
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
    INSERT OR REPLACE INTO khcc_authors 
    (paper_id, author_id, author_name, author_position, is_corresponding)
    VALUES (?, ?, ?, ?, ?)
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
                    author_id = author_info.get('id', '')  # Keep full OpenAlex URL
                    author_name = author_info.get('display_name', '')
                    author_position = author.get('author_position', '')
                    is_corresponding = author.get('is_corresponding', False)
                    
                    # Insert into database
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

def main():
    # Connect to the database
    conn = sqlite3.connect('khcc_papers.sqlite')
    
    try:
        # Create table and extract data
        create_khcc_authors_table(conn)
        authors_count = extract_khcc_authors(conn)
        
        print(f"\nSuccessfully saved {authors_count} KHCC authors to khcc_authors table")
        
        # Display sample of results
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM khcc_authors 
        ORDER BY 
            paper_id,
            CASE author_position
                WHEN 'first' THEN 1
                WHEN 'middle' THEN 2
                WHEN 'last' THEN 3
                ELSE 4
            END
        LIMIT 5
        ''')
        
        print("\nSample of saved records:")
        print("ID | Paper ID | Author ID | Name | Position | Corresponding")
        print("-" * 80)
        for row in cursor.fetchall():
            print(" | ".join(str(x) for x in row))
            
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()