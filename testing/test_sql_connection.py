(venv) E:\code\bibliometric_dash>python e:\code\bibliometric_dash\test_sql_connection.py

Testing database connection and queries...

1. Testing KHCC authors query...
Retrieved 0 authors
Empty DataFrame
Columns: [author_name, paper_id, citations]
Index: []

2. Testing author metrics query...
Retrieved metrics for 0 authors
Empty DataFrame
Columns: [author_name, total_papers, total_citations]
Index: []

3. Testing journal metrics query...
Retrieved metrics for 837 journals

4. Testing search functionality...

Error during testing: (pyodbc.ProgrammingError) ('42S22', "[42S22] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Invalid column name 'journal'. (207) (SQLExecDirectW); [42S22] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Statement(s) could not be prepared. (8180)")
[SQL:
        SELECT p.*
        FROM dbo.vw_bibliometric_papers_summary p
        LEFT JOIN dbo.vw_bibliometric_khcc_authors a
            ON p.paper_id = a.paper_id
        WHERE
            p.title LIKE ? OR
            a.author_name LIKE ? OR
            p.journal LIKE ?
        ]
[parameters: ('%cancer%', '%cancer%', '%cancer%')]
(Background on this error at: https://sqlalche.me/e/20/f405)