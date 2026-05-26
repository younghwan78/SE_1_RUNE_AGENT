LOAD 'age';

SET search_path = ag_catalog, "$user", public;

SELECT drop_graph('soc_graph', true)
WHERE EXISTS (
    SELECT 1
    FROM ag_catalog.ag_graph
    WHERE name = 'soc_graph'
);
