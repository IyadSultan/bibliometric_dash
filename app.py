"""
Review of the Dash application code.

Below is a consolidated version of app.py with proper ordering:
1. Imports
2. Initial data loading and processing for figures
3. Functions for data loading and tab creation
4. App instantiation (inside if __name__ == '__main__')
5. Tab definitions
6. Layout definition
7. Callbacks
8. App runner

This ordering avoids "Error loading layout" by ensuring all referenced objects are defined before the layout is declared.
"""

# 1. Imports
import dash
from dash import html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash.dash_table.Format import Format, Scheme
import pandas as pd
import sqlite3
import json

# Initialize the app at the very top
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

def load_data():
    print("Loading initial data...")
    conn = sqlite3.connect('khcc_papers.sqlite')
    df = pd.read_sql_query("SELECT * FROM papers", conn)
    conn.close()
    
    # Add publication_month column if it doesn't exist
    if 'publication_date' in df.columns:
        df['publication_month'] = pd.to_datetime(df['publication_date']).dt.month
    else:
        df['publication_month'] = 1  # Default to January if no date available
    
    return df

def create_figures(papers_df):
    print("Creating figures...")
    yearly_metrics = papers_df.groupby("publication_year").agg({
        "citations": ["sum", "mean", "count"]
    }).reset_index()
    yearly_metrics.columns = ['publication_year', 'total_citations', 'mean_citations', 'publications']
    
    fig_pubs = px.line(
        yearly_metrics,
        x="publication_year",
        y="publications",
        title="Publications by Year"
    )
    
    fig_cites = px.line(
        yearly_metrics,
        x="publication_year",
        y="mean_citations",
        title="Citations Trend"
    )
    
    return fig_pubs, fig_cites

# Load data and create figures
papers_df = load_data()
fig_pubs, fig_cites = create_figures(papers_df)

# Define tab contents
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
                        html.H5(f"Open Access: {papers_df['is_open_access'].sum():,} ({(papers_df['is_open_access'].mean()*100):.1f}%)")
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

# Update the publications table with formatted authors
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
        'authors': ', '.join(eval(row['authors'])),  # Convert JSON array string to comma-separated authors
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

# First, get the total number of publications
total_pubs = len(papers_df)

# Update the publications tab with dynamic page size control
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

# Define the layout with tabs
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
        dbc.Tab(tab_publications, label="Publications List", tab_id="tab-publications"),
    ]),
], fluid=True)

# Add callbacks for the modal
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
        # Calculate the actual row index based on current page
        actual_row_index = (page_current * page_size) + active_cell["row"]
        row = virtual_data[actual_row_index]
        
        # Parse authorships JSON and format authors list
        authorships = json.loads(row['authorships'])
        formatted_authors = []
        
        for authorship in authorships:
            author_name = authorship['author']['display_name']
            is_khcc_author = False
            
            # Check if author has KHCC affiliation
            if 'institutions' in authorship:
                for inst in authorship['institutions']:
                    if inst.get('id') == 'https://openalex.org/I2799468983':  # KHCC ID
                        is_khcc_author = True
                        break
            
            # Format author name with bold if from KHCC
            if is_khcc_author:
                formatted_authors.append(f"**{author_name}**")
            else:
                formatted_authors.append(author_name)
        
        authors_text = ", ".join(formatted_authors)
        
        content = [
            html.H5(row["title"]),
            html.P([
                html.Strong("Authors: "),
                dcc.Markdown(authors_text)
            ]),
            html.P([
                html.Strong("Journal: "),
                row["journal_name"]
            ]),
            html.P([
                html.Strong("Year: "),
                str(row["publication_year"])
            ])
        ]
        
        # Add PDF link if it exists
        if row.get('pdf_url'):
            content.append(html.P([
                html.Strong("PDF: "),
                html.A("Download PDF", 
                      href=row['pdf_url'],
                      target="_blank",
                      className="btn btn-primary btn-sm")
            ]))
        
        # Add abstract
        content.append(html.P([
            html.Strong("Abstract: "),
            row.get("abstract", "No abstract available")
        ]))
        
        return content
    
    except Exception as e:
        print(f"Error in modal content: {str(e)}")
        return html.Div("Error loading paper details", 
                       style={'color': 'red'})

# Update the callback for search functionality
@app.callback(
    Output('publications-table', 'filter_query'),
    Input('search-input', 'value')
)
def update_filter(search_value):
    if not search_value:
        return ''
    # Search across multiple columns
    return f'{{title}} contains "{search_value}" || {{authors}} contains "{search_value}" || {{journal_name}} contains "{search_value}" || {{abstract}} contains "{search_value}"'

# Add callback to update page size
@app.callback(
    Output('publications-table', 'page_size'),
    Input('page-size-select', 'value')
)
def update_page_size(selected_size):
    return int(selected_size)

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)