"""Gráfico de mercado no estilo terminal (Lightweight Charts, TradingView, licença Apache 2.0)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

from ui import theme

_VENDOR = Path(__file__).resolve().parent.parent / "assets" / "vendor" / "lightweight-charts.standalone.production.js"


_CDN = "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"


@lru_cache(maxsize=1)
def _biblioteca() -> str:
    """Biblioteca embutida a partir de assets/vendor; sem o arquivo, o navegador busca no CDN."""
    try:
        return "<script>" + _VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script") + "</script>"
    except OSError:
        return f'<script src="{_CDN}"></script>'



def grafico(dados: dict, moda: float | None = None, altura: int = 430) -> None:
    t = theme.tokens()
    cores = {k: t[k] for k in ("ink", "muted", "faint", "primary", "up", "down", "amber", "surface_solid", "line_hex")}
    nomes = {"var_conc": "Varejo concorrente", "atac_conc": "Atacado concorrente", "var_pdv": "Varejo PDV", "atac_pdv": "Atacado PDV"}
    payload = json.dumps({"dados": dados, "moda": moda, "cores": cores, "nomes": nomes, "escuro": theme.modo() == "Dark"})
    components.html(f"""<!doctype html><html><head><meta charset="utf-8">
<style>
@import url('{theme.FONTE_URL}');
*{{box-sizing:border-box}} html,body{{margin:0;height:100%;background:transparent;font:13px 'Geist',-apple-system,sans-serif;color:{t['ink']}}}
.wrap{{display:flex;flex-direction:column;height:100%;gap:10px}}
.top{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
.leg{{display:flex;gap:6px;flex-wrap:wrap}}
.chip{{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:10px;border:1px solid {t['line']};background:transparent;
  color:{t['muted']};cursor:pointer;font:inherit;transition:all .15s}}
.chip i{{width:8px;height:8px;border-radius:50%}} .chip b{{font:500 13px 'Geist Mono',monospace;color:{t['ink']}}}
.chip.off{{opacity:.38}} .chip:hover{{border-color:{t['line_strong']}}}
.rng{{display:flex;gap:2px;padding:3px;border-radius:10px;border:1px solid {t['line']}}}
.rng button{{border:0;background:transparent;color:{t['muted']};font:500 12px 'Geist Mono',monospace;padding:5px 10px;border-radius:7px;cursor:pointer}}
.rng button.on{{background:{t['primary_soft']};color:{t['primary']}}}
.body{{flex:1;display:flex;gap:12px;min-height:0}}
#chart{{flex:1;min-width:0;position:relative}}
.side{{width:250px;border-left:1px solid {t['line']};padding-left:14px;overflow:auto}}
.side h4{{margin:2px 0 2px;font:600 13px 'Geist',sans-serif;color:{t['ink']}}}
.side small{{color:{t['faint']};font:12px 'Geist Mono',monospace}}
.row{{display:grid;grid-template-columns:1fr auto;gap:6px;padding:7px 0;border-bottom:1px solid {t['line']};font-size:12px}}
.row span{{color:{t['muted']};overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.row b{{font:500 12px 'Geist Mono',monospace}} .row .bar{{grid-column:1/3;height:3px;border-radius:3px;background:{t['raised']}}}
.row .bar i{{display:block;height:100%;border-radius:3px;background:{t['primary']}}}
.row.first b{{color:{t['up']}}}
@media (max-width:700px){{.side{{display:none}}}}
</style></head><body><div class="wrap">
<div class="top"><div class="leg" id="leg"></div>
<div class="rng" id="rng"><button data-d="7">7D</button><button data-d="15">15D</button><button data-d="30">30D</button><button data-d="0" class="on">Tudo</button></div></div>
<div class="body"><div id="chart"></div><div class="side"><h4>Concorrentes no dia</h4><small id="dia"></small><div id="lista"></div></div></div>
</div>
{_biblioteca()}
<script>
const P = {payload}, C = P.cores, D = P.dados, LC = LightweightCharts;
const brl = v => v == null ? '-' : 'R$ ' + v.toLocaleString('pt-BR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
const dataBR = s => s.split('-').reverse().join('/');
const alfa = (h, a) => h + Math.round(a * 255).toString(16).padStart(2, '0');
const chart = LC.createChart(document.getElementById('chart'), {{
  autoSize: true,
  layout: {{ background: {{ type: 'solid', color: 'transparent' }}, textColor: C.muted, fontFamily: "'Geist Mono', monospace", fontSize: 11 }},
  grid: {{ vertLines: {{ color: alfa(C.faint, .12) }}, horzLines: {{ color: alfa(C.faint, .12) }} }},
  rightPriceScale: {{ borderVisible: false, scaleMargins: {{ top: .12, bottom: .08 }} }},
  timeScale: {{ borderVisible: false, fixLeftEdge: true, fixRightEdge: true, rightOffset: 2 }},
  crosshair: {{ mode: LC.CrosshairMode.Normal,
    vertLine: {{ color: alfa(C.faint, .7), style: 3, labelBackgroundColor: C.surface_solid }},
    horzLine: {{ color: alfa(C.faint, .7), style: 3, labelBackgroundColor: C.surface_solid }} }},
  localization: {{ locale: 'pt-BR', priceFormatter: brl,
    timeFormatter: t => typeof t === 'string' ? dataBR(t) : String(t.day).padStart(2,'0') + '/' + String(t.month).padStart(2,'0') + '/' + t.year }},
  watermark: {{ visible: true, text: 'PRICESENSE', fontSize: 46, color: alfa(C.faint, .07), fontFamily: 'Geist', fontStyle: '600' }},
}});
const def = {{
  var_conc: () => chart.addAreaSeries({{ lineColor: C.primary, topColor: alfa(C.primary, .38), bottomColor: alfa(C.primary, 0), lineWidth: 2 }}),
  atac_conc: () => chart.addLineSeries({{ color: C.down, lineWidth: 2 }}),
  var_pdv: () => chart.addLineSeries({{ color: C.amber, lineWidth: 2 }}),
  atac_pdv: () => chart.addLineSeries({{ color: alfa(C.amber, .7), lineWidth: 2, lineStyle: 2 }}),
}};
const cor = {{ var_conc: C.primary, atac_conc: C.down, var_pdv: C.amber, atac_pdv: alfa(C.amber, .7) }};
const series = {{}}, ultimo = {{}};
for (const k of Object.keys(D.series)) {{
  const pts = D.datas.map((d, i) => [d, D.series[k][i]]).filter(p => p[1] != null).map(([time, value]) => ({{ time, value }}));
  if (!pts.length) continue;
  const s = def[k](); s.applyOptions({{ priceLineVisible: false, lastValueVisible: true }}); s.setData(pts);
  series[k] = s; ultimo[k] = pts[pts.length - 1].value;
}}
if (P.moda && series.var_conc) series.var_conc.createPriceLine({{ price: P.moda, color: C.up, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'Moda' }});
chart.timeScale().fitContent();

const leg = document.getElementById('leg'), chips = {{}};
for (const k of Object.keys(series)) {{
  const b = document.createElement('button'); b.className = 'chip'; b.type = 'button';
  b.innerHTML = '<i style="background:' + cor[k] + '"></i>' + P.nomes[k] + ' <b>' + brl(ultimo[k]) + '</b>';
  b.onclick = () => {{ const on = !b.classList.toggle('off'); series[k].applyOptions({{ visible: on }}); }};
  leg.appendChild(b); chips[k] = b.querySelector('b');
}}
function lista(d) {{
  const r = D.ranking[d] || [], max = Math.max(...r.map(x => x[1]), 1);
  document.getElementById('dia').textContent = d ? dataBR(d) : '';
  document.getElementById('lista').innerHTML = r.map((x, i) => '<div class="row' + (i ? '' : ' first') + '"><span title="' + x[0] + '">' + x[0] + '</span><b>' + brl(x[1]) +
    '</b><div class="bar"><i style="width:' + (100 * x[1] / max).toFixed(1) + '%"></i></div></div>').join('') || '<small>Sem coletas nesse dia.</small>';
}}
const ultimaData = D.datas[D.datas.length - 1];
lista(ultimaData);
chart.subscribeCrosshairMove(p => {{
  if (!p || !p.time) {{ for (const k in chips) chips[k].textContent = brl(ultimo[k]); lista(ultimaData); return; }}
  const t = typeof p.time === 'string' ? p.time : p.time.year + '-' + String(p.time.month).padStart(2,'0') + '-' + String(p.time.day).padStart(2,'0');
  for (const k in series) {{ const v = p.seriesData.get(series[k]); chips[k].textContent = brl(v ? v.value : null); }}
  lista(t);
}});
document.querySelectorAll('#rng button').forEach(b => b.onclick = () => {{
  document.querySelectorAll('#rng button').forEach(x => x.classList.remove('on')); b.classList.add('on');
  const dias = +b.dataset.d; if (!dias || !ultimaData) {{ chart.timeScale().fitContent(); return; }}
  const fim = new Date(ultimaData + 'T00:00:00'), ini = new Date(fim); ini.setDate(ini.getDate() - dias + 1);
  chart.timeScale().setVisibleRange({{ from: ini.toISOString().slice(0, 10), to: ultimaData }});
}});
</script></body></html>""", height=altura)
