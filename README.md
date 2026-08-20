# Dicionário de Tarot

Um guia das 78 cartas para consulta — significado tradicional, simbolismo,
psicologia e sombra — em site estático que funciona offline, sem servidor,
sem contas e sem IA.

**→ https://joypac.github.io/tarot_helper/**

## O que é

Cada carta tem uma ficha com sete secções:

| | |
|---|---|
| **Palavras-chave** | 5 a 8 conceitos, clicáveis para navegar por tema |
| **Essência** | o significado geral, num parágrafo |
| **Simbolismo** | os símbolos principais e as tensões que criam |
| **Psicologia** | a dimensão psicológica dos símbolos |
| **Sombra** | como o princípio da carta se torna excessivo ou se inverte |
| **Na leitura** | possibilidades de interpretação, não previsões |
| **Para pensar** | perguntas para o leitor trabalhar a carta |

O guia trata o Tarot como linguagem simbólica e instrumento de reflexão, não
como previsão de acontecimentos. As cartas não são apresentadas como prova de
factos sobre terceiros nem como acontecimentos inevitáveis.

## O site

Pesquisa instantânea sobre todo o texto, filtros por arcano e naipe,
navegação com as setas do teclado, `/` para procurar, modo claro e escuro,
e um endereço por carta (`#/c/the-tower`).

Abre-se com duplo clique no `index.html`. Não precisa de rede depois de
carregado.

## Reconstruir a partir do zero

```bash
./corpus.py baixar          # obras em domínio público → fontes/
./corpus.py extrair         # 78 cartas a partir do Waite
./enriquecer.py imagens     # liga cada carta ao PNG
./enriquecer.py nomes       # nomes portugueses
./enriquecer.py guia        # fichas de síntese
./enriquecer.py fichas      # cartas/*.md
./site.py --raiz --sem-pg   # gera o index.html público
```

`./corpus.py indice` gera o índice em `cartas/README.md`.

## Estrutura

```
index.html      o site publicado
cartas.json     as 78 cartas em dados estruturados — a fonte única
cartas/         uma ficha .md por carta
capitulos/      ensaios do Waite: história, método, tiragens
cards-png/      baralho Rider-Waite-Smith (1909, domínio público)
notas/          as tuas notas, uma por carta
fontes/         textos-fonte (fora do repositório)
```

## Notas pessoais

`notas/<carta>.md` é teu. O `enriquecer.py fichas` só **inclui** o que lá
estiver e nunca escreve por cima — podes regenerar as 78 fichas as vezes que
quiseres sem perder nada.

É também o sítio certo para o que fores aprendendo em livros que tens: em vez
de copiar texto de terceiros para a base, escreves a tua leitura com a
referência ao autor.

## Fontes

- **A. E. Waite**, *The Pictorial Key to the Tarot* (1911) — descrições e
  significados das 78 cartas. Domínio público.
- **Papus**, *The Tarot of the Bohemians* (1896) — contexto teórico. Domínio
  público. Não tem significados por carta.
- Fichas de síntese em `fontes/Dicionario Tarot - *.txt`.

As imagens são o baralho Rider-Waite-Smith de 1909, desenhado por Pamela
Colman Smith (1878–1951). Domínio público.

## Cuidado com a numeração

O Waite segue a Golden Dawn: **VIII = Força, XI = Justiça** — trocadas em
relação ao Tarot de Marselha. Se juntares outra fonte, casa os capítulos
**por nome e nunca por número**, ou as duas cartas trocam-se em silêncio.

## Build local vs. público

`./site.py --raiz --sem-pg` gera a versão publicável. Sem as flags, obténs o
build local, que pode incluir camadas de fontes que não devem ser
redistribuídas.
