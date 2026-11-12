# PriceSense: leia-me do projeto

Plataforma de inteligência de mercado e precificação de varejo (rede Mateus, estados do Nordeste e Norte), feita em **Streamlit** com banco e arquivos no **Supabase**. Este documento descreve o projeto inteiro: o que existe, onde fica cada coisa, as regras de negócio combinadas com o dono do projeto, como publicar e o que ficou pendente. Ele é a referência para retomar o trabalho em outra conversa.

Situação em 11/11/2026: todas as telas abaixo estão no ar e testadas. A última rodada corrigiu o filtro do modo ao vivo, as cores dos componentes nativos nos três temas e o zoom de 90%.

---

## 1. Onde o projeto roda

| Item | Valor |
|---|---|
| Site | https://pricesense-web.streamlit.app (Streamlit Community Cloud) |
| Repositório | https://github.com/wilgnercmachado-cloud/pricesense-web (branch `main`) |
| Arquivo principal | `portal.py` |
| Banco e arquivos | Supabase, projeto `jawdoxmvnvidqkmfohsn` (URL e chave ficam só nos *Secrets* do Streamlit, nunca no código) |
| Bucket de arquivos | `relatorios` (relatórios HTML, caches, backups, chat, base PROP%) |
| Versão do Streamlit | sem versão fixa (`streamlit>=1.50`); o Cloud usa a mais nova (testado na 1.67) e Python 3.14 |

### Como publicar uma atualização

1. Subir no GitHub **só os arquivos alterados**, cada um na pasta certa (Add file > Upload files, dentro da pasta).
2. Se houver SQL novo, rodar no Supabase: SQL Editor > New query > colar > Run. O arquivo `supabase/migrations.sql` tem todos os blocos e pode ser rodado mais de uma vez sem duplicar nada.
3. No site: **Manage app > Reboot app**.
4. No navegador: zoom em 100% (Ctrl + 0) e **Ctrl + F5**. O site aplica sozinho o zoom de 90%.

Cuidado ao subir arquivos: dois arquivos com o mesmo nome em pastas diferentes já derrubaram o site uma vez. Por isso o componente das telas se chama `pricesense_telas.html` (nome único). Nenhum recurso novo deve depender de criar pasta nova no GitHub; componentes extras são gravados numa pasta temporária pelo próprio Python.

### Secrets do Streamlit

```toml
SUPABASE_URL = "https://jawdoxmvnvidqkmfohsn.supabase.co"
SUPABASE_KEY = "chave do projeto"
```

---

## 2. Estrutura de arquivos

```
portal.py                    navegação (menu no topo), login, tema, chat flutuante, notificações, avatar do usuário
requirements.txt             streamlit, pandas, numpy, plotly, openpyxl, pillow, supabase, bcrypt, python-calamine
.streamlit/config.toml       tema base do Streamlit, upload até 300 MB
supabase/migrations.sql      todo o SQL do projeto (blocos 1 a 18)
assets/                      logos (claro/escuro) e bibliotecas JS de terceiros
core/                        regras de negócio, sem interface
  auth.py                    login (bcrypt), permissões, setor/estados, estados_permitidos(), sugestão de login no cadastro
  db.py                      acesso ao Supabase (usuários, lojas, dim_produto, dim_fornecedor, visões, encartes, backups)
  state.py                   estado da sessão, nome do usuário, páginas
  gmat_reader.py             lê o HTML "Competitividade Pricing GMAT" (blocos data, data4, data5, data6); preço vencedor e moda
  pesquisa_1067.py           upload da pesquisa 1067 (CSV/XLSX/ZIP), somada ao HTML
  precificacao.py            base da mesa PriceMetrics (PAI/similares, curva ABC, pacote para o componente)
  profimetrics.py            regras de margem por produto e zona de preço (objetiva, mínima, máxima, merch)
  proporcoes.py              base PROP% (PAI, filho, proporção): soma ao que já existe
  trava.py                   trava mínima (acordo) por filial e produto
  target.py                  preço target do fornecedor (35 dias) e flags comprador → categoria → fornecedor
  parametros.py              formação de preço por usuário (Mercado − 0,01 ou curva de venda; delta seguro)
  blocks.py                  BLOCK do comercial
  sugestoes.py               sugestão de preço do comprador (uma filial ou várias)
  notificacoes.py            notificações (pop-up de 7 s e sininho)
  chat.py                    chat por estado e privado, com anexos
  ao_vivo.py                 precificação online (ao vivo)
  revisao.py                 revisão de margem (sugestões e simulação de lucro)
  aprovacoes.py              fila de aprovação do administrador (Profimetrics, PROP%, trava, target, margens, formação)
  mercado.py                 painel de mercado do Início e da Pesquisa de Mercado
  reports.py                 biblioteca de relatórios HTML (visibilidade por pessoa, setor e estado)
  presenca.py, preco_bot.py, promo_engine.py, market_engine.py, pricing_engine.py, gmat_pricing.py
ui/
  theme.py                   três temas (claro, escuro, Optimus), CSS do site, zoom de 90%, cores dos componentes nativos
  components.py              cabeçalho, script do menu (ilha dinâmica, menus alinhados, avatar, Ctrl+V no chat), miniaturas
  metrics_comp/pricesense_telas.html   UM componente HTML com todas as telas grandes (ver seção 4)
  charts.py, terminal.py
views/                       uma página por arquivo
  home.py (Início), regular.py (PriceMetrics), margem.py (Revisão de margem), promo.py (Metrics Promo),
  preco_bot.py (PriceBot), pesquisa.py (Pesquisa de Mercado), biblioteca.py, publicar.py, admin.py, perfil.py, login.py
tests/
  fake_supabase.py           Supabase falso em memória (usuários ana, bruno, carla, davi; senha 123456)
  run_fake.py                roda o site com o banco falso
  test_motores.py
```

O componente `ui/metrics_comp/pricesense_telas.html` é carregado por `ui.components.pasta_telas()` (que o copia como `index.html` para uma pasta temporária) e escolhe a tela pelo parâmetro `app`: `home`, `price` (PriceMetrics), `promo`, `bot`, `market` (Pesquisa de Mercado) e `margem` (Revisão de margem).

---

## 3. Menu, acessos e perfis

O menu fica numa ilha no topo: **Início**, **Ferramentas** (PriceBot, Metrics Promo, Pesquisa de Mercado, PriceMetrics, Revisão de margem), **Relatórios** (Biblioteca, Publicar) e o **círculo com a foto do usuário** (Meu perfil, Administração para administradores, Sair). Os menus abrem ao passar o mouse, logo abaixo do item.

As permissões gravadas no banco têm nomes antigos e não devem ser renomeadas: `Preço Bot` (aparece como PriceBot), `Pricing Promo` (Metrics Promo), `Pesquisa de Mercado`, `Pricing Regular` (PriceMetrics e Revisão de margem).

Cada usuário tem **setor** e **estados** (`usuarios.setor`, `usuarios.estado`, siglas separadas por ponto e vírgula ou `TODOS`). O administrador vê todos os estados. Os demais veem só os seus, na PriceMetrics, no PriceBot, na Revisão de margem e no chat.

Na PriceMetrics, o setor define a visão: **PRICE** vê a visão de Pricing; **COMERCIAL**, outro setor ou setor vazio veem a visão do Comercial. O administrador alterna entre as duas no topo.

Cadastro (Solicitar acesso): ao digitar o nome completo, o site sugere o login (ex.: João da Costa Silva → `joao.silva`; se existir, `joao.csilva`, `joao.costa`, ...), só com opções livres no Supabase. O administrador aprova na Administração.

Login: o navegador guarda o usuário por 1 ano (cookie `ps_usuario`). Na volta, a entrada mostra a foto em círculo com aura neon, "Boa tarde, Nome" e o usuário já preenchido, com o botão "Não é você?".

---

## 4. Telas e regras de negócio

### 4.1 Base de dados das telas

Tudo parte do relatório **Competitividade Pricing GMAT** mais recente publicado na biblioteca (HTML grande, em partes no Storage). O leitor (`core/gmat_reader.py`) usa:

- `data`: uma linha por filial + produto (custo, preço PDV varejo e atacado, mercado, moda, venda, quantidade, estoque, DDE, comprador, categoria, cesta, tipo de preço do PDV, grupo empresarial);
- `data4`: coletas por filial; `data5`: histórico de 30 dias de pesquisa;
- `data6` ("ritmo do mês", alinhado linha a linha com `data`): `eVP/eLP` = venda e lucro do **mês anterior, mesmos dias** (loja); `eMV/eML` = meta de venda e de lucro; `eVM/eLM` = mês atual até a data.

A base pronta fica guardada em cache no Storage (`cache_base/`). Mudar a versão do leitor (`gmat_reader.VERSAO`) força uma nova leitura.

### 4.2 PriceMetrics (mesa de precificação)

**Preço vencedor:** recorte por filial dos últimos 3 dias de pesquisa; para cada concorrente associado à filial, a coleta do dia mais recente; se nesse dia houver coleta de tipo excluído (encarte, mídia, validade, outros), o concorrente sai, mesmo com regular no mesmo dia. Vencedor = menor preço que sobrou. Tipos válidos: REGULAR, PROMOÇÃO e PONTO EXTRA.

**Moda:** só regular, promoção e ponto extra; por concorrente, o varejo praticado em mais dias (mínimo 3 dias); empate, o menor. Atacado da moda = atacado das mesmas coletas. No card, a moda do concorrente vencedor; sem moda consistente, a de mais dias entre os concorrentes da filial.

**Pesquisa 1067:** cada usuário sobe a sua (CSV, XLSX ou ZIP); todas as do mesmo HTML se somam; na mesma filial + produto + concorrente + data, a 1067 substitui o HTML; com HTML novo, os envios são descartados.

**Motor (novo preço):** Mercado − R$ 0,01 (padrão) ou **curva de venda** (percentual por curva A/B/C sobre o concorrente), escolhido por usuário no botão de **Formação de preço**. Respeita margem mínima e máxima (cesta: piso −15%; não cesta: Profimetrics; **trava mínima** acima de todas). **Delta seguro** (padrão ±25% acima do custo, ±15% abaixo): se o vencedor se afasta da moda além do delta, o preço sai da moda. Arredondamento pela régua da companhia (igual ao PriceBot). Sem pesquisa: preço objetivo.

**Regra de corte** (só quando a vigência atual não termina hoje nem no próximo sábado/domingo): preço atual em encarte, mídia ou app; promoção comercial com IP ≤ 100%; ou variação entre −1,5% e +1,5%. Esses itens não entram no "Aceitar todos". Os cartões do topo contam **só os itens aceitos**.

**Optimus:** ajusta pelo mesmo vencedor com o delta do usuário; identifica **encarte coletado com outro tipo** (mesmo preço, até 1%, como encarte, mídia ou validade nos últimos 15 dias para curva A e 30 dias para B e C, no próprio concorrente ou em outra loja da mesma empresa no estado). Nesse caso usa o **concorrente secundário**, que é descartado se estiver abaixo do encarte suspeito ou fora do delta da própria moda; aí usa a **menor moda consistente** da filial e, sem nenhuma, o preço objetivo com atacado pela base de redução.

**PAI e similares (base PROP%):** na mesa aparece só o PAI; o filho entra só quando o PAI está ausente da filial (o de proporção 100% com maior venda, marcado com ⇄). **Um envio de PROP% soma à base**: substitui os produtos enviados e mantém o resto.

**Preço target (fornecedor):** arquivo ID filial | ID Produto | Varejo; Pricing e Comercial enviam, o administrador aprova; vale **35 dias a partir da aprovação**. Sem a flag: o motor indica "Programar target (oferta 11)"; quando o PDV já está no target com tipo PROMOCAO COMERCIAL (11) ou APP (10), fica "Target vigente: sem recomendação" até o fim. Com a flag "pode seguir o mercado se for menor" (marcada por comprador → categoria → fornecedor; marcar um nível marca os de baixo), o target vira o preço máximo do motor e do Optimus. Fornecedor vem da `dim_produto.id_fornecedor` cruzada com `dim_fornecedor`.

**Visão do Comercial:** mesma mesa, sem aceite, Optimus, importação e uploads (exceto preço target); exporta a análise em Excel; **visão por produto (cascata)**, com o produto resumido e as filiais dentro; **BLOCK** pelo botão direito (só com novo preço abaixo do custo; motivo obrigatório; dura pelo menos 3 dias e até o vencedor do block mudar; no Pricing o item só aceita preço manual pelo menos 2% diferente); **sugestão de preço** para uma filial ou várias (o Pricing aceita uma a uma, todas, ou rejeita com motivo; pendente expira no dia seguinte, com aviso do preço aplicado).

**Precificação online (ao vivo):** o analista inicia nos seus estados (um analista por estado); cada ajuste chega em segundos para quem assiste. O Comercial, quando há alguém ao vivo, **entra direto assistindo, só nos estados transmitidos**; outros analistas podem assistir (também filtrado). Ao encerrar, os preços ficam congelados para o Comercial até um HTML novo.

**Também na PriceMetrics:** backup da precificação (3 dias por usuário), aceite e edição direto na célula (Enter desce; margem digitada forma o varejo; atacado pela base de redução), pedido de nova margem pelo botão direito (vai para o administrador).

### 4.3 Revisão de margem

Categoria → produto, filtros de **vários estados ou todos**, filiais, departamento, comprador, categoria e fornecedor. Linha selecionada e setas como na PriceMetrics.

- **Margem do mês anterior** = lucro ÷ venda da loja, mesmos dias do mês anterior. **Lucro do mês anterior** e **ganho de lucro** (simulado − realizado).
- **Margem de mercado** = (moda − custo) ÷ moda, só com pesquisa consistente (moda de 3 dias ou mais, sem erro).
- **Objetiva sugerida**: com pesquisa, parte da margem de mercado do produto; sem pesquisa (ou inconsistente), da média de mercado da categoria; nos dois casos é puxada para a meta (do produto, senão da categoria) **no máximo 3 pontos** do mercado; nunca abaixo de 0. **Máxima** = objetiva + 5; **mínima** = 0. Tudo editável.
- **Simulação de lucro** com o volume dos últimos 30 dias, item a item: com pesquisa segue o motor (cesta: piso −15% e máxima; não cesta: nova mínima e máxima); sem pesquisa, preço objetivo pela régua.
- **Diagnóstico** pelo IP simulado: 98,9 a 100,9 dentro da faixa; acima, zona crítica; abaixo, zona de atenção; pesquisa inconsistente avisa.
- Enviar sugestões: vai para o administrador, que pode editar antes de aprovar; grava no Profimetrics nas zonas de preço das filiais; o solicitante recebe aviso com as modificações.

### 4.4 Outras telas

**Início:** "Olá, Nome", letreiro de estados, cartões de mercado, pregão por estado, captura x investimento, ferramentas e relatórios.

**Pesquisa de Mercado:** termômetro, ranking, grade de produtos e extrações em Excel, a partir dos 30 dias da base.

**Metrics Promo:** encartes, calendário de campanhas, conflitos e clusters.

**PriceBot:** cola preços, aplica a régua e gera a importação (só lojas dos estados do usuário).

**Biblioteca e Publicar:** relatórios HTML com visibilidade por pessoas, setores e estados. O relatório aberto não recarrega sozinho: os links do arquivo ficam fixos na sessão (`reports.links_sessao`, válidos por 24 h) e o quadro não depende do tema, então favoritar, trocar o tema ou as atualizações automáticas do chat e do sininho não o redesenham.

**Administração:** solicitações, usuários (setor, estados, permissões, administrador), clusters, bloqueados e **Uploads** (fila de aprovação).

### 4.5 Recursos gerais

**Chat** flutuante (canto inferior esquerdo): canal público por estado e privado; @menção e mensagem privada geram pop-up; anexos (imagem, texto, Excel, CSV, ZIP, PDF; Ctrl + V cola print); baixar no tamanho original.

**Notificações:** pop-up no canto superior direito que some em cerca de 7 s, e **sininho** no topo com o histórico.

**Temas** no botão do canto: sol (claro), lua (escuro, neon ciano e violeta) e estrela (**Optimus**, preto com neon azul e vermelho). Os componentes nativos usam sempre as cores do tema de cada pessoa (o tema nativo do Streamlit é do servidor inteiro).

**Zoom de 90%** aplicado só no corpo do site (`.stApp`); menus e listas suspensas ficam fora dele e abrem alinhados. Quando falta espaço no topo, os botões da direita viram só ícones; nada se sobrepõe à ilha.

---

## 5. Banco de dados (Supabase)

Tabelas existentes antes do projeto: `usuarios`, `lojas`, `tipo_ofertas`, `filial-cluster`, `dim_produto`, `dim_fornecedor`, `dim_empresa_concorrente`, `filiais`.

Blocos de `supabase/migrations.sql` (todos já rodados no Supabase até o 18):

| Bloco | Conteúdo |
|---|---|
| 1, 2, 2b | `relatorios`, bucket `relatorios`, favoritos e recentes |
| 3 | `solicitacoes_cluster` |
| 4 | orientação de acesso (RLS) |
| 5, 6 | presença e acessos; `visoes_usuario` |
| 7 | `dim_produto.id_pai`, `proporcao` e função `atualizar_proporcoes` |
| 8 | `encartes_campanhas`, `encartes_itens` |
| 9 | `backups_precificacao` |
| 10 | `aprovacoes_upload` |
| 11 | `usuarios.setor`, `usuarios.estado`; visibilidade dos relatórios |
| 12 | `trava_minima` |
| 13 | `parametros_preco` |
| 14 | `blocks_comercial` |
| 15 | `sugestoes_preco`, `notificacoes` |
| 16, 16b, 16c | `chat_mensagens` (anexo, arquivos), `chat_leituras` |
| 17 | `precificacao_online` |
| 18 | `precos_target`, `target_flags` |

Arquivos no Storage (`relatorios`): relatórios em partes, `cache_base/` (base pronta), `relatorios/pesquisa1067/`, `config/proporcoes.csv.gz` (base PROP% completa), `backups/`, `pendentes/` (uploads aguardando aprovação), `chat/`.

---

## 6. Como testar localmente

```bash
pip install -r requirements.txt playwright --break-system-packages
python -m playwright install chromium
# secrets falsos só para o teste (não subir):
printf 'SUPABASE_URL = "https://fake.supabase.co"\nSUPABASE_KEY = "fake"\n' > .streamlit/secrets.toml
PS_GMAT_HTML=/caminho/Pricing_GMAT3_30-10-2026.html streamlit run tests/run_fake.py --server.port 8599 --server.headless true
```

Usuários do banco falso (senha `123456`): `ana` (administradora, setor PRICE, todos os estados), `bruno` (comercial, MA), `carla` (pendente), `davi` (recusado). O servidor guarda módulos em memória: depois de mudar código em `views/` ou `core/`, reinicie o servidor. Bases de teste usadas: `Pricing_GMAT3_30-10-2026.html`, `Profimetrics_Cad.xlsx`, `PROP_.xlsx`, `1067_BASE.zip`, `1067_DMS3031.zip`.

---

## 7. Como o dono do projeto prefere trabalhar

- Responder em **português**, em linguagem simples, e explicar o que mudou e como subir.
- **Perguntar as dúvidas uma por vez, com opções para marcar**, e não inventar regras, números nem simulações. Quando algo for decidido sem perguntar, avisar claramente.
- **Não fazer mudanças que não foram pedidas.**
- Entregar **só os arquivos alterados**, dizendo a pasta de cada um, mais o SQL quando houver (com o passo a passo do Supabase).
- O site **não pode cair nem ficar lento**: cuidado com memória (o Cloud derruba o app com "Error running app" quando falta memória), caches limitados e sem pastas novas obrigatórias.
- Visual premium, moderno, com toques de neon; nada pode se sobrepor; testar em várias larguras e nos três temas.

---

## 8. Pendências e pontos em aberto

1. **Base PROP%:** depois da correção que passou a somar os envios, subir uma vez o arquivo PROP% completo (cerca de 42 mil relações), porque um envio antigo deixou o arquivo do Storage com um produto só.
2. **Revisão de margem:** confirmar com o dono se o ganho de lucro deve comparar com o **lucro do preço atual** (mesmo volume) em vez do lucro realizado do mês anterior; se quer teto para sugestões em categorias com margem de mercado muito alta; e como tratar os "casos específicos" de objetiva na cesta.
3. **Preço target:** confirmar se a flag deve exigir aprovação e se, com a flag marcada, o target deve prevalecer sobre a margem mínima (hoje a mínima prevalece).
4. **Zonas de preço:** aprovar margens depende de achar a zona da filial (tabela `filiais` ou nome da zona no Profimetrics); filiais sem zona geram aviso.
5. **Memória no Cloud:** se voltar o "Error running app", pedir as últimas linhas do log (Manage app) para confirmar a causa.
6. **Antigas:** DTFIM vazia em parte da base; regras para itens "sem pesquisa"; elasticidade e estoque na PriceMetrics (futuro); ativar RLS nas tabelas depois de validar a chave secreta.
