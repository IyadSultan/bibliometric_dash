import sqlite3

def drop_tables(conn):
    """Drop the existing tables if they exist."""
    cursor = conn.cursor()
    
    # Drop tables
    cursor.execute("DROP TABLE IF EXISTS authors")
    cursor.execute("DROP TABLE IF EXISTS khcc_authors")
    
    conn.commit()
    print("Tables 'authors' and 'khcc_authors' have been dropped successfully.")

def main():
    try:
        # Connect to the database
        conn = sqlite3.connect('khcc_papers.sqlite')
        
        # Drop the tables
        drop_tables(conn)
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    confirm = input("This will delete all data in 'authors' and 'khcc_authors' tables. Continue? (y/n): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("Operation cancelled.")