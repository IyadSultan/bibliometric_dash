# ... (keep existing imports) ...
import os  # Add this import at the top

def inspect_database():
    """Debug function to inspect database schema"""
    try:
        print("\nInspecting database schema...")
        biblio = BibliometricData()
        
        with biblio.db.get_connection() as conn:
            # Get all views
            views_query = """
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.VIEWS 
                WHERE TABLE_NAME LIKE 'vw_bibliometric%'
            """
            views_df = pd.read_sql(views_query, conn)
            print("\nAvailable views:")
            print(views_df)
            
            # For each view, get its columns
            for view_name in views_df['TABLE_NAME']:
                columns_query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{view_name}'
                """
                columns_df = pd.read_sql(columns_query, conn)
                print(f"\nColumns in {view_name}:")
                print(columns_df)
                
            # Get sample data from papers summary view
            sample_query = """
                SELECT TOP 1 * 
                FROM vw_bibliometric_papers_summary
            """
            sample_df = pd.read_sql(sample_query, conn)
            print("\nSample data columns:")
            print(sample_df.columns.tolist())
            
            return sample_df
            
    except Exception as e:
        print(f"Error in inspect_database: {str(e)}")
        return None

# Modify load_data function to include debugging
def load_data():
    """Load bibliometric data from Azure SQL views."""
    try:
        print("\nInitializing data loading...")
        biblio = BibliometricData()
        
        # Load papers summary
        papers_df = biblio.get_papers_summary()
        print(f"Loaded {len(papers_df)} papers.")
        print("\nColumns in papers_df:")
        print(papers_df.columns.tolist())
        
        # Check for missing columns
        required_columns = ['publication_year', 'citations', 'journal_name', 'quartile']
        missing_columns = [col for col in required_columns if col not in papers_df.columns]
        if missing_columns:
            print(f"\nWARNING: Missing required columns: {missing_columns}")
        
        return papers_df
        
    except Exception as e:
        print(f"Error in load_data: {str(e)}")
        return pd.DataFrame()

# Add this before creating figures
print("\nInspecting database...")
sample_df = inspect_database()

# Then load data
papers_df = load_data()

# Check if papers_df is empty before creating figures
if papers_df.empty:
    print("Error: No data loaded. Cannot create figures.")
else:
    fig_pubs, fig_cites, fig_quartile_trend = create_figures(papers_df)