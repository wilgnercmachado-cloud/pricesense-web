-- =====================================================================
-- PriceSense: migração para a nova versão
-- Rode no Supabase: SQL Editor > New query > cole tudo > Run.
-- Pode rodar mais de uma vez sem duplicar nada.
-- =====================================================================

-- 1. Biblioteca de relatórios --------------------------------------------
create table if not exists public.relatorios (
  id                  uuid primary key default gen_random_uuid(),
  titulo              text not null,
  descricao           text,
  categoria           text not null default 'Geral',
  tags                text[] not null default '{}',
  arquivo_path        text not null,
  tamanho_bytes       bigint,
  autor_usuario       text not null,
  autor_nome          text,
  visibilidade        text not null default 'Todos'
                      check (visibilidade in ('Todos', 'Selecionados', 'Admins')),
  usuarios_permitidos text[] not null default '{}',
  destaque            boolean not null default false,
  visualizacoes       integer not null default 0,
  versao              integer not null default 1,
  criado_em           timestamptz not null default now(),
  atualizado_em       timestamptz not null default now()
);
alter table public.relatorios add column if not exists partes integer not null default 1;
create index if not exists relatorios_criado_em_idx on public.relatorios (criado_em desc);

-- Contador de visualizações (atômico).
create or replace function public.incrementar_visualizacao(rid uuid)
returns void language sql as $$
  update public.relatorios set visualizacoes = visualizacoes + 1 where id = rid;
$$;

-- 2. Bucket privado para os arquivos HTML -------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('relatorios', 'relatorios', false, 52428800, array['text/html', 'application/gzip'])
on conflict (id) do update
  set file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

-- 2b. Favoritos e recentes de cada usuário --------------------------------
create table if not exists public.relatorios_usuario (
  usuario       text not null,
  relatorio_id  uuid not null references public.relatorios(id) on delete cascade,
  favorito      boolean not null default false,
  ultimo_acesso timestamptz,
  primary key (usuario, relatorio_id)
);
alter table public.relatorios_usuario enable row level security;

-- 3. Pedidos de mapeamento de cluster (usado no Pricing Promo) ----------
create table if not exists public.solicitacoes_cluster (
  id          bigint generated always as identity primary key,
  cluster     text not null,
  id_filial   text not null,
  status      text not null default 'Pendente',
  solicitante text,
  criado_em   timestamptz not null default now()
);

-- =====================================================================
-- 4. ACESSO: escolha UMA das opções abaixo
-- =====================================================================

-- OPÇÃO A (recomendada): usar a chave service_role nos Secrets do Streamlit.
--   O app roda no servidor, então a chave nunca chega ao navegador.
--   Com ela, ative RLS em TODAS as tabelas SEM criar políticas: o banco fica
--   fechado para quem tiver a chave pública, e o app continua funcionando.
--   Descomente para aplicar:
--
-- alter table public.usuarios              enable row level security;
-- alter table public.lojas                 enable row level security;
-- alter table public.tipo_ofertas          enable row level security;
-- alter table public."filial-cluster"      enable row level security;
-- alter table public.dim_produto           enable row level security;
-- alter table public.dim_fornecedor        enable row level security;
-- alter table public.dim_empresa_concorrente enable row level security;
-- alter table public.relatorios            enable row level security;
-- alter table public.solicitacoes_cluster  enable row level security;

-- OPÇÃO B (provisória): continuar com a chave publishable/anon.
--   As tabelas novas seguem sem RLS (como as atuais) e o Storage precisa
--   de uma política liberando o bucket. Atenção: com esta opção, qualquer
--   pessoa com a chave pública consegue ler e alterar os dados.
--
-- create policy "pricesense_relatorios_bucket" on storage.objects
--   for all to anon, authenticated
--   using (bucket_id = 'relatorios') with check (bucket_id = 'relatorios');

-- 5. Presença e acessos dos usuários ------------------------------------
alter table public.usuarios add column if not exists ultimo_acesso    timestamptz;
alter table public.usuarios add column if not exists ultima_atividade timestamptz;
alter table public.usuarios add column if not exists acessos_dia      integer not null default 0;
alter table public.usuarios add column if not exists acessos_data     date;


-- 6. Visões salvas por usuário (colunas, ordem e larguras da mesa de precificação) ----
create table if not exists public.visoes_usuario (
  usuario       text not null,
  tela          text not null,
  visao         jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now(),
  primary key (usuario, tela)
);
alter table public.visoes_usuario enable row level security;


-- 7. Proporcionais na dim_produto (filho = preço do PAI x proporção / 100) --------------
alter table public.dim_produto add column if not exists id_pai    bigint;
alter table public.dim_produto add column if not exists proporcao numeric;
create index if not exists dim_produto_id_pai on public.dim_produto (id_pai);

-- Atualiza só id_pai e proporcao dos produtos que já existem (sem inserir, sem tocar nas outras colunas)
create or replace function public.atualizar_proporcoes(dados jsonb)
returns integer language sql security definer set search_path = public as $$
  with d as (
    select (x->>'id_produto')::bigint as id_produto, (x->>'id_pai')::bigint as id_pai, (x->>'proporcao')::numeric as proporcao
    from jsonb_array_elements(dados) as x
  ), u as (
    update public.dim_produto p set id_pai = d.id_pai, proporcao = d.proporcao
    from d where p.id_produto = d.id_produto
    returning 1
  )
  select count(*)::integer from u;
$$;


-- 8. Histórico de encartes (Pricing Promo): campanhas programadas e seus itens por filial ----
create table if not exists public.encartes_campanhas (
  campanha       text primary key,
  inicio         date,
  fim            date,
  itens          integer not null default 0,
  filiais        integer not null default 0,
  status         text not null default 'pendente',   -- pendente | programada
  atualizado_em  timestamptz not null default now(),
  atualizado_por text
);
create table if not exists public.encartes_itens (
  campanha text not null,
  filial   text not null,
  produto  text not null,
  preco    numeric,
  inicio   date not null,
  fim      date,
  primary key (campanha, filial, produto, inicio)
);
create index if not exists encartes_itens_filial on public.encartes_itens (filial, inicio);
alter table public.encartes_campanhas enable row level security;
alter table public.encartes_itens enable row level security;


-- 9. Backup da precificação do PriceMetrics: últimos 3 dias por usuário (arquivo no Storage) ----
create table if not exists public.backups_precificacao (
  usuario   text not null,
  dia       date not null,
  criado_em timestamptz not null default now(),
  resumo    jsonb not null default '{}'::jsonb,
  caminho   text not null,
  primary key (usuario, dia)
);
alter table public.backups_precificacao enable row level security;


-- 10. Aprovação de uploads de regras (Profimetrics e base PROP%) enviados por usuários ----
create table if not exists public.aprovacoes_upload (
  id            uuid primary key,
  tipo          text not null,              -- profimetrics | proporcoes
  usuario       text not null,
  nome_arquivo  text,
  caminho       text not null,              -- arquivo guardado em relatorios/pendentes/
  resumo        jsonb not null default '{}'::jsonb,
  status        text not null default 'pendente',   -- pendente | aprovado | recusado
  criado_em     timestamptz not null default now(),
  decidido_por  text,
  decidido_em   timestamptz,
  observacao    text
);
alter table public.aprovacoes_upload enable row level security;


-- 11. Setor e estado do usuário; relatórios publicados por setor e/ou estado ----
alter table public.usuarios add column if not exists setor text;
alter table public.usuarios add column if not exists estado text;
alter table public.relatorios add column if not exists setores_permitidos jsonb not null default '[]'::jsonb;
alter table public.relatorios add column if not exists estados_permitidos jsonb not null default '[]'::jsonb;
alter table public.relatorios add column if not exists combinar_publico text not null default 'e';
