-- 20260511000000_init_schema.sql
-- Database Schema for Company Intelligence Platform

-- Enable UUID extension if not already present
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (To identify queries with owners)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Seed a default admin user for application setup
INSERT INTO users (id, email)
VALUES ('00000000-0000-0000-0000-000000000000', 'admin@companyintel.com')
ON CONFLICT (email) DO NOTHING;

-- 2. Research Sessions Table
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    custom_query TEXT,
    status VARCHAR(50) DEFAULT 'initiated', -- initiated, researching, consolidating, validating, regenerating, completed, failed
    confidence_score NUMERIC(4,3) DEFAULT 0.000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Index for speedy lookups
CREATE INDEX IF NOT EXISTS idx_research_sessions_company_name ON research_sessions(company_name);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status ON research_sessions(status);

-- 3. Agent Outputs Table (Stores intermediate raw research outputs per agent)
CREATE TABLE IF NOT EXISTS agent_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    agent_name VARCHAR(50) NOT NULL, -- website, linkedin, news, funding, product, social
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    raw_json_output JSONB,
    token_usage INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_agent_outputs_session_id ON agent_outputs(session_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_output_session_agent ON agent_outputs(session_id, agent_name);

-- 4. Validation Logs Table (Tracks validation checks and history of regeneration loops)
CREATE TABLE IF NOT EXISTS validation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL,
    rules_checked JSONB NOT NULL, -- JSON array of {rule_name, field, passed, message}
    overall_confidence NUMERIC(4,3) NOT NULL,
    failed_fields TEXT[],
    needs_regeneration BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_validation_logs_session_id ON validation_logs(session_id);

-- 5. Final Reports Table (Stores compiled executive profiles)
CREATE TABLE IF NOT EXISTS final_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES research_sessions(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    market_analysis JSONB NOT NULL,       -- size, growth, competitor list, segment
    competitor_insights JSONB NOT NULL,   -- rivals, strengths, weaknesses
    technology_stack TEXT[] NOT NULL,     -- list of tools, stacks, software
    funding_status JSONB NOT NULL,        -- capital raised, recent series, investor list
    risk_opportunity_analysis JSONB NOT NULL, -- SWOT, risk level, primary gaps
    token_usage_summary JSONB NOT NULL,   -- input, output, cost, total
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_final_reports_session_id ON final_reports(session_id);
