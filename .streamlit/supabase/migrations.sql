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
create index if not exists relatorios_criado_em_idx on public.relatorios (criado_em desc);

-- Contador de visualizações (atômico).
create or replace function public.incrementar_visualizacao(rid uuid)
returns void language sql as $$
  update public.relatorios set visualizacoes = visualizacoes + 1 where id = rid;
$$;

-- 2. Bucket privado para os arquivos HTML -------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('relatorios', 'relatorios', false, 26214400, array['text/html'])
on conflict (id) do nothing;

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
