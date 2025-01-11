-- Create authors table
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT,
    author_name TEXT,
    author_position TEXT,
    is_corresponding BOOLEAN
);

-- Extract paper ID from the OpenAlex URL
UPDATE papers 
SET paper_id = SUBSTR(paper_id, 27) 
WHERE paper_id LIKE 'https://openalex.org/W%';

-- Insert authors from KHCC into authors table
INSERT INTO authors (paper_id, author_name, author_position, is_corresponding)
SELECT 
    paper_id,
    json_extract(value, '$.author.display_name') as author_name,
    json_extract(value, '$.author_position') as author_position,
    json_extract(value, '$.is_corresponding') as is_corresponding
FROM papers,
json_each(papers.authorships) 
WHERE json_extract(value, '$.institutions[0].id') = 'https://openalex.org/I2799468983';

-- Query to view the results
SELECT 
    a.paper_id,
    a.author_name,
    a.author_position,
    CASE 
        WHEN a.is_corresponding = 1 THEN 'Yes'
        ELSE 'No'
    END as is_corresponding
FROM authors a
ORDER BY a.paper_id, 
    CASE a.author_position
        WHEN 'first' THEN 1
        WHEN 'middle' THEN 2
        WHEN 'last' THEN 3
        ELSE 4
    END;