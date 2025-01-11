"""
Combined Dash application that merges features from the old code (authors, citations,
journal metrics) into the new code (overview, publications list) without touching the 
publications list tab.
"""

# 1. Imports
import dash
from dash import html, dcc, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Scheme
import pandas as pd
import sqlite3
import json
from collections import Counter
import pycountry
import networkx as nx
import numpy as np
import scipy
from wordcloud import WordCloud
import re
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Set backend to Agg before importing pyplot
import matplotlib.pyplot as plt

# Keep the same DB_PATH if desired
DB_PATH = 'khcc_papers.sqlite'

# 2. App initialization
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# 3. Data Loading
# ------------------------------------------------------------------------------
def load_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Modified SQL query to include all necessary fields
    papers_df = pd.read_sql_query("""
        SELECT 
            paper_id,
            title,
            journal_name,
            impact_factor,
            quartile,
            citations,
            is_open_access,
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
            CAST(strftime('%Y', publication_date) AS INTEGER) as publication_year,
            CAST(strftime('%m', publication_date) AS INTEGER) as publication_month
        FROM papers
    """, conn)
    
    # Load authors data with enhanced details
    authors_df = pd.read_sql_query("""
        SELECT 
            ka.*,
            p.citations,
            p.publication_year,
            p.journal_name,
            p.quartile,
            p.is_open_access,
            p.impact_factor
        FROM khcc_authors ka
        JOIN papers p ON ka.paper_id = p.openalex_id
    """, conn)
    
    conn.close()
    
    # Clean and prepare papers data
    papers_df["publication_year"] = papers_df["publication_year"].fillna(0).astype(int)
    papers_df["publication_month"] = papers_df["publication_month"].fillna(0).astype(int)
    papers_df["journal_name"] = papers_df["journal_name"].fillna("Unknown Journal")
    papers_df["citations"] = papers_df["citations"].fillna(0)
    papers_df["quartile"] = papers_df["quartile"].fillna("Unknown")
    papers_df["impact_factor"] = papers_df["impact_factor"].fillna(0)
    papers_df["abstract_summary"] = papers_df["abstract_summary"].fillna("No summary available")
    papers_df["pmid"] = papers_df["pmid"].fillna("N/A")
    
    return papers_df, authors_df

def create_figures(papers_df):
    # Group by year
    yearly_metrics = (
        papers_df.groupby("publication_year")
        .agg({
            "citations": ["sum", "mean", "count"]
        })
        .reset_index()
    )
    yearly_metrics.columns = ["publication_year", "total_citations", "mean_citations", "publications"]
    
    # Publications by Year
    fig_pubs = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
        x="publication_year",
        y="publications",
        title="Publications by Year",
        labels={"publication_year": "Year", "publications": "Number of Publications"},
        markers=True
    )
    
    # Average Citations per Year with total citations on secondary axis
    fig_cites = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
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
    
    # Create quartile distribution by year
    quartile_by_year = pd.crosstab(
        papers_df['publication_year'], 
        papers_df['quartile'],
        margins=False
    ).reset_index()
    
    # Create stacked bar chart for quartile distribution
    fig_quartile_trend = px.bar(
        quartile_by_year,
        x='publication_year',
        y=['Q1', 'Q2', 'Q3', 'Q4', 'Unknown'],
        title='Journal Quartile Distribution by Year',
        labels={
            'publication_year': 'Year',
            'value': 'Number of Publications',
            'variable': 'Quartile'
        },
        color_discrete_sequence=['#2ecc71', '#3498db', '#f1c40f', '#e74c3c', '#95a5a6']
    )
    
    fig_quartile_trend.update_layout(
        barmode='stack',
        legend_title='Quartile',
        xaxis_tickangle=0
    )
    
    return fig_pubs, fig_cites, fig_quartile_trend

# Now load data and create figures
papers_df, authors_df = load_data()
fig_pubs, fig_cites, fig_quartile_trend = create_figures(papers_df)

# ------------------------------------------------------------------------------
# 4. Data Preprocessing & Figure Creation
# ------------------------------------------------------------------------------

## 4.1 Basic transformations for papers_df
papers_df["publication_year"] = papers_df.get("publication_year", 0).fillna(0).astype(int)
papers_df["citations"] = papers_df["citations"].fillna(0)
papers_df["journal_name"] = papers_df["journal_name"].fillna("Unknown Journal")
papers_df["quartile"] = papers_df["quartile"].fillna("Unknown")
papers_df["impact_factor"] = papers_df["impact_factor"].fillna(0)
papers_df["is_open_access"] = papers_df["is_open_access"].fillna(0)

## 4.2 Build summary metrics for the "Overview" tab
def create_overview_figures(papers_df):
    # Group by year
    yearly_metrics = (
        papers_df.groupby("publication_year")
        .agg({
            "citations": ["sum", "mean", "count"]
        })
        .reset_index()
    )
    yearly_metrics.columns = ["publication_year", "total_citations", "mean_citations", "publications"]
    
    # Publications by Year
    fig_pubs = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
        x="publication_year",
        y="publications",
        title="Publications by Year",
        labels={"publication_year": "Year", "publications": "Number of Publications"},
        markers=True
    )
    
    # Average Citations per Year with total citations on secondary axis
    fig_cites = px.line(
        yearly_metrics[yearly_metrics["publication_year"] > 0],
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
    return fig_pubs, fig_cites

fig_pubs, fig_cites = create_overview_figures(papers_df)

## 4.3 Author-related metrics (from old code) if authors_df is not empty
if not authors_df.empty:
    authors_df["is_corresponding"] = authors_df["is_corresponding"].fillna(0)
    
    # Summaries
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
    author_metrics["citations_per_paper"] = author_metrics["citations"] / author_metrics["paper_count"]
    
    # Top 10 authors by citations
    top_10_authors = author_metrics.nlargest(10, "citations")
    
    # Compute positions
    author_positions = (
        authors_df.groupby("author_name")["author_position"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    
    for pos in ["first", "middle", "last"]:
        if pos not in author_positions.columns:
            author_positions[pos] = 0
    
    author_positions["total_papers"] = author_positions[["first", "middle", "last"]].sum(axis=1)
    top_20_authors = author_positions.nlargest(20, "total_papers")
    
    # Figures
    fig_author_impact = px.scatter(
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
    
    fig_author_positions = go.Figure()
    for pos in ["first", "middle", "last"]:
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
    # Fallback if no authors_df
    fig_author_impact = px.scatter(title="No Author Data Available")
    fig_author_positions = go.Figure().add_annotation(
        text="No Author Data Available", 
        showarrow=False
    )

## 4.4 Journal/Citations figures from old code

# Group by year for citations if needed (already done in create_overview_figures)
yearly_metrics = (
    papers_df.groupby("publication_year")
    .agg({"citations": ["sum", "mean", "count"]})
    .reset_index()
)
yearly_metrics.columns = ["publication_year", "total_citations", "mean_citations", "publications"]

# Pie of quartiles
quartile_counts = papers_df["quartile"].value_counts()
fig_quartile = px.pie(
    values=quartile_counts.values,
    names=quartile_counts.index,
    title="Journal Quartile Distribution"
)

# Impact Factor distribution
fig_impact_factor = px.histogram(
    papers_df[papers_df["impact_factor"] > 0],
    x="impact_factor",
    title="Impact Factor Distribution",
    nbins=20
)

# Open Access
is_open_access_counts = papers_df["is_open_access"].value_counts()
# Could be 0/1 or boolean. We'll map them to labels:
if len(is_open_access_counts) == 2:
    fig_open_access = px.pie(
        names=["Open Access" if x == 1 else "Closed Access" for x in is_open_access_counts.index],
        values=is_open_access_counts.values,
        title="Open Access Distribution"
    )
else:
    fig_open_access = px.pie(title="Open Access Distribution (No data)")

# Add these functions before defining any layout components
def extract_institutions_and_countries(authorships):
    """Extract unique institutions and countries from authorships data"""
    if isinstance(authorships, str):
        # Convert string to list of dictionaries if needed
        authorships = json.loads(authorships)
    
    institutions = []
    countries = []
    
    for authorship in authorships:
        # Check if author is from KHCC
        is_khcc_author = False
        if 'institutions' in authorship:
            for inst in authorship['institutions']:
                if inst['display_name'] == "King Hussein Cancer Center":
                    is_khcc_author = True
                    break
                institutions.append(inst['display_name'])
        
        # Only add countries if author is not from KHCC
        if not is_khcc_author and 'countries' in authorship:
            countries.extend(authorship['countries'])
    
    return institutions, countries

def extract_external_authors(authorships):
    """Extract authors who are not from KHCC"""
    if isinstance(authorships, str):
        authorships = json.loads(authorships)
    
    external_authors = []
    
    for authorship in authorships:
        # Check if author is from KHCC
        is_khcc_author = False
        if 'institutions' in authorship:
            for inst in authorship['institutions']:
                if inst['display_name'] == "King Hussein Cancer Center":
                    is_khcc_author = True
                    break
        
        # Only add author if they're not from KHCC
        if not is_khcc_author and 'author' in authorship:
            external_authors.append(authorship['author']['display_name'])
    
    return external_authors

def create_frequency_charts(exclude_khcc=True):
    """Create frequency charts for institutions, countries, and external authors"""
    all_institutions = []
    all_countries = []
    all_external_authors = []
    
    for authorships in papers_df['authorships'].dropna():
        institutions, countries = extract_institutions_and_countries(authorships)
        external_authors = extract_external_authors(authorships)
        
        # Filter out KHCC if exclude_khcc is True
        if exclude_khcc:
            institutions = [inst for inst in institutions if inst != "King Hussein Cancer Center"]
            
        all_institutions.extend(institutions)
        all_countries.extend(countries)
        all_external_authors.extend(external_authors)
    
    # Count frequencies
    inst_counts = Counter(all_institutions)
    country_counts = Counter(all_countries)
    author_counts = Counter(all_external_authors)
    
    # Create external authors bar chart - Top 20
    author_df = pd.DataFrame.from_dict(author_counts, orient='index', columns=['count']).reset_index()
    author_df.columns = ['Author', 'Count']
    author_df = author_df.nlargest(20, 'Count')  # Get top 20
    
    fig_authors = px.bar(author_df, 
                        x='Count', 
                        y='Author',
                        orientation='h',
                        title='Top 20 External Collaborating Authors')
    fig_authors.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=600
    )
    
    # Create institution bar chart - Top 20
    inst_df = pd.DataFrame.from_dict(inst_counts, orient='index', columns=['count']).reset_index()
    inst_df.columns = ['Institution', 'Count']
    inst_df = inst_df.nlargest(20, 'Count')
    
    fig_inst = px.bar(inst_df, 
                      x='Count', 
                      y='Institution',
                      orientation='h',
                      title='Top 20 Collaborating Institutions')
    fig_inst.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=600
    )
    
    # Create country bar chart and map - Top 20
    country_df = pd.DataFrame.from_dict(country_counts, orient='index', columns=['count']).reset_index()
    country_df.columns = ['Country', 'Count']
    country_df = country_df.nlargest(20, 'Count')
    
    # Create world map
    country_iso3 = {}
    for country_code in country_df['Country']:
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            if country:
                country_iso3[country_code] = country.alpha_3
        except:
            continue
    
    country_df['ISO3'] = country_df['Country'].map(country_iso3)
    
    fig_map = px.choropleth(
        country_df,
        locations='ISO3',
        color='Count',
        hover_name='Country',
        color_continuous_scale='Viridis',
        title='Global Research Collaboration Network (Top 20 Countries)'
    )
    fig_map.update_layout(
        height=600,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular'
        )
    )
    
    fig_country = px.bar(country_df, 
                        x='Count', 
                        y='Country',
                        orientation='h',
                        title='Top 20 Collaborating Countries')
    fig_country.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=600
    )
    
    return fig_inst, fig_country, fig_map, fig_authors

def extract_khcc_and_collaborator_links(authorships):
    """Extract KHCC authors and their collaborators from a paper"""
    if isinstance(authorships, str):
        authorships = json.loads(authorships)
    
    khcc_authors = []
    external_authors = []
    
    # First pass to identify KHCC authors
    for authorship in authorships:
        is_khcc_author = False
        if 'institutions' in authorship:
            for inst in authorship['institutions']:
                if inst['display_name'] == "King Hussein Cancer Center":
                    is_khcc_author = True
                    khcc_authors.append(authorship['author']['display_name'])
                    break
        
        if not is_khcc_author and 'author' in authorship:
            external_authors.append(authorship['author']['display_name'])
    
    # Create links between KHCC authors and external authors
    links = []
    for khcc_author in khcc_authors:
        for external_author in external_authors:
            links.append((khcc_author, external_author))
    
    return links

def extract_khcc_authors(authorships):
    """Extract only authors who are affiliated with KHCC"""
    if isinstance(authorships, str):
        authorships = json.loads(authorships)
    
    khcc_authors = []
    for authorship in authorships:
        if 'institutions' in authorship:
            for inst in authorship['institutions']:
                # Check specifically for KHCC using its OpenAlex ID
                if inst.get('id') == 'https://openalex.org/I2799468983':
                    khcc_authors.append(authorship['author']['display_name'])
                    break
    return khcc_authors

def create_sankey_diagram():
    """Create a Sankey diagram showing top 10 KHCC authors and top 10 collaborators"""
    # Collect all KHCC authors and their collaborations
    khcc_collaborations = []
    all_khcc_authors = set()
    
    for authorships in papers_df['authorships'].dropna():
        auth_data = json.loads(authorships) if isinstance(authorships, str) else authorships
        
        # Get KHCC authors in this paper
        khcc_authors = extract_khcc_authors(auth_data)
        all_khcc_authors.update(khcc_authors)
        
        # Get external authors
        external_authors = []
        for auth in auth_data:
            is_khcc = False
            if 'institutions' in auth:
                for inst in auth['institutions']:
                    if inst.get('id') == 'https://openalex.org/I2799468983':
                        is_khcc = True
                        break
            if not is_khcc:
                external_authors.append(auth['author']['display_name'])
        
        # Create links between KHCC authors and external authors
        for khcc_author in khcc_authors:
            for ext_author in external_authors:
                khcc_collaborations.append((khcc_author, ext_author))
    
    # Count collaborations for KHCC authors
    khcc_author_counts = Counter()
    for khcc_author, _ in khcc_collaborations:
        khcc_author_counts[khcc_author] += 1
    
    # Get top 10 KHCC authors
    top_khcc_authors = [author for author, _ in khcc_author_counts.most_common(10)]
    
    # Get top 10 external collaborators for these KHCC authors
    external_author_counts = Counter()
    for khcc_author, ext_author in khcc_collaborations:
        if khcc_author in top_khcc_authors:
            external_author_counts[ext_author] += 1
    top_external_authors = [author for author, _ in external_author_counts.most_common(10)]
    
    # Create nodes and get indices
    nodes = top_khcc_authors + top_external_authors
    node_indices = {node: idx for idx, node in enumerate(nodes)}
    
    # Create source, target, and value lists
    sources = []
    targets = []
    values = []
    
    # Count specific collaborations between top authors
    collaboration_counts = Counter(khcc_collaborations)
    for (khcc_author, ext_author), count in collaboration_counts.items():
        if khcc_author in top_khcc_authors and ext_author in top_external_authors:
            sources.append(node_indices[khcc_author])
            targets.append(node_indices[ext_author])
            values.append(count)
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 50,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = nodes,
            color = ["#1f77b4"]*len(top_khcc_authors) + ["#ff7f0e"]*len(top_external_authors)
        ),
        link = dict(
            source = sources,
            target = targets,
            value = values
        ),
        arrangement = "snap"
    )])
    
    fig_sankey.update_layout(
        title=dict(
            text="Top 10 KHCC Researchers (blue) and Top 10 External Collaborators (orange)",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        font=dict(size=12),
        height=600,
        width=800,
        margin=dict(l=150, r=150, t=50, b=50)
    )
    
    return fig_sankey

def extract_khcc_institution_country_links(authorships):
    """Extract KHCC authors' links with institutions and countries"""
    if isinstance(authorships, str):
        authorships = json.loads(authorships)
    
    khcc_authors = []
    external_institutions = []
    external_countries = []
    
    # First identify KHCC authors
    for authorship in authorships:
        is_khcc = False
        author_name = authorship['author']['display_name']
        
        if 'institutions' in authorship:
            for inst in authorship['institutions']:
                if inst.get('id') == 'https://openalex.org/I2799468983':
                    is_khcc = True
                    khcc_authors.append(author_name)
                    break
    
    # Then collect external institutions and countries from non-KHCC authors
    for authorship in authorships:
        author_name = authorship['author']['display_name']
        if author_name not in khcc_authors:  # if not a KHCC author
            if 'institutions' in authorship:
                for inst in authorship['institutions']:
                    if inst.get('id') != 'https://openalex.org/I2799468983':  # not KHCC
                        for khcc_author in khcc_authors:
                            external_institutions.append((khcc_author, inst['display_name']))
            
            if 'countries' in authorship:
                for country in authorship['countries']:
                    for khcc_author in khcc_authors:
                        external_countries.append((khcc_author, country))
    
    return khcc_authors, external_institutions, external_countries

def create_institution_country_sankeys():
    """Create Sankey diagrams for top 10 KHCC authors with top 10 institutions and countries"""
    # Collect all links
    all_khcc_authors = set()
    all_institution_links = []
    all_country_links = []
    
    for authorships in papers_df['authorships'].dropna():
        khcc_authors, inst_links, country_links = extract_khcc_institution_country_links(authorships)
        all_khcc_authors.update(khcc_authors)
        all_institution_links.extend(inst_links)
        all_country_links.extend(country_links)
    
    # Get top 10 KHCC authors by total collaborations
    khcc_author_counts = Counter()
    for author in all_khcc_authors:
        inst_count = sum(1 for a, _ in all_institution_links if a == author)
        country_count = sum(1 for a, _ in all_country_links if a == author)
        khcc_author_counts[author] = inst_count + country_count
    top_khcc_authors = [author for author, _ in khcc_author_counts.most_common(10)]
    
    # Count frequencies for institutions and countries (only for top 10 KHCC authors)
    institution_counts = Counter(dict(Counter(x[1] for x in all_institution_links 
                                            if x[0] in top_khcc_authors)))
    country_counts = Counter(dict(Counter(x[1] for x in all_country_links 
                                        if x[0] in top_khcc_authors)))
    
    # Get top 10 institutions and countries
    top_institutions = [inst for inst, _ in institution_counts.most_common(10)]
    top_countries = [country for country, _ in country_counts.most_common(10)]
    
    # Create Institution Sankey
    inst_nodes = top_khcc_authors + top_institutions
    inst_node_indices = {node: idx for idx, node in enumerate(inst_nodes)}
    
    inst_sources = []
    inst_targets = []
    inst_values = []
    
    # Count author-institution collaborations
    for author in top_khcc_authors:
        for inst in top_institutions:
            count = sum(1 for a, i in all_institution_links if a == author and i == inst)
            if count > 0:
                inst_sources.append(inst_node_indices[author])
                inst_targets.append(inst_node_indices[inst])
                inst_values.append(count)
    
    fig_inst_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 50,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = inst_nodes,
            color = ["#1f77b4"]*len(top_khcc_authors) + ["#ff7f0e"]*len(top_institutions)
        ),
        link = dict(
            source = inst_sources,
            target = inst_targets,
            value = inst_values
        ),
        arrangement = "snap"
    )])
    
    fig_inst_sankey.update_layout(
        title=dict(
            text="Top 10 KHCC Researchers (blue) and Top 10 Collaborating Institutions (orange)",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        font=dict(size=12),
        height=600,
        width=800,
        margin=dict(l=150, r=150, t=50, b=50)
    )
    
    # Create Country Sankey
    country_nodes = top_khcc_authors + top_countries
    country_node_indices = {node: idx for idx, node in enumerate(country_nodes)}
    
    country_sources = []
    country_targets = []
    country_values = []
    
    # Count author-country collaborations
    for author in top_khcc_authors:
        for country in top_countries:
            count = sum(1 for a, c in all_country_links if a == author and c == country)
            if count > 0:
                country_sources.append(country_node_indices[author])
                country_targets.append(country_node_indices[country])
                country_values.append(count)
    
    fig_country_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 50,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = country_nodes,
            color = ["#1f77b4"]*len(top_khcc_authors) + ["#ff7f0e"]*len(top_countries)
        ),
        link = dict(
            source = country_sources,
            target = country_targets,
            value = country_values
        ),
        arrangement = "snap"
    )])
    
    fig_country_sankey.update_layout(
        title=dict(
            text="Top 10 KHCC Researchers (blue) and Top 10 Collaborating Countries (orange)",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        font=dict(size=12),
        height=600,
        width=800,
        margin=dict(l=150, r=150, t=50, b=50)
    )
    
    return fig_inst_sankey, fig_country_sankey

def standardize_department_name(dept_name):
    """Standardize department names, combining similar departments"""
    if not dept_name:
        return None
        
    # Combine Medical Oncology with Internal Medicine
    if any(name in dept_name for name in ["Medical Oncology", "Internal Medicine", "Medicine"]):
        return "Department of Internal Medicine"
    
    if any(name in dept_name for name in ["Diagnostic Radiology", "Radiology"]):
        return "Department of Diagnostic Radiology"
    
    if any(name in dept_name for name in ["Pediatrics", "Pediatric Oncology"]):
        return "Department of Pediatrics"
    
    return dept_name

def extract_khcc_department(raw_affiliation):
    """Extract department name from KHCC raw affiliation string"""
    if not isinstance(raw_affiliation, str):
        return None
    
    # Check if this is a KHCC affiliation
    if "King Hussein Cancer Center" not in raw_affiliation:
        return None
    
    # Common department patterns
    dept_patterns = [
        "Department of",
        "Departments of",
        "Division of",
        "Divisions of",
        "Section of",
        "Sections of"
    ]
    
    # Try to find department name
    for pattern in dept_patterns:
        if pattern in raw_affiliation:
            # Split by pattern and take the relevant part
            parts = raw_affiliation.split(pattern)
            if len(parts) > 1:
                # Take the text after the pattern until the next comma or 'King Hussein'
                dept_text = parts[1].split(',')[0].split('King Hussein')[0].strip()
                if dept_text:
                    dept_name = f"{pattern} {dept_text}"
                    return standardize_department_name(dept_name)
    
    return None

def create_department_charts():
    """Create Sankey and bar charts for KHCC department collaborations"""
    dept_collaborations = []
    dept_counts = Counter()
    
    print("\nStarting department extraction...")
    
    for authorships in papers_df['authorships'].dropna():
        if isinstance(authorships, str):
            authorships = json.loads(authorships)
            
        paper_depts = set()  # Use set to avoid duplicates within same paper
        
        # Process each author
        for auth in authorships:
            # Check if author is from KHCC
            is_khcc_author = False
            for inst in auth.get('institutions', []):
                if inst.get('id') == 'https://openalex.org/I2799468983':
                    is_khcc_author = True
                    break
            
            if is_khcc_author:
                # Process all raw affiliation strings for this author
                for raw_aff in auth.get('raw_affiliation_strings', []):
                    dept = extract_khcc_department(raw_aff)
                    if dept:
                        print(f"Found department: {dept}")  # Debug print
                        paper_depts.add(dept)
        
        # Add departments found in this paper
        for dept in paper_depts:
            dept_counts[dept] += 1
        
        # Create collaboration links between departments
        paper_depts = list(paper_depts)
        for i, dept1 in enumerate(paper_depts):
            for dept2 in paper_depts[i+1:]:
                if dept1 != dept2:
                    dept_collaborations.append(tuple(sorted([dept1, dept2])))
    
    print("\nDepartment counts:", dict(dept_counts))
    print("\nDepartment collaborations:", dict(Counter(dept_collaborations)))
    
    if not dept_counts:
        print("No departments found!")
        return go.Figure(), go.Figure()
    
    # Create DataFrame with explicit numeric type for Count
    dept_df = pd.DataFrame(list(dept_counts.items()), columns=['Department', 'Count'])
    dept_df['Count'] = pd.to_numeric(dept_df['Count'], errors='coerce')
    dept_df = dept_df.sort_values('Count', ascending=True).tail(10)
    
    # Get top 10 departments list
    top_departments = dept_df['Department'].tolist()
    
    # Create bar chart
    fig_dept_bar = px.bar(dept_df,
                         x='Count',
                         y='Department',
                         orientation='h',
                         title='Top 10 KHCC Departments by Publication Count')
    fig_dept_bar.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=600,
        width=800
    )
    
    # Create Sankey diagram
    dept_collab_counts = Counter(dept_collaborations)
    nodes = top_departments
    node_indices = {node: idx for idx, node in enumerate(nodes)}
    
    sources = []
    targets = []
    values = []
    
    for (dept1, dept2), count in dept_collab_counts.items():
        if dept1 in top_departments and dept2 in top_departments:
            sources.append(node_indices[dept1])
            targets.append(node_indices[dept2])
            values.append(count)
    
    fig_dept_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 50,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = nodes,
            color = ["#1f77b4"] * len(nodes)
        ),
        link = dict(
            source = sources,
            target = targets,
            value = values
        ),
        arrangement = "snap"
    )])
    
    fig_dept_sankey.update_layout(
        title=dict(
            text="Collaboration Network between Top 10 KHCC Departments",
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        font=dict(size=12),
        height=600,
        width=800,
        margin=dict(l=150, r=150, t=50, b=50)
    )
    
    return fig_dept_sankey, fig_dept_bar


def create_enhanced_topic_graph(papers_df, min_papers=3, min_connections=2):
    """
    Creates an enhanced topic knowledge graph with better spacing and filtering.
    
    Args:
        papers_df: DataFrame containing papers data
        min_papers: Minimum number of papers for a topic to be included
        min_connections: Minimum number of connections for an edge to be shown
    """
    # Extract and organize topics data
    topic_connections = []
    topic_counts = Counter()
    topic_to_papers = {}
    
    for _, paper in papers_df.iterrows():
        if paper['topics'] and isinstance(paper['topics'], str):
            try:
                topics_data = json.loads(paper['topics'])
                paper_topics = []
                
                # Extract main topics and subfields
                for topic in topics_data:
                    main_topic = topic['display_name']
                    paper_topics.append(main_topic)
                    
                    # Count papers per topic
                    topic_counts[main_topic] += 1
                    
                    # Store paper reference
                    if main_topic not in topic_to_papers:
                        topic_to_papers[main_topic] = []
                    topic_to_papers[main_topic].append(paper['paper_id'])
                
                # Create connections between topics in same paper
                for i in range(len(paper_topics)):
                    for j in range(i + 1, len(paper_topics)):
                        topic_connections.append((paper_topics[i], paper_topics[j]))
                        
            except:
                continue
    
    # Filter topics by minimum paper count
    significant_topics = {topic for topic, count in topic_counts.items() 
                         if count >= min_papers}
    
    # Count connections between significant topics
    connection_counts = Counter(tuple(sorted(conn)) for conn in topic_connections 
                              if conn[0] in significant_topics and conn[1] in significant_topics)
    
    # Filter connections by minimum count
    significant_connections = {conn: count for conn, count in connection_counts.items() 
                             if count >= min_connections}
    
    # Create network graph
    G = nx.Graph()
    
    # Add edges with weights
    for (source, target), weight in significant_connections.items():
        G.add_edge(source, target, weight=weight)
    
    # Calculate layout with more spacing
    pos = nx.spring_layout(G, k=2/np.sqrt(len(G.nodes())), iterations=50)
    
    # Create the figure
    fig = go.Figure()
    
    # Add edges with varying width based on weight
    edge_x = []
    edge_y = []
    edge_weights = []
    
    for (source, target), weight in significant_connections.items():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.extend([weight, weight, None])
    
    # Add edges with varying width
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(
            width=1,
            color='rgba(150,150,150,0.5)'
        ),
        hoverinfo='none',
        mode='lines'
    ))
    
    # Add nodes
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_colors = []
    
    # Calculate node metrics for colors
    degrees = dict(G.degree())
    max_degree = max(degrees.values()) if degrees else 1
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        papers_count = topic_counts[node]
        degree = degrees[node]
        
        # Create hover text
        node_text.append(
            f"Topic: {node}<br>"
            f"Papers: {papers_count}<br>"
            f"Connections: {degree}"
        )
        
        # Size based on paper count
        node_size.append(np.log1p(papers_count) * 20)
        
        # Color based on degree centrality
        node_colors.append(degree / max_degree)
    
    # Add nodes with custom styling
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node for node in G.nodes()],
        textposition="top center",
        hovertext=node_text,
        marker=dict(
            showscale=True,
            size=node_size,
            colorscale='Viridis',
            reversescale=False,
            color=node_colors,
            colorbar=dict(
                title='Connectivity<br>Degree',
                thickness=15,
                x=1.02
            ),
            line=dict(color='white', width=1)
        ),
        textfont=dict(size=10)
    ))
    
    # Update layout for better spacing and interactivity
    fig.update_layout(
        title=dict(
            text='Research Topics Network<br>'
                 f'<span style="font-size: 12px">Showing topics with ≥{min_papers} papers '
                 f'and ≥{min_connections} connections</span>',
            x=0.5,
            y=0.95
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=60),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white'
    )
    
    return fig, topic_to_papers







def create_topics_wordcloud(papers_df):
    # Collect all topic names
    all_topics = []
    for _, paper in papers_df.iterrows():
        if paper['topics'] and isinstance(paper['topics'], str):
            try:
                topics_data = json.loads(paper['topics'])
                for topic in topics_data:
                    # Add main topic
                    all_topics.append(topic['display_name'])
                    # Add subfield
                    all_topics.append(topic['subfield']['display_name'])
            except json.JSONDecodeError:
                continue
    
    # Join all topics into a single string
    text = ' '.join(all_topics)
    
    # Define stopwords
    stopwords = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after',
                    'research', 'study', 'studies', 'analysis', 'based'])
    
    try:
        # Create WordCloud with simpler configuration
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            stopwords=stopwords,
            min_font_size=10,
            max_font_size=150,
            prefer_horizontal=0.7
        ).generate(text)
        
        # Convert to image without using matplotlib directly
        img = wordcloud.to_image()
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Encode
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f'data:image/png;base64,{image_base64}'
    
    except Exception as e:
        print(f"Error generating wordcloud: {str(e)}")
        return ''

# Then modify the tab_overview definition to include these charts
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
                        html.H5(f"Open Access: "
                                f"{papers_df['is_open_access'].sum():,} "
                                f"({(papers_df['is_open_access'].mean()*100):.1f}%)")
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

# Create a new tab for collaboration analysis
tab_collaboration = dbc.Card(
    dbc.CardBody([
        html.H4("Research Collaboration Network", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5("Global Collaboration Map", className="text-center"),
                dcc.Graph(figure=create_frequency_charts()[2])
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("Author Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_sankey_diagram())
            ], width=6),
            dbc.Col([
                html.H5("Top External Collaborating Authors", className="text-center"),
                dcc.Graph(figure=create_frequency_charts()[3])
            ], width=6)
        ], className="mt-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Institution Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_institution_country_sankeys()[0])
            ], width=6),
            dbc.Col([
                html.H5("Top Collaborating Institutions", className="text-center"),
                dcc.Graph(figure=create_frequency_charts()[0])
            ], width=6)
        ], className="mt-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Country Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_institution_country_sankeys()[1])
            ], width=6),
            dbc.Col([
                html.H5("Top Collaborating Countries", className="text-center"),
                dcc.Graph(figure=create_frequency_charts()[1])
            ], width=6)
        ], className="mt-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Department Collaboration Network", className="text-center"),
                dcc.Graph(figure=create_department_charts()[0])
            ], width=6),
            dbc.Col([
                html.H5("Top KHCC Departments", className="text-center"),
                dcc.Graph(figure=create_department_charts()[1])
            ], width=6)
        ], className="mt-4")
    ]),
    className="mt-3"
)

# Create a new tab for the knowledge graph
# Modified Knowledge Graph tab with controls
tab_knowledge_graph = dbc.Card(
    dbc.CardBody([
        html.H4("Research Topics Analysis", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.H5("Topics Word Cloud", className="text-center mb-3"),
                html.Img(
                    id='topics-wordcloud',
                    src=create_topics_wordcloud(papers_df),
                    style={'width': '100%', 'height': 'auto'}
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
                            min=1,
                            max=10,
                            value=3,
                            marks={i: str(i) for i in range(1, 11)},
                            step=1
                        ),
                    ], width=6),
                    dbc.Col([
                        html.Label("Minimum Connections"),
                        dcc.Slider(
                            id='min-connections-slider',
                            min=1,
                            max=5,
                            value=2,
                            marks={i: str(i) for i in range(1, 6)},
                            step=1
                        ),
                    ], width=6),
                ], className="mb-3"),
            ], width=12),
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("Topics Knowledge Graph", className="text-center mb-3"),
                dcc.Graph(
                    id='topic-knowledge-graph',
    figure=create_enhanced_topic_graph(papers_df, 3, 2)[0],
    style={'height': '800px'}
                ),
            ], width=12),
        ]),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Topic-Related Papers")),
            dbc.ModalBody(id="topic-papers-content"),
            dbc.ModalFooter(
                dbc.Button("Close", id="close-topic-modal", className="ms-auto")
            ),
        ], id="topic-papers-modal", size="xl", scrollable=True)
    ]),
    className="mt-3"
)
# ------------------------------------------------------------------------------
# 5. Define Tab Contents
# ------------------------------------------------------------------------------

## 5.1 Overview Tab (unchanged from new code + old code logic)
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
                        html.H5(f"Open Access: "
                                f"{papers_df['is_open_access'].sum():,} "
                                f"({(papers_df['is_open_access'].mean()*100):.1f}%)")
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

## 5.2 Authors Tab (from old code)
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

## 5.3 Citations Tab (old code had a separate Citations Tab; 
##     we can display additional citations info or reuse figure_cites)
tab_citations = dbc.Card(
    dbc.CardBody([
        html.H4("Citations Analysis", className="card-title"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_cites), md=12),
        ]),
    ]),
    className="mt-3"
)

## 5.4 Journal Metrics Tab
tab_journals = dbc.Card(
    dbc.CardBody([
        html.H4("Journal Metrics", className="card-title"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_quartile), md=4),
            dbc.Col(dcc.Graph(figure=fig_impact_factor), md=4),
            dbc.Col(dcc.Graph(figure=fig_open_access), md=4),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_quartile_trend), md=12),
        ], className="mt-3")
    ]),
    className="mt-3"
)

## 5.5 Publication Types Tab
def create_publication_type_figures(df):
    print("Creating figures with DataFrame size:", len(df))  # Debug print
    
    # Create pie chart of publication types
    type_counts = df['type'].value_counts()
    print("Publication type counts:", type_counts)  # Debug print
    
    fig_type_pie = px.pie(
        values=type_counts.values,
        names=type_counts.index,
        title=f"Distribution of Publication Types (Total: {len(df)})"
    )

    # Create stacked bar chart of publication types by year
    type_by_year = pd.crosstab(
        df['publication_year'], 
        df['type'],
        margins=False
    ).reset_index()
    
    print("Type by year data:", type_by_year)  # Debug print
    
    fig_type_trend = px.bar(
        type_by_year,
        x='publication_year',
        y=type_by_year.columns[1:],  # All columns except publication_year
        title=f'Publication Types by Year (Total: {len(df)})',
        labels={
            'publication_year': 'Year',
            'value': 'Number of Publications',
            'variable': 'Publication Type'
        }
    )
    
    fig_type_trend.update_layout(
        barmode='stack',
        legend_title='Publication Type',
        xaxis_tickangle=0
    )
    
    return fig_type_pie, fig_type_trend

# Create initial figures
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

# ------------------------------------------------------------------------------
# 6. Publications List Tab (from your new code -- DO NOT TOUCH!)
# ------------------------------------------------------------------------------
# We keep everything exactly as in the new code
# (just copy-paste your new code's publications table, modal, etc.)

# 6.1 Publications DataTable
publications_table = dash_table.DataTable(
    id='publications-table',
    columns=[
        {'name': 'Title', 'id': 'title'},
        {'name': 'Authors', 'id': 'authors'},
        {'name': 'Journal', 'id': 'journal_name'},
        {'name': 'Year', 'id': 'publication_year', 'type': 'numeric'},
        {'name': 'Month', 'id': 'publication_month', 'type': 'numeric'},
        {'name': 'Citations', 'id': 'citations', 'type': 'numeric'},
        {'name': 'Details', 'id': 'details', 'presentation': 'markdown'}
    ],
    data=[{
        **row,
        'authors': ', '.join([author['author']['display_name'] for author in json.loads(row['authorships'])]) if row.get('authorships') else '',
        'details': '🔍 View'
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
    },
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
    sort_action='native',
    filter_action='native',
    filter_options={'case': 'insensitive'},
    sort_by=[
        {'column_id': 'publication_year', 'direction': 'desc'},
        {'column_id': 'publication_month', 'direction': 'desc'}
    ]
)

total_pubs = len(papers_df)

tab_publications = dbc.Card(
    dbc.CardBody([
        html.H4("Publications List", className="card-title"),
        dbc.Row([
            dbc.Col([
                dbc.Select(
                    id="page-size-select",
                    options=[
                        {"label": f"10 per page", "value": "10"},
                        {"label": f"25 per page", "value": "25"},
                        {"label": f"50 per page", "value": "50"},
                        {"label": f"100 per page", "value": "100"},
                        {"label": f"Show all ({total_pubs})", "value": str(total_pubs)}
                    ],
                    value="50",
                    className="mb-3"
                ),
            ], width=12),
        ]),
        html.Div(
            f"Showing {total_pubs} publications in total",
            className="text-muted mb-3"
        ),
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

# ------------------------------------------------------------------------------
# 7. App Layout
# ------------------------------------------------------------------------------
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
        dbc.Tab(tab_collaboration, label="Collaboration Network", tab_id="tab-collaboration"),
        dbc.Tab(tab_authors, label="Authors", tab_id="tab-authors"),
        dbc.Tab(tab_citations, label="Citations", tab_id="tab-citations"),
        dbc.Tab(tab_journals, label="Journal Metrics", tab_id="tab-journals"),
        dbc.Tab(tab_publication_types, label="Publication Types", tab_id="tab-publication-types"),
        dbc.Tab(tab_publications, label="Publications List", tab_id="tab-publications"),
        dbc.Tab(tab_knowledge_graph, label="Knowledge Graph", tab_id="tab-knowledge-graph"),
    ]),
], fluid=True)

# ------------------------------------------------------------------------------
# 8. Callbacks
# ------------------------------------------------------------------------------
# Keep your new code callbacks for the publications tab
# Add callback to update graph based on slider values
@app.callback(
    Output('topic-knowledge-graph', 'figure'),
    [Input('min-papers-slider', 'value'),
     Input('min-connections-slider', 'value')]
)
def update_knowledge_graph(min_papers, min_connections):
    fig, _ = create_enhanced_topic_graph(papers_df, min_papers, min_connections)
    return fig


@app.callback(
    Output("paper-modal", "is_open"),
    [Input("publications-table", "active_cell"),
     Input("close-paper-modal", "n_clicks")],
    [State("paper-modal", "is_open")]
)
def toggle_modal(active_cell, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger_id == "publications-table" and active_cell and active_cell["column_id"] == "details":
        return True
    elif trigger_id == "close-paper-modal":
        return False
    return is_open if is_open is not None else False


@app.callback(
    Output("paper-details-content", "children"),
    Input("publications-table", "active_cell"),
    [State("publications-table", "derived_virtual_data"),
     State("publications-table", "page_current"),
     State("publications-table", "page_size")]
)
def show_paper_details(active_cell, virtual_data, page_current, page_size):
    if active_cell is None or virtual_data is None:
        return "Click on a paper to see details"
    
    try:
        actual_row_index = (page_current * page_size) + active_cell["row"]
        row = virtual_data[actual_row_index]
        
        # Parse authorships JSON if it exists
        authorships = []
        if 'authorships' in row and row['authorships']:
            authorships = json.loads(row['authorships'])
        
        # Format authors with KHCC authors in bold
        formatted_authors = []
        for authorship in authorships:
            author_name = authorship['author']['display_name']
            is_khcc_author = False
            
            if 'institutions' in authorship:
                for inst in authorship['institutions']:
                    if inst.get('id') == 'https://openalex.org/I2799468983':
                        is_khcc_author = True
                        break
            formatted_authors.append(f"**{author_name}**" if is_khcc_author else author_name)
        
        authors_text = ", ".join(formatted_authors)
        
        # Extract concepts and format them
        concepts = []
        if 'concepts' in row and row['concepts']:
            try:
                concepts_data = json.loads(row['concepts'])
                concepts = [f"{concept['display_name']} ({concept['score']:.2f})" 
                          for concept in concepts_data 
                          if float(concept.get('score', 0)) > 0.4]
            except:
                concepts = []

        # Extract topics
        topics = []
        if 'topics' in row and row['topics']:
            try:
                topics_data = json.loads(row['topics'])
                topics = [f"{topic['display_name']} ({topic['subfield']['display_name']})" 
                         for topic in topics_data]
            except:
                topics = []

        # Journal and metrics section with modified impact factor display
        metrics_col2 = [
            html.P([html.Strong("Citations: "), str(row.get("citations", 0))]),
            html.P([html.Strong("Quartile: "), row.get("quartile", "N/A")])
        ]
        
        # Only add impact factor if it's greater than 0
        if row.get('impact_factor', 0) > 0:
            metrics_col2.insert(0, 
                html.P([
                    html.Strong("Impact Factor: "), 
                    f"{row.get('impact_factor', 0):.2f}",
                    html.Span(" (based on 2024 estimates)", 
                             className="text-muted small ms-1")
                ])
            )
        
        # Create the modal content
        content = [
            html.H5(row["title"], className="mb-3"),
            
            # Authors section
            html.P([html.Strong("Authors: "), dcc.Markdown(authors_text)]),
            
            # Journal and metrics section
            dbc.Row([
                dbc.Col([
                    html.P([html.Strong("Journal: "), row.get("journal_name", "Unknown")]),
                    html.P([html.Strong("Publication Date: "), row.get("publication_date", "N/A")]),
                    html.P([html.Strong("PMID: "), str(row.get("pmid", "N/A"))]),
                ], width=6),
                dbc.Col(metrics_col2, width=6),
            ], className="mb-3"),
            
            # Abstract section
            html.Div([
                html.Strong("Abstract: "),
                html.P(row.get("abstract", "No abstract available"), 
                      className="mt-2 text-justify"),
            ], className="mb-3"),
            
            # Abstract summary if available
            html.Div([
                html.Strong("Abstract Summary: "),
                html.P(row.get("abstract_summary", "No summary available"),
                      className="mt-2 text-justify"),
            ], className="mb-3") if row.get("abstract_summary") else None,
            
            # Keywords, concepts, and topics
            dbc.Row([
                dbc.Col([
                    html.Strong("Keywords: "),
                    html.P(", ".join(json.loads(row["keywords"])) if row.get("keywords") else "No keywords available"),
                ], width=12, className="mb-2"),
                
                dbc.Col([
                    html.Strong("Key Concepts: "),
                    html.P(", ".join(concepts) if concepts else "No concepts available"),
                ], width=12, className="mb-2"),
                
                dbc.Col([
                    html.Strong("Research Topics: "),
                    html.P(", ".join(topics) if topics else "No topics available"),
                ], width=12, className="mb-2"),
            ], className="mb-3"),
        ]
        
        # Add PDF link if present - modified section
        pdf_url = row.get('pdf_url')
        if pdf_url and pdf_url.strip() and pdf_url.strip() != 'None':
            # Remove any '@' symbol if present at the start
            pdf_url = pdf_url.strip().lstrip('@')
            
            content.append(
                html.Div([
                    dbc.Button(
                        [
                            html.I(className="fas fa-file-pdf me-2"), 
                            "Download PDF"
                        ],
                        href=pdf_url,
                        target="_blank",
                        color="primary",
                        className="mt-3",
                        external_link=True
                    )
                ])
            )
            # Add a text link as fallback
            content.append(
                html.Div([
                    html.A(
                        "Direct PDF Link",
                        href=pdf_url,
                        target="_blank",
                        className="mt-2 d-block"
                    )
                ])
            )
        
        return content
    
    except Exception as e:
        print(f"Error in modal content: {str(e)}")
        return html.Div([
            "Error loading paper details",
            html.Pre(str(e))  # This will help debug the error
        ], style={'color': 'red'})


@app.callback(
    Output('publications-table', 'filter_query'),
    Input('search-input', 'value')
)
def update_filter(search_value):
    if not search_value:
        return ''
    return (
        f'{{title}} contains "{search_value}" || '
        f'{{authors}} contains "{search_value}" || '
        f'{{journal_name}} contains "{search_value}" || '
        f'{{abstract}} contains "{search_value}"'
    )


@app.callback(
    Output('publications-table', 'page_size'),
    Input('page-size-select', 'value')
)
def update_page_size(selected_size):
    return int(selected_size)

# Add callback for topic node clicks
@app.callback(
    [Output("topic-papers-modal", "is_open"),
     Output("topic-papers-content", "children")],
    [Input("topic-knowledge-graph", "clickData")],
    [State("topic-papers-modal", "is_open")]
)
def show_topic_papers(clickData, is_open):
    if clickData is None:
        return False, None
        
    topic = clickData['points'][0]['text'].split('<br>')[0]
    _, topic_to_papers = create_topic_knowledge_graph(papers_df)
    
    if topic in topic_to_papers:
        paper_ids = topic_to_papers[topic]
        related_papers = papers_df[papers_df['paper_id'].isin(paper_ids)]
        
        paper_list = []
        for _, paper in related_papers.iterrows():
            paper_list.append(
                html.Div([
                    html.H6(paper['title']),
                    html.P(f"Published in {paper['journal_name']} ({paper['publication_year']})"),
                    html.Hr()
                ])
            )
        
        return True, paper_list
    
    return False, None

# ------------------------------------------------------------------------------
# 9. Run Server
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)


