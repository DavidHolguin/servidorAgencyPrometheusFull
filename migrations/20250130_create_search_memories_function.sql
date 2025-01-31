-- Función para búsqueda de memorias
CREATE OR REPLACE FUNCTION search_memories(
    search_query TEXT,
    chatbot_id UUID,
    min_relevance FLOAT DEFAULT 0.5,
    limit_param INTEGER DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    chatbot_id UUID,
    lead_id UUID,
    key TEXT,
    value TEXT,
    created_at TIMESTAMPTZ,
    relevance_score FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cm.id,
        cm.chatbot_id,
        cm.lead_id,
        cm.key,
        cm.value,
        cm.created_at,
        cm.relevance_score,
        cm.metadata
    FROM chatbot_memories cm
    WHERE 
        cm.chatbot_id = search_memories.chatbot_id
        AND cm.relevance_score >= min_relevance
        AND (
            to_tsvector('spanish', cm.key || ' ' || cm.value) @@ plainto_tsquery('spanish', search_query)
            OR cm.key ILIKE '%' || search_query || '%'
            OR cm.value ILIKE '%' || search_query || '%'
        )
    ORDER BY 
        ts_rank(to_tsvector('spanish', cm.key || ' ' || cm.value), plainto_tsquery('spanish', search_query)) DESC,
        cm.relevance_score DESC,
        cm.created_at DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- Crear índice GIN para búsqueda full-text
CREATE INDEX IF NOT EXISTS idx_chatbot_memories_full_text ON chatbot_memories 
USING gin(to_tsvector('spanish', key || ' ' || value));
