-- Complete the landing_interactions table
CREATE TABLE IF NOT EXISTS landing_interactions (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    landing_page_id uuid REFERENCES landing_pages(id),
    lead_id uuid REFERENCES leads(id),
    component_id text NOT NULL,
    interaction_type text NOT NULL,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);

-- Add RLS policy for landing_interactions
ALTER TABLE landing_interactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their landing interactions"
ON landing_interactions
FOR ALL
TO authenticated
USING (
    landing_page_id IN (
        SELECT id FROM landing_pages 
        WHERE agency_id IN (
            SELECT id FROM agencies 
            WHERE profile_id = auth.uid()
        )
    )
);

CREATE POLICY "Public can create landing interactions"
ON landing_interactions
FOR INSERT
WITH CHECK (true);

-- Create index for better performance
CREATE INDEX idx_landing_interactions_landing_page ON landing_interactions(landing_page_id);
CREATE INDEX idx_landing_interactions_lead ON landing_interactions(lead_id);

-- Add trigger for tracking interactions
CREATE OR REPLACE FUNCTION update_lead_on_interaction()
RETURNS trigger AS $$
BEGIN
    UPDATE leads
    SET 
        last_interaction = NOW(),
        updated_at = NOW()
    WHERE id = NEW.lead_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_landing_interaction
    AFTER INSERT ON landing_interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_lead_on_interaction();

COMMENT ON TABLE landing_interactions IS 'Tracks user interactions with landing page components';
COMMENT ON COLUMN landing_interactions.component_id IS 'Identifier of the interacted component';
COMMENT ON COLUMN landing_interactions.interaction_type IS 'Type of interaction (click, view, submit, etc.)';
COMMENT ON COLUMN landing_interactions.metadata IS 'Additional interaction data';

-- Modificar la tabla chatbots para incluir más configuraciones
ALTER TABLE chatbots
ADD COLUMN IF NOT EXISTS personality jsonb DEFAULT '{
    "tone": "profesional",
    "formality_level": "formal",
    "emoji_usage": "moderado",
    "language_style": "claro y conciso"
}'::jsonb,
ADD COLUMN IF NOT EXISTS welcome_message text,
ADD COLUMN IF NOT EXISTS key_points jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS example_qa jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS special_instructions jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS response_weights jsonb DEFAULT '{
    "key_points_weight": 0.3,
    "example_qa_weight": 0.4,
    "special_instructions_weight": 0.5
}'::jsonb,
ADD COLUMN IF NOT EXISTS purpose text,
ADD COLUMN IF NOT EXISTS context_template jsonb DEFAULT '{
    "agency_info": true,
    "available_services": true,
    "pricing_info": true,
    "booking_process": true
}'::jsonb;

-- Agregar comentarios para documentación
COMMENT ON COLUMN chatbots.personality IS 'Configuración de la personalidad del chatbot incluyendo tono, formalidad y uso de emojis';
COMMENT ON COLUMN chatbots.welcome_message IS 'Mensaje de bienvenida personalizado';
COMMENT ON COLUMN chatbots.key_points IS 'Puntos clave que el chatbot debe considerar en sus respuestas';
COMMENT ON COLUMN chatbots.example_qa IS 'Ejemplos de preguntas y respuestas para entrenar al chatbot';
COMMENT ON COLUMN chatbots.special_instructions IS 'Instrucciones especiales con alto peso en la toma de decisiones';
COMMENT ON COLUMN chatbots.response_weights IS 'Pesos para diferentes aspectos en la generación de respuestas';
COMMENT ON COLUMN chatbots.purpose IS 'Propósito general del chatbot';
COMMENT ON COLUMN chatbots.context_template IS 'Plantilla de contexto para incluir información específica';

-- Crear índice para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_chatbots_purpose ON chatbots USING gin (to_tsvector('spanish', purpose));
CREATE INDEX IF NOT EXISTS idx_chatbots_personality ON chatbots USING gin (personality);
CREATE INDEX IF NOT EXISTS idx_chatbots_key_points ON chatbots USING gin (key_points);
