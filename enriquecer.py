#!/usr/bin/env python3
"""enriquecer.py — junta às fichas das cartas:
     imagens   liga cada carta ao PNG correspondente em cards-png/
     pg        junta o manual português (Arcanos Maiores), casando por NOME

Aviso: o manual PG segue a numeração de Marselha (VIII=Justiça, XI=Força),
inversa à do Waite. Casar por número trocaria as duas cartas — casa-se por nome.
"""
import html
import json
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
IMGS = RAIZ / "cards-png"
EPUB = RAIZ / "fontes" / "PG Manual Tarot Completo.epub"

NAIPE_EN = {"Paus": "Wands", "Copas": "Cups", "Espadas": "Swords", "Ouros": "Pentacles"}

# nome português -> nome canónico Waite (a numeração vem do Waite, não do PG)
PT = {
    "O LOUCO": "The Fool", "O MAGO": "The Magician", "A PAPISA": "The High Priestess",
    "A SACERDOTISA": "The High Priestess", "A IMPERATRIZ": "The Empress",
    "O IMPERADOR": "The Emperor", "O PAPA": "The Hierophant",
    "O HIEROFANTE": "The Hierophant", "OS ENAMORADOS": "The Lovers",
    "O AMOR": "The Lovers", "OS AMANTES": "The Lovers", "O CARRO": "The Chariot",
    "A JUSTICA": "Justice", "O EREMITA": "The Hermit", "O ERMITAO": "The Hermit", "O ERMITA": "The Hermit",
    "A RODA DA FORTUNA": "Wheel of Fortune", "RODA DA FORTUNA": "Wheel of Fortune",
    "A RODA": "Wheel of Fortune",
    "A FORCA": "Strength, or Fortitude", "O ENFORCADO": "The Hanged Man",
    "O PENDURADO": "The Hanged Man", "O DEPENDURADO": "The Hanged Man", "A MORTE": "Death", "A TEMPERANCA": "Temperance",
    "O DIABO": "The Devil", "A TORRE": "The Tower", "A CASA DE DEUS": "The Tower",
    "A ESTRELA": "The Star", "A LUA": "The Moon", "O SOL": "The Sun",
    "O JULGAMENTO": "The Last Judgment", "O JUIZO": "The Last Judgment",
    "O MUNDO": "The World",
}

# nomes portugueses de apresentação, para a app/EPUB
NOME_PT = {
    "The Fool": "O Louco", "The Magician": "O Mago", "The High Priestess": "A Papisa",
    "The Empress": "A Imperatriz", "The Emperor": "O Imperador",
    "The Hierophant": "O Papa", "The Lovers": "Os Enamorados", "The Chariot": "O Carro",
    "Strength, or Fortitude": "A Força", "The Hermit": "O Eremita",
    "Wheel of Fortune": "A Roda da Fortuna", "Justice": "A Justiça",
    "The Hanged Man": "O Enforcado", "Death": "A Morte", "Temperance": "A Temperança",
    "The Devil": "O Diabo", "The Tower": "A Torre", "The Star": "A Estrela",
    "The Moon": "A Lua", "The Sun": "O Sol", "The Last Judgment": "O Julgamento",
    "The World": "O Mundo",
}
POS_PT = {"Ace": "Ás", "Two": "Dois", "Three": "Três", "Four": "Quatro", "Five": "Cinco",
          "Six": "Seis", "Seven": "Sete", "Eight": "Oito", "Nine": "Nove", "Ten": "Dez",
          "Page": "Valete", "Knight": "Cavaleiro", "Queen": "Rainha", "King": "Rei"}


def sem_acento(s):
    tabela = str.maketrans("ÁÀÂÃÄÉÊÍÓÔÕÚÇáàâãäéêíóôõúç", "AAAAAEEIOOOUCaaaaaeeiooouc")
    return s.translate(tabela)


def carregar():
    p = RAIZ / "cartas.json"
    if not p.exists():
        sys.exit("  ✗ falta cartas.json — corre ./corpus.py extrair")
    return json.loads(p.read_text()), p


def cmd_imagens():
    cartas, destino = carregar()
    if not IMGS.exists():
        sys.exit(f"  ✗ não encontro {IMGS}")
    disponiveis = {f.name for f in IMGS.glob("*.png")}
    ligadas, falhadas = 0, []

    for c in cartas:
        if c["arcano"] == "maior":
            achado = next((n for n in sorted(disponiveis)
                           if n.startswith(f"{c['numero']:02d}-")), None)
        else:
            achado = f"{NAIPE_EN[c['naipe']]}{c['numero']:02d}.png"
            achado = achado if achado in disponiveis else None
        if achado:
            c["imagem"] = f"cards-png/{achado}"
            ligadas += 1
        else:
            falhadas.append(c["nome"])

    destino.write_text(json.dumps(cartas, indent=2, ensure_ascii=False))
    print(f"\n  ✓ {ligadas}/78 cartas ligadas à imagem")
    if falhadas:
        print(f"  ⚠  sem imagem: {falhadas}")


def cmd_nomes():
    cartas, destino = carregar()
    for c in cartas:
        if c["arcano"] == "maior":
            c["nome_pt"] = NOME_PT.get(c["nome"], "")
        else:
            c["nome_pt"] = f"{POS_PT[c['posicao']]} de {c['naipe']}"
    destino.write_text(json.dumps(cartas, indent=2, ensure_ascii=False))
    print(f"  ✓ nomes portugueses em {sum(1 for c in cartas if c['nome_pt'])} cartas")


def cmd_pg():
    if not EPUB.exists():
        sys.exit(f"  ✗ não encontro {EPUB.name}")
    cartas, destino = carregar()
    por_nome = {c["nome"]: c for c in cartas}

    z = zipfile.ZipFile(EPUB)
    docs = sorted(n for n in z.namelist() if n.lower().endswith((".html", ".xhtml", ".htm")))
    casadas, ignoradas = [], []

    for n in docs:
        bruto = z.read(n).decode("utf-8", "replace")
        # parágrafos, preservando as quebras de bloco
        bruto = re.sub(r'(?i)</(p|div|h[1-6]|br)\s*/?>', '\n', bruto)
        texto = html.unescape(re.sub(r'<[^>]+>', ' ', bruto))
        linhas = [re.sub(r'\s+', ' ', l).strip() for l in texto.splitlines()]
        linhas = [l for l in linhas if l and l.lower() != "unknown"]
        if not linhas:
            continue

        # o título vem no início: "XV – O DIABO"
        cabeca = sem_acento(" ".join(linhas[:2]).upper())
        alvo = None
        for pt, canonico in PT.items():
            if re.search(r'\b' + re.escape(sem_acento(pt)) + r'\b', cabeca):
                alvo = canonico
                break
        if not alvo or alvo not in por_nome:
            ignoradas.append((n, " ".join(linhas[:1])[:52]))
            continue

        corpo = [l for l in linhas[1:] if len(l.split()) > 2]
        if not corpo:
            continue
        c = por_nome[alvo]
        c.setdefault("pg", []).extend(corpo)
        casadas.append((alvo, c["numero"], len(" ".join(corpo).split())))

    destino.write_text(json.dumps(cartas, indent=2, ensure_ascii=False))
    print(f"\n  ✓ {len(casadas)} capítulos casados com cartas\n")
    for nome, num, w in sorted(casadas, key=lambda x: x[1]):
        print(f"    {num:>2}  {nome:<24} {w:>5} palavras")
    if ignoradas:
        print(f"\n  {len(ignoradas)} secções sem carta (prefácio, índice, etc.):")
        for n, a in ignoradas[:8]:
            print(f"    {a}")


GUIA_TXTS = [RAIZ / "fontes" / "Dicionario Tarot - Arcanos Maiores.txt",
             RAIZ / "fontes" / "Dicionario Tarot - Arcanos Menores.txt"]

SECOES = ["Palavras-chave", "Essência", "Simbolismo", "Psicologia e sombra",
          "Psicologia", "Sombra", "Na leitura", "Para pensar", "Nota", "Fontes"]
CHAVE = {"Palavras-chave": "palavras", "Essência": "essencia", "Simbolismo": "simbolismo",
         "Psicologia": "psicologia", "Psicologia e sombra": "psicologia_sombra",
         "Sombra": "sombra", "Na leitura": "leitura", "Para pensar": "pensar",
         "Nota": "nota", "Fontes": "fontes"}
LISTAS = {"simbolismo", "sombra", "leitura", "pensar"}


def cmd_guia():
    """Integra os dicionários de síntese (Maiores e Menores), casando por nome."""
    cartas, destino = carregar()
    por_nome = {c["nome"]: c for c in cartas}
    # índice de nomes portugueses, para os Arcanos Menores
    por_pt = {sem_acento(c.get("nome_pt", "")).upper(): c["nome"]
              for c in cartas if c.get("nome_pt")}

    cab_maior = re.compile(r'^([0-9IVX]+)\s+—\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+)$')
    casadas, falhadas = [], []

    for ficheiro in GUIA_TXTS:
        if not ficheiro.exists():
            continue
        blocos, atual = [], None
        for l in ficheiro.read_text().splitlines():
            t = l.strip()
            alvo = None
            m = cab_maior.match(t)
            if m:
                alvo = PT.get(sem_acento(m.group(2)).upper())
            elif t and t == t.upper() and 4 <= len(t) <= 40 and not t.endswith(":"):
                alvo = por_pt.get(sem_acento(t).upper())
            if alvo:
                atual = {"alvo": alvo, "linhas": []}
                blocos.append(atual)
            elif atual is not None:
                atual["linhas"].append(l)

        for b in blocos:
            if b["alvo"] not in por_nome:
                falhadas.append(b["alvo"]); continue
            guia, seccao = {}, None
            for l in b["linhas"]:
                t = l.strip()
                if not t:
                    continue
                achou = next((x for x in SECOES if t == x or t.startswith(x + ":")), None)
                if achou:
                    seccao = CHAVE[achou]
                    resto = t[len(achou):].lstrip(": ").strip()
                    guia[seccao] = [resto] if resto else []
                    continue
                if seccao:
                    guia[seccao].append(re.sub(r'^[-•]\s*', '', t))

            limpo = {}
            for k, v in guia.items():
                if k == "palavras":
                    limpo[k] = [x.strip() for x in " ".join(v).split(",") if x.strip()]
                elif k in LISTAS:
                    limpo[k] = v
                else:
                    limpo[k] = " ".join(v)
            por_nome[b["alvo"]]["guia"] = limpo
            casadas.append(b["alvo"])

    destino.write_text(json.dumps(cartas, indent=2, ensure_ascii=False))
    mai = sum(1 for n in casadas if por_nome[n]["arcano"] == "maior")
    print(f"\n  ✓ {len(casadas)} cartas com ficha de síntese  ({mai} maiores, {len(casadas)-mai} menores)")
    if falhadas:
        print(f"  ⚠  sem correspondência: {falhadas}")


NOTAS = RAIZ / "notas"
CARTAS = RAIZ / "cartas"


def slug(nome):
    return re.sub(r'[^a-z0-9]+', '-', nome.lower()).strip('-')


def cmd_fichas():
    """Regenera cartas/*.md a partir do cartas.json enriquecido.

    As notas pessoais vivem em notas/<slug>.md e são apenas *incluidas* —
    este comando nunca lhes toca, por isso podes reescrever as fichas
    sempre que quiseres sem perder o que escreveste."""
    cartas, _ = carregar()
    CARTAS.mkdir(exist_ok=True)
    NOTAS.mkdir(exist_ok=True)
    com_pg = 0

    for c in cartas:
        pre = f"{c['numero']:02d}" if c["arcano"] == "maior" else \
              f"{c['naipe'][:3].lower()}-{c['numero']:02d}"
        nome_fich = f"{pre}-{slug(c['nome'])}.md"

        fm = [f"carta: {c['nome']}", f"nome_pt: {c.get('nome_pt', '')}",
              f"arcano: {c['arcano']}", f"numero: {c['numero']}"]
        if c["naipe"]:
            fm.append(f"naipe: {c['naipe']}")
        if c.get("imagem"):
            fm.append(f"imagem: {c['imagem']}")
        partes = ["---\n" + "\n".join(fm) + "\n---\n"]

        titulo = c.get("nome_pt") or c["nome"]
        partes.append(f"# {titulo}\n\n*{c['nome']}*\n")
        if c.get("imagem"):
            partes.append(f"![{titulo}]({'../' + c['imagem']})\n")

        partes.append("## Waite — descrição e simbolismo\n\n" + "\n\n".join(c["descricao"]) + "\n")
        if c["direita"]:
            partes.append("## Waite — significados\n\n" + "\n\n".join(c["direita"]) + "\n")
        if c["invertida"]:
            partes.append("## Waite — invertida\n\n" + "\n\n".join(c["invertida"]) + "\n")
        if c.get("extra"):
            partes.append("## Waite — resumo\n\n" + c["extra"] + "\n")
        if c.get("pg") and "--sem-pg" not in sys.argv:
            com_pg += 1
            partes.append("## Manual PG (português)\n\n" + "\n\n".join(c["pg"]) + "\n")

        nota = NOTAS / f"{slug(c['nome'])}.md"
        if nota.exists() and nota.read_text().strip():
            partes.append("## Notas pessoais\n\n" + nota.read_text().strip() + "\n")
        else:
            nota.touch()

        partes.append(f"---\n\n*Fontes: A. E. Waite, The Pictorial Key to the Tarot (1911), "
                      f"domínio público{'; Manual PG' if c.get('pg') else ''}.*\n")
        (CARTAS / nome_fich).write_text("\n".join(partes))

    print(f"\n  ✓ {len(cartas)} fichas em cartas/")
    print(f"    {com_pg} com o manual PG")
    print(f"    {sum(1 for c in cartas if c.get('imagem'))} com imagem")
    print(f"    notas pessoais editáveis em notas/ (nunca sobrescritas)\n")


if __name__ == "__main__":
    cmds = {"imagens": cmd_imagens, "pg": cmd_pg, "nomes": cmd_nomes, "fichas": cmd_fichas, "guia": cmd_guia}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"uso: ./enriquecer.py [{' | '.join(cmds)}]")
    cmds[sys.argv[1]]()
