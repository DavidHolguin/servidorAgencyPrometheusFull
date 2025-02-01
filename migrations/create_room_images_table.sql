-- Crear tabla de imágenes de habitaciones
create table if not exists room_images (
    id uuid default uuid_generate_v4() primary key,
    room_name text not null,
    url text not null,
    description text,
    is_cover boolean default false,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Crear índice para búsqueda por nombre de habitación
create index if not exists room_images_room_name_idx on room_images (room_name);

-- Insertar algunas imágenes de ejemplo
insert into room_images (room_name, url, description, is_cover) values
    ('casa arbol', 'https://example.com/casa-arbol-1.jpg', 'Vista exterior de la Casa en el Árbol', true),
    ('casa arbol', 'https://example.com/casa-arbol-2.jpg', 'Interior acogedor de la Casa en el Árbol', false),
    ('casa arbol', 'https://example.com/casa-arbol-3.jpg', 'Vista nocturna de la Casa en el Árbol', false);

-- Crear función para actualizar el timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Crear trigger para actualizar el timestamp
create trigger update_room_images_updated_at
    before update on room_images
    for each row
    execute procedure update_updated_at_column();
