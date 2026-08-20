#!/usr/bin/env python3
"""corpus.py — constrói uma base de conhecimento de tarot a partir de obras
em domínio público, organizada carta a carta.

Fontes (todas em domínio público):
  · A. E. Waite, "The Pictorial Key to the Tarot" (1911)
  · Papus, "The Tarot of the Bohemians" (1896)

    ./corpus.py baixar     descarrega os textos originais para fontes/
    ./corpus.py extrair    parte o Waite em cartas/ (uma ficha por carta)
    ./corpus.py indice     gera cartas/README.md com o índice
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
FONTES = RAIZ / "fontes"
CARTAS = RAIZ / "cartas"
CAPITULOS = RAIZ / "capitulos"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

OBRAS = {
    "waite_pkt": {
        "titulo": "The Pictorial Key to the Tarot",
        "autor": "A. E. Waite",
        "ano": 1911,
        "url": "https://archive.org/stream/A.EWaiteThePictorialKeyToTheTarot/"
               "A.%20E%20Waite%20-%20The%20Pictorial%20Key%20to%20the%20Tarot_djvu.txt",
    },
    "papus_bohemians": {
        "titulo": "The Tarot of the Bohemians",
        "autor": "Papus (Gérard Encausse)",
        "ano": 1896,
        "url": "https://ia800509.us.archive.org/24/items/tarotofbohemians00papu/"
               "tarotofbohemians00papu_djvu.txt",
    },
}

ROMANOS = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
           "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
           "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21, "0": 0}

NAIPES = {"WANDS": "Paus", "CUPS": "Copas", "SWORDS": "Espadas", "PENTACLES": "Ouros"}

ORDEM_MENOR = ["King", "Queen", "Knight", "Page", "Ten", "Nine", "Eight", "Seven",
               "Six", "Five", "Four", "Three", "Two", "Ace"]

VALOR_MENOR = {n: v for v, n in enumerate(
    ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
     "Page", "Knight", "Queen", "King"], start=1)}

LIXO = re.compile(
    r'^(http://|https://|sacred-texts|\d{1,3}\s*$|\[\d{2}/\d{2}/\d{4})', re.I)


def limpar(texto):
    """Tira rodapés do scrape e reagrupa as linhas partidas em parágrafos."""
    paragrafos, buf = [], []
    for linha in texto.splitlines():
        l = linha.strip()
        if not l or LIXO.match(l):
            if buf:
                paragrafos.append(" ".join(buf))
                buf = []
            continue
        buf.append(l)
    if buf:
        paragrafos.append(" ".join(buf))
    limpos = [re.sub(r'\s+', ' ', p).strip() for p in paragrafos if len(p.split()) > 2]
    return [p for p in limpos if not e_navegacao(p)]


# Um parágrafo que é *só* uma referência a uma carta é o link "Next" do scan,
# não conteúdo. Ex.: "IV. The Emperor", "King of Wands".
_NOMES_MAI = "|".join(re.escape(n) for n in
                      ["The Fool", "The Magician", "The High Priestess", "The Empress",
                       "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
                       "Strength, or Fortitude", "Strength", "The Hermit",
                       "Wheel of Fortune", "Justice", "The Hanged Man", "Death",
                       "Temperance", "The Devil", "The Tower", "The Star", "The Moon",
                       "The Sun", "The Last Judgment", "The Last Judgement", "Judgement",
                       "The World"])
_NAV = re.compile(
    r'^(?:[IVXL]+|\d{1,2}|Zero)?\s*\.?\s*(?:' + _NOMES_MAI + r'|'
    r'(?:King|Queen|Knight|Page|Ace|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)'
    r'\s+of\s+(?:Wands|Cups|Swords|Pentacles))\s*\.?$', re.I)


def e_navegacao(p):
    return bool(_NAV.match(p.strip()))


def partir_significados(paragrafos):
    """Separa descrição / significados / invertida a partir dos marcadores do Waite."""
    corpo, direita, invertida = [], [], []
    alvo = corpo
    for p in paragrafos:
        # os marcadores aparecem a meio do parágrafo, não em linha própria
        while True:
            m = re.search(r'\b(Divinatory Meanings?|Reversed)\s*:\s*', p)
            if not m:
                break
            antes, p = p[:m.start()].strip(), p[m.end():].strip()
            if antes:
                alvo.append(antes)
            alvo = direita if m.group(1).lower().startswith("divinatory") else invertida
        if p:
            alvo.append(p)
    return corpo, direita, invertida


MAIORES = ["The Fool", "The Magician", "The High Priestess", "The Empress",
           "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
           "Strength, or Fortitude", "The Hermit", "Wheel of Fortune", "Justice",
           "The Hanged Man", "Death", "Temperance", "The Devil", "The Tower",
           "The Star", "The Moon", "The Sun", "The Last Judgment", "The World"]

# chave normalizada -> (numero, nome canónico)
IDX_MAIOR = {re.sub(r'[^a-z]', '', n.lower()): (i, n) for i, n in enumerate(MAIORES)}
IDX_MAIOR["strength"] = (8, "Strength, or Fortitude")
IDX_MAIOR["fortitude"] = (8, "Strength, or Fortitude")
IDX_MAIOR["thewheeloffortune"] = (10, "Wheel of Fortune")
IDX_MAIOR["judgment"] = (20, "The Last Judgment")


def _norm(l):
    return re.sub(r'[^a-z]', '', l.lower())


def _cabecalho_maior(linhas):
    """Identifica um arcano maior pelo nome (os numerais nem sempre sobrevivem ao OCR)."""
    for i, l in enumerate(linhas[:3]):
        hit = IDX_MAIOR.get(_norm(l))
        if hit:
            return hit[0], hit[1], i + 1
    return None


def _cabecalho_menor(linhas, naipe_atual):
    """Identifica um arcano menor. A primeira página do naipe diz 'THE SUIT OF X';
    as seguintes trazem só o naipe."""
    idx = 0
    for i, l in enumerate(linhas[:2]):
        u = l.upper().strip().rstrip('.')
        m = re.match(r'THE SUIT OF (\w+)$', u) or re.match(r'^(WANDS|CUPS|SWORDS|PENTACLES)$', u)
        if m:
            naipe_atual = m.group(1)
            idx = i + 1
            break
    if naipe_atual and idx < len(linhas):
        pos = linhas[idx].strip().rstrip('.').title()
        if pos in ORDEM_MENOR:
            return naipe_atual, pos, idx + 1
    return None if not naipe_atual else (naipe_atual, None, 0)


def _resumo_maiores(pag):
    """Página '§3 The Greater Arcana and their Divinatory Meanings' -> {numero: texto}."""
    txt = " ".join(limpar(pag))
    out = {}
    padrao = re.compile(r'(\d{1,2}|ZERO)\.\s+([A-Z][A-Z\'’ ,.-]{3,40}?)\.?\s*[—–-]{1,2}\s*')
    achados = list(padrao.finditer(txt))
    for j, m in enumerate(achados):
        fim = achados[j + 1].start() if j + 1 < len(achados) else len(txt)
        hit = IDX_MAIOR.get(_norm(m.group(2)))
        if hit:
            out[hit[0]] = txt[m.end():fim].strip()
    return out


def _resumo_menores(pag):
    """Página '§4 Some Additional Meanings of the Lesser Arcana' -> {(naipe, pos): texto}."""
    txt = " ".join(limpar(pag))
    out, naipe = {}, None
    padrao = re.compile(
        r'(?:(WANDS|CUPS|SWORDS|PENTACLES)\.\s*)?'
        r'(King|Queen|Knight|Page|Ten|Nine|Eight|Seven|Six|Five|Four|Three|Two|Ace)'
        r'\.?\s*[—–-]{1,2}\s*')
    achados = list(padrao.finditer(txt))
    for j, m in enumerate(achados):
        if m.group(1):
            naipe = m.group(1)
        if not naipe:
            continue
        fim = achados[j + 1].start() if j + 1 < len(achados) else len(txt)
        out[(naipe, m.group(2))] = txt[m.end():fim].strip()
    return out


def parse_waite(texto):
    """Devolve (cartas, capitulos) a partir do texto do Pictorial Key."""
    paginas = re.split(r'\n\s*sacred-texts\s+Waite\s+Index\s+Previous\s+Next\s*\n', texto)
    cartas, capitulos, naipe_atual = [], [], None
    resumo_mai, resumo_men = {}, {}

    for pag in paginas:
        linhas = [l.strip() for l in pag.splitlines() if l.strip()]
        if not linhas or "<!DOCTYPE html>" in pag[:200]:
            continue

        junto = " ".join(linhas[:4]).upper()
        if "GREATER ARCANA AND THEIR DIVINATORY" in junto:
            resumo_mai = _resumo_maiores(pag); continue
        if "ADDITIONAL MEANINGS OF THE LESSER" in junto:
            resumo_men = _resumo_menores(pag); continue

        carta = None
        mai = _cabecalho_maior(linhas)
        if mai:
            num, nome, corta = mai
            carta = {"nome": nome, "arcano": "maior", "numero": num,
                     "naipe": None, "posicao": None}
        else:
            men = _cabecalho_menor(linhas, naipe_atual)
            if men:
                naipe_atual, pos, corta = men
                if pos:
                    carta = {"nome": f"{pos} of {naipe_atual.title()}", "arcano": "menor",
                             "numero": VALOR_MENOR[pos], "naipe": NAIPES[naipe_atual],
                             "posicao": pos, "naipe_en": naipe_atual}

        paragrafos = limpar("\n".join(linhas[corta:] if carta else linhas))
        if not paragrafos:
            continue

        if carta:
            corpo, direita, invertida = partir_significados(paragrafos)
            carta.update(descricao=corpo, direita=direita, invertida=invertida, extra="")
            cartas.append(carta)
        else:
            capitulos.append({"titulo": " — ".join(linhas[:2])[:80], "texto": paragrafos})

    # juntar os resumos do próprio Waite a cada carta
    for c in cartas:
        if c["arcano"] == "maior":
            c["extra"] = resumo_mai.get(c["numero"], "")
        else:
            c["extra"] = resumo_men.get((c.get("naipe_en"), c["posicao"]), "")
        c.pop("naipe_en", None)

    return cartas, capitulos


def ficha(c, obra):
    fm = {"carta": c["nome"], "arcano": c["arcano"], "numero": c["numero"]}
    if c["naipe"]:
        fm["naipe"] = c["naipe"]
    cab = "---\n" + "\n".join(f"{k}: {v}" for k, v in fm.items())
    cab += f"\nfonte: {obra['autor']}, {obra['titulo']} ({obra['ano']}) — domínio público\n---\n"

    partes = [cab, f"\n# {c['nome']}\n"]
    if c["descricao"]:
        partes.append("## Descrição e simbolismo\n\n" + "\n\n".join(c["descricao"]) + "\n")
    if c["direita"]:
        partes.append("## Significados adivinhatórios\n\n" + "\n\n".join(c["direita"]) + "\n")
    if c["invertida"]:
        partes.append("## Invertida\n\n" + "\n\n".join(c["invertida"]) + "\n")
    if c.get("extra"):
        partes.append("## Resumo do autor\n\n" + c["extra"] + "\n")
    return "\n".join(partes)


def slug(nome):
    return re.sub(r'[^a-z0-9]+', '-', nome.lower()).strip('-')


# ------------------------------------------------------------------ comandos

def cmd_baixar(args):
    FONTES.mkdir(exist_ok=True)
    for chave, obra in OBRAS.items():
        destino = FONTES / f"{chave}.txt"
        if destino.exists() and not args.forcar:
            print(f"  · {chave}: já existe ({destino.stat().st_size // 1024} KB)")
            continue
        print(f"  ↓ {obra['titulo']}...", end=" ", flush=True)
        r = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "90",
                            "-o", str(destino), obra["url"]])
        if r.returncode != 0 or destino.stat().st_size < 10000:
            print("falhou")
            destino.unlink(missing_ok=True)
        else:
            print(f"{destino.stat().st_size // 1024} KB")
    print(f"\n  fontes em {FONTES}\n")


def cmd_extrair(args):
    origem = FONTES / "waite_pkt.txt"
    if not origem.exists():
        sys.exit("  ✗ falta o texto — corre primeiro: ./corpus.py baixar")

    cartas, capitulos = parse_waite(origem.read_text(errors="replace"))
    CARTAS.mkdir(exist_ok=True)
    CAPITULOS.mkdir(exist_ok=True)

    for c in cartas:
        pre = f"{c['numero']:02d}" if c["arcano"] == "maior" else \
              f"{c['naipe'][:3].lower()}-{c['numero']:02d}"
        (CARTAS / f"{pre}-{slug(c['nome'])}.md").write_text(ficha(c, OBRAS["waite_pkt"]))

    for i, cap in enumerate(capitulos, 1):
        (CAPITULOS / f"{i:02d}-{slug(cap['titulo'])[:40]}.md").write_text(
            f"# {cap['titulo']}\n\n" + "\n\n".join(cap["texto"]) + "\n")

    (RAIZ / "cartas.json").write_text(json.dumps(cartas, indent=2, ensure_ascii=False))

    maiores = sum(1 for c in cartas if c["arcano"] == "maior")
    menores = len(cartas) - maiores
    com_sig = sum(1 for c in cartas if c["direita"])
    print(f"\n  ✓ {len(cartas)} cartas  ({maiores} maiores, {menores} menores)")
    print(f"    {com_sig} com significados adivinhatórios extraídos")
    print(f"    {len(capitulos)} capítulos de contexto em {CAPITULOS.name}/")
    print(f"    dados estruturados em cartas.json\n")
    if len(cartas) != 78:
        print(f"  ⚠  esperava 78 cartas — faltam {78 - len(cartas)}, ver abaixo\n")
        vistas = {c["nome"] for c in cartas}
        for naipe in NAIPES.values():
            tem = sorted(c["posicao"] for c in cartas if c["naipe"] == naipe)
            if len(tem) != 14:
                print(f"    {naipe}: {len(tem)}/14 → falta {set(ORDEM_MENOR) - set(tem)}")
        if maiores != 22:
            print(f"    maiores: {maiores}/22")


def cmd_indice(args):
    dados = json.loads((RAIZ / "cartas.json").read_text())
    linhas = ["# Cartas\n",
              f"Fonte: {OBRAS['waite_pkt']['autor']}, *{OBRAS['waite_pkt']['titulo']}* "
              f"({OBRAS['waite_pkt']['ano']}), domínio público.\n",
              "## Arcanos Maiores\n"]
    for c in sorted([c for c in dados if c["arcano"] == "maior"], key=lambda c: c["numero"]):
        linhas.append(f"- {c['numero']:>2}. [{c['nome']}]({c['numero']:02d}-{slug(c['nome'])}.md)")
    for naipe in NAIPES.values():
        doNaipe = sorted([c for c in dados if c["naipe"] == naipe], key=lambda c: c["numero"])
        if not doNaipe:
            continue
        linhas.append(f"\n## {naipe}\n")
        for c in doNaipe:
            linhas.append(f"- [{c['nome']}]({naipe[:3].lower()}-{c['numero']:02d}-{slug(c['nome'])}.md)")
    (CARTAS / "README.md").write_text("\n".join(linhas) + "\n")
    print(f"\n  ✓ {CARTAS / 'README.md'}\n")


def main():
    ap = argparse.ArgumentParser(description="base de conhecimento de tarot (domínio público)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("baixar"); p.add_argument("--forcar", action="store_true")
    sub.add_parser("extrair")
    sub.add_parser("indice")
    args = ap.parse_args()
    {"baixar": cmd_baixar, "extrair": cmd_extrair, "indice": cmd_indice}[args.cmd](args)


if __name__ == "__main__":
    main()
