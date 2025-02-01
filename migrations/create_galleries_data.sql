-- Insertar galerías de ejemplo
INSERT INTO image_galleries (id, name, description, keywords) VALUES
    ('550e8400-e29b-41d4-a716-446655440000', 'Casa del Árbol', 'Galería de imágenes de nuestra Casa del Árbol', ARRAY['casa', 'arbol', 'tree', 'house', 'photo']),
    ('550e8400-e29b-41d4-a716-446655440001', 'Cabaña Presidencial', 'Galería de imágenes de la Cabaña Presidencial', ARRAY['cabaña', 'presidencial', 'presidential', 'cabin', 'photo']),
    ('550e8400-e29b-41d4-a716-446655440002', 'Cabaña Cacique', 'Galería de imágenes de la Cabaña Cacique', ARRAY['cabaña', 'cacique', 'cabin', 'photo']),
    ('550e8400-e29b-41d4-a716-446655440003', 'Casa Roca', 'Galería de imágenes de la Casa Roca', ARRAY['casa', 'roca', 'rock', 'house', 'photo']);

-- Insertar imágenes de ejemplo para Casa del Árbol
INSERT INTO gallery_images (gallery_id, url, name, description, keywords, position) VALUES
    ('550e8400-e29b-41d4-a716-446655440000', 'https://example.com/casa-arbol-1.jpg', 'Exterior Casa Árbol', 'Vista exterior de la Casa del Árbol', ARRAY['exterior', 'casa', 'arbol'], 1),
    ('550e8400-e29b-41d4-a716-446655440000', 'https://example.com/casa-arbol-2.jpg', 'Interior Casa Árbol', 'Sala de estar de la Casa del Árbol', ARRAY['interior', 'sala', 'casa', 'arbol'], 2),
    ('550e8400-e29b-41d4-a716-446655440000', 'https://example.com/casa-arbol-3.jpg', 'Terraza Casa Árbol', 'Terraza con vista panorámica', ARRAY['terraza', 'vista', 'casa', 'arbol'], 3);

-- Insertar imágenes de ejemplo para Cabaña Presidencial
INSERT INTO gallery_images (gallery_id, url, name, description, keywords, position) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'https://example.com/cabana-presidencial-1.jpg', 'Exterior Cabaña', 'Vista exterior de la Cabaña Presidencial', ARRAY['exterior', 'cabaña', 'presidencial'], 1),
    ('550e8400-e29b-41d4-a716-446655440001', 'https://example.com/cabana-presidencial-2.jpg', 'Suite Principal', 'Suite principal con jacuzzi', ARRAY['interior', 'suite', 'cabaña', 'presidencial'], 2),
    ('550e8400-e29b-41d4-a716-446655440001', 'https://example.com/cabana-presidencial-3.jpg', 'Sala Estar', 'Amplia sala de estar', ARRAY['interior', 'sala', 'cabaña', 'presidencial'], 3);

-- Insertar imágenes de ejemplo para Cabaña Cacique
INSERT INTO gallery_images (gallery_id, url, name, description, keywords, position) VALUES
    ('550e8400-e29b-41d4-a716-446655440002', 'https://example.com/cabana-cacique-1.jpg', 'Vista Frontal', 'Vista frontal de la Cabaña Cacique', ARRAY['exterior', 'cabaña', 'cacique'], 1),
    ('550e8400-e29b-41d4-a716-446655440002', 'https://example.com/cabana-cacique-2.jpg', 'Dormitorio', 'Dormitorio principal', ARRAY['interior', 'dormitorio', 'cabaña', 'cacique'], 2),
    ('550e8400-e29b-41d4-a716-446655440002', 'https://example.com/cabana-cacique-3.jpg', 'Cocina', 'Cocina equipada', ARRAY['interior', 'cocina', 'cabaña', 'cacique'], 3);

-- Insertar imágenes de ejemplo para Casa Roca
INSERT INTO gallery_images (gallery_id, url, name, description, keywords, position) VALUES
    ('550e8400-e29b-41d4-a716-446655440003', 'https://example.com/casa-roca-1.jpg', 'Exterior Casa Roca', 'Vista exterior de la Casa Roca', ARRAY['exterior', 'casa', 'roca'], 1),
    ('550e8400-e29b-41d4-a716-446655440003', 'https://example.com/casa-roca-2.jpg', 'Sala Principal', 'Sala principal con chimenea', ARRAY['interior', 'sala', 'casa', 'roca'], 2),
    ('550e8400-e29b-41d4-a716-446655440003', 'https://example.com/casa-roca-3.jpg', 'Terraza', 'Terraza con vista al bosque', ARRAY['exterior', 'terraza', 'casa', 'roca'], 3);
