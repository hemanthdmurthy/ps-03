-- ===========================================================================
-- SUPABASE SCHEMA MIGRATION: DATA QUALITY & LLM REMEDIATION TABLES
-- Run these statements in the Supabase SQL Editor to enable analytics tables.
-- ===========================================================================

-- Enable pgvector extension for semantic deduplication and embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation extension if not already present
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. VALIDATION RUNS TABLE
-- Tracks the high-level metadata of each execution run
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    triggered_by VARCHAR(50) DEFAULT 'system',
    total_records_checked INT NOT NULL,
    passed_records INT NOT NULL,
    failed_records INT NOT NULL,
    overall_quality_score NUMERIC(5,2) NOT NULL,
    execution_time_seconds NUMERIC(6,2) NOT NULL
);

-- Enable Row Level Security (RLS) and allow public read/write for convenience
ALTER TABLE validation_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public select access on validation_runs" ON validation_runs FOR SELECT USING (true);
CREATE POLICY "Allow public insert access on validation_runs" ON validation_runs FOR INSERT WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 2. VALIDATION RESULTS DETAIL TABLE
-- Stores specific validation test failure cases for granular reporting
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_results_detail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES validation_runs(id) ON DELETE CASCADE,
    company_id INT REFERENCES companies(company_id) ON DELETE CASCADE,
    rule_id VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(10) NOT NULL,
    actual_value TEXT,
    expected_condition TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Optimization indexes for queries on specific categories, rules, and companies
CREATE INDEX IF NOT EXISTS idx_val_results_category ON validation_results_detail(category);
CREATE INDEX IF NOT EXISTS idx_val_results_status ON validation_results_detail(status);
CREATE INDEX IF NOT EXISTS idx_val_results_company ON validation_results_detail(company_id);
CREATE INDEX IF NOT EXISTS idx_val_results_run ON validation_results_detail(run_id);

ALTER TABLE validation_results_detail ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public select access on validation_results_detail" ON validation_results_detail FOR SELECT USING (true);
CREATE POLICY "Allow public insert access on validation_results_detail" ON validation_results_detail FOR INSERT WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 3. VALIDATION CORRECTION SUGGESTIONS (HITL QUEUE)
-- Stores AI/Heuristic-driven correction proposals for Human-in-the-Loop review
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_correction_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id INT REFERENCES companies(company_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    original_value TEXT,
    suggested_value TEXT NOT NULL,
    rationale TEXT,
    confidence NUMERIC(4,3) NOT NULL,
    source VARCHAR(50) DEFAULT 'LLM_Remediation',
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'applied', 'rejected'
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_val_suggestions_status ON validation_correction_suggestions(status);

ALTER TABLE validation_correction_suggestions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access on validation_correction_suggestions" ON validation_correction_suggestions FOR ALL USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 4. COMPANY EMBEDDINGS (DEDUPLICATION LAYER)
-- Stores semantic vectors of companies for duplicate detection
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id INT UNIQUE REFERENCES companies(company_id) ON DELETE CASCADE,
    metadata_text TEXT NOT NULL,
    embedding VECTOR(1536), -- Designed for OpenAI text-embedding-3-small or Gemini text-embedding-004
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

ALTER TABLE company_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access on company_embeddings" ON company_embeddings FOR ALL USING (true) WITH CHECK (true);
