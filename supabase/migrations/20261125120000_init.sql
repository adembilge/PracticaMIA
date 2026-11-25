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

create or replace function public.match_chunks(
  query_embedding vector(384),
  query_text text,
  topic_filter text,
  match_count int
)
returns table (
  id uuid,
  content text,
  heading text,
  url text,
  title text,
  topic text,
  fetched_at timestamptz,
  cosine_similarity float,
  rank_score float
)
language sql
stable
as $$
  with semantic as (
    select
      nearest.id,
      row_number() over (order by nearest.distance) as rnk,
      (1 - nearest.distance)::float as cosine_similarity
    from (
      select
        c.id,
        (c.embedding <=> query_embedding) as distance
      from public.chunks c
      join public.documents d on d.id = c.document_id
      where c.embedding is not null
        and (topic_filter = '' or d.topic = topic_filter)
      order by c.embedding <=> query_embedding
      limit 20
    ) nearest
  ),
  lexical as (
    select
      best.id,
      row_number() over (order by best.rank desc) as rnk
    from (
      select
        c.id,
        ts_rank_cd(c.tsv, websearch_to_tsquery('italian', query_text)) as rank
      from public.chunks c
      join public.documents d on d.id = c.document_id
      where query_text <> ''
        and c.tsv @@ websearch_to_tsquery('italian', query_text)
        and (topic_filter = '' or d.topic = topic_filter)
      order by ts_rank_cd(c.tsv, websearch_to_tsquery('italian', query_text)) desc
      limit 20
    ) best
  ),
  fused as (
    select
      coalesce(s.id, l.id) as id,
      coalesce(s.cosine_similarity, 0)::float as cosine_similarity,
      (
        coalesce(1.0 / (60 + s.rnk), 0) + coalesce(1.0 / (60 + l.rnk), 0)
      )::float as rank_score
    from semantic s
    full outer join lexical l on s.id = l.id
  )
  select
    c.id, c.content, c.heading, d.url, d.title, d.topic, d.fetched_at,
    f.cosine_similarity, f.rank_score
  from fused f
  join public.chunks c on c.id = f.id
  join public.documents d on d.id = c.document_id
  where f.cosine_similarity >= 0.30
  order by f.rank_score desc
  limit match_count;
$$;

alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.usage_daily enable row level security;
alter table public.global_usage_daily enable row level security;
alter table public.sources enable row level security;
alter table public.documents enable row level security;
alter table public.chunks enable row level security;
alter table public.topic_profiles enable row level security;

create policy conversations_own on public.conversations
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy messages_own on public.messages
  for all
  using (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  );