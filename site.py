#!/usr/bin/env python3
"""site.py — gera site/ a partir do cartas.json: um dicionário de tarot
navegável, offline, sem servidor e sem IA.

    ./site.py            gera site/index.html + site/cards-png/
    ./site.py --sem-copiar   não duplica as imagens (referencia ../cards-png)
"""
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "cartas.json"
IMGS = RAIZ / "cards-png"
NOTAS = RAIZ / "notas"
SAIDA = RAIZ / "site"

ORDEM_NAIPE = ["Paus", "Copas", "Espadas", "Ouros"]


def slug(nome):
    return re.sub(r'[^a-z0-9]+', '-', nome.lower()).strip('-')


def preparar():
    cartas = json.loads(DADOS.read_text())
    saida = []
    for c in cartas:
        s = slug(c["nome"])
        nota = NOTAS / f"{s}.md"
        texto_nota = nota.read_text().strip() if nota.exists() else ""
        secoes = []
        if c["descricao"]:
            secoes.append(("Descrição e simbolismo", "Waite", c["descricao"]))
        if c["direita"]:
            secoes.append(("Significados", "Waite", c["direita"]))
        if c["invertida"]:
            secoes.append(("Invertida", "Waite", c["invertida"]))
        if c.get("extra"):
            secoes.append(("Resumo", "Waite", [c["extra"]]))
        if c.get("pg") and "--sem-pg" not in sys.argv:
            secoes.append(("Leitura", "Manual PG", c["pg"]))
        if texto_nota:
            secoes.append(("Notas pessoais", "tuas", texto_nota.split("\n\n")))

        g = c.get("guia") or {}
        saida.append({
            "id": s,
            "guia": g,
            "nome": c["nome"],
            "pt": c.get("nome_pt") or c["nome"],
            "arcano": c["arcano"],
            "num": c["numero"],
            "naipe": c["naipe"],
            "img": c.get("imagem", "").replace("cards-png/", ""),
            "secoes": [{"t": t, "f": f, "p": p} for t, f, p in secoes],
            "busca": " ".join(
                [c["nome"], c.get("nome_pt", "")]
                + sum([s[2] for s in secoes], [])
                + [" ".join(v) if isinstance(v, list) else v for v in g.values()]
            ).lower(),
        })

    def chave(c):
        if c["arcano"] == "maior":
            return (0, 0, c["num"])
        return (1, ORDEM_NAIPE.index(c["naipe"]), c["num"])

    return sorted(saida, key=chave)


PAGINA = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dicionário de Tarot</title>
<style>
:root {
  --fundo: #fbfaf8; --papel: #fff; --tinta: #23201c; --suave: #6b6459;
  --linha: #e4ded4; --realce: #7c5c3e; --sombra: 0 1px 3px rgba(0,0,0,.06);
}
@media (prefers-color-scheme: dark) {
  :root {
    --fundo: #16140f; --papel: #1e1b16; --tinta: #ece6dc; --suave: #a09888;
    --linha: #322c24; --realce: #c9a227; --sombra: 0 1px 3px rgba(0,0,0,.3);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--fundo); color: var(--tinta);
  font: 16px/1.6 Georgia, "Iowan Old Style", serif;
}
header {
  position: sticky; top: 0; z-index: 10; background: var(--papel);
  border-bottom: 1px solid var(--linha); padding: .9rem 1.2rem;
}
.topo { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;
        max-width: 1180px; margin: 0 auto; }
h1 { font-size: 1.15rem; margin: 0; letter-spacing: .02em; font-weight: 600; }
h1 a { color: inherit; text-decoration: none; }
#busca {
  flex: 1; min-width: 200px; padding: .5rem .8rem; font: inherit; font-size: .95rem;
  background: var(--fundo); color: var(--tinta);
  border: 1px solid var(--linha); border-radius: 7px;
}
#busca:focus { outline: 2px solid var(--realce); outline-offset: -1px; }
.filtros { display: flex; gap: .35rem; flex-wrap: wrap; }
.filtros button {
  font: inherit; font-size: .85rem; padding: .3rem .75rem; cursor: pointer;
  background: transparent; color: var(--suave);
  border: 1px solid var(--linha); border-radius: 20px;
}
.filtros button[aria-pressed="true"] {
  background: var(--realce); border-color: var(--realce); color: var(--papel);
}
main { max-width: 1180px; margin: 0 auto; padding: 1.5rem 1.2rem 4rem; }
.grelha {
  display: grid; gap: 1.1rem;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
}
.carta { cursor: pointer; text-align: center; text-decoration: none; color: inherit; }
.carta img {
  width: 100%; aspect-ratio: 300/527; object-fit: cover; display: block;
  border-radius: 6px; box-shadow: var(--sombra); background: var(--papel);
  transition: transform .12s ease;
}
.carta:hover img { transform: translateY(-3px); }
.carta b { display: block; font-size: .82rem; font-weight: 600; margin-top: .5rem; }
.carta span { display: block; font-size: .72rem; color: var(--suave); }
.vazio { color: var(--suave); padding: 3rem 0; text-align: center; }
.secao-titulo {
  grid-column: 1/-1; font-size: .78rem; text-transform: uppercase;
  letter-spacing: .11em; color: var(--suave); margin: 1.2rem 0 -.3rem;
}
.secao-titulo:first-child { margin-top: 0; }
/* ---- ficha ---- */
.ficha { display: grid; grid-template-columns: 300px 1fr; gap: 2.4rem; align-items: start; }
@media (max-width: 720px) { .ficha { grid-template-columns: 1fr; gap: 1.4rem; } }
.ficha img { width: 100%; border-radius: 8px; box-shadow: var(--sombra); }
.ficha h2 { font-size: 2rem; margin: 0 0 .2rem; line-height: 1.15; }
.ficha .en { color: var(--suave); font-style: italic; margin: 0 0 .4rem; }
.ficha .meta { color: var(--suave); font-size: .85rem; margin: 0 0 1.8rem; }
.bloco { margin-bottom: 2rem; }
.chips { display: flex; flex-wrap: wrap; gap: .35rem; margin: 0 0 1.8rem; }
.chips button {
  font: inherit; font-size: .8rem; padding: .22rem .7rem; cursor: pointer;
  background: transparent; color: var(--realce);
  border: 1px solid var(--linha); border-radius: 20px;
}
.chips button:hover { border-color: var(--realce); }
.guia { border-left: 2px solid var(--linha); padding-left: 1.3rem; margin-bottom: 2.6rem; }
.guia ul { margin: 0 0 .8rem; padding-left: 1.1rem; }
.guia li { margin-bottom: .35rem; }
.guia .pensar li { color: var(--realce); font-style: italic; }
.fontes-linha { font-size: .8rem; color: var(--suave); font-style: italic; margin: 0; }
details.originais { margin-top: 1rem; }
details.originais summary {
  cursor: pointer; font-size: .78rem; text-transform: uppercase;
  letter-spacing: .11em; color: var(--suave); padding: .6rem 0;
}
details.originais[open] summary { margin-bottom: 1rem; }
.bloco h3 {
  font-size: .78rem; text-transform: uppercase; letter-spacing: .11em;
  color: var(--realce); margin: 0 0 .1rem; font-weight: 700;
}
.bloco .fonte { font-size: .75rem; color: var(--suave); margin: 0 0 .7rem; font-style: italic; }
.bloco p { margin: 0 0 .8rem; }
.nav { display: flex; justify-content: space-between; gap: 1rem;
       margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--linha); }
.nav a { color: var(--realce); text-decoration: none; font-size: .9rem; }
.nav a:hover { text-decoration: underline; }
mark { background: var(--realce); color: var(--papel); padding: 0 .15em; border-radius: 2px; }
</style>
</head>
<body>
<header><div class="topo">
  <h1><a href="#">Dicionário de Tarot</a></h1>
  <input id="busca" type="search" placeholder="Procurar carta, símbolo, tema..." autocomplete="off">
  <div class="filtros" id="filtros"></div>
</div></header>
<main id="app"></main>
<script id="dados" type="application/json">__DADOS__</script>
<script>
const CARTAS = JSON.parse(document.getElementById('dados').textContent);
const app = document.getElementById('app');
const busca = document.getElementById('busca');
const FILTROS = ['Tudo', 'Maiores', 'Paus', 'Copas', 'Espadas', 'Ouros'];
let filtro = 'Tudo';

const esc = s => s.replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

function realcar(txt, termo) {
  const e = esc(txt);
  if (!termo) return e;
  return e.replace(new RegExp('(' + termo.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'),
                   '<mark>$1</mark>');
}

document.getElementById('filtros').innerHTML = FILTROS.map(f =>
  `<button data-f="${f}" aria-pressed="${f === filtro}">${f}</button>`).join('');
document.getElementById('filtros').onclick = e => {
  const b = e.target.closest('button'); if (!b) return;
  filtro = b.dataset.f;
  document.querySelectorAll('#filtros button').forEach(x =>
    x.setAttribute('aria-pressed', x.dataset.f === filtro));
  if (!location.hash.startsWith('#/c/')) render();
};

function correspondem() {
  const t = busca.value.trim().toLowerCase();
  return CARTAS.filter(c => {
    const okF = filtro === 'Tudo' || (filtro === 'Maiores' && c.arcano === 'maior')
                || c.naipe === filtro;
    return okF && (!t || c.busca.includes(t));
  });
}

function grelha() {
  const lista = correspondem();
  if (!lista.length) { app.innerHTML = '<p class="vazio">Nada encontrado.</p>'; return; }
  let html = '<div class="grelha">', grupo = null;
  for (const c of lista) {
    const g = c.arcano === 'maior' ? 'Arcanos Maiores' : c.naipe;
    if (g !== grupo) { grupo = g; html += `<h2 class="secao-titulo">${g}</h2>`; }
    html += `<a class="carta" href="#/c/${c.id}">
      <img src="cards-png/${c.img}" alt="${esc(c.pt)}" loading="lazy">
      <b>${esc(c.pt)}</b><span>${esc(c.nome)}</span></a>`;
  }
  app.innerHTML = html + '</div>';
}

function lista(arr, termo, cls) {
  return `<ul class="${cls || ''}">` +
         arr.map(x => `<li>${realcar(x, termo)}</li>`).join('') + '</ul>';
}

function guiaHTML(c, termo) {
  const g = c.guia || {};
  if (!g.essencia && !g.palavras) return '';
  let h = '';
  if (g.palavras && g.palavras.length)
    h += `<div class="chips">` + g.palavras.map(p =>
      `<button data-termo="${esc(p)}">${esc(p)}</button>`).join('') + `</div>`;
  h += '<div class="guia">';
  const bloco = (titulo, corpo) => corpo
    ? `<section class="bloco"><h3>${titulo}</h3>${corpo}</section>` : '';
  h += bloco('Essência', g.essencia ? `<p>${realcar(g.essencia, termo)}</p>` : '');
  h += bloco('Simbolismo', g.simbolismo ? lista(g.simbolismo, termo) : '');
  h += bloco('Psicologia', g.psicologia ? `<p>${realcar(g.psicologia, termo)}</p>` : '');
  h += bloco('Psicologia e sombra',
             g.psicologia_sombra ? `<p>${realcar(g.psicologia_sombra, termo)}</p>` : '');
  h += bloco('Sombra', g.sombra ? lista(g.sombra, termo) : '');
  h += bloco('Na leitura', g.leitura ? lista(g.leitura, termo) : '');
  h += bloco('Para pensar', g.pensar ? lista(g.pensar, termo, 'pensar') : '');
  if (g.nota) h += `<p class="fontes-linha">${esc(g.nota)}</p>`;
  if (g.fontes) h += `<p class="fontes-linha">${esc(g.fontes)}</p>`;
  return h + '</div>';
}

function ficha(id) {
  const i = CARTAS.findIndex(c => c.id === id);
  if (i < 0) return grelha();
  const c = CARTAS[i];
  const ant = CARTAS[(i - 1 + CARTAS.length) % CARTAS.length];
  const seg = CARTAS[(i + 1) % CARTAS.length];
  const termo = busca.value.trim();
  const meta = c.arcano === 'maior'
    ? `Arcano Maior · ${c.num}` : `${c.naipe} · Arcano Menor`;

  app.innerHTML = `<div class="ficha">
    <div><img src="cards-png/${c.img}" alt="${esc(c.pt)}"></div>
    <div>
      <h2>${esc(c.pt)}</h2>
      <p class="en">${esc(c.nome)}</p>
      <p class="meta">${meta}</p>
      ${guiaHTML(c, termo)}
      ${c.secoes.length ? `<details class="originais"${c.guia.essencia ? '' : ' open'}>
        <summary>Fontes originais (${c.secoes.length})</summary>
        ${c.secoes.map(s => `<section class="bloco">
          <h3>${esc(s.t)}</h3><p class="fonte">${esc(s.f)}</p>
          ${s.p.map(p => `<p>${realcar(p, termo)}</p>`).join('')}
        </section>`).join('')}</details>` : ''}
      <nav class="nav">
        <a href="#/c/${ant.id}">← ${esc(ant.pt)}</a>
        <a href="#">Índice</a>
        <a href="#/c/${seg.id}">${esc(seg.pt)} →</a>
      </nav>
    </div></div>`;
  scrollTo(0, 0);
}

function render() {
  const m = location.hash.match(/^#\\/c\\/(.+)$/);
  m ? ficha(m[1]) : grelha();
}

busca.oninput = () => { if (location.hash.startsWith('#/c/')) location.hash = ''; else grelha(); };
app.addEventListener('click', e => {
  const b = e.target.closest('.chips button'); if (!b) return;
  busca.value = b.dataset.termo; filtro = 'Tudo';
  document.querySelectorAll('#filtros button').forEach(x =>
    x.setAttribute('aria-pressed', x.dataset.f === 'Tudo'));
  location.hash = ''; grelha();
});
addEventListener('hashchange', render);
addEventListener('keydown', e => {
  if (document.activeElement === busca) { if (e.key === 'Escape') busca.blur(); return; }
  if (e.key === '/') { e.preventDefault(); busca.focus(); return; }
  const m = location.hash.match(/^#\\/c\\/(.+)$/); if (!m) return;
  const i = CARTAS.findIndex(c => c.id === m[1]);
  if (e.key === 'ArrowLeft') location.hash = '#/c/' + CARTAS[(i - 1 + CARTAS.length) % CARTAS.length].id;
  if (e.key === 'ArrowRight') location.hash = '#/c/' + CARTAS[(i + 1) % CARTAS.length].id;
  if (e.key === 'Escape') location.hash = '';
});
render();
</script>
</body></html>
"""


def main():
    if not DADOS.exists():
        sys.exit("  ✗ falta cartas.json — corre ./corpus.py extrair")
    cartas = preparar()
    SAIDA.mkdir(exist_ok=True)

    dados = json.dumps(cartas, ensure_ascii=False).replace("</", "<\\/")
    (SAIDA / "index.html").write_text(PAGINA.replace("__DADOS__", dados))

    if "--sem-copiar" not in sys.argv:
        destino = SAIDA / "cards-png"
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(IMGS, destino)

    kb = (SAIDA / "index.html").stat().st_size // 1024
    com_pg = sum(1 for c in cartas if any(s["f"] == "Manual PG" for s in c["secoes"]))
    com_notas = sum(1 for c in cartas if any(s["f"] == "tuas" for s in c["secoes"]))
    print(f"\n  ✓ {SAIDA / 'index.html'}  ({kb} KB)")
    print(f"    {len(cartas)} cartas · {com_pg} com manual PG · {com_notas} com notas tuas")
    print(f"\n  abre com:  open {SAIDA / 'index.html'}\n")


if __name__ == "__main__":
    main()
