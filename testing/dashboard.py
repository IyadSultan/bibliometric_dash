import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse
import pandas as pd
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger('bibliometric_dashboard')
if not logger.handlers:
    handler = logging.FileHandler(f'dashboard_{datetime.now().strftime("%Y%m%d")}.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

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
    
    def get_papers_summary(self):
        """Get papers summary with all columns"""
        query = """
        SELECT 
            paper_id, title, publication_date, publication_year, 
            publication_month, journal, impact_factor, quartile,
            citations, open_access, publication_type,
            concepts, mesh_terms
        FROM dbo.vw_bibliometric_papers_summary
        ORDER BY publication_date DESC
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(text(query), conn)
            # Convert bit to boolean
            df['open_access'] = df['open_access'].astype(bool)
            return df

    def get_research_topics(self):
        """Get research topics"""
        query = """
        SELECT 
            concept_id, concept_name, papers_count,
            avg_relevance_score, years_active
        FROM dbo.vw_bibliometric_research_topics
        """
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

    def get_collaborating_institutions(self):
        """Get collaborating institutions"""
        query = """
        SELECT 
            institution_id, institution_name, country_code,
            collaboration_count, first_collaboration_year,
            latest_collaboration_year
        FROM dbo.vw_bibliometric_collaborating_institutions
        """
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

    def get_journal_metrics(self):
        """Get journal metrics"""
        query = """
        SELECT 
            journal, quartile, impact_factor, publication_count,
            total_citations, avg_citations, open_access_count,
            first_publication_year, latest_publication_year
        FROM dbo.vw_bibliometric_journal_metrics
        WHERE journal IS NOT NULL
        """
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

    def get_author_productivity(self):
        """Get author productivity metrics"""
        query = """
        SELECT 
            author_name, total_papers, corresponding_author_count,
            total_citations, avg_citations_per_paper, active_years,
            unique_journals, years_active
        FROM dbo.vw_bibliometric_author_productivity
        """
        with self.db.get_connection() as conn:
            return pd.read_sql_query(text(query), conn)

# Initialize the app
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Load data
try:
    logger.info("Initializing database connection and loading data...")
    biblio = BibliometricData()
    
    # Load all data
    papers_df = biblio.get_papers_summary()
    research_topics_df = biblio.get_research_topics()
    collaborating_inst_df = biblio.get_collaborating_institutions()
    journal_metrics_df = biblio.get_journal_metrics()
    author_metrics_df = biblio.get_author_productivity()
    
    # Debug print
    logger.info(f"Loaded {len(papers_df)} papers")
    logger.info(f"Loaded {len(research_topics_df)} research topics")
    logger.info(f"Loaded {len(collaborating_inst_df)} collaborating institutions")
    logger.info(f"Loaded {len(journal_metrics_df)} journal metrics")
    logger.info(f"Loaded {len(author_metrics_df)} author metrics")
    
    # Create overview figures
    yearly_metrics = (
        papers_df.groupby("publication_year")
        .agg({
            "citations": ["sum", "mean", "count"],
            "open_access": "sum"
        })
        .reset_index()
    )
    yearly_metrics.columns = [
        "publication_year", "total_citations", 
        "mean_citations", "publications", "open_access_count"
    ]
    
    # Filter out invalid years and sort
    yearly_metrics = yearly_metrics[yearly_metrics["publication_year"] > 0].sort_values("publication_year")
    
    # Calculate summary statistics
    total_citations = int(papers_df['citations'].sum())
    avg_citations = papers_df['citations'].mean()
    open_access_count = int(papers_df['open_access'].sum())
    open_access_percent = (papers_df['open_access'].mean() * 100)
    
    # Create figures
    fig_pubs = px.line(
        yearly_metrics,
        x="publication_year",
        y="publications",
        title="Publications by Year",
        labels={"publication_year": "Year", "publications": "Number of Publications"},
        markers=True
    )
    
    fig_cites = px.line(
        yearly_metrics,
        x="publication_year",
        y="mean_citations",
        title="Average Citations per Publication Year",
        labels={"mean_citations": "Average Citations"},
        markers=True
    )
    
    # Add total citations line
    fig_cites.add_scatter(
        x=yearly_metrics["publication_year"],
        y=yearly_metrics["total_citations"],
        name="Total Citations",
        yaxis="y2",
        line=dict(dash="dash")
    )
    fig_cites.update_layout(
        yaxis2=dict(
            title="Total Citations",
            overlaying="y",
            side="right"
        )
    )
    
    # Create author impact figure
    fig_author_impact = px.scatter(
        author_metrics_df,
        x="total_papers",
        y="total_citations",
        hover_data=["author_name", "corresponding_author_count", "years_active"],
        title="Author Impact Analysis",
        labels={
            "total_papers": "Number of Publications",
            "total_citations": "Total Citations",
            "author_name": "Author"
        }
    ) if not author_metrics_df.empty else go.Figure()
    
    # Create journal metrics figures
    fig_quartile = px.pie(
        journal_metrics_df,
        values='publication_count',
        names='quartile',
        title='Publications by Journal Quartile'
    )
    
    fig_impact_factor = px.box(
        journal_metrics_df,
        y='impact_factor',
        title='Journal Impact Factor Distribution'
    )

except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")
    # Initialize empty DataFrames with correct columns
    papers_df = pd.DataFrame(columns=['paper_id', 'title', 'citations', 'open_access'])
    research_topics_df = pd.DataFrame(columns=['concept_id', 'concept_name', 'papers_count'])
    collaborating_inst_df = pd.DataFrame(columns=['institution_id', 'institution_name'])
    journal_metrics_df = pd.DataFrame(columns=['journal', 'impact_factor', 'publication_count'])
    author_metrics_df = pd.DataFrame(columns=[
        'author_name', 'total_papers', 'corresponding_author_count',
        'total_citations', 'avg_citations_per_paper', 'years_active'
    ])
    
    # Initialize empty statistics
    total_citations = 0
    avg_citations = 0
    open_access_count = 0
    open_access_percent = 0
    
    # Initialize empty figures
    fig_pubs = go.Figure()
    fig_cites = go.Figure()
    fig_quartile = go.Figure()
    fig_impact_factor = go.Figure()
    fig_author_impact = go.Figure()

# Define the Overview tab with error handling
tab_overview = dbc.Card(
    dbc.CardBody([
        html.H4("Publications Overview", className="card-title"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"Total Publications: {len(papers_df):,}"),
                        html.H5(f"Total Citations: {total_citations:,}"),
                        html.H5(f"Average Citations: {avg_citations:.1f}"),
                        html.H5(f"Open Access: {open_access_count:,} ({open_access_percent:.1f}%)")
                    ])
                ])
            ], md=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_pubs), md=6),
            dbc.Col(dcc.Graph(figure=fig_cites), md=6),
        ])
    ]),
    className="mt-3"
)

# Define the Authors tab with error handling
tab_authors = dbc.Card(
    dbc.CardBody([
        html.H4("Author Analysis", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5(f"Total Authors: {len(author_metrics_df):,}"),
                html.H5("Average Papers per Author: {:.1f}".format(
                    author_metrics_df['total_papers'].mean() if not author_metrics_df.empty else 0
                )),
                html.H5("Average Citations per Author: {:.1f}".format(
                    author_metrics_df['total_citations'].mean() if not author_metrics_df.empty else 0
                )),
                html.H5("Total Corresponding Author Papers: {:,}".format(
                    int(author_metrics_df['corresponding_author_count'].sum()) if not author_metrics_df.empty else 0
                ))
            ], md=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_author_impact), md=12),
        ])
    ]),
    className="mt-3"
)

# Define the Journal Metrics tab with error handling
tab_journals = dbc.Card(
    dbc.CardBody([
        html.H4("Journal Metrics", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5(f"Total Journals: {len(journal_metrics_df):,}"),
                html.H5(f"Average Impact Factor: {journal_metrics_df['impact_factor'].mean():.2f}" if 'impact_factor' in journal_metrics_df else "N/A"),
                html.H5(f"Total Publications: {journal_metrics_df['publication_count'].sum():,}" if 'publication_count' in journal_metrics_df else "N/A"),
                html.H5(f"Open Access Publications: {journal_metrics_df['open_access_count'].sum():,}" if 'open_access_count' in journal_metrics_df else "N/A")
            ], md=12)
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_quartile), md=6),
            dbc.Col(dcc.Graph(figure=fig_impact_factor), md=6),
        ])
    ]),
    className="mt-3"
)

# Update the app layout to include new tabs
app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="KHCC Publications Dashboard",
        brand_href="#",
        color="primary",
        dark=True,
        className="mb-2"
    ),
    dbc.Tabs([
        dbc.Tab(tab_overview, label="Overview", tab_id="tab-overview"),
        dbc.Tab(tab_authors, label="Authors", tab_id="tab-authors"),
        dbc.Tab(tab_journals, label="Journal Metrics", tab_id="tab-journals"),
    ]),
], fluid=True)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)