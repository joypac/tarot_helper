#!/usr/bin/env python3
"""bookgrab — captura um livro/documento página a página a partir do ecrã e faz OCR.

Fluxo típico:
    ./grab.py area          delimitas a área da página com o rato (uma vez)
    ./grab.py teste         confirma que a captura e o OCR estão bons
    ./grab.py run           passa as páginas todas e compila o texto
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
HELPER = RAIZ / "bin" / "bookgrab-helper"

TECLAS = {
    "right": 124, "left": 123, "down": 125, "up": 126,
    "pagedown": 121, "pageup": 116, "space": 49, "enter": 36,
    "j": 38, "k": 40, "n": 45,
}

PADRAO = {
    "regiao": None,
    "idiomas": ["pt-BR", "en-US"],
    "tecla": "right",
    "espera": 1.2,
    "reflow": True,
    "correcao": True,
    "trim_top": 0.0,
    "trim_bottom": 0.0,
    "clique": None,
    "app": None,
}


# ---------------------------------------------------------------- infra

def erro(msg):
    print(f"\n  ✗ {msg}\n", file=sys.stderr)
    sys.exit(1)


def helper(*args, **kw):
    if not HELPER.exists():
        erro(f"falta compilar o helper — corre:  bash {RAIZ / 'build.sh'}")
    return subprocess.run([str(HELPER), *map(str, args)],
                          capture_output=True, text=True, **kw)


class Projeto:
    def __init__(self, pasta):
        self.pasta = Path(pasta).resolve()
        self.cfg_path = self.pasta / "bookgrab.json"
        self.imagens = self.pasta / "imagens"
        self.texto = self.pasta / "texto"
        self.cfg = dict(PADRAO)
        if self.cfg_path.exists():
            self.cfg.update(json.loads(self.cfg_path.read_text()))

    def gravar(self):
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.cfg_path.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False))

    def regiao(self):
        r = self.cfg.get("regiao")
        if not r:
            erro("área não definida ainda — corre primeiro:  ./grab.py area")
        return r

    def paginas_existentes(self):
        return sorted(self.imagens.glob("pag_*.png"))


# ---------------------------------------------------------------- captura

def capturar(regiao, destino):
    r = regiao
    subprocess.run(
        ["screencapture", "-x", "-t", "png",
         f"-R{r['x']},{r['y']},{r['w']},{r['h']}", str(destino)],
        check=True,
    )
    return destino


def digest(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ocr_imagem(caminho, cfg):
    args = ["ocr", str(caminho), "--langs", ",".join(cfg["idiomas"]),
            "--trim-top", cfg["trim_top"], "--trim-bottom", cfg["trim_bottom"]]
    if cfg["reflow"]:
        args.append("--reflow")
    if not cfg.get("correcao", True):
        args.append("--sem-correcao")
    p = helper(*args)
    if p.returncode != 0:
        erro(p.stderr.strip() or "OCR falhou")
    return p.stdout.strip()


def avancar(cfg):
    if cfg.get("app"):
        subprocess.run(["osascript", "-e", f'tell application "{cfg["app"]}" to activate'],
                       capture_output=True)
        time.sleep(0.15)
    if cfg.get("clique"):
        x, y = cfg["clique"]
        helper("click", x, y)
    else:
        helper("key", TECLAS[cfg["tecla"]])


# ---------------------------------------------------------------- comandos

def cmd_area(proj, args):
    print("\n  Arrasta o rato para delimitar a área da página (Esc cancela)...\n")
    time.sleep(0.4)
    p = helper("select")
    if p.returncode == 2:
        erro("cancelado")
    if p.returncode != 0:
        erro(p.stderr.strip() or "não consegui ler a seleção")
    proj.cfg["regiao"] = json.loads(p.stdout.strip())
    proj.gravar()
    r = proj.cfg["regiao"]
    print(f"  ✓ área guardada: {r['w']}×{r['h']} px em ({r['x']}, {r['y']})")
    print(f"    → {proj.cfg_path}\n")


def cmd_teste(proj, args):
    regiao = proj.regiao()
    proj.pasta.mkdir(parents=True, exist_ok=True)
    alvo = proj.pasta / "teste.png"
    if args.aquecimento:
        contagem(args.aquecimento)
    capturar(regiao, alvo)
    if alvo.stat().st_size < 3000:
        print("  ⚠  a imagem saiu quase vazia — falta a permissão de Gravação de Ecrã?")
    texto = ocr_imagem(alvo, proj.cfg)
    print("\n" + "─" * 70)
    print(texto if texto else "  (nenhum texto reconhecido)")
    print("─" * 70)
    print(f"\n  imagem: {alvo}")
    print(f"  {len(texto.split())} palavras, {len(texto)} caracteres\n")


def contagem(seg):
    print(f"\n  Clica na janela do livro. A começar em {seg}s: ", end="", flush=True)
    for i in range(seg, 0, -1):
        print(f"{i} ", end="", flush=True)
        time.sleep(1)
    print("\n")


def cmd_run(proj, args):
    regiao = proj.regiao()
    proj.imagens.mkdir(parents=True, exist_ok=True)
    proj.texto.mkdir(parents=True, exist_ok=True)

    inicio = 1
    if args.continuar:
        existentes = proj.paginas_existentes()
        if existentes:
            inicio = int(existentes[-1].stem.split("_")[1]) + 1
            print(f"\n  a continuar a partir da página {inicio}")

    if not args.manual:
        contagem(args.aquecimento)

    anterior = None
    capturadas = []
    n = inicio
    fim = inicio + args.paginas - 1
    try:
        while n <= fim:
            if args.manual and n > inicio:
                try:
                    input(f"  página {n - 1} capturada — Enter para a seguinte (Ctrl-C para acabar) ")
                except EOFError:
                    break

            destino = proj.imagens / f"pag_{n:04d}.png"
            capturar(regiao, destino)
            d = digest(destino)

            if n == inicio and destino.stat().st_size < 3000:
                print("\n  ⚠  imagem quase vazia — confirma a permissão de Gravação de Ecrã")

            if anterior is not None and d == anterior and not args.sem_autostop:
                destino.unlink()
                print(f"\n  ▪ página {n} igual à anterior — provavelmente chegaste ao fim.")
                break

            anterior = d
            capturadas.append(destino)
            print(f"\r  capturadas: {len(capturadas)}   (página {n})   ", end="", flush=True)

            if not args.manual:
                avancar(proj.cfg)
                time.sleep(proj.cfg["espera"] if args.espera is None else args.espera)
            n += 1
    except KeyboardInterrupt:
        print("\n\n  interrompido — as páginas já capturadas ficam guardadas.")

    print(f"\n\n  ✓ {len(capturadas)} páginas em {proj.imagens}")
    if not args.so_imagens:
        cmd_ocr(proj, args)


def cmd_ocr(proj, args):
    imagens = proj.paginas_existentes()
    if not imagens:
        erro("não há imagens capturadas ainda")
    proj.texto.mkdir(parents=True, exist_ok=True)
    print(f"\n  OCR de {len(imagens)} páginas...")

    feitas = [0]

    def trabalho(img):
        alvo = proj.texto / (img.stem + ".txt")
        if alvo.exists() and not args.forcar:
            feitas[0] += 1
            return
        alvo.write_text(ocr_imagem(img, proj.cfg))
        feitas[0] += 1
        print(f"\r  {feitas[0]}/{len(imagens)}   ", end="", flush=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(trabalho, imagens))
    print(f"\r  {len(imagens)}/{len(imagens)}   ")
    cmd_juntar(proj, args)


def cmd_juntar(proj, args):
    fichs = sorted(proj.texto.glob("pag_*.txt"))
    if not fichs:
        erro("não há texto para juntar — corre ./grab.py ocr")
    partes = []
    for f in fichs:
        n = int(f.stem.split("_")[1])
        corpo = f.read_text().strip()
        if args.marcadores:
            partes.append(f"<!-- página {n} -->\n\n{corpo}")
        else:
            partes.append(corpo)
    saida = proj.pasta / args.saida
    saida.write_text("\n\n".join(partes) + "\n")
    palavras = sum(len(p.split()) for p in partes)
    print(f"\n  ✓ {saida}")
    print(f"    {len(fichs)} páginas · {palavras:,} palavras\n".replace(",", " "))


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(
        prog="grab.py", description="captura um livro do ecrã, página a página, e faz OCR")
    ap.add_argument("--projeto", default=".", help="pasta do projeto (por omissão: atual)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comum(p):
        p.add_argument("--idiomas", help="ex: pt-BR,en-US")
        p.add_argument("--sem-reflow", action="store_true",
                       help="manter as quebras de linha originais")
        p.add_argument("--sem-correcao", action="store_true",
                       help="não deixar o Vision corrigir a ortografia (grafia antiga)")
        p.add_argument("--trim-top", type=float, help="ignorar o topo (0-1), p.ex. cabeçalhos")
        p.add_argument("--trim-bottom", type=float, help="ignorar o fundo (0-1), p.ex. nº de página")
        p.add_argument("--saida", default="livro.md")
        p.add_argument("--marcadores", action="store_true", help="marcar nº de página no ficheiro")
        p.add_argument("--forcar", action="store_true", help="refazer OCR de páginas já feitas")

    p = sub.add_parser("area", help="delimitar a área da página no ecrã")

    p = sub.add_parser("teste", help="capturar e ler uma página, para afinar")
    p.add_argument("--aquecimento", type=int, default=0)
    comum(p)

    p = sub.add_parser("run", help="percorrer o livro todo")
    p.add_argument("--paginas", type=int, default=2000, help="máximo de páginas")
    p.add_argument("--espera", type=float, help="segundos entre virar e capturar")
    p.add_argument("--tecla", choices=sorted(TECLAS), help="tecla que vira a página")
    p.add_argument("--clique", help="clicar em X,Y em vez de premir tecla")
    p.add_argument("--app", help='app a focar antes de virar, ex: "Google Chrome"')
    p.add_argument("--manual", action="store_true", help="avanças tu; Enter entre páginas")
    p.add_argument("--aquecimento", type=int, default=5)
    p.add_argument("--continuar", action="store_true", help="retomar de onde ficou")
    p.add_argument("--sem-autostop", action="store_true")
    p.add_argument("--so-imagens", action="store_true", help="capturar sem fazer OCR")
    comum(p)

    p = sub.add_parser("ocr", help="(re)processar as imagens guardadas")
    comum(p)

    p = sub.add_parser("juntar", help="gerar o ficheiro final a partir do texto")
    comum(p)

    args = ap.parse_args()
    proj = Projeto(args.projeto)

    # opções que persistem na config
    for chave, valor in [("idiomas", getattr(args, "idiomas", None)),
                         ("tecla", getattr(args, "tecla", None)),
                         ("espera", getattr(args, "espera", None)),
                         ("trim_top", getattr(args, "trim_top", None)),
                         ("trim_bottom", getattr(args, "trim_bottom", None)),
                         ("app", getattr(args, "app", None))]:
        if valor is not None:
            proj.cfg[chave] = valor.split(",") if chave == "idiomas" else valor
    if getattr(args, "sem_reflow", False):
        proj.cfg["reflow"] = False
    if getattr(args, "sem_correcao", False):
        proj.cfg["correcao"] = False
    if getattr(args, "clique", None):
        proj.cfg["clique"] = [float(v) for v in args.clique.split(",")]
    if args.cmd != "area":
        proj.gravar()

    {"area": cmd_area, "teste": cmd_teste, "run": cmd_run,
     "ocr": cmd_ocr, "juntar": cmd_juntar}[args.cmd](proj, args)


if __name__ == "__main__":
    main()
