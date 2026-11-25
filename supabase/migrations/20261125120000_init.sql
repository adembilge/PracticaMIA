create extension if not exists vector;
create extension if not exists pgcrypto;

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  citations jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table public.usage_daily (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  request_count int not null default 0,
  primary key (user_id, day)
);

create table public.global_usage_daily (
  day date primary key,
  request_count int not null default 0
);

create table public.sources (
  id text primary key,
  topic text not null,
  name text not null,
  batch text not null check (batch in ('a', 'b', 'c')),
  portal_url text not null,
  last_crawled_at timestamptz,
  status text not null default 'pending' check (status in ('pending', 'ok', 'error')),
  error text
);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  source_id text not null references public.sources(id) on delete cascade,
  url text not null unique,
  title text not null,
  topic text not null,
  language text not null default 'it',
  fetched_at timestamptz not null,
  content_hash text not null
);

create table public.chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index int not null,
  heading text not null default '',
  content text not null,
  content_hash text not null,
  embedding vector(384),
  tsv tsvector generated always as (to_tsvector('italian', content)) stored,
  unique (document_id, chunk_index)
);

create table public.topic_profiles (
  topic text primary key,
  description text not null,
  portal_url text not null,
  portal_name text not null,
  embedding vector(384)
);

create index chunks_embedding_hnsw on public.chunks
  using hnsw (embedding vector_cosine_ops);
create index chunks_tsv_gin on public.chunks using gin (tsv);
create index documents_topic_idx on public.documents (topic);
create index messages_conversation_idx on public.messages (conversation_id, created_at);