-- Initialize SkillPM registry database
-- Author: Bogdan Ticu

CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    gpg_key TEXT,
    gpg_verified BOOLEAN DEFAULT FALSE,
    bio TEXT,
    website VARCHAR(255),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    version VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    license VARCHAR(50) NOT NULL,
    repository VARCHAR(255) NOT NULL,
    homepage VARCHAR(255),
    language VARCHAR(50) NOT NULL,
    entry_point VARCHAR(255) NOT NULL,
    capabilities JSONB,
    dependencies JSONB,
    tags JSONB,
    author_verified BOOLEAN DEFAULT FALSE,
    maintenance_status VARCHAR(50) DEFAULT 'active',
    downloads_total INTEGER DEFAULT 0,
    downloads_month INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0.0,
    reviews_count INTEGER DEFAULT 0,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author) REFERENCES authors(username)
);

CREATE TABLE IF NOT EXISTS installations (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) NOT NULL,
    skill_version VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (skill_name) REFERENCES skills(name)
);

CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) NOT NULL,
    skill_version VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    duration_ms INTEGER,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    author VARCHAR(255) NOT NULL,
    definition JSONB NOT NULL,
    downloads INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0.0,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author) REFERENCES authors(username)
);

CREATE INDEX idx_skills_author ON skills(author);
CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_installations_skill ON installations(skill_name);
CREATE INDEX idx_reviews_skill ON reviews(skill_name);
CREATE INDEX idx_executions_skill ON executions(skill_name);
CREATE INDEX idx_workflows_author ON workflows(author);

INSERT INTO authors (username, email, display_name, verified)
VALUES ('skillpm-registry', 'registry@skillpm.dev', 'SkillPM Registry', true)
ON CONFLICT DO NOTHING;
