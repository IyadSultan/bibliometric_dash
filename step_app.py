"""
KHCC Bibliometric Dashboard (Aligned with Current Schema)
Combined Dash application merging old/new features, referencing the
actual columns in your vw_bibliometric_* views on Azure.
"""

# ------------------------------------------------------------------------------
# 1. Imports & Setup
# ------------------------------------------------------------------------------
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
from collections import Counter
import pycountry
from wordcloud import WordCloud
import re
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
import urllib.parse
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# 2. Database Connection Classes
# ------------------------------------------------------------------------------
class DatabaseConnection:
    """Handles database connection to Azure SQL, using environment variables."""
    def __init__(self):
        load_dotenv()
        self.server = os.getenv('DB_SERVER', 'aidi-db-server.database.windows.net')
        self.name   = os.getenv('DB_NAME',   'IRN-DB')
        self.user   = os.getenv('DB_USERNAME','aidiadmin')
        self.password = os.getenv('DB_PASSWORD')

        if not self.password:
            raise ValueError("DB_PASSWORD not found in environment variables")

        params = urllib.parse.quote_plus(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.name};"
            f"UID={self.user};"
            f"PWD={self.password};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )
        self.engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    def get_connection(self):
        return self.engine.connect()


class BibliometricData:
    """
    Loads data from your Azure SQL views: 
      - vw_bibliometric_papers_summary
      - vw_bibliometric_khcc_authors
      - vw_bibliometric_journal_metrics
      - vw_bibliometric_research_topics
      - vw_bibliometric_author_productivity
      - vw_bibliometric_collaborating_institutions
      - vw_bibliometric_collaborations
      etc.
    """
    def __init__(self):
        self.db = DatabaseConnection()

    def _safe_json_loads(self, x):
        """Safely load JSON string with fallback to None."""
        if pd.isna(x) or not x:
            return None
        try:
            return json.loads(x)
        except:
            return None

    def get_papers_summary(self):
        """
        Fields from vw_bibliometric_papers_summary:
          paper_id, title, publication_date, publication_year, publication_month,
          journal, impact_factor, quartile, citations, open_access,
          publication_type, authors_text, concepts_text, mesh_terms_text,
          authorships_json, concepts_json, mesh_json
        """
        query = """
            SELECT 
                paper_id, 
                title, 
                publication_date, 
                publication_year,
                publication_month, 
                journal, 
                impact_factor, 
                quartile, 
                citations,
                open_access, 
                publication_type,
                authors_text,
                concepts_text,
                mesh_terms_text,
                authorships_json,
                concepts_json,
                mesh_json
            FROM vw_bibliometric_papers_summary
            ORDER BY publication_date DESC
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql(query, conn)
        
        # Clean up numeric fields
        df['publication_year'] = df['publication_year'].fillna(0).astype(int)
        df['publication_month'] = df['publication_month'].fillna(0).astype(int)
        df['journal'] = df['journal'].fillna('Unknown Journal')
        df['impact_factor'] = df['impact_factor'].fillna(0.0)
        df['quartile'] = df['quartile'].fillna('Unknown')
        df['citations'] = df['citations'].fillna(0)
        df['open_access'] = df['open_access'].fillna(0)
        
        # Parse JSON fields for detailed views
        df['authorships'] = df['authorships_json'].apply(self._safe_json_loads)
        df['concepts'] = df['concepts_json'].apply(self._safe_json_loads)
        df['mesh_terms'] = df['mesh_json'].apply(self._safe_json_loads)
        
        # Use pre-computed text fields
        df['authors'] = df['authors_text']
        df['concepts_display'] = df['concepts_text']
        df['mesh_terms_display'] = df['mesh_terms_text']
        
        return df

    def get_khcc_authors(self):
        """
        Fields in vw_bibliometric_khcc_authors:
          id, paper_id, author_id, author_name, author_position, is_corresponding,
          publication_year, citations, journal_name, quartile, open_access, impact_factor
        """
        query = """
            SELECT id, paper_id, author_id, author_name, author_position,
                   is_corresponding, publication_year, citations, journal_name,
                   quartile, open_access, impact_factor
            FROM vw_bibliometric_khcc_authors
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql(query, conn)
        df['is_corresponding'] = df['is_corresponding'].fillna(False).astype(bool)
        df['quartile']         = df['quartile'].fillna('Unknown')
        df['journal_name']     = df['journal_name'].fillna('Unknown Journal')
        df['impact_factor']    = df['impact_factor'].fillna(0.0)
        df['citations']        = df['citations'].fillna(0)
        return df

    def get_journal_metrics(self):
        """
        Fields in vw_bibliometric_journal_metrics:
          journal, quartile, impact_factor, publication_count, total_citations,
          avg_citations, open_access_count, first_publication_year,
          latest_publication_year
        """
        query = """
            SELECT journal, quartile, impact_factor, publication_count,
                   total_citations, avg_citations, open_access_count,
                   first_publication_year, latest_publication_year
            FROM vw_bibliometric_journal_metrics
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def get_research_topics(self):
        """
        Fields in vw_bibliometric_research_topics:
          concept_id, concept_name, papers_count, avg_relevance_score,
          years_active (and others if present).
        """
        query = """
            SELECT concept_id, concept_name, papers_count, avg_relevance_score,
                   years_active
            FROM vw_bibliometric_research_topics
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def get_author_productivity(self):
        """
        Fields in vw_bibliometric_author_productivity:
          author_name, total_papers, corresponding_author_count, total_citations,
          avg_citations_per_paper, active_years, unique_journals, years_active
        """
        query = """
            SELECT author_name, total_papers, corresponding_author_count,
                   total_citations, avg_citations_per_paper, active_years,
                   unique_journals, years_active
            FROM vw_bibliometric_author_productivity
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def get_collaborating_institutions(self):
        """
        Fields in vw_bibliometric_collaborating_institutions:
          institution_id, institution_name, country_code, collaboration_count,
          first_collaboration_year, latest_collaboration_year
        """
        query = """
            SELECT institution_id, institution_name, country_code,
                   collaboration_count, first_collaboration_year,
                   latest_collaboration_year
            FROM vw_bibliometric_collaborating_institutions
        """
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def get_collaborations(self):
        """
        Fields in vw_bibliometric_collaborations:
        author1, author2, collaboration_count, collaboration_years,
        dept1_list, dept2_list, dept_collaboration_count, collaboration_type
        """
        try:
            query = """
                SELECT author1, author2, collaboration_count, collaboration_years,
                    dept1_list, dept2_list, dept_collaboration_count,
                    collaboration_type
                FROM vw_bibliometric_collaborations
                WHERE collaboration_count > 0
            """
            with self.db.get_connection() as conn:
                df = pd.read_sql(query, conn)
                
            # Clean up the data
            df['dept1_list'] = df['dept1_list'].fillna('Unknown')
            df['dept2_list'] = df['dept2_list'].fillna('Unknown')
            df['dept_collaboration_count'] = df['dept_collaboration_count'].fillna(0).astype(int)
            df['collaboration_count'] = df['collaboration_count'].fillna(0).astype(int)
            df['collaboration_years'] = df['collaboration_years'].fillna('')
            df['collaboration_type'] = df['collaboration_type'].fillna('coauthor')
            
            # Convert collaboration_years string to list of years
            df['years_list'] = df['collaboration_years'].apply(
                lambda x: sorted([int(y) for y in x.split(',')]) if x else []
            )
            
            # Add additional metrics
            df['first_collaboration'] = df['years_list'].apply(lambda x: min(x) if x else None)
            df['latest_collaboration'] = df['years_list'].apply(lambda x: max(x) if x else None)
            df['collaboration_span'] = df['years_list'].apply(lambda x: len(set(x)) if x else 0)
        
            return df
            
        except Exception as e:
            print(f"Warning: Collaboration query failed: {e}")
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'author1', 'author2', 'collaboration_count', 'collaboration_years',
                'dept1_list', 'dept2_list', 'dept_collaboration_count',
                'collaboration_type', 'years_list', 'first_collaboration',
                'latest_collaboration', 'collaboration_span'
            ])


# Add this right after the class definitions and before load_data()
def extract_collaborations_from_papers(papers_df):
    """Extract collaboration data from papers dataframe."""
    institution_collaborations = []
    country_collaborations = []
    
    for _, paper in papers_df.iterrows():
        authorships = paper.get('authorships')
        if not isinstance(authorships, list):
            try:
                authorships = json.loads(authorships) if authorships else []
            except:
                continue
                
        # Get KHCC and non-KHCC institutions/countries for this paper
        external_institutions = []
        external_countries = []
        
        for authorship in authorships:
            institutions = authorship.get('institutions', [])
            is_khcc = False
            
            # Check if author is from KHCC
            for inst in institutions:
                if inst.get('display_name') == "King Hussein Cancer Center":
                    is_khcc = True
                    break
            
            # If not KHCC, collect institution and country
            if not is_khcc:
                for inst in institutions:
                    inst_name = inst.get('display_name')
                    country_code = inst.get('country_code')
                    
                    if inst_name and inst_name != "King Hussein Cancer Center":
                        external_institutions.append(inst_name)
                    if country_code:
                        external_countries.append(country_code)
        
        # Add collaborations for this paper
        for inst in set(external_institutions):
            institution_collaborations.append({
                'institution': inst,
                'collaboration_count': 1
            })
            
        for country in set(external_countries):
            country_collaborations.append({
                'country_code': country,
                'collaboration_count': 1
            })
    
    # Aggregate collaboration counts
    inst_df = pd.DataFrame(institution_collaborations)
    country_df = pd.DataFrame(country_collaborations)
    
    if not inst_df.empty:
        inst_df = inst_df.groupby('institution')['collaboration_count'].sum().reset_index()
    if not country_df.empty:
        country_df = country_df.groupby('country_code')['collaboration_count'].sum().reset_index()
        
    return inst_df, country_df
# ------------------------------------------------------------------------------
# 3. Data Loading & Caching
# ------------------------------------------------------------------------------
def load_data():
    biblio = BibliometricData()
    data = {}
    try:
        data['papers'] = biblio.get_papers_summary()
        data['authors'] = biblio.get_khcc_authors()
        data['journals'] = biblio.get_journal_metrics()
        data['topics'] = biblio.get_research_topics()
        data['author_productivity'] = biblio.get_author_productivity()
        
        # Extract collaborations directly from papers
        inst_df, country_df = extract_collaborations_from_papers(data['papers'])
        data['institution_collaborations'] = inst_df
        data['country_collaborations'] = country_df
            
    except Exception as e:
        print(f"Error loading data: {e}")
        raise
    return data

data_cache = load_data()

# "papers_df" and "authors_df" for convenience
papers_df  = data_cache['papers'].copy()
authors_df = data_cache['authors'].copy()

# ------------------------------------------------------------------------------
# 4. Figures & Transformations
# ------------------------------------------------------------------------------
# 4.1 Basic transformations
papers_df["publication_year"]  = papers_df["publication_year"].fillna(0).astype(int)
papers_df["publication_month"] = papers_df["publication_month"].fillna(0).astype(int)
papers_df["citations"]         = papers_df["citations"].fillna(0)
papers_df["journal"]           = papers_df["journal"].fillna("Unknown Journal")
papers_df["quartile"]          = papers_df["quartile"].fillna("Unknown")
papers_df["impact_factor"]     = papers_df["impact_factor"].fillna(0)
papers_df["open_access"]       = papers_df["open_access"].fillna(0)

def create_overview_figures(df):
    yearly_metrics = (
        df.groupby("publication_year")
        .agg({"citations": ["sum","mean","count"]})
        .reset_index()
    )
    yearly_metrics.columns = ["publication_year","total_citations","mean_citations","publications"]

    fig_pubs = px.line(
        yearly_metrics[yearly_metrics["publication_year"]>0],
        x="publication_year",
        y="publications",
        title="Publications by Year",
        labels={"publication_year":"Year","publications":"Number of Publications"},
        markers=True
    )
    fig_cites = px.line(
        yearly_metrics[yearly_metrics["publication_year"]>0],
        x="publication_year",
        y="mean_citations",
        title="Average Citations per Publication Year",
        labels={"mean_citations":"Average Citations"},
        markers=True
    )
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
    return fig_pubs, fig_cites

fig_pubs, fig_cites = create_overview_figures(papers_df)

if not authors_df.empty:
    # group by author
    author_metrics = (
        authors_df.groupby("author_name")
        .agg({
            "paper_id": "nunique",  # count unique papers
            "citations": "sum",
            "is_corresponding": "sum"
        })
        .reset_index()
        .rename(columns={
            "paper_id": "paper_count",
            "is_corresponding": "corresponding_count"
        })
    )
    author_metrics["citations_per_paper"] = (
        author_metrics["citations"] / author_metrics["paper_count"]
    )

    fig_author_impact = px.scatter(
        author_metrics,
        x="paper_count",
        y="citations",
        size="citations_per_paper",
        color="corresponding_count",
        hover_name="author_name",
        title="Author Impact Analysis",
        labels={
            "paper_count": "Number of Papers",
            "citations": "Total Citations",
            "corresponding_count": "Times as Corresponding Author"
        }
    )

    # position distribution
    author_pos_counts = (
        authors_df.groupby(["author_name", "author_position"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for pos in ["first", "middle", "last", "unknown"]:
        if pos not in author_pos_counts.columns:
            author_pos_counts[pos] = 0
    author_pos_counts["total_papers"] = author_pos_counts[["first", "middle", "last", "unknown"]].sum(axis=1)
    top_20_authors = author_pos_counts.nlargest(20, "total_papers")

    fig_author_positions = go.Figure()
    for pos in ["first", "middle", "last", "unknown"]:
        if pos in top_20_authors.columns:
            fig_author_positions.add_trace(
                go.Bar(
                    name=pos.capitalize(),
                    x=top_20_authors["author_name"],
                    y=top_20_authors[pos]
                )
            )
    fig_author_positions.update_layout(
        barmode="stack",
        title="Author Position Distribution (Top 20)",
        xaxis_tickangle=45
    )
else:
    fig_author_impact = px.scatter(title="No Author Data Available")
    fig_author_positions = go.Figure().add_annotation(
        text="No Author Data Available", showarrow=False
    )

# Journal & Open Access distributions
quartile_counts = papers_df["quartile"].value_counts()
fig_quartile = px.pie(
    values=quartile_counts.values,
    names=quartile_counts.index,
    title="Journal Quartile Distribution"
)

fig_impact_factor = px.histogram(
    papers_df[papers_df["impact_factor"]>0],
    x="impact_factor",
    title="Impact Factor Distribution",
    nbins=20
)

open_access_counts = papers_df["open_access"].value_counts()
if len(open_access_counts)==2:
    fig_open_access = px.pie(
        names=["Open Access" if x==1 else "Closed Access" for x in open_access_counts.index],
        values=open_access_counts.values,
        title="Open Access Distribution"
    )
else:
    fig_open_access = px.pie(title="Open Access Distribution (No data)")

# Collaboration figures, etc.
def extract_institutions_and_countries(authorships):
    if not authorships: return [], []
    if isinstance(authorships, str):
        try: authorships = json.loads(authorships)
        except: return [],[]
    institutions, countries = [], []
    for a in authorships:
        is_khcc = False
        if 'institutions' in a:
            for inst in a['institutions']:
                if inst.get('display_name')=="King Hussein Cancer Center":
                    is_khcc = True
                    break
                institutions.append(inst.get('display_name','Unknown Inst'))
        if (not is_khcc) and ('countries' in a):
            countries.extend(a['countries'])
    return institutions, countries

def extract_external_authors(authorships):
    if not authorships: return []
    if isinstance(authorships, str):
        try: authorships = json.loads(authorships)
        except: return []
    externals = []
    for a in authorships:
        is_khcc = False
        if 'institutions' in a:
            for inst in a['institutions']:
                if inst.get('display_name')=="King Hussein Cancer Center":
                    is_khcc = True
                    break
        if not is_khcc and 'author' in a:
            externals.append(a['author'].get('display_name','Unknown'))
    return externals

def create_frequency_charts():
    all_institutions = []
    all_countries    = []
    all_ext_authors  = []

    for _, row in papers_df.iterrows():
        auth = row.get('authorships',None)
        inst, ctries = extract_institutions_and_countries(auth)
        extauths     = extract_external_authors(auth)
        # Exclude KHCC itself from institutions
        inst = [i for i in inst if i!="King Hussein Cancer Center"]
        all_institutions.extend(inst)
        all_countries.extend(ctries)
        all_ext_authors.extend(extauths)

    inst_counts = Counter(all_institutions)
    country_counts = Counter(all_countries)
    author_counts = Counter(all_ext_authors)

    # Top 20 external authors
    author_df = (pd.DataFrame
        .from_dict(author_counts, orient='index', columns=['count'])
        .reset_index().rename(columns={'index':'Author'})
        .nlargest(20, 'count'))
    fig_authors = px.bar(
        author_df,
        x='count',y='Author',
        orientation='h',
        title='Top 20 External Collaborating Authors'
    )
    fig_authors.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=600
    )

    # Institutions
    inst_df = (pd.DataFrame
        .from_dict(inst_counts, orient='index', columns=['count'])
        .reset_index().rename(columns={'index':'Institution'})
        .nlargest(20,'count'))
    fig_inst = px.bar(
        inst_df,
        x='count', y='Institution',
        orientation='h',
        title='Top 20 Collaborating Institutions'
    )
    fig_inst.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=600
    )

    # Countries
    country_df = (pd.DataFrame
        .from_dict(country_counts, orient='index', columns=['count'])
        .reset_index().rename(columns={'index':'Country'})
        .nlargest(20,'count'))
    iso_map={}
    for c in country_df['Country']:
        try:
            co = pycountry.countries.get(alpha_2=c)
            if co: iso_map[c]=co.alpha_3
        except:
            pass
    country_df['ISO3']= country_df['Country'].map(iso_map)
    fig_map = px.choropleth(
        country_df,
        locations='ISO3',
        color='count',
        hover_name='Country',
        color_continuous_scale='Viridis',
        title='Global Research Collaboration Network (Top 20 Countries)'
    )
    fig_map.update_layout(
        height=600,
        geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular')
    )

    fig_country = px.bar(
        country_df,
        x='count',y='Country',
        orientation='h',
        title='Top 20 Collaborating Countries'
    )
    fig_country.update_layout(
        yaxis={'categoryorder':'total ascending'},
        height=600
    )

    return fig_inst, fig_country, fig_map, fig_authors

fig_inst, fig_country, fig_map, fig_authors = create_frequency_charts()

def create_sankey_diagram():
    """
    Create a simplified Sankey diagram if collaboration data is unavailable.
    """
    # Create an empty figure with a message if no data
    if data_cache['collaboration_network'].empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Collaboration network data unavailable",
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title="Author Collaboration Network (Data Unavailable)",
            height=600,
            width=800
        )
        return fig
    
    # Original Sankey diagram code here if data is available
    khcc_pairs = []
    all_khcc   = set()
    for _, row in papers_df.iterrows():
        auth = row.get('authorships')
        if not auth: continue
        if isinstance(auth,str):
            try: auth = json.loads(auth)
            except: continue
        khcc_list = []
        ext_list  = []
        for a in auth:
            is_khcc=False
            if 'institutions' in a:
                for inst in a['institutions']:
                    if inst.get('display_name')=="King Hussein Cancer Center":
                        is_khcc=True
                        break
            if is_khcc:
                khcc_list.append(a['author'].get('display_name','KHCC Unknown'))
                all_khcc.add(khcc_list[-1])
            else:
                ext_list.append(a['author'].get('display_name','External Unknown'))
        for kh in khcc_list:
            for ex in ext_list:
                khcc_pairs.append((kh,ex))

    c = Counter(khcc_pairs)
    # top 10 khcc
    khcc_count = Counter(kh for (kh,ex) in khcc_pairs)
    top_khcc = [a for (a,_) in khcc_count.most_common(10)]
    # among these, top 10 external
    ext_count = Counter()
    for (k,e) in khcc_pairs:
        if k in top_khcc:
            ext_count[e]+=1
    top_ext = [ex for (ex,_) in ext_count.most_common(10)]

    nodes = top_khcc + top_ext
    idx_map = {n:i for i,n in enumerate(nodes)}
    sources, targets, values = [], [], []
    for (k,e),val in c.items():
        if (k in top_khcc) and (e in top_ext):
            sources.append(idx_map[k])
            targets.append(idx_map[e])
            values.append(val)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=50,
            thickness=20,
            line=dict(color="black",width=0.5),
            label=nodes,
            color=["#1f77b4"]*len(top_khcc)+["#ff7f0e"]*len(top_ext)
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        ),
        arrangement="snap"
    )])
    fig.update_layout(
        title="Top 10 KHCC Researchers (blue) & Top 10 External Collaborators (orange)",
        font=dict(size=12),
        height=600,width=800,
        margin=dict(l=150,r=150,t=50,b=50)
    )
    return fig


def create_institution_country_sankeys():
    """Create Sankey diagrams for institution and country collaborations."""
    # Extract collaboration data from papers
    inst_df, country_df = extract_collaborations_from_papers(papers_df)
    
    if inst_df.empty or country_df.empty:
        return create_empty_figure("Institution Network"), create_empty_figure("Country Network")
    
    # Create institution Sankey
    top_institutions = inst_df.nlargest(20, 'collaboration_count')
    inst_nodes = ["KHCC"] + top_institutions['institution'].tolist()
    inst_node_map = {node: idx for idx, node in enumerate(inst_nodes)}
    
    # Create links from KHCC to each institution
    inst_sources = [0] * len(top_institutions)  # KHCC is always source (index 0)
    inst_targets = [inst_node_map[inst] for inst in top_institutions['institution']]
    inst_values = top_institutions['collaboration_count'].tolist()
    
    inst_fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=inst_nodes,
            color=["#1f77b4"] + ["#ff7f0e"] * len(top_institutions)
        ),
        link=dict(
            source=inst_sources,
            target=inst_targets,
            value=inst_values
        )
    )])
    inst_fig.update_layout(
        title="Institution Collaboration Network",
        font=dict(size=12),
        height=600
    )
    
    # Create country Sankey
    top_countries = country_df.nlargest(20, 'collaboration_count')
    country_nodes = ["Jordan"] + [
        pycountry.countries.get(alpha_2=code).name 
        if pycountry.countries.get(alpha_2=code) else code
        for code in top_countries['country_code']
    ]
    
    # Create links from Jordan to each country
    country_sources = [0] * len(top_countries)  # Jordan is always source (index 0)
    country_targets = list(range(1, len(top_countries) + 1))
    country_values = top_countries['collaboration_count'].tolist()
    
    country_fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=country_nodes,
            color=["#1f77b4"] + ["#ff7f0e"] * len(top_countries)
        ),
        link=dict(
            source=country_sources,
            target=country_targets,
            value=country_values
        )
    )])
    country_fig.update_layout(
        title="Country Collaboration Network",
        font=dict(size=12),
        height=600
    )
    
    return inst_fig, country_fig

def create_empty_figure(title):
    """Helper function to create empty figure with message"""
    fig = go.Figure()
    fig.add_annotation(
        text=f"{title} data unavailable",
        showarrow=False,
        font=dict(size=14)
    )
    fig.update_layout(
        title=title,
        height=600
    )
    return fig

def create_department_charts():
    """Create Sankey and bar charts for KHCC department collaborations"""
    # Get collaboration data
    collab_df = data_cache.get('collaboration_network', pd.DataFrame())
    
    if collab_df.empty:
        return create_empty_figure("Department Network"), create_empty_figure("Department Bar Chart")
    
    # Process department collaborations
    dept_collaborations = []
    dept_counts = Counter()
    
    # Process department lists
    for _, row in collab_df.iterrows():
        # Split department lists and clean
        depts1 = [d.strip() for d in row['dept1_list'].split(',') if d.strip() and d.strip() != 'Unknown']
        depts2 = [d.strip() for d in row['dept2_list'].split(',') if d.strip() and d.strip() != 'Unknown']
        
        # Count departments
        for dept in set(depts1 + depts2):
            dept_counts[dept] += row['collaboration_count']
        
        # Create collaboration pairs
        for dept1 in depts1:
            for dept2 in depts2:
                if dept1 != dept2:
                    dept_collaborations.append((dept1, dept2, row['collaboration_count']))
    
    # Get top 15 departments by collaboration count
    top_depts = dict(sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:15])
    
    # Filter collaborations to only include top departments
    filtered_collaborations = [
        (d1, d2, count) for d1, d2, count in dept_collaborations 
        if d1 in top_depts and d2 in top_depts
    ]
    
    # Create nodes list and mapping
    nodes = list(top_depts.keys())
    node_map = {node: idx for idx, node in enumerate(nodes)}
    
    # Aggregate collaboration counts between departments
    collab_counts = {}
    for d1, d2, count in filtered_collaborations:
        key = tuple(sorted([d1, d2]))
        collab_counts[key] = collab_counts.get(key, 0) + count
    
    # Create Sankey diagram data
    sources = []
    targets = []
    values = []
    for (d1, d2), count in collab_counts.items():
        sources.append(node_map[d1])
        targets.append(node_map[d2])
        values.append(count)
    
    # Create Sankey diagram
    sankey_fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color=["#1f77b4"] * len(nodes)
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    )])
    sankey_fig.update_layout(
        title="Department Collaboration Network (Top 15 Departments)",
        font=dict(size=12),
        height=600
    )
    
    # Create bar chart
    dept_df = pd.DataFrame(list(top_depts.items()), columns=['Department', 'Collaborations'])
    dept_df = dept_df.sort_values('Collaborations', ascending=True)
    
    bar_fig = px.bar(
        dept_df,
        x='Collaborations',
        y='Department',
        orientation='h',
        title="Department Collaboration Frequency"
    )
    bar_fig.update_layout(
        height=600,
        xaxis_title="Number of Collaborations",
        yaxis_title="Department",
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return sankey_fig, bar_fig

def create_enhanced_topic_graph(df, min_papers=3, min_connections=2):
    """
    For your 'concepts' or 'mesh_terms' we can build a small knowledge graph. 
    We'll just do 'concepts' as in old code. 
    """
    from collections import Counter
    import math

    topic_connections = []
    topic_counts = Counter()
    topic_to_papers = {}

    for _, row in df.iterrows():
        c_list = row.get('concepts')
        if not c_list or not isinstance(c_list,list):
            continue
        # gather these topics
        paper_topics = []
        for cdict in c_list:
            name = cdict.get('display_name')
            if not name: 
                continue
            topic_counts[name]+=1
            paper_topics.append(name)
            if name not in topic_to_papers:
                topic_to_papers[name]=[]
            topic_to_papers[name].append(row['paper_id'])
        # connections among these topics in same paper
        for i in range(len(paper_topics)):
            for j in range(i+1,len(paper_topics)):
                t1, t2 = sorted([paper_topics[i], paper_topics[j]])
                topic_connections.append((t1,t2))

    # filter by min_papers
    significant = {t for t,cnt in topic_counts.items() if cnt>=min_papers}
    pair_counts = Counter((a,b) for (a,b) in topic_connections if a in significant and b in significant)
    # filter by min_connections
    final_pairs = {k:v for k,v in pair_counts.items() if v>=min_connections}

    G = nx.Graph()
    for (a,b),w in final_pairs.items():
        G.add_edge(a,b,weight=w)
    pos = nx.spring_layout(G, k=2/math.sqrt(len(G.nodes())+0.1), iterations=50)

    fig = go.Figure()
    # edges
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0,y0 = pos[edge[0]]
        x1,y1 = pos[edge[1]]
        edge_x.extend([x0,x1,None])
        edge_y.extend([y0,y1,None])
    fig.add_trace(go.Scatter(
        x=edge_x,y=edge_y,
        line=dict(width=1,color='rgba(150,150,150,0.5)'),
        hoverinfo='none',
        mode='lines'
    ))
    # nodes
    node_x, node_y, node_size, node_text, node_color = [], [], [], [], []
    deg = dict(G.degree())
    max_deg = max(deg.values()) if deg else 1
    for node in G.nodes():
        x,y=pos[node]
        node_x.append(x)
        node_y.append(y)
        count = topic_counts[node]
        dval = deg[node]
        node_size.append(np.log1p(count)*20)
        node_text.append(f"{node}<br>Papers: {count}<br>Connections: {dval}")
        node_color.append(dval/max_deg)

    fig.add_trace(go.Scatter(
        x=node_x,y=node_y,
        mode='markers+text',
        text=[n for n in G.nodes()],
        textposition='top center',
        hovertext=node_text,
        hoverinfo='text',
        marker=dict(
            showscale=True,
            size=node_size,
            colorscale='Viridis',
            color=node_color,
            line=dict(color='white',width=1),
            colorbar=dict(title='Connectivity')
        )
    ))
    fig.update_layout(
        title=f"Research Topics (≥{min_papers} papers, ≥{min_connections} connections)",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=60),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    return fig, topic_to_papers

def create_topics_wordcloud(df):
    all_concepts = []
    for _, row in df.iterrows():
        c_list = row.get('concepts')
        if isinstance(c_list, list):
            for cdict in c_list:
                name = cdict.get('display_name','')
                if name: 
                    all_concepts.append(name)
    text = ' '.join(all_concepts)
    stopwords = set(["the","a","and","in","for","of","with","by","from","on","to"])
    try:
        wc = WordCloud(width=800,height=400,background_color='white',stopwords=stopwords)
        wc.generate(text)
        buf = io.BytesIO()
        wc.to_image().save(buf,format='PNG')
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except:
        return ""

# ------------------------------------------------------------------------------
# 5. Build Tabs
# ------------------------------------------------------------------------------

# 5.1 Overview Tab
tab_overview = dbc.Card(
    dbc.CardBody([
        html.H4("Publications Overview", className="card-title"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"Total Publications: {len(papers_df):,}"),
                        html.H5(f"Total Citations: {int(papers_df['citations'].sum()):,}"),
                        html.H5(f"Average Citations: {papers_df['citations'].mean():.1f}"),
                        html.H5(f"Open Access: {papers_df['open_access'].sum():,} "
                                f"({(papers_df['open_access'].mean()*100):.1f}%)")
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

# 5.2 Collaboration Network Tab
tab_collaboration = dbc.Card(
    dbc.CardBody([
        html.H4("Research Collaboration Network", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5("Global Collaboration Map", className="text-center"),
                dcc.Graph(figure=fig_map)
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("Institution Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_institution_country_sankeys()[0])
            ], width=6),
            dbc.Col([
                html.H5("Top 20 Collaborating Institutions", className="text-center"),
                dcc.Graph(figure=fig_inst)
            ], width=6)
        ], className="mt-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Country Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_institution_country_sankeys()[1])
            ], width=6),
            dbc.Col([
                html.H5("Top 20 Collaborating Countries", className="text-center"),
                dcc.Graph(figure=fig_country)
            ], width=6)
        ], className="mt-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Department Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_department_charts()[0])
            ], width=6),
            dbc.Col([
                html.H5("Department Collaboration Frequency", className="text-center"),
                dcc.Graph(figure=create_department_charts()[1])
            ], width=6)
        ], className="mt-4")
    ]),
    className="mt-3"
)

# 5.3 Authors Tab
tab_authors = dbc.Card(
    dbc.CardBody([
        html.H4("Author Analysis", className="card-title"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_author_impact), md=12),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_author_positions), md=12),
        ])
    ]),
    className="mt-3"
)

# 5.4 Citations Tab
tab_citations = dbc.Card(
    dbc.CardBody([
        html.H4("Citations Analysis", className="card-title"),
        dcc.Graph(figure=fig_cites)
    ]),
    className="mt-3"
)

# 5.5 Journal Metrics Tab
# We'll add a quartile by year bar:
quartile_by_year = pd.crosstab(
    papers_df["publication_year"],
    papers_df["quartile"]
).reset_index()

for q in ["Q1","Q2","Q3","Q4","Unknown"]:
    if q not in quartile_by_year.columns:
        quartile_by_year[q]=0

fig_quartile_trend = px.bar(
    quartile_by_year,
    x="publication_year",
    y=["Q1","Q2","Q3","Q4","Unknown"],
    title="Journal Quartile Distribution by Year",
    labels={"publication_year":"Year","value":"Number of Publications","variable":"Quartile"},
    color_discrete_sequence=['#2ecc71','#3498db','#f1c40f','#e74c3c','#95a5a6']
)
fig_quartile_trend.update_layout(barmode='stack')

tab_journals = dbc.Card(
    dbc.CardBody([
        html.H4("Journal Metrics", className="card-title"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_quartile), md=4),
            dbc.Col(dcc.Graph(figure=fig_impact_factor), md=4),
            dbc.Col(dcc.Graph(figure=fig_open_access), md=4),
        ], className="mt-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_quartile_trend), md=12),
        ], className="mt-3")
    ]),
    className="mt-3"
)

# 5.6 Publication Types Tab (uses "publication_type")
def create_publication_type_figures(df):
    tcounts = df["publication_type"].fillna("Unknown").value_counts()
    fig_pie = px.pie(
        values=tcounts.values,
        names=tcounts.index,
        title="Distribution of Publication Types"
    )
    # stacked bar by year
    tby_year = pd.crosstab(df["publication_year"], df["publication_type"].fillna("Unknown")).reset_index()
    # all columns except "publication_year"
    col_list = list(tby_year.columns[1:])
    fig_trend = px.bar(
        tby_year,
        x="publication_year",
        y=col_list,
        title="Publication Types by Year",
        labels={"publication_year":"Year","value":"Count","variable":"Publication Type"}
    )
    fig_trend.update_layout(barmode="stack")
    return fig_pie, fig_trend

fig_type_pie, fig_type_trend = create_publication_type_figures(papers_df)

tab_publication_types = dbc.Card(
    dbc.CardBody([
        html.H4("Publication Types Analysis", className="card-title"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_type_pie), md=6),
            dbc.Col(dcc.Graph(figure=fig_type_trend), md=6),
        ])
    ]),
    className="mt-3"
)

# 5.7 Publications List Tab
def flatten_authors(row):
    auths = row.get('authorships')
    if not auths: return ''
    # parse if string
    if isinstance(auths,str):
        try: auths = json.loads(auths)
        except: return ''
    # build comma list
    return ', '.join(a['author']['display_name'] for a in auths if 'author' in a)

def flatten_concepts(concepts):
    """Convert concepts list to readable string"""
    if not concepts: return ''
    if isinstance(concepts, str):
        try: concepts = json.loads(concepts)
        except: return ''
    return ', '.join(c.get('display_name','') for c in concepts if 'display_name' in c)

def flatten_mesh_terms(terms):
    """Convert mesh_terms list to readable string"""
    if not terms: return ''
    if isinstance(terms, str):
        try: terms = json.loads(terms)
        except: return ''
    return ', '.join(str(term) for term in terms if term)

pubs_sorted = papers_df.sort_values(by=['publication_year','publication_month'], ascending=[False,False]).copy()
table_data = []
for _,r in pubs_sorted.iterrows():
    table_data.append({
        "title": r["title"],
        "authors": flatten_authors(r),
        "journal": r["journal"],
        "publication_year": r["publication_year"],
        "publication_month": r["publication_month"],
        "citations": r["citations"],
        "details": "🔍 View",
        # Convert complex fields to strings
        "quartile": r["quartile"],
        "impact_factor": r["impact_factor"],
        "open_access": int(r["open_access"]) if pd.notnull(r["open_access"]) else 0,
        "publication_type": r["publication_type"],
        "concepts": flatten_concepts(r["concepts"]),
        "mesh_terms": flatten_mesh_terms(r["mesh_terms"]),
    })

# Create the publications table
publications_table = dash_table.DataTable(
    id='publications-table',
    columns=[
        {'name': 'Title', 'id': 'title'},
        {'name': 'Authors', 'id': 'authors_text'},
        {'name': 'Journal', 'id': 'journal'},
        {'name': 'Year', 'id': 'publication_year', 'type': 'numeric'},
        {'name': 'Month', 'id': 'publication_month', 'type': 'numeric'},
        {'name': 'Citations', 'id': 'citations', 'type': 'numeric'},
        {'name': 'Details', 'id': 'details', 'presentation': 'markdown'}
    ],
    data=[{
        'title': row['title'],
        'authors_text': row['authors_text'],
        'journal': row['journal'],
        'publication_year': row['publication_year'],
        'publication_month': row['publication_month'],
        'citations': row['citations'],
        'details': '🔍 View',
        # Add these fields for the modal
        'quartile': row['quartile'],
        'impact_factor': row['impact_factor'],
        'open_access': row['open_access'],
        'publication_type': row['publication_type'],
        'concepts_text': row['concepts_text'],
        'mesh_terms_text': row['mesh_terms_text'],
        'authorships_json': row['authorships_json']
    } for row in papers_df.sort_values(
        by=['publication_year', 'publication_month'],
        ascending=[False, False]
    ).to_dict('records')],
    page_size=50,
    page_action='native',
    page_current=0,
    style_table={'overflowX': 'auto'},
    style_cell={
        'textAlign': 'left',
        'padding': '10px',
        'whiteSpace': 'normal',
        'height': 'auto',
        'minWidth': '100px',
        'maxWidth': '400px',
    },
    style_cell_conditional=[
        {'if': {'column_id': 'title'},
         'maxWidth': '400px'},
        {'if': {'column_id': 'authors_text'},
         'maxWidth': '300px'},
        {'if': {'column_id': 'journal'},
         'maxWidth': '200px'},
    ],
    style_data={
        'whiteSpace': 'normal',
        'height': 'auto',
    },
    style_header={
        'backgroundColor': 'rgb(230, 230, 230)',
        'fontWeight': 'bold'
    },
    style_data_conditional=[{
        'if': {'column_id': 'details'},
        'cursor': 'pointer',
        'color': '#007bff',
        'textDecoration': 'none',
        'fontWeight': 'bold'
    }],
    tooltip_delay=0,
    tooltip_duration=None,
    sort_action='native',
    filter_action='native',
    filter_options={'case': 'insensitive'},
    sort_by=[
        {'column_id': 'publication_year', 'direction': 'desc'},
        {'column_id': 'publication_month', 'direction': 'desc'}
    ]
)

total_pubs = len(pubs_sorted)
tab_publications = dbc.Card(
    dbc.CardBody([
        html.H4("Publications List", className="card-title"),
        dbc.Row([
            dbc.Col([
                dbc.Select(
                    id="page-size-select",
                    options=[
                        {"label":"10 per page","value":"10"},
                        {"label":"25 per page","value":"25"},
                        {"label":"50 per page","value":"50"},
                        {"label":"100 per page","value":"100"},
                        {"label":f"Show all ({total_pubs})","value":str(total_pubs)}
                    ],
                    value="50",
                    className="mb-3"
                )
            ], width=12),
        ]),
        html.Div(f"Showing {total_pubs} publications in total", className="text-muted mb-3"),
        publications_table,
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Paper Details")),
                dbc.ModalBody(id="paper-details-content"),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-paper-modal", className="ms-auto")
                ),
            ],
            id="paper-modal",
            size="xl",
            scrollable=True
        )
    ]),
    className="mt-3"
)

# 5.8 Knowledge Graph Tab
fig_topic_graph, topic_to_papers = create_enhanced_topic_graph(papers_df, 3, 2)

tab_knowledge_graph = dbc.Card(
    dbc.CardBody([
        html.H4("Research Topics Analysis", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5("Topics Word Cloud", className="text-center mb-3"),
                html.Img(
                    id='topics-wordcloud',
                    src=create_topics_wordcloud(papers_df),
                    style={'width':'100%','height':'auto'}
                ),
            ], width=12, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("Graph Controls", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Minimum Papers per Topic"),
                        dcc.Slider(
                            id='min-papers-slider',
                            min=1,max=10,value=3,
                            marks={i:str(i) for i in range(1,11)},
                            step=1
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Minimum Connections"),
                        dcc.Slider(
                            id='min-connections-slider',
                            min=1,max=5,value=2,
                            marks={i:str(i) for i in range(1,6)},
                            step=1
                        )
                    ], width=6),
                ], className="mb-3"),
            ], width=12),
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("Topics Knowledge Graph", className="text-center mb-3"),
                dcc.Graph(
                    id='topic-knowledge-graph',
                    figure=fig_topic_graph,
                    style={'height':'800px'}
                )
            ], width=12),
        ]),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Topic-Related Papers")),
                dbc.ModalBody(id="topic-papers-content"),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-topic-modal", className="ms-auto")
                ),
            ],
            id="topic-papers-modal",
            size="xl",
            scrollable=True
        )
    ]),
    className="mt-3"
)

# ------------------------------------------------------------------------------
# 6. App Layout
# ------------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "KHCC Publications Dashboard"

app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="KHCC Publications Dashboard",
        brand_href="#",
        color="primary",
        dark=True,
        className="mb-2"
    ),
    dbc.Tabs([
        dbc.Tab(tab_overview,           label="Overview"),
        dbc.Tab(tab_collaboration,      label="Collaboration Network"),
        dbc.Tab(tab_authors,            label="Authors"),
        dbc.Tab(tab_citations,          label="Citations"),
        dbc.Tab(tab_journals,           label="Journal Metrics"),
        dbc.Tab(tab_publication_types,  label="Publication Types"),
        dbc.Tab(tab_publications,       label="Publications List"),
        dbc.Tab(tab_knowledge_graph,    label="Knowledge Graph"),
    ])
], fluid=True)

# ------------------------------------------------------------------------------
# 7. Callbacks
# ------------------------------------------------------------------------------
@app.callback(
    Output('topic-knowledge-graph','figure'),
    [Input('min-papers-slider','value'),
     Input('min-connections-slider','value')]
)
def update_topic_graph(min_papers, min_connections):
    fig, _ = create_enhanced_topic_graph(papers_df, min_papers, min_connections)
    return fig

@app.callback(
    Output("paper-modal","is_open"),
    [Input("publications-table","active_cell"),
     Input("close-paper-modal","n_clicks")],
    [State("paper-modal","is_open")]
)
def toggle_modal(active_cell, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger_id=="publications-table" and active_cell and active_cell["column_id"]=="details":
        return True
    elif trigger_id=="close-paper-modal":
        return False
    return is_open if is_open else False


@app.callback(
    Output("paper-details-content", "children"),
    Input("publications-table", "active_cell"),
    [State("publications-table", "derived_virtual_data"),
     State("publications-table", "page_current"),
     State("publications-table", "page_size")]
)
def show_paper_details(active_cell, virtual_data, page_current, page_size):
    if not active_cell or not virtual_data:
        return "Click on a paper to see details"

    try:
        idx = active_cell["row"]
        row = virtual_data[idx]
        
        content = [
            html.H5(row["title"], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.P([html.Strong("Journal: "), row.get("journal", "Unknown")]),
                    html.P([html.Strong("Year: "), str(row.get("publication_year", ""))]),
                    html.P([html.Strong("Month: "), str(row.get("publication_month", ""))]),
                ], width=6),
                dbc.Col([
                    html.P([html.Strong("Citations: "), str(row.get("citations", 0))]),
                    html.P([html.Strong("Quartile: "), row.get("quartile", "Unknown")]),
                    html.P([html.Strong("Impact Factor: "), f"{row.get('impact_factor', 0):.2f}"]),
                ], width=6)
            ], className="mb-3"),
            html.P([html.Strong("Open Access: "), "Yes" if row.get("open_access", 0) == 1 else "No"]),
            html.P([html.Strong("Publication Type: "), row.get("publication_type", "Unknown")]),
            html.Div([
                html.Strong("Authors: "),
                html.P(row.get("authors_text", ""), className="mt-2"),
            ], className="mb-3"),
        ]

        # Add research topics if available
        if row.get('concepts_text'):
            content.append(html.Div([
                html.Strong("Research Topics: "),
                html.P(row["concepts_text"], className="mt-2"),
            ], className="mb-3"))

        # Add MeSH terms if available
        if row.get('mesh_terms_text'):
            content.append(html.Div([
                html.Strong("MeSH Terms: "),
                html.P(row["mesh_terms_text"], className="mt-2"),
            ], className="mb-3"))

        return content
    except Exception as e:
        return html.Div([
            "Error loading paper details",
            html.Pre(str(e))
        ], style={'color': 'red'})
    

@app.callback(
    Output('publications-table','filter_query'),
    Input('search-input','value')
)
def update_filter(search_value):
    if not search_value:
        return ''
    # Filter by title, authors, journal
    return (
        f'{{title}} contains "{search_value}" || '
        f'{{authors}} contains "{search_value}" || '
        f'{{journal}} contains "{search_value}"'
    )

@app.callback(
    Output('publications-table','page_size'),
    Input('page-size-select','value')
)
def update_page_size(selected_size):
    return int(selected_size)

# If you want to handle knowledge-graph node clicks -> show papers:
@app.callback(
    [Output("topic-papers-modal","is_open"),
     Output("topic-papers-content","children")],
    [Input("topic-knowledge-graph","clickData"),
     Input("close-topic-modal","n_clicks")],
    [State("topic-papers-modal","is_open")]
)
def show_topic_papers(clickData, close_n, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, None
    trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trig_id=="close-topic-modal":
        return False, None
    if not clickData:
        return False, None

    # We'll parse the node text
    node_label = clickData['points'][0]['text'].split('<br>')[0]
    # find all papers having a concept with display_name == node_label
    matched = papers_df[papers_df['concepts'].notna()].copy()
    results = []
    for _,r in matched.iterrows():
        c_list = r['concepts']
        if any(c.get('display_name')==node_label for c in c_list):
            results.append(r)
    if not results:
        return True, html.P("No papers found for this topic.")
    # build a short list
    items = []
    for pap in results:
        items.append(html.Div([
            html.H6(pap['title']),
            html.P(f"Journal: {pap['journal']} ({pap['publication_year']})"),
            html.Hr()
        ]))
    return True, items


# ------------------------------------------------------------------------------
# 8. Run the App
# ------------------------------------------------------------------------------
if __name__=="__main__":
    app.run_server(debug=True, port=8050, host="127.0.0.1")
