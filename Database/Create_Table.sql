CREATE TABLE fingerprints (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    template BYTEA NOT NULL,
    template_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
