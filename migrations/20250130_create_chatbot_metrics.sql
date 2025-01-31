-- Create chatbot metrics table
CREATE TABLE IF NOT EXISTS chatbot_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    processing_time FLOAT NOT NULL,
    message_length INTEGER NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices para análisis de rendimiento
    CONSTRAINT idx_chatbot_metrics_time 
        PRIMARY KEY (chatbot_id, timestamp)
);

-- Crear función para limpiar métricas antiguas
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
    DELETE FROM chatbot_metrics
    WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
