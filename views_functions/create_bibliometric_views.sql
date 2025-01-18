-- First drop all existing views
DROP VIEW IF EXISTS dbo.vw_bibliometric_khcc_authors;
DROP VIEW IF EXISTS dbo.vw_bibliometric_papers_summary;
DROP VIEW IF EXISTS dbo.vw_bibliometric_journal_metrics;
DROP VIEW IF EXISTS dbo.vw_bibliometric_collaborating_institutions;
DROP VIEW IF EXISTS dbo.vw_bibliometric_research_topics;
DROP VIEW IF EXISTS dbo.vw_bibliometric_author_productivity;
GO

-------------------------------------------------------------------------------
-- 1. KHCC Authors View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_khcc_authors AS
WITH parsed_authors AS (
    SELECT 
        CASE 
            WHEN p.openalex_id LIKE 'https://openalex.org/%' THEN p.openalex_id 
            ELSE 'https://openalex.org/' + p.openalex_id 
        END AS paper_id,
        a.author_id,
        a.author_name,
        COALESCE(auth.position, 'unknown') AS author_position,
        CAST(COALESCE(auth.corresponding, 0) AS BIT) AS is_corresponding,
        YEAR(p.publication_date) AS publication_year,
        p.cited_by_count AS citations,
        p.journal AS journal_name,
        p.quartile,
        CASE 
            WHEN ISJSON(p.open_access) = 1 
            THEN CASE 
                WHEN JSON_VALUE(p.open_access, '$.is_oa') = 'true' THEN 1 
                ELSE 0 
            END
            ELSE 0 
        END AS open_access,
        p.impact_factor
    FROM [dbo].[GOLD_Bibliometry] p
    -- Ensure only valid JSON authorships before OPENJSON
    CROSS APPLY OPENJSON(p.authorships)
    WITH (
        position       NVARCHAR(50)  '$.raw_author_position',
        corresponding  BIT          '$.raw_is_corresponding',
        author         NVARCHAR(MAX) AS JSON,
        institutions   NVARCHAR(MAX) AS JSON
    ) AS auth
    CROSS APPLY OPENJSON(auth.author)
    WITH (
        author_id   NVARCHAR(500) '$.id',
        author_name NVARCHAR(500) '$.display_name'
    ) AS a
    WHERE p.authorships IS NOT NULL 
      AND ISJSON(p.authorships) = 1
      AND dbo.fn_bibliometric_IsKHCCAuthor(p.authorships) = 1
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY paper_id, author_position) AS id,
    paper_id,
    author_id,
    author_name,
    author_position,
    is_corresponding,
    publication_year,
    citations,
    journal_name,
    quartile,
    open_access,
    impact_factor
FROM parsed_authors;
GO

-------------------------------------------------------------------------------
-- 2. Papers Summary View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_papers_summary AS
SELECT 
    CASE 
        WHEN openalex_id LIKE 'https://openalex.org/%' THEN openalex_id 
        ELSE 'https://openalex.org/' + openalex_id 
    END AS paper_id,
    COALESCE(title, 'Untitled') AS title,
    
    CAST(publication_date AS DATE) AS publication_date,
    YEAR(publication_date) AS publication_year,
    MONTH(publication_date) AS publication_month,
    
    COALESCE(journal, 'Unknown Journal') AS journal,
    COALESCE(impact_factor, 0.0) AS impact_factor,
    COALESCE(quartile, 'Unknown') AS quartile,
    COALESCE(cited_by_count, 0) AS citations,
    
    CASE 
        WHEN ISJSON(open_access) = 1 
        THEN CASE 
            WHEN JSON_VALUE(open_access, '$.is_oa') = 'true' THEN 1 
            ELSE 0 
        END
        ELSE 0 
    END AS open_access,
    
    COALESCE(type, 'Unknown') AS publication_type,
    
    -- Safely cast authorships to JSON or []
    CAST(
        CASE 
            WHEN authorships IS NOT NULL AND ISJSON(authorships) = 1 
            THEN authorships 
            ELSE '[]' 
        END 
    AS NVARCHAR(MAX)) AS authorships,
    
    -- Safely cast concepts to JSON or []
    CAST(
        CASE 
            WHEN concepts IS NOT NULL AND ISJSON(concepts) = 1 
            THEN concepts 
            ELSE '[]' 
        END 
    AS NVARCHAR(MAX)) AS concepts,
    
    -- Safely cast mesh to JSON or []
    CAST(
        CASE 
            WHEN mesh IS NOT NULL AND ISJSON(mesh) = 1 
            THEN mesh 
            ELSE '[]' 
        END 
    AS NVARCHAR(MAX)) AS mesh_terms

FROM [dbo].[GOLD_Bibliometry]
WHERE openalex_id IS NOT NULL;
GO

-------------------------------------------------------------------------------
-- 3. Journal Metrics View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_journal_metrics AS
SELECT 
    journal,
    quartile,
    impact_factor,
    COUNT(*) AS publication_count,
    SUM(cited_by_count) AS total_citations,
    AVG(CAST(cited_by_count AS FLOAT)) AS avg_citations,
    SUM(
        CASE 
            WHEN ISJSON(open_access) = 1 
            THEN CASE 
                WHEN JSON_VALUE(open_access, '$.is_oa') = 'true' THEN 1 
                ELSE 0 
            END
            ELSE 0 
        END
    ) AS open_access_count,
    MIN(YEAR(publication_date)) AS first_publication_year,
    MAX(YEAR(publication_date)) AS latest_publication_year
FROM [dbo].[GOLD_Bibliometry]
WHERE journal IS NOT NULL
GROUP BY journal, quartile, impact_factor;
GO

-------------------------------------------------------------------------------
-- 4. Collaborating Institutions View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_collaborating_institutions AS
WITH parsed_institutions AS (
    SELECT 
        p.openalex_id AS paper_id,
        p.publication_date,
        YEAR(p.publication_date) AS publication_year,
        inst.institution_id,
        inst.institution_name,
        inst.country_code
    FROM [dbo].[GOLD_Bibliometry] p
    CROSS APPLY OPENJSON(p.authorships)
    WITH (
        institutions NVARCHAR(MAX) AS JSON
    ) AS auth
    CROSS APPLY OPENJSON(auth.institutions)
    WITH (
        institution_id   NVARCHAR(500) '$.id',
        institution_name NVARCHAR(500) '$.display_name',
        country_code     NVARCHAR(10)  '$.country_code'
    ) AS inst
    WHERE p.authorships IS NOT NULL
      AND ISJSON(p.authorships) = 1
      AND inst.institution_id IS NOT NULL
      AND inst.institution_name IS NOT NULL
      AND inst.institution_id != 'https://openalex.org/I2799468983'
)
SELECT 
    institution_id,
    institution_name,
    COALESCE(country_code, 'Unknown') AS country_code,
    COUNT(DISTINCT paper_id) AS collaboration_count,
    MIN(publication_year) AS first_collaboration_year,
    MAX(publication_year) AS latest_collaboration_year
FROM parsed_institutions
WHERE institution_id IS NOT NULL
GROUP BY institution_id, institution_name, country_code;
GO

-------------------------------------------------------------------------------
-- 5. Research Topics View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_research_topics AS
WITH parsed_concepts AS (
    SELECT 
        openalex_id AS paper_id,
        YEAR(publication_date) AS publication_year,
        c.concept_id,
        c.concept_name,
        c.score
    FROM [dbo].[GOLD_Bibliometry]
    CROSS APPLY OPENJSON(concepts)
    WITH (
        concept_id   NVARCHAR(500) '$.id',
        concept_name NVARCHAR(500) '$.display_name',
        score        FLOAT         '$.score'
    ) AS c
    WHERE concepts IS NOT NULL 
      AND ISJSON(concepts) = 1
)
SELECT 
    concept_id,
    concept_name,
    COUNT(DISTINCT paper_id) AS papers_count,
    AVG(score) AS avg_relevance_score,
    -- Use VARCHAR(MAX) to avoid STRING_AGG hitting 8,000 limit
    STRING_AGG(CAST(publication_year AS VARCHAR(MAX)), ',') AS years_active
FROM parsed_concepts
WHERE score >= 0.5
GROUP BY concept_id, concept_name;
GO

-------------------------------------------------------------------------------
-- 6. Author Productivity View
-------------------------------------------------------------------------------
CREATE VIEW dbo.vw_bibliometric_author_productivity AS
SELECT 
    a.author_name,
    COUNT(DISTINCT a.paper_id) AS total_papers,
    SUM(CAST(a.is_corresponding AS INT)) AS corresponding_author_count,
    SUM(p.cited_by_count) AS total_citations,
    AVG(CAST(p.cited_by_count AS FLOAT)) AS avg_citations_per_paper,
    -- Again, cast to VARCHAR(MAX) for safety
    STRING_AGG(CAST(YEAR(p.publication_date) AS VARCHAR(MAX)), ',') AS active_years,
    COUNT(DISTINCT p.journal) AS unique_journals,
    COUNT(DISTINCT YEAR(p.publication_date)) AS years_active
FROM dbo.vw_bibliometric_khcc_authors a
JOIN [dbo].[GOLD_Bibliometry] p 
    ON p.openalex_id = a.paper_id
GROUP BY a.author_name;
GO

-------------------------------------------------------------------------------
-- Grant SELECT permissions on all new views
-------------------------------------------------------------------------------
DECLARE @ViewName NVARCHAR(128);
DECLARE @SQL NVARCHAR(MAX);

DECLARE view_cursor CURSOR FOR 
    SELECT name 
    FROM sys.views 
    WHERE name LIKE 'vw_bibliometric%';

OPEN view_cursor;
FETCH NEXT FROM view_cursor INTO @ViewName;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @SQL = 'GRANT SELECT ON dbo.' + QUOTENAME(@ViewName) + ' TO PUBLIC';
    EXEC sp_executesql @SQL;
    FETCH NEXT FROM view_cursor INTO @ViewName;
END;

CLOSE view_cursor;
DEALLOCATE view_cursor;

-------------------------------------------------------------------------------
-- Check creation success
-------------------------------------------------------------------------------
SELECT 
    'Successfully created ' + CAST(COUNT(*) AS VARCHAR) + ' views.' AS Status
FROM sys.views 
WHERE name LIKE 'vw_bibliometric%';
GO
