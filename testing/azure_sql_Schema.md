Inspecting database schema...

Available views:
                                   TABLE_NAME
0         vw_bibliometric_author_productivity
1  vw_bibliometric_collaborating_institutions
2              vw_bibliometric_collaborations
3          vw_bibliometric_department_metrics
4             vw_bibliometric_journal_metrics
5                vw_bibliometric_khcc_authors
6              vw_bibliometric_papers_summary
7             vw_bibliometric_research_topics
8               vw_bibliometric_topic_network

Columns in vw_bibliometric_author_productivity:
                  COLUMN_NAME DATA_TYPE
0                 author_name  nvarchar
1                total_papers       int
2  corresponding_author_count       int
3             total_citations       int
4     avg_citations_per_paper     float
5                active_years   varchar
6             unique_journals       int
7                years_active       int

Columns in vw_bibliometric_collaborating_institutions:
                 COLUMN_NAME DATA_TYPE
0             institution_id  nvarchar
1           institution_name  nvarchar
2               country_code  nvarchar
3        collaboration_count       int
4   first_collaboration_year       int
5  latest_collaboration_year       int

Columns in vw_bibliometric_collaborations:
                COLUMN_NAME DATA_TYPE
0                   author1  nvarchar
1                   author2  nvarchar
2       collaboration_count       int
3       collaboration_years   varchar
4                dept1_list  nvarchar
5                dept2_list  nvarchar
6  dept_collaboration_count       int
7        collaboration_type   varchar

Columns in vw_bibliometric_department_metrics:
         COLUMN_NAME DATA_TYPE
0         department  nvarchar
1  publication_count       int
2    total_citations       int
3      avg_citations     float
4       author_count       int
5    unique_journals       int
6  avg_impact_factor     float
7       active_years   varchar
8          q1_papers       int

Columns in vw_bibliometric_journal_metrics:
               COLUMN_NAME DATA_TYPE
0                  journal  nvarchar
1                 quartile  nvarchar
2            impact_factor      real
3        publication_count       int
4          total_citations       int
5            avg_citations     float
6        open_access_count       int
7   first_publication_year       int
8  latest_publication_year       int

Columns in vw_bibliometric_khcc_authors:
         COLUMN_NAME DATA_TYPE
0                 id    bigint
1           paper_id  nvarchar
2          author_id  nvarchar
3        author_name  nvarchar
4    author_position  nvarchar
5   is_corresponding       bit
6   publication_year       int
7          citations       int
8       journal_name  nvarchar
9           quartile  nvarchar
10       open_access       int
11     impact_factor      real

Columns in vw_bibliometric_papers_summary:
          COLUMN_NAME DATA_TYPE
0            paper_id  nvarchar
1               title  nvarchar
2    publication_date      date
3    publication_year       int
4   publication_month       int
5             journal  nvarchar
6       impact_factor      real
7            quartile  nvarchar
8           citations       int
9         open_access       int
10   publication_type  nvarchar
11        authorships  nvarchar
12           concepts  nvarchar
13         mesh_terms  nvarchar

Columns in vw_bibliometric_research_topics:
           COLUMN_NAME DATA_TYPE
0           concept_id  nvarchar
1         concept_name  nvarchar
2         papers_count       int
3  avg_relevance_score     float
4         years_active   varchar

Columns in vw_bibliometric_topic_network:
           COLUMN_NAME DATA_TYPE
0            source_id  nvarchar
1          source_name  nvarchar
2            target_id  nvarchar
3          target_name  nvarchar
4   cooccurrence_count       int
5  connection_strength   numeric

Sample data columns:
['paper_id', 'title', 'publication_date', 'publication_year', 'publication_month', 'journal', 'impact_factor', 'quartile', 'citations', 'open_access', 'publication_type', 'authorships', 'concepts', 'mesh_terms']