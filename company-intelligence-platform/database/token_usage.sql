-- SQL script to create the token_usage_logs table in Supabase
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS token_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost NUMERIC(10, 6) DEFAULT 0.0,
    execution_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster querying
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_company ON token_usage_logs(company_name);
