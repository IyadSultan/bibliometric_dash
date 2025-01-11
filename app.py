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

# Keep the same DB_PATH if desired
DB_PATH = 'khcc_papers.sqlite'

# 2. App initialization
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# ------------------------------------------------------------------------------
# 2.1 Global Filters
# ------------------------------------------------------------------------------
publication_type_filter = dbc.Row([
    dbc.Col([
        html.Label("Publication Types:", className="fw-bold"),
        dcc.Dropdown(
            id='publication-type-filter',
            options=[],  # Will be populated on load
            multi=True,
            placeholder="Select publication types...",
            value=[],
            className="mb-3"
        ),
        # Add a debug div to show current filter value
        html.Div(id='debug-output', style={'color': 'gray', 'fontSize': '12px'})
    ], width=12)
], className="mt-2 mb-3")

# 3. Data Loading
# ------------------------------------------------------------------------------
def load_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Modified SQL query to include authors field
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
            pdf_url,
            type,
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
                dbc.Input(
                    id="search-input",
                    type="text",
                    placeholder="Search in titles, authors, abstracts...",
                    className="mb-3"
                ),
            ], width=9),
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
            ], width=3),
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
    publication_type_filter,
    dbc.Tabs([
        dbc.Tab(tab_overview, label="Overview", tab_id="tab-overview"),
        dbc.Tab(tab_authors, label="Authors", tab_id="tab-authors"),
        dbc.Tab(tab_citations, label="Citations", tab_id="tab-citations"),
        dbc.Tab(tab_journals, label="Journal Metrics", tab_id="tab-journals"),
        dbc.Tab(tab_publication_types, label="Publication Types", tab_id="tab-publication-types"),
        dbc.Tab(tab_publications, label="Publications List", tab_id="tab-publications"),
    ]),
], fluid=True)

# ------------------------------------------------------------------------------
# 8. Callbacks
# ------------------------------------------------------------------------------
# Keep your new code callbacks for the publications tab

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
        
        formatted_authors = []
        for authorship in authorships:
            author_name = authorship['author']['display_name']
            is_khcc_author = False
            
            if 'institutions' in authorship:
                for inst in authorship['institutions']:
                    # Check KHCC ID
                    if inst.get('id') == 'https://openalex.org/I2799468983':
                        is_khcc_author = True
                        break
            # Bold if KHCC
            if is_khcc_author:
                formatted_authors.append(f"**{author_name}**")
            else:
                formatted_authors.append(author_name)
        
        authors_text = ", ".join(formatted_authors)
        
        content = [
            html.H5(row["title"]),
            html.P([html.Strong("Authors: "), dcc.Markdown(authors_text)]),
            html.P([html.Strong("Journal: "), row.get("journal_name", "Unknown")]),
            html.P([html.Strong("Year: "), str(row.get("publication_year", "N/A"))]),
        ]
        
        # Add PDF link if present
        if row.get('pdf_url'):
            content.append(
                html.P([
                    html.Strong("PDF: "),
                    html.A("Download PDF", href=row['pdf_url'], target="_blank",
                           className="btn btn-primary btn-sm")
                ])
            )
        
        # Add abstract
        content.append(html.P([
            html.Strong("Abstract: "),
            row.get("abstract", "No abstract available")
        ]))
        
        return content
    
    except Exception as e:
        print(f"Error in modal content: {str(e)}")
        return html.Div("Error loading paper details", style={'color': 'red'})


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

# 2. Separate callback just to populate the dropdown options on page load
@app.callback(
    Output('publication-type-filter', 'options'),
    Input('publication-type-filter', 'id')
)
def populate_filter_options(_):
    # Get unique types and normalize them
    types = papers_df['type'].dropna().str.strip().str.lower().unique()
    types = sorted(types)
    print("\nFilter options:")
    print("Available types:", types)
    return [{'label': t.title(), 'value': t} for t in types]

# 3. Debug callback to verify filter changes are detected
@app.callback(
    Output('debug-output', 'children'),
    Input('publication-type-filter', 'value')
)
def debug_filter_value(selected_types):
    print("Debug - Selected types:", selected_types)
    return f"Selected: {selected_types}"

# 4. Main callback for updating the tabs
@app.callback(
    [Output('tab-overview', 'children'),
     Output('tab-authors', 'children'),
     Output('tab-citations', 'children'),
     Output('tab-journals', 'children'),
     Output('tab-publication-types', 'children'),
     Output('tab-publications', 'children')],
    [Input('publication-type-filter', 'value')]
)
def update_tabs_with_filter(selected_types):
    print("\nDEBUG FILTERING:")
    print("Selected types:", selected_types)
    
    # Filter the dataframe
    filtered_df = papers_df.copy()
    
    # Debug information about the 'type' column
    print("\nColumn info:")
    print("Type column dtype:", filtered_df['type'].dtype)
    print("Unique values in type column:", filtered_df['type'].unique())
    print("Value counts:", filtered_df['type'].value_counts())
    
    if selected_types and len(selected_types) > 0:
        print("\nBefore filtering:", len(filtered_df))
        
        # Check for exact matches
        for type_val in selected_types:
            matching_rows = filtered_df[filtered_df['type'] == type_val]
            print(f"Rows matching exactly '{type_val}': {len(matching_rows)}")
        
        # Apply filter with string normalization
        filtered_df['type'] = filtered_df['type'].str.strip().str.lower()
        selected_types = [t.strip().lower() for t in selected_types]
        
        filtered_df = filtered_df[filtered_df['type'].isin(selected_types)]
        print("After filtering:", len(filtered_df))
        
        # Show sample of filtered data
        print("\nSample of filtered data:")
        print(filtered_df[['title', 'type']].head())
    
    # Create figures with filtered data
    fig_pubs, fig_cites, fig_quartile_trend = create_figures(filtered_df)
    fig_type_pie, fig_type_trend = create_publication_type_figures(filtered_df)
    
    # Create new tab contents with filtered data
    new_tab_overview = dbc.Card(
        dbc.CardBody([
            html.H4("Publications Overview", className="card-title"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(f"Total Publications: {len(filtered_df):,}"),
                            html.H5(f"Total Citations: {int(filtered_df['citations'].sum()):,}"),
                            html.H5(f"Average Citations: {filtered_df['citations'].mean():.1f}"),
                            html.H5(f"Open Access: "
                                   f"{filtered_df['is_open_access'].sum():,} "
                                   f"({(filtered_df['is_open_access'].mean()*100):.1f}%)")
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
    
    new_tab_publication_types = dbc.Card(
        dbc.CardBody([
            html.H4("Publication Types Analysis", className="card-title"),
            html.Div(f"Showing {len(filtered_df)} publications", className="mb-3"),  # Added count
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_type_pie), md=6),
                dbc.Col(dcc.Graph(figure=fig_type_trend), md=6),
            ])
        ]),
        className="mt-3"
    )
    
    # Update publications table with filtered data
    new_tab_publications = dbc.Card(
        dbc.CardBody([
            html.H4("Publications List", className="card-title"),
            html.Div(f"Showing {len(filtered_df)} publications", className="mb-3"),  # Added count
            dash_table.DataTable(
                id='publications-table',
                data=[{
                    **row,
                    'authors': ', '.join([author['author']['display_name'] for author in json.loads(row['authorships'])]) if row.get('authorships') else '',
                    'details': '🔍 View'
                } for row in filtered_df.sort_values(
                    by=['publication_year', 'publication_month'],
                    ascending=[False, False]
                ).to_dict('records')],
                columns=[
                    {'name': 'Title', 'id': 'title'},
                    {'name': 'Authors', 'id': 'authors'},
                    {'name': 'Journal', 'id': 'journal_name'},
                    {'name': 'Year', 'id': 'publication_year', 'type': 'numeric'},
                    {'name': 'Month', 'id': 'publication_month', 'type': 'numeric'},
                    {'name': 'Citations', 'id': 'citations', 'type': 'numeric'},
                    {'name': 'Details', 'id': 'details', 'presentation': 'markdown'}
                ],
                page_size=50,
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
                }
            )
        ]),
        className="mt-3"
    )
    
    # Create other tabs similarly...
    
    return (new_tab_overview, new_tab_authors, new_tab_citations, 
            new_tab_journals, new_tab_publication_types, new_tab_publications)

# ------------------------------------------------------------------------------
# 9. Run Server
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
