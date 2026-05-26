"""pgvector query builder for SoC artifact retrieval."""

from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.storage_sql import StorageQuery


class PgVectorSearchBackend:
    """Build parameterized pgvector similarity queries."""

    def build_search(
        self,
        *,
        query_vector: list[float],
        query_slice: SocSlice,
        limit: int = 50,
    ) -> StorageQuery:
        """Return a parameterized pgvector query for one SoC slice."""
        where_sql, where_params = _slice_filters(query_slice)
        sql = f"""
            SELECT
                a.external_id,
                a.source_type,
                a.source_url,
                a.project_key,
                a.title,
                a.body_text,
                a.created_at,
                a.updated_at,
                a.labels,
                a.links,
                a.metadata
            FROM soc_artifact_embeddings e
            JOIN soc_artifacts a ON a.external_id = e.artifact_id
            WHERE {where_sql}
            ORDER BY e.embedding <=> %s::vector ASC, a.external_id ASC
            LIMIT %s
        """
        return StorageQuery(
            tool="vector_search",
            sql=sql,
            params=(*where_params, _vector_literal(query_vector), limit),
        )


def _slice_filters(query_slice: SocSlice) -> tuple[str, tuple[object, ...]]:
    filters: list[str] = ["true"]
    params: list[object] = []
    if query_slice.project_keys:
        filters.append("a.project_key = ANY(%s)")
        params.append(query_slice.project_keys)
    if query_slice.v_levels:
        filters.append("a.metadata->'soc_axes'->>'v_level' = ANY(%s)")
        params.append([str(item) for item in query_slice.v_levels])
    if query_slice.concerns:
        filters.append("a.metadata->'soc_axes'->'concerns' ?| %s")
        params.append(query_slice.concerns)
    if query_slice.components:
        filters.append("a.metadata->'soc_axes'->'components' ?| %s")
        params.append(query_slice.components)
    if query_slice.artifact_id:
        filters.append("a.external_id = %s")
        params.append(query_slice.artifact_id)
    return " AND ".join(filters), tuple(params)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"
