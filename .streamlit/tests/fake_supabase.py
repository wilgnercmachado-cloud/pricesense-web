"""Supabase falso em memória, só para testes locais (não é usado em produção)."""
from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace

import bcrypt

_DB: dict | None = None
_FILES: dict = {}

RELATORIO_HTML = """<!doctype html><html><head><meta charset='utf-8'><style>
body{font-family:Georgia,serif;margin:40px;color:#222} h1{color:#0a5} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:6px 10px}
</style></head><body><h1>Ruptura de hortifruti, semana 43</h1><p>Exemplo de relatório publicado. Acentuação: ação, preço, órgão.</p>
<table><tr><th>Filial</th><th>Ruptura</th></tr><tr><td>544 - Paralela</td><td>3,2%</td></tr><tr><td>601 - Feira</td><td>5,8%</td></tr></table>
<script>document.body.insertAdjacentHTML('beforeend','<p id=js>JavaScript executado dentro do relatório.</p>');
try{ window.parent.document.title='HACK'; document.body.insertAdjacentHTML('beforeend','<p>FALHA: acessou o app</p>'); }
catch(e){ document.body.insertAdjacentHTML('beforeend','<p>Isolado do app: OK</p>'); }</script></body></html>"""


def _seed() -> dict:
    h = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
    lojas = []
    for est, dirs in {"BA": ["Carlos", "Marta"], "PE": ["Joana"], "SE": ["Paulo"]}.items():
        for d in dirs:
            for n in range(3):
                fid = 500 + len(lojas)
                lojas.append({"estado": est, "diretor": d, "filial": f"{fid} - {['Paralela','Feira','Lauro','Boa Viagem','Aracaju','Iguatemi'][len(lojas)%6]} {est}"})
    rels = []
    for i, (tit, cat, dest, vis) in enumerate([
        ("Ruptura de hortifruti, semana 43", "Operação", True, "Todos"),
        ("Elasticidade de preço em mercearia seca", "Estudos", True, "Todos"),
        ("Resultado do encarte de aniversário", "Promoções", False, "Todos"),
        ("Índice de preço vs. Atacadão, Bahia", "Concorrência", False, "Todos"),
        ("Margem por categoria, outubro", "Financeiro", False, "Admins"),
    ]):
        rid = str(uuid.uuid4()); path = f"2026/10/{rid}.html"
        _FILES[path] = RELATORIO_HTML.encode("utf-8")
        rels.append({"id": rid, "titulo": tit, "descricao": "Leitura semanal com os principais desvios por filial e as ações recomendadas para a próxima rodada de preços.",
                     "categoria": cat, "tags": ["Bahia", "semanal"] if i % 2 == 0 else ["nacional"], "arquivo_path": path, "tamanho_bytes": len(RELATORIO_HTML),
                     "autor_usuario": "ana", "autor_nome": "Ana Ribeiro", "visibilidade": vis, "usuarios_permitidos": [], "destaque": dest,
                     "visualizacoes": 40 - i * 7, "versao": 1 + i % 2, "criado_em": f"2026-10-{20 + i}T12:00:00+00:00", "atualizado_em": f"2026-10-{20 + i}T12:00:00+00:00"})
    return {
        "lojas": lojas,
        "tipo_ofertas": [{"tipo_preço": t} for t in ["0 - Preço Fixo", "1 - Encarte", "2 - Tabloide", "5 - Ponto Extra", "14 - Regular", "21 - Clube"]],
        "usuarios": [
            {"usuario": "ana", "senha": h, "nome": "Ana Ribeiro", "cargo": "Coordenadora de Pricing", "status": "Aprovado", "is_admin": True, "permissoes": [], "foto_perfil": ""},
            {"usuario": "bruno", "senha": "123456", "nome": "Bruno Souza", "cargo": "Analista", "status": "Aprovado", "is_admin": False, "permissoes": ["Preço Bot", "Pesquisa de Mercado"], "foto_perfil": ""},
            {"usuario": "carla", "senha": h, "nome": "Carla Mendes", "cargo": "Analista Jr.", "matricula": "88123", "status": "Pendente", "is_admin": False, "permissoes": []},
            {"usuario": "davi", "senha": h, "nome": "Davi Lima", "status": "Rejeitado", "is_admin": False, "permissoes": []},
        ],
        "relatorios": rels,
        "filial-cluster": [{"CLUSTER": "CL_SALVADOR", "ID FILIAL": 500}, {"CLUSTER": "CL_SALVADOR", "ID FILIAL": 501}, {"CLUSTER": "CL_FEIRA", "ID FILIAL": 502}],
        "solicitacoes_cluster": [{"id": 1, "cluster": "CL_LAURO", "id_filial": "503", "status": "Pendente", "solicitante": "Bruno Souza"}],
        "dim_produto": [{"id_produto": 1000 + i, "id_fornecedor": 10 + i % 3, "categoria_comercial": ["MERCEARIA", "BEBIDAS", "LIMPEZA"][i % 3]} for i in range(8)],
        "dim_fornecedor": [{"id_fornecedor": 10 + i, "nome_grupo_empresarial": ["UNILEVER", "AMBEV", "P&G"][i]} for i in range(3)],
        "dim_empresa_concorrente": [],
    }


class _Query:
    def __init__(self, nome: str):
        self.nome, self.filtros, self.modo, self.payload, self.ordem = nome, [], "select", None, None

    def select(self, *_a, **_k): return self
    def eq(self, c, v): self.filtros.append(lambda r: r.get(c) == v); return self
    def in_(self, c, vs): s = set(vs); self.filtros.append(lambda r: r.get(c) in s); return self
    def order(self, c, desc=False): self.ordem = (c, desc); return self
    def insert(self, rec): self.modo, self.payload = "insert", rec; return self
    def update(self, campos): self.modo, self.payload = "update", campos; return self
    def delete(self): self.modo = "delete"; return self

    def execute(self):
        tabela = _DB.setdefault(self.nome, [])
        alvo = [r for r in tabela if all(f(r) for f in self.filtros)]
        if self.modo == "insert":
            recs = self.payload if isinstance(self.payload, list) else [self.payload]
            tabela.extend(copy.deepcopy(recs)); return SimpleNamespace(data=recs)
        if self.modo == "update":
            for r in alvo: r.update(copy.deepcopy(self.payload))
            return SimpleNamespace(data=alvo)
        if self.modo == "delete":
            _DB[self.nome] = [r for r in tabela if r not in alvo]; return SimpleNamespace(data=alvo)
        if self.ordem:
            alvo = sorted(alvo, key=lambda r: str(r.get(self.ordem[0]) or ""), reverse=self.ordem[1])
        return SimpleNamespace(data=copy.deepcopy(alvo))


class _Bucket:
    def upload(self, path, data, opts=None): _FILES[path] = bytes(data)
    def download(self, path): return _FILES[path]
    def remove(self, paths): [_FILES.pop(p, None) for p in paths]


class _Rpc:
    def __init__(self, nome, params): self.nome, self.params = nome, params
    def execute(self):
        if self.nome == "incrementar_visualizacao":
            for r in _DB["relatorios"]:
                if r["id"] == self.params["rid"]: r["visualizacoes"] = (r.get("visualizacoes") or 0) + 1
        return SimpleNamespace(data=None)


class FakeClient:
    storage = SimpleNamespace(from_=lambda _b: _Bucket())
    def table(self, nome): return _Query(nome)
    def rpc(self, nome, params): return _Rpc(nome, params)


_CLIENT = FakeClient()


def install() -> None:
    global _DB
    if _DB is None:
        _DB = _seed()
    from core import db
    db.get_client = lambda: _CLIENT
    db.sb = lambda: _CLIENT
