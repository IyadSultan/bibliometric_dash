"""
KHCC Bibliometric Dashboard
A Dash application for visualizing bibliometric data from Azure SQL views.
"""

# -------------------------------
# 1. Imports & Constants
# -------------------------------
import os
import json
import dash
from dash import html, dcc, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import networkx as nx
from wordcloud import WordCloud
import re
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Must set before importing pyplot
import matplotlib.pyplot as plt
from collections import Counter
from sqlalchemy import create_engine, text
import urllib.parse
from dotenv import load_dotenv
import random
import itertools

# -------------------------------
# 2. Database Classes
# -------------------------------
class DatabaseConnection:
    """Handles database connection using environment variables."""
    def __init__(self):
        load_dotenv()  # Load .env file if present
        self.server = os.getenv('DB_SERVER', 'aidi-db-server.database.windows.net')
        self.name = os.getenv('DB_NAME', 'IRN-DB')
        self.user = os.getenv('DB_USERNAME', 'aidiadmin')
        self.password = os.getenv('DB_PASSWORD')

        if not self.password:
            raise ValueError("DB_PASSWORD not found in environment variables")

        # Construct ODBC connection string
        params = urllib.parse.quote_plus(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={self.server};'
            f'DATABASE={self.name};'
            f'UID={self.user};'
            f'PWD={self.password};'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )
        self.engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    def get_connection(self):
        """Return a new SQLAlchemy connection."""
        return self.engine.connect()

class BibliometricData:
    """Data access layer for bibliometric views."""
    def __init__(self):
        self.db = DatabaseConnection()

    def execute_query(self, query, params=None):
        """Execute SQL query and return DataFrame."""
        with self.db.get_connection() as conn:
            try:
                return pd.read_sql_query(text(query), conn, params=params or {})
            except Exception as e:
                print(f"Error executing query: {str(e)}")
                return pd.DataFrame()

    def get_papers_summary(self):
        """Get papers summary from Azure SQL."""
        query = """
        SELECT 
            paper_id, title, publication_date, publication_year, 
            publication_month, journal, impact_factor, quartile,
            citations, open_access, publication_type,
            concepts, mesh_terms, authorships
        FROM dbo.vw_bibliometric_papers_summary
        ORDER BY publication_date DESC
        """
        return self.execute_query(query)

    def get_khcc_authors(self):
        """Get KHCC authors data."""
        query = """
        SELECT 
            id, paper_id, author_id, author_name, author_position,
            is_corresponding, publication_year, citations,
            journal_name, quartile, open_access, impact_factor
        FROM dbo.vw_bibliometric_khcc_authors
        """
        return self.execute_query(query)

    def get_journal_metrics(self):
        """Get journal metrics."""
        query = """
        SELECT 
            journal, quartile, impact_factor, publication_count,
            total_citations, avg_citations, open_access_count,
            first_publication_year, latest_publication_year
        FROM dbo.vw_bibliometric_journal_metrics
        ORDER BY total_citations DESC
        """
        return self.execute_query(query)

    def get_collaborating_institutions(self):
        """Get institution collaboration data."""
        query = """
        SELECT 
            institution_id, institution_name, country_code,
            collaboration_count, first_collaboration_year,
            latest_collaboration_year
        FROM dbo.vw_bibliometric_collaborating_institutions
        WHERE institution_id IS NOT NULL
        ORDER BY collaboration_count DESC
        """
        return self.execute_query(query)

    def get_research_topics(self):
        """Get research topics analysis."""
        query = """
        SELECT 
            concept_id, concept_name, papers_count,
            avg_relevance_score, years_active
        FROM dbo.vw_bibliometric_research_topics
        WHERE papers_count >= 3
        ORDER BY papers_count DESC
        """
        return self.execute_query(query)

    def get_author_productivity(self):
        """Get author productivity metrics."""
        query = """
        SELECT 
            author_name, total_papers, corresponding_author_count,
            total_citations, avg_citations_per_paper, active_years,
            unique_journals, years_active
        FROM dbo.vw_bibliometric_author_productivity
        ORDER BY total_papers DESC
        """
        return self.execute_query(query)

# -------------------------------
# 3. Helper Functions
# -------------------------------
def process_authorships(row):
    """Process authorships JSON data into a comma-delimited string."""
    try:
        if pd.isna(row['authorships']) or row['authorships'] == '':
            return ''
        auth_data = json.loads(row['authorships'])
        return ', '.join([
            a['author']['display_name'] 
            for a in auth_data 
            if 'author' in a and 'display_name' in a['author']
        ])
    except:
        return ''

# -------------------------------
# 4. Data Loading
# -------------------------------
def load_data():
    """Load all bibliometric data from Azure SQL views and clean them."""
    try:
        print("\nInitializing data loading...")
        biblio = BibliometricData()
        data = {}

        # Load and clean papers data
        try:
            papers_df = biblio.get_papers_summary()
            papers_df["publication_year"] = pd.to_numeric(
                papers_df["publication_year"], errors='coerce'
            ).fillna(0).astype(int)
            papers_df["publication_month"] = pd.to_numeric(
                papers_df["publication_month"], errors='coerce'
            ).fillna(0).astype(int)
            papers_df["citations"] = pd.to_numeric(
                papers_df["citations"], errors='coerce'
            ).fillna(0).astype(int)
            papers_df["impact_factor"] = pd.to_numeric(
                papers_df["impact_factor"], errors='coerce'
            ).fillna(0).astype(float)
            papers_df["open_access"] = papers_df["open_access"].fillna(0).astype(int)
            papers_df["journal"] = papers_df["journal"].fillna("Unknown Journal")
            papers_df["journal_name"] = papers_df["journal"]
            papers_df["quartile"] = papers_df["quartile"].fillna("Unknown")
            papers_df["publication_type"] = papers_df["publication_type"].fillna("Unknown")
            data['papers'] = papers_df
            print(f"Loaded {len(papers_df)} papers.")
        except Exception as e:
            print(f"Error loading papers: {str(e)}")
            data['papers'] = pd.DataFrame()

        # Load and clean authors data
        try:
            authors_df = biblio.get_khcc_authors()
            authors_df["is_corresponding"] = authors_df["is_corresponding"].fillna(0).astype(int)
            authors_df["citations"] = pd.to_numeric(
                authors_df["citations"], errors='coerce'
            ).fillna(0).astype(int)
            authors_df["impact_factor"] = pd.to_numeric(
                authors_df["impact_factor"], errors='coerce'
            ).fillna(0).astype(float)
            authors_df["publication_year"] = pd.to_numeric(
                authors_df["publication_year"], errors='coerce'
            ).fillna(0).astype(int)
            data['authors'] = authors_df
            print(f"Loaded {len(authors_df)} author records.")
        except Exception as e:
            print(f"Error loading authors: {str(e)}")
            data['authors'] = pd.DataFrame()

        # Load and clean journal metrics data
        try:
            journal_metrics_df = biblio.get_journal_metrics()
            journal_metrics_df["impact_factor"] = pd.to_numeric(
                journal_metrics_df["impact_factor"], errors='coerce'
            ).fillna(0).astype(float)
            journal_metrics_df["publication_count"] = pd.to_numeric(
                journal_metrics_df["publication_count"], errors='coerce'
            ).fillna(0).astype(int)
            journal_metrics_df["total_citations"] = pd.to_numeric(
                journal_metrics_df["total_citations"], errors='coerce'
            ).fillna(0).astype(int)
            journal_metrics_df["avg_citations"] = pd.to_numeric(
                journal_metrics_df["avg_citations"], errors='coerce'
            ).fillna(0).astype(float)
            journal_metrics_df["open_access_count"] = pd.to_numeric(
                journal_metrics_df["open_access_count"], errors='coerce'
            ).fillna(0).astype(int)
            data['journal_metrics'] = journal_metrics_df
            print(f"Loaded metrics for {len(journal_metrics_df)} journals.")
        except Exception as e:
            print(f"Error loading journal metrics: {str(e)}")
            data['journal_metrics'] = pd.DataFrame()

        # Load other data
        try:
            data['collaborations'] = biblio.get_collaborating_institutions()
        except Exception as e:
            print(f"Error loading collaborations: {str(e)}")
            data['collaborations'] = pd.DataFrame()

        try:
            data['topics'] = biblio.get_research_topics()
        except Exception as e:
            print(f"Error loading topics: {str(e)}")
            data['topics'] = pd.DataFrame()

        try:
            data['author_productivity'] = biblio.get_author_productivity()
        except Exception as e:
            print(f"Error loading author productivity: {str(e)}")
            data['author_productivity'] = pd.DataFrame()

        print("\nData loading completed!")
        return data

    except Exception as e:
        print(f"\nCritical error during data loading: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# -------------------------------
# 5. Visualization Functions
# -------------------------------
def create_overview_figures(papers_df):
    """Create main overview figures."""
    if papers_df.empty:
        return go.Figure(), go.Figure(), go.Figure()

    # Group by year
    yearly_metrics = (
        papers_df.groupby("publication_year")
        .agg({"citations": ["sum", "mean", "count"]})
        .reset_index()
    )
    yearly_metrics.columns = ["publication_year", "total_citations", "mean_citations", "publications"]

    # Figure 1: Publications by Year
    fig_pubs = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
        x="publication_year",
        y="publications",
        title="Publications by Year",
        labels={"publication_year": "Year", "publications": "Number of Publications"},
        markers=True
    )

    # Figure 2: Citation Metrics by Year
    fig_cites = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
        x="publication_year",
        y="mean_citations",
        title="Citation Metrics by Year",
        labels={"mean_citations": "Average Citations"},
        markers=True
    )
    # Add a secondary trace for total citations
    fig_cites.add_scatter(
        x=yearly_metrics["publication_year"],
        y=yearly_metrics["total_citations"],
        name="Total Citations",
        yaxis="y2",
        line=dict(dash="dash")
    )
    fig_cites.update_layout(
        yaxis2=dict(title="Total Citations", overlaying="y", side="right")
    )

    # Figure 3: Quartile Distribution
    quartile_by_year = pd.crosstab(papers_df["publication_year"], papers_df["quartile"]).reset_index()
    known_quarts = ["Q1", "Q2", "Q3", "Q4", "Unknown"]
    for q in known_quarts:
        if q not in quartile_by_year.columns:
            quartile_by_year[q] = 0

    fig_quartile = px.bar(
        quartile_by_year,
        x="publication_year",
        y=known_quarts,
        title="Journal Quartile Distribution by Year",
        labels={"publication_year": "Year", "value": "Number of Publications", "variable": "Quartile"},
        color_discrete_sequence=['#2ecc71', '#3498db', '#f1c40f', '#e74c3c', '#95a5a6']
    )
    fig_quartile.update_layout(barmode='stack', legend_title='Quartile')

    return fig_pubs, fig_cites, fig_quartile

def create_author_figures(authors_df):
    """Create author analysis figures."""
    if authors_df.empty:
        return go.Figure(), go.Figure()

    # Aggregate data for author metrics
    author_metrics = (
        authors_df.groupby("author_name")
        .agg({
            "paper_id": "count",
            "citations": "sum",
            "is_corresponding": "sum"
        })
        .reset_index()
    )
    author_metrics.rename(columns={"paper_id": "paper_count"}, inplace=True)
    author_metrics["citations_per_paper"] = (
        author_metrics["citations"] / author_metrics["paper_count"]
    )

    # Figure 1: Author Impact Scatter
    fig_impact = px.scatter(
        author_metrics,
        x="paper_count",
        y="citations",
        size="citations_per_paper",
        color="is_corresponding",
        hover_name="author_name",
        title="Author Impact Analysis",
        labels={
            "paper_count": "Number of Papers",
            "citations": "Total Citations",
            "is_corresponding": "Times as Corresponding Author"
        }
    )

    # Figure 2: Author Position Distribution
    author_positions = (
        authors_df.groupby("author_name")["author_position"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    for pos in ["first", "middle", "last"]:
        if pos not in author_positions.columns:
            author_positions[pos] = 0
    author_positions["total_papers"] = author_positions[["first","middle","last"]].sum(axis=1)
    top_20_authors = author_positions.nlargest(20, "total_papers")

    fig_positions = go.Figure()
    for pos in ["first", "middle", "last"]:
        fig_positions.add_trace(
            go.Bar(
                name=pos.capitalize(),
                x=top_20_authors["author_name"],
                y=top_20_authors[pos]
            )
        )
    fig_positions.update_layout(
        barmode="stack",
        title="Author Position Distribution (Top 20)",
        xaxis_tickangle=45
    )

    return fig_impact, fig_positions

def create_collaboration_network(df):
    """Create a placeholder collaboration network visualization."""
    if df.empty:
        return go.Figure()

    G = nx.Graph()

    # Add nodes for each institution
    for _, row in df.iterrows():
        G.add_node(
            row['institution_name'],
            country=row['country_code'],
            weight=row['collaboration_count']
        )

    # Add edges (placeholder: ~10% random edges)
    edges = []
    for node1, node2 in itertools.combinations(G.nodes(), 2):
        if random.random() < 0.1:
            edges.append((node1, node2))
    G.add_edges_from(edges)

    # Layout
    pos = nx.spring_layout(G)

    # Edge coordinates
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Node coordinates
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        text=list(G.nodes()),
        mode='markers+text',
        hoverinfo='text',
        marker=dict(size=10),
        textposition="top center"
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        title='Institution Collaboration Network',
        hovermode='closest'
    )
    return fig

def create_topics_wordcloud(papers_df):
    """Generate a wordcloud from topics in 'papers_df'."""
    try:
        if papers_df.empty:
            return ""

        topics = []
        for _, paper in papers_df.iterrows():
            if pd.isna(paper['concepts']):
                continue
            try:
                concepts = json.loads(paper['concepts'])
                for concept in concepts:
                    # Filter by a minimum score
                    if float(concept.get('score', 0)) > 0.4:
                        topics.append(concept['display_name'])
            except:
                continue

        if topics:
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white'
            ).generate(' '.join(topics))

            # Convert to base64 image
            img = wordcloud.to_image()
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            return f'data:image/png;base64,{img_str}'

    except Exception as e:
        print(f"Error creating wordcloud: {str(e)}")

    return ""

# -------------------------------
# 6. Build the Dash App
# -------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "KHCC Bibliometric Dashboard"

# 6a. Load all data once (caching in a global variable)
data_cache = load_data()

# 6b. Create sample figures
if data_cache:
    fig_pubs, fig_cites, fig_quartiles = create_overview_figures(data_cache["papers"])
    fig_author_impact, fig_author_positions = create_author_figures(data_cache["authors"])
    fig_collab = create_collaboration_network(data_cache["collaborations"])
    img_wordcloud_src = create_topics_wordcloud(data_cache["papers"])
else:
    # Fallback if data loading fails
    fig_pubs, fig_cites, fig_quartiles = go.Figure(), go.Figure(), go.Figure()
    fig_author_impact, fig_author_positions = go.Figure(), go.Figure()
    fig_collab = go.Figure()
    img_wordcloud_src = ""

# 6c. Dash Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("KHCC Bibliometric Dashboard"), className="mt-2")
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H3("Publications by Year"),
            dcc.Graph(figure=fig_pubs)
        ], width=12),
    ]),
    dbc.Row([
        dbc.Col([
            html.H3("Citations Over the Years"),
            dcc.Graph(figure=fig_cites)
        ], width=6),
        dbc.Col([
            html.H3("Quartile Distribution by Year"),
            dcc.Graph(figure=fig_quartiles)
        ], width=6),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H3("Author Impact Analysis"),
            dcc.Graph(figure=fig_author_impact)
        ], width=6),
        dbc.Col([
            html.H3("Author Position Distribution (Top 20)"),
            dcc.Graph(figure=fig_author_positions)
        ], width=6),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H3("Collaboration Network (Placeholder)"),
            dcc.Graph(figure=fig_collab)
        ], width=8),
        dbc.Col([
            html.H3("Topic Wordcloud"),
            html.Img(src=img_wordcloud_src, style={"max-width": "100%"}),
        ], width=4),
    ], className="mb-5"),
], fluid=True)

# -------------------------------
# 7. Run the App
# -------------------------------
if __name__ == "__main__":
    app.run_server(debug=True, host='127.0.0.1', port=8050)
