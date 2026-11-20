-- Schéma Supabase reconstitué à partir du code de départ (projet 2, MGL805).
-- Le schéma de la base d'origine n'était pas fourni : ce fichier déduit les tables et
-- les colonnes des appels faits par embedding_valid_pipeline.py et fine_tuning_qwen.py.
-- Exécutez-le dans l'éditeur SQL de votre projet Supabase. Les tables ont été vérifiées sur
-- PostgreSQL 16 ; l'extension pgvector, l'index et la fonction de recherche n'ont pas pu l'être.

create extension if not exists vector;

-- ---------------------------------------------------------------- Entraînement
create table if not exists "JIRA User Stories" (
  id                     bigint generated always as identity primary key,
  issue_key              text not null unique,       -- clé d'upsert (ex. PM-176)
  use_case_id            text,                       -- ex. UC-03
  titre                  text,
  statut_jira            text,
  module                 text,
  description            text,
  "critères_acceptances" text,                       -- nom utilisé par le script d'ingestion
  created_at             timestamptz default now()
);

create table if not exists "Zephyr Tests" (
  id            bigint generated always as identity primary key,
  test_key      text not null unique,                -- clé d'upsert (ex. PM-T119)
  story_key     text references "JIRA User Stories"(issue_key) on delete cascade,
  name          text,
  status        text,
  objective     text,
  precondition  text,
  folder        text,
  steps         jsonb,
  created_at    timestamptz default now()
);

-- Aucune ligne n'est écrite ici par le code de départ : l'ingestion des maquettes reste à faire.
-- wireframe_path est un dossier du compartiment de stockage « balsamiq_wireframes ».
create table if not exists "Balsamiq Wireframes" (
  id              bigint generated always as identity primary key,
  story_key       text references "JIRA User Stories"(issue_key) on delete cascade,
  wireframe_path  text not null,
  created_at      timestamptz default now()
);

-- ---------------------------------------------------------------- Validation
-- ATTENTION : les deux scripts n'utilisent pas les mêmes noms (voir GUIDE.md, section 6).
-- Ces noms sont ceux de fine_tuning_qwen.py.
create table if not exists "JIRA User Stories Validation" (like "JIRA User Stories" including all);
create table if not exists "Zephyr Tests Validation" (
  like "Zephyr Tests" including defaults including identity,
  foreign key (story_key) references "JIRA User Stories Validation"(issue_key) on delete cascade
);
create table if not exists "Balsamiq Wireframes Validation" (
  like "Balsamiq Wireframes" including defaults including identity,
  foreign key (story_key) references "JIRA User Stories Validation"(issue_key) on delete cascade
);
alter table "Zephyr Tests Validation" add primary key (id);
alter table "Zephyr Tests Validation" add unique (test_key);
alter table "Balsamiq Wireframes Validation" add primary key (id);

-- ---------------------------------------------------------------- RAG
-- 1024 dimensions : taille des vecteurs de Qwen/Qwen3-Embedding-0.6B.
create table if not exists "RAG Embeddings" (
  id          bigint generated always as identity primary key,
  source_key  text not null unique,                  -- clé d'upsert (issue_key ou test_key)
  story_key   text,
  embeddings  vector(1024),
  content     text,
  metadata    jsonb default '{}'::jsonb,
  created_at  timestamptz default now()
);

create index if not exists rag_embeddings_hnsw
  on "RAG Embeddings" using hnsw (embeddings vector_cosine_ops);

-- Fonction de recherche pour le pipeline d'inférence (à écrire par l'équipe) :
-- retourne les k passages les plus proches d'un vecteur de requête normalisé.
create or replace function match_rag_embeddings(query_embedding vector(1024), match_count int default 5)
returns table (source_key text, story_key text, content text, metadata jsonb, similarity float)
language sql stable as $$
  select source_key, story_key, content, metadata,
         1 - (embeddings <=> query_embedding) as similarity
  from "RAG Embeddings"
  order by embeddings <=> query_embedding
  limit match_count;
$$;

-- Compartiment de stockage des maquettes (à créer dans Storage) : balsamiq_wireframes
-- Arborescence attendue par fine_tuning_qwen.py : <wireframe_path>/etape_01.png, etape_02.png, ...
