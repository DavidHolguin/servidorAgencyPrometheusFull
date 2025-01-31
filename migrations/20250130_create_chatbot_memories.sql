-- Create chatbot memories table
CREATE TABLE IF NOT EXISTS chatbot_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    lead_id UUID,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    relevance_score FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Índices para búsqueda eficiente
    CONSTRAINT unique_chatbot_key UNIQUE (chatbot_id, key)
);

-- Crear índice para búsqueda por texto
CREATE INDEX IF NOT EXISTS idx_chatbot_memories_key_value ON chatbot_memories USING gin (
    to_tsvector('spanish', key || ' ' || value)
);

-- Crear índice para búsqueda por relevancia
CREATE INDEX IF NOT EXISTS idx_chatbot_memories_relevance ON chatbot_memories (relevance_score DESC);

-- Función para actualizar el timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para actualizar el timestamp
CREATE TRIGGER update_chatbot_memories_updated_at
    BEFORE UPDATE ON chatbot_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Función para limpiar memorias expiradas
CREATE OR REPLACE FUNCTION cleanup_expired_memories()
RETURNS void AS $$
BEGIN
    DELETE FROM chatbot_memories
    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Programar limpieza diaria de memorias expiradas
SELECT cron.schedule(
    'cleanup-expired-memories',
    '0 0 * * *',  -- Ejecutar a medianoche todos los días
    'SELECT cleanup_expired_memories()'
);
