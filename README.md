# KHCC Publications Dashboard

A Dash-based web application for visualizing and analyzing research publications from King Hussein Cancer Center (KHCC).

## Features

### 1. Overview Tab
- Total publication metrics
- Publication trends over time
- Citation analysis
- Open access statistics

### 2. Collaboration Network Tab
- Global collaboration map
- Author collaboration networks
- Institution collaboration networks
- Country collaboration patterns
- Department collaboration analysis

### 3. Authors Tab
- Author impact analysis
- Author positions in publications

### 4. Citations Tab
- Detailed citation metrics
- Citation trends over time

### 5. Journal Metrics Tab
- Journal quartile distribution
- Impact factor analysis
- Open access trends
- Quartile trends over time

### 6. Publication Types Tab
- Distribution of publication types
- Publication type trends over time

### 7. Publications List Tab
- Searchable and sortable publications table
- Detailed paper information modal
- PDF links when available
- Customizable page size

## Technical Details

### Dependencies
```python
dash==2.14.1
dash-bootstrap-components==1.5.0
plotly==5.18.0
pandas==2.1.3
sqlite3
pycountry==23.12.1
```

### Database Schema
The application uses SQLite database (`khcc_papers.sqlite`) with the following main tables:
- papers: Contains core paper information
- khcc_authors: Contains author-specific information

### Installation & Setup

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the dashboard at `http://localhost:8050`

### Data Updates
The database can be updated by running the data collection scripts (not included in this repository).

## Usage

1. Navigate through different tabs to explore various aspects of KHCC's research output
2. Use the Publications List tab to search and filter specific papers
3. Click on any paper to view detailed information including abstract, authors, and metrics
4. Download PDFs when available through the paper details modal

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments
- King Hussein Cancer Center for providing the research data
- OpenAlex API for additional publication metadata 