# PriceSense

Plataforma de inteligência de preços para o varejo, em Streamlit + Supabase.

## Estrutura

```
portal.py              navegação e controle de acesso
core/                  regras de negócio (sem interface)
  preco_bot.py         arredondamento de varejo/atacado e arquivo de importação
  promo_engine.py      leitura de encartes, clusters e conflitos
  market_engine.py     rotina 1067: moda, menor preço, mercado total
  reports.py           biblioteca de relatórios HTML
  auth.py              login, senhas com bcrypt, permissões
  db.py                acesso ao Supabase (com cache)
ui/                    sistema visual, componentes e gráficos
views/                 uma página por arquivo
assets/                logotipos
supabase/migrations.sql
tests/                 testes e um Supabase falso para rodar localmente
```

## Publicar a nova versão

1. **Rode o SQL.** No Supabase, abra o SQL Editor, cole `supabase/migrations.sql` e execute.
   Leia a seção 4 do arquivo e escolha como o app vai acessar o banco.
2. **Tire a chave do código.** Em Streamlit Community Cloud > App > Settings > Secrets:
   ```toml
   SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
   SUPABASE_KEY = "sua-chave"
   ```
   A chave antiga estava escrita no código. Gere uma nova no Supabase (Settings > API) e use a nova.
3. **Suba os arquivos** para o repositório, substituindo o `portal.py` antigo.
   O arquivo principal continua sendo `portal.py`, então nada muda no Streamlit Cloud.

## O que muda para os usuários

- As senhas passam a ser guardadas com hash bcrypt. As antigas, em texto puro, são convertidas
  sozinhas no primeiro login de cada pessoa. Ninguém precisa redefinir nada.
- Nova permissão **Publicar Relatórios**, liberada em Administração. Administradores já têm.
- Todos os usuários aprovados veem a Biblioteca de relatórios (respeitando a visibilidade de cada um).

## Relatórios

- Qualquer HTML autocontido funciona: Plotly (`fig.write_html`), pandas (`df.to_html`),
  Excel salvo como página da web, ou HTML feito à mão. Limite de 25 MB por arquivo.
- O relatório roda isolado (iframe com sandbox): scripts funcionam, mas não acessam o app.
- O link copiado no visualizador abre o relatório direto; se a pessoa não estiver logada,
  o link é guardado e aberto logo após o login.

## Rodar localmente sem tocar no banco real

```bash
pip install -r requirements.txt
streamlit run tests/run_fake.py        # usuário: ana / senha: 123456 (admin)
python tests/test_motores.py           # compara os motores com a lógica original
```
