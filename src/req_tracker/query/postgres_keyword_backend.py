"""PostgreSQL FTS/pg_trgm query builder for SoC artifacts."""

from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.storage_sql import StorageQuery


class PostgresKeywordSearchBackend:
    """Build parameterized Postgres FTS and trigram search queries."""

    def build_search(
        self,
        *,
        user_query: str,
        query_slice: SocSlice,
        limit: int = 50,
    ) -> StorageQuery:
        """Return a parameterized keyword search query for one SoC slice."""
        where_sql, where_params = _slice_filters(query_slice)
        sql = f"""
            SELECT
                external_id,
                source_type,
                source_url,
                project_key,
                title,
                body_text,
                created_at,
                updated_at,
                labels,
                links,
                metadata
            FROM soc_artifacts
            WHERE {where_sql}
              AND (
                to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body_text, ''))
                  @@ plainto_tsquery('simple', %s)
                OR similarity(coalesce(title, '') || ' ' || coalesce(body_text, ''), %s) > 0.05
              )
            ORDER BY
                ts_rank(
                    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body_text, '')),
                    plainto_tsquery('simple', %s)
                ) DESC,
                similarity(coalesce(title, '') || ' ' || coalesce(body_text, ''), %s) DESC,
                created_at ASC,
                external_id ASC
            LIMIT %s
        """
        return StorageQuery(
            tool="keyword_search",
            sql=sql,
            params=(*where_params, user_query, user_query, user_query, user_query, limit),
        )


def _slice_filters(query_slice: SocSlice) -> tuple[str, tuple[object, ...]]:
    filters: list[str] = ["true"]
    params: list[object] = []
    if query_slice.project_keys:
        filters.append("project_key = ANY(%s)")
        params.append(query_slice.project_keys)
    if query_slice.v_levels:
        filters.append("metadata->'soc_axes'->>'v_level' = ANY(%s)")
        params.append([str(item) for item in query_slice.v_levels])
    if query_slice.concerns:
        filters.append("metadata->'soc_axes'->'concerns' ?| %s")
        params.append(query_slice.concerns)
    if query_slice.components:
        filters.append("metadata->'soc_axes'->'components' ?| %s")
        params.append(query_slice.components)
    if query_slice.artifact_id:
        filters.append("external_id = %s")
        params.append(query_slice.artifact_id)
    return " AND ".join(filters), tuple(params)
