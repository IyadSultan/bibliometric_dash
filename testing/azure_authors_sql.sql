-- Drop existing view if it exists
IF OBJECT_ID('dbo.vw_bibliometric_khcc_authors', 'V') IS NOT NULL
    DROP VIEW dbo.vw_bibliometric_khcc_authors;
GO

-- Create the view
CREATE VIEW dbo.vw_bibliometric_khcc_authors AS
WITH parsed_authors AS (
    SELECT 
        p.openalex_id as paper_id,
        JSON_VALUE(value, '$.author.id') as author_id,
        JSON_VALUE(value, '$.author.display_name') as author_name,
        COALESCE(JSON_VALUE(value, '$.raw_author_position'), 'unknown') as author_position,
        COALESCE(CAST(JSON_VALUE(value, '$.raw_is_corresponding') AS BIT), 0) as is_corresponding,
        YEAR(p.publication_date) as publication_year,
        p.cited_by_count as citations,
        p.journal as journal_name,
        p.quartile,
        CASE 
            WHEN ISJSON(p.open_access) = 1 
            THEN CASE 
                WHEN JSON_VALUE(p.open_access, '$.is_oa') = 'true' THEN 1 
                ELSE 0 
            END
            ELSE 0 
        END as open_access,
        p.impact_factor
    FROM dbo.GOLD_Bibliometry p
    CROSS APPLY OPENJSON(p.authorships) 
    WHERE ISJSON(p.authorships) = 1
    AND EXISTS (
        SELECT 1 
        FROM OPENJSON(JSON_QUERY(value, '$.institutions'))
        WHERE JSON_VALUE(value, '$.id') = 'https://openalex.org/I2799468983'
    )
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY paper_id, 
        CASE author_position
            WHEN 'first' THEN 1
            WHEN 'middle' THEN 2
            WHEN 'last' THEN 3
            ELSE 4
        END) as id,
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