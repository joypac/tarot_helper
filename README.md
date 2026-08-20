# bookgrab

Captura uma zona do ecrã, página a página, e converte em texto com o OCR
nativo do macOS (framework Vision). Sem dependências externas.

## Âmbito

Ferramenta para material que tens o direito de copiar: documentos teus,
digitalizações próprias, obras em domínio público, PDFs que possuis, notas
tuas. **Não** para extrair livros comerciais protegidos por DRM (Kindle,
Kobo, Scribd e afins) — nesses casos o texto pertence a quem o publicou e
existem vias próprias (ver secção final).

## Instalação

```bash
bash build.sh        # compila bin/bookgrab-helper (precisa de Xcode CLT)
```

Duas permissões em Definições → Privacidade e Segurança:

- **Gravação de Ecrã** → para a app onde corres isto (Terminal / VS Code).
  Depois de dares a permissão, **fecha e reabre a app** — o macOS só a
  aplica no arranque seguinte.
- **Acessibilidade** → só se usares o avanço automático de página.

## Uso

```bash
./grab.py area      # arrastas o rato para delimitar a área útil da página
./grab.py teste     # captura uma página e mostra o texto, para afinares
./grab.py run       # percorre o documento e compila tudo em livro.md
```

O `run` para sozinho quando a página deixa de mudar. `Ctrl-C` interrompe
sem perder o que já foi capturado; `--continuar` retoma de onde ficou.

### Opções úteis

| Opção | Para quê |
|---|---|
| `--idiomas pt-BR,en-US` | línguas do OCR (`bin/bookgrab-helper langs` lista as disponíveis) |
| `--sem-correcao` | não deixa o Vision "corrigir" a ortografia — essencial em grafia antiga |
| `--sem-reflow` | mantém as quebras de linha originais (poesia, tabelas) |
| `--trim-top 0.06` | ignora o topo da página (cabeçalhos correntes) |
| `--trim-bottom 0.05` | ignora o fundo (números de página) |
| `--tecla right` | tecla que vira a página (`pagedown`, `space`, ...) |
| `--clique X,Y` | clicar num botão em vez de premir tecla |
| `--manual` | avanças tu, Enter entre páginas |
| `--marcadores` | marca o nº de página no ficheiro final |

### Estrutura

```
imagens/pag_0001.png   capturas em bruto (podes refazer o OCR sem recapturar)
texto/pag_0001.txt     texto por página
livro.md               ficheiro final
bookgrab.json          a área e as preferências ficam guardadas aqui
```

`./grab.py ocr --forcar` refaz o OCR de todas as imagens com definições
novas. `./grab.py juntar` regenera só o ficheiro final.

## PDFs

Se o que tens é mesmo um PDF, não precisas de nada disto — o OCR lê PDFs
diretamente, com muito melhor qualidade:

```bash
./bin/bookgrab-helper ocr documento.pdf --langs pt-BR --reflow > texto.md
```

E se o PDF já tiver camada de texto, `pdftotext` (Homebrew: `poppler`) é
mais fiel ainda.

## Livros comerciais com DRM

Para um livro que compraste numa loja fechada, as vias legítimas são:

- **read.amazon.com/notebook** — exporta os teus destaques e notas.
- **Pesquisa dentro do livro**, no próprio leitor.
- **VoiceOver / leitura em voz alta**, se a questão for acessibilidade.
- **Edição sem DRM** — há editoras que vendem EPUB/PDF diretamente.

## Resolução de problemas

- **Imagem em branco ou só com o fundo do ecrã** → falta Gravação de Ecrã,
  ou não reiniciaste a app depois de a dares.
- **A página não vira** → falta Acessibilidade, ou o leitor não tem foco;
  usa `--app "Google Chrome"` para o focar antes de cada tecla.
- **Overlay de seleção preso** → `Esc` cancela; em último caso
  `pkill bookgrab-helper`.

---

# corpus.py — base de conhecimento de tarot

Constrói uma ficha por carta a partir de obras em **domínio público**:

- A. E. Waite, *The Pictorial Key to the Tarot* (1911) — a obra que acompanha
  o baralho Rider-Waite-Smith
- Papus, *The Tarot of the Bohemians* (1896) — descarregado como contexto

```bash
./corpus.py baixar     # busca os textos ao Internet Archive → fontes/
./corpus.py extrair    # 78 fichas em cartas/ + capítulos em capitulos/
./corpus.py indice     # gera cartas/README.md
```

## O que sai

```
cartas/00-the-fool.md ... cartas/oui-14-king-of-pentacles.md
cartas.json            todas as cartas em dados estruturados
capitulos/             os ensaios (história, método, tiragens)
```

Cada ficha tem frontmatter (`carta`, `arcano`, `numero`, `naipe`, `fonte`) e
até quatro secções: **Descrição e simbolismo**, **Significados
adivinhatórios**, **Invertida** e **Resumo do autor** (as listas condensadas
que o Waite pôs nos §3 e §4).

## Notas sobre a fonte

O texto vem de um scan OCR, por isso tem imperfeições conhecidas:

- Os numerais romanos de *II* e *III* não sobreviveram, e o Louco aparece
  como `ZERO` — o parser ancora nos **nomes canónicos**, não nos numerais.
- Em *Five of Cups* o scan perdeu a etiqueta "Divinatory Meanings", por isso
  os significados dessa carta ficam dentro da secção **Descrição**.
- Legendas de imagens corrompidas (`THfc LOVERS.`) são filtradas por
  descartarem-se parágrafos com menos de três palavras.

Waite segue a numeração da Golden Dawn: **VIII = Força**, **XI = Justiça**
(trocadas em relação ao Tarot de Marselha).

## enriquecer.py — juntar imagens e fontes próprias

```bash
./enriquecer.py imagens   # liga cada carta ao PNG em cards-png/
./enriquecer.py nomes     # nomes portugueses de apresentação
./enriquecer.py pg        # junta o manual PG (Arcanos Maiores)
./enriquecer.py fichas    # regenera cartas/*.md a partir do JSON
```

Ordem completa a partir do zero:

```bash
./corpus.py baixar && ./corpus.py extrair
./enriquecer.py imagens && ./enriquecer.py nomes && ./enriquecer.py pg
./enriquecer.py fichas && ./corpus.py indice
```

### Notas pessoais

`notas/<carta>.md` é teu. O `fichas` só **inclui** o que lá estiver e nunca
escreve por cima, por isso podes regenerar as 78 fichas as vezes que
quiseres sem perder nada do que escreveste.

É também o sítio certo para o que fores aprendendo em livros que tens: em
vez de copiar o texto de terceiros para a base, escreves a tua leitura, com
a referência ao autor. Fica teu, é citável, e não é uma cópia.

### Cuidado com a numeração

O manual PG segue Marselha (**VIII = Justiça, XI = Força**) e o Waite segue
a Golden Dawn (**VIII = Força, XI = Justiça**). O `enriquecer.py pg` casa os
capítulos **por nome**, nunca por número — casar por número trocava as duas
cartas silenciosamente. Se juntares outra fonte, respeita a mesma regra.

O manual PG não cobre a XVI (A Torre); essa carta tem só o Waite.

---

## Sobre este repositório

Contém o código, o guia das 78 cartas e as imagens do baralho
Rider-Waite-Smith (1909, domínio público).

Os textos-fonte ficam **fora** do repositório, em `fontes/` (ignorada). Para
reconstruir a base a partir do zero, o `corpus.py baixar` vai buscar as obras
em domínio público ao Internet Archive:

```bash
./corpus.py baixar && ./corpus.py extrair
./enriquecer.py imagens && ./enriquecer.py nomes && ./enriquecer.py guia
./enriquecer.py fichas && ./site.py
```

A flag `--sem-pg` gera o build público, sem camadas de fontes locais.
