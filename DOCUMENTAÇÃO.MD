# Pyrtugues — Documentação completa

> Programação em português que vira Python.

Esta documentação descreve o projeto **Pyrtugues** como ele está hoje: o tradutor, os dois dicionários (EDU e COMPLETO), o aplicativo desktop com curso integrado, a extensão para VS Code e a demo do Desafio do Chefão. Tudo aqui foi levantado a partir do código-fonte do projeto, e as tabelas de palavras e os exemplos de tradução foram gerados rodando o próprio tradutor, não escritos de memória.

## Ficha do projeto

| Item | Valor |
|---|---|
| Nome | Pyrtugues (escrito exatamente assim) |
| O que é | Tradutor de português para Python, com editor, curso e extensão para VS Code |
| Extensão de arquivo | `.pyrt` |
| Repositório | https://github.com/pyrtugues/Pyrtugues |
| Aplicativo desktop (`curso.py`) | versão **1.4.0** (interface em CustomTkinter) |
| Núcleo do tradutor na extensão | `pyrtugues_core.py`, com a mesma lógica de tradução da v1.4.0 |
| Extensão do VS Code | versão **1.5.0**, publisher `pyrtugues`, nome `pyrtugues` |
| Requisito de execução | Python **3.8 ou superior** instalado no computador |
| Dicionários | `dicionario.json` (modo **EDU**) e `dicionario_completo.json` (modo **COMPLETO**) |
| Licença | Pyrtugues Personal & Individual Educational License (texto no arquivo `LICENSE` do repositório) |

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Guia rápido](#3-guia-rápido)
4. [A linguagem: referência de sintaxe](#4-a-linguagem-referência-de-sintaxe)
5. [Os dicionários](#5-os-dicionários)
6. [O tradutor por dentro](#6-o-tradutor-por-dentro)
7. [Linha de comando (`pyrtugues_cli.py`)](#7-linha-de-comando-pyrtugues_clipy)
8. [Extensão para VS Code](#8-extensão-para-vs-code)
9. [Aplicativo desktop (`curso.py`)](#9-aplicativo-desktop-cursopy)
10. [O curso integrado](#10-o-curso-integrado)
11. [Demo: Desafio do Chefão](#11-demo-desafio-do-chefão)
12. [Exemplos completos](#12-exemplos-completos)
13. [Pontos de atenção e comportamentos observados](#13-pontos-de-atenção-e-comportamentos-observados)
14. [Licença e publicação](#14-licença-e-publicação)
15. [Apêndices](#15-apêndices)

---

## 1. Visão geral

### 1.1 O que é o Pyrtugues

O Pyrtugues permite escrever programas com palavras em português (`se`, `senão`, `para`, `enquanto`, `função`, `mostrar`, `pergunte`…) e executá-los como Python. Ele **não é um interpretador novo**: é um tradutor de texto que converte o código `.pyrt` em código Python comum e entrega o resultado ao Python instalado no computador.

A proposta pedagógica que aparece na página *Sobre* do aplicativo é um caminho em quatro passos: programar em português, entender a lógica, enxergar o Python gerado e, por fim, aprender Python de verdade. Por isso o Python traduzido fica sempre visível ao lado do código (no aplicativo, no painel "Python"; na extensão, no comando **Ver Python gerado**).

Como o resultado é Python normal, tudo o que existe em Python continua valendo: bibliotecas externas (`pygame`, `numpy`, `customtkinter`…), classes, geradores, decoradores, `match`/`case`. Também é possível **misturar** português e Python no mesmo arquivo; a demo do Chefão, por exemplo, usa `def` (Python) junto com `se`, `para` e `retornar`.

### 1.2 Componentes do projeto

| Componente | Arquivo(s) | Para que serve |
|---|---|---|
| Tradutor (núcleo) | `curso.py` (função `traduzir`) e `python/pyrtugues_core.py` | Converte português em Python |
| Dicionários | `dicionario.json`, `dicionario_completo.json` | Mapeiam palavras em português para Python (modos EDU e COMPLETO) |
| Aplicativo desktop | `curso.py` (classe `JanelaBR`) | Editor com tradução em tempo real, terminal, exemplos, curso e página Sobre |
| Linha de comando | `python/pyrtugues_cli.py` | Traduz e executa arquivos `.pyrt`; usada pela extensão |
| Extensão VS Code | `extension.js`, `package.json`, `syntaxes/`, `snippets/` e demais | Destaque de sintaxe, executar, ver Python, exportar, snippets, modo EDU/COMPLETO |
| Curso | `DADOS_CURSO` dentro de `curso.py` | 61 aulas no modo EDU e 125 no COMPLETO |
| Demo | `demos/chefao.pyrt` | Chefão 2D feito em Pyrtugues com Pygame |

### 1.3 Os dois modos: EDU e COMPLETO

| | EDU | COMPLETO |
|---|---|---|
| Dicionário | `dicionario.json` | `dicionario_completo.json` (no app original: `dicionario_completo_json`, sem o ponto) |
| Entradas no arquivo | 2680 | 9394 |
| Entradas ativas após o filtro do tradutor | 2671 | 9358 |
| Foco | Aprender: núcleo da linguagem, tipos, exceções e biblioteca padrão | Cobertura máxima: inclui métodos especiais, mais exceções e muito mais nomes |
| Curso | 61 aulas em 15 módulos | 125 aulas em 31 módulos (as 61 do EDU mais 64 de nível COMPLETO) |
| Padrão | Sim (`edu`) | Escolhido pelo usuário |

O dicionário EDU está contido no COMPLETO (toda chave do EDU existe também no COMPLETO), mas alguns valores diferem; veja a seção [5.4](#54-diferenças-entre-edu-e-completo). Os pontos de atenção do modo COMPLETO estão na [seção 13](#13-pontos-de-atenção-e-comportamentos-observados).

---

## 2. Arquitetura

### 2.1 Visão em diagrama

```
                         ┌────────────────────────────┐
  código .pyrt  ───────► │  pyrtugues_core.traduzir() │ ───────► código Python
  (português)            └─────────────▲──────────────┘              │
                                       │                             ├──► "Ver Python gerado" / painel Python
                         dicionário (EDU ou COMPLETO)                ├──► exportar como .py
                         + tabelas internas (métodos,                └──► executado pelo Python do sistema
                           módulos, aliases)
```

### 2.2 Arquivos da extensão (pacote `pyrtugues-vscode`)

| Caminho | Função |
|---|---|
| `package.json` | Manifesto: linguagem, gramática, snippets, comandos, menus, atalho, configurações e tema de ícones |
| `extension.js` | Código da extensão (ativação, comandos, preview ao vivo, execução, barra de status) |
| `python/pyrtugues_core.py` | Tradutor extraído do aplicativo (sem interface gráfica nem curso) |
| `python/pyrtugues_cli.py` | Comandos `traduzir` e `executar`, chamados pela extensão |
| `python/dicionario.json` | Dicionário do modo EDU |
| `python/dicionario_completo.json` | Dicionário do modo COMPLETO |
| `syntaxes/pyrtugues.tmLanguage.json` | Gramática TextMate de destaque de sintaxe (gerada) |
| `tools/gerar_gramatica.py` | Regenera a gramática a partir dos dicionários |
| `snippets/pyrtugues.json` | Snippets da linguagem |
| `language-configuration.json` | Comentários, pares de delimitadores, indentação e dobras |
| `fileicons/pyrtugues-icon-theme.json` + `icons/pyrtugues.svg` | Tema de ícones para arquivos `.pyrt` |
| `icon.png` | Ícone da extensão |
| `demos/chefao.pyrt` | Demo "Desafio do Chefão" |
| `README.md`, `.vscodeignore`, `.vscode/launch.json` | Leia-me, arquivos excluídos do pacote e configuração para testar com F5 |

### 2.3 Dois caminhos de execução

- **Aplicativo desktop:** traduz o código, localiza um Python instalado no sistema, grava um script temporário e o executa em um processo separado. O `input()` do programa vira uma janela modal do aplicativo (veja [9.4](#94-execução-e-entrada-interativa)).
- **Extensão VS Code:** chama `pyrtugues_cli.py executar <arquivo>` em uma *Task* do VS Code, dentro do terminal integrado. O `pergunte()` funciona direto no terminal.

Nos dois casos o programa roda no **Python do computador do usuário**, o que significa que bibliotecas como `pygame` ou `numpy` precisam estar instaladas nesse mesmo Python (`pip install ...`).

---

## 3. Guia rápido

### 3.1 Usando a extensão do VS Code

1. Instale o **Python 3.8+** e confirme que ele está no PATH (ou informe o caminho em `pyrtugues.caminhoPython`).
2. No VS Code, abra a aba de extensões e procure por **Pyrtugues — Python em português** (ID `pyrtugues.pyrtugues`). Para instalar de um arquivo, use *Extensões → ⋯ → Instalar do VSIX…*.
3. Crie um arquivo `ola.pyrt`:

```pyrt
mostrar("Olá, mundo!")
```

```python
print("Olá, mundo!")
```

4. Aperte **Ctrl+F5** (ou o botão ▶ no topo do editor) para executar no terminal integrado.
5. Use o botão **Ver Python gerado** para abrir a tradução ao lado; ela se atualiza enquanto você digita.
6. O modo (`edu` ou `completo`) aparece na barra de status, no canto inferior direito. Clique para alternar.

### 3.2 Usando o aplicativo desktop

1. Tenha o **Python** e a biblioteca `customtkinter` (`pip install customtkinter`).
2. Deixe `curso.py`, `dicionario.json` e `dicionario_completo_json` na **mesma pasta** (o app procura os dicionários ao lado do script).
3. Rode `python curso.py`.
4. Na tela inicial, escolha **EDU** ou **COMPLETO**. Dá para trocar depois na página *Curso*.
5. Escreva no editor e use **Ctrl+Enter** (ou o botão **▶ Executar código**).

### 3.3 Usando pela linha de comando

```bash
python python/pyrtugues_cli.py traduzir programa.pyrt --modo edu
python python/pyrtugues_cli.py executar programa.pyrt --modo completo
echo 'mostrar("oi")' | python python/pyrtugues_cli.py traduzir -
```

Detalhes na [seção 7](#7-linha-de-comando-pyrtugues_clipy).

---

## 4. A linguagem: referência de sintaxe

### 4.1 Princípios

- **A estrutura é a do Python.** Blocos são marcados por `:` e por **indentação** (o editor insere 4 espaços). O Pyrtugues só troca palavras; ele não muda a gramática.
- **A tradução não altera a quantidade de linhas.** Por isso, quando acontece um erro, a linha mostrada ao usuário é a do código em português.
- **Maiúsculas e minúsculas não importam na tradução.** O tradutor usa substituição sem diferenciar caixa; veja o exemplo abaixo.
- **Strings e comentários são protegidos.** O texto dentro de aspas e depois de `#` nunca é traduzido.
- **Você pode misturar com Python.** Palavras que já são Python (`def`, `print`, `lambda`, `self`…) continuam funcionando como estão.

```pyrt
MOSTRAR("oi")
Se verdadeiro:
    Mostrar("ok")
```

```python
MOSTRAR("oi")
Se True:
    Mostrar("ok")
```

### 4.2 Palavras de controle

Estruturas de decisão, repetição, funções, classes, exceções, módulos e operadores lógicos (extraídas do dicionário EDU):

| Pyrtugues | Python |
|---|---|
| `se` | `if` |
| `senão` | `else` |
| `senão_se` | `elif` |
| `para` | `for` |
| `enquanto` | `while` |
| `quebrar` | `break` |
| `continuar` | `continue` |
| `passar` | `pass` |
| `com` | `with` |
| `excluir` | `del` |
| `função` | `def` |
| `classe` | `class` |
| `retornar` | `return` |
| `produzir` | `yield` |
| `assíncrono` | `async` |
| `aguardar` | `await` |
| `global` | `global` |
| `não_local` | `nonlocal` |
| `importar` | `import` |
| `de` | `from` |
| `como` | `as` |
| `tentar` | `try` |
| `exceto` | `except` |
| `finalmente` | `finally` |
| `levantar` | `raise` |
| `afirmar` | `assert` |
| `e` | `and` |
| `ou` | `or` |
| `não` | `not` |
| `é` | `is` |
| `em` | `in` |

Também existem `correspondência` (→ `match`) e `caso` (→ `case`), que o Python trata como palavras-chave "suaves". Além dessas, o tradutor reconhece expressões de duas ou mais palavras: `senão se` (→ `elif`), `para cada` (→ `for`) e `enquanto verdadeiro` (→ `while True`). A forma com sublinhado, `senão_se`, também funciona.

```pyrt
nota = 6
se nota maior ou igual a 7:
    mostrar("Aprovado")
senão se nota maior ou igual a 5:
    mostrar("Recuperação")
senão_se nota menor que 3:
    mostrar("Muito baixa")
senão:
    mostrar("Reprovado")
```

```python
nota = 6
if nota >= 7:
    print("Aprovado")
elif nota >= 5:
    print("Recuperação")
elif nota < 3:
    print("Muito baixa")
else:
    print("Reprovado")
```

```pyrt
para i em intervalo(1, 6):
    mostrar(i)
```

```python
for i in range(1, 6):
    print(i)
```

```pyrt
para cada fruta em ["maçã", "uva"]:
    mostrar(fruta)
```

```python
for fruta in ["maçã", "uva"]:
    print(fruta)
```

```pyrt
n = 0
enquanto n menor que 3:
    n mais igual 1

enquanto verdadeiro:
    quebrar
```

```python
n = 0
while n < 3:
    n += 1

while True:
    break
```

### 4.3 Constantes

| Pyrtugues | Python |
|---|---|
| `verdadeiro` | `True` |
| `falso` | `False` |
| `nulo` | `None` |

```pyrt
x = nulo
se x é nulo:
    mostrar("sem valor")
se x não é nulo:
    mostrar("com valor")
```

```python
x = None
if x is None:
    print("sem valor")
if x is not None:
    print("com valor")
```

### 4.4 Operadores por extenso

#### Expressões compostas

São substituídas primeiro, das mais longas para as mais curtas, antes de qualquer outra regra.

| Escreva | Vira | Verificado |
|---|---|---|
| `maior ou igual a` | `>=` | ✅ |
| `menor ou igual a` | `<=` | ✅ |
| `maior ou igual` | `>=` | ✅ |
| `menor ou igual` | `<=` | ✅ |
| `maior que` | `>` | ✅ |
| `menor que` | `<` | ✅ |
| `diferente de` | `!=` | ✅ |
| `igual a` | `==` | ✅ |
| `fora de` | `not in` | ✅ |
| `dentro de` | `in` | ✅ |
| `dividido por` | `/` | ✅ |
| `elevado a` | `**` | ✅ |
| `potência` | `**` | ✅ |
| `divisão inteira` | `//` | ✅ |
| `mais igual` | `+=` | ✅ |
| `menos igual` | `-=` | ✅ |
| `vezes igual` | `*=` | ✅ |
| `dividido igual` | `/=` | ✅ |
| `resto igual` | `%=` | ✅ |
| `potência igual` | `**=` | ⚠️ gera `a ** igual b` |
| `e também` | `and` | ✅ |
| `ou então` | `or` | ✅ |
| `não é` | `is not` | ✅ |
| `senão se` | `elif` | ✅ |
| `para cada` | `for` | ✅ |
| `enquanto verdadeiro` | `while True` | ✅ |

A coluna **Verificado** mostra o resultado real obtido rodando o tradutor no modo EDU: ✅ quando a tradução é a esperada e ⚠️ quando o resultado difere (veja a [seção 13](#13-pontos-de-atenção-e-comportamentos-observados)).

#### Palavras soltas (dependem do contexto)

`e`, `ou`, `mais`, `menos`, `vezes` e `resto` só viram operador quando ficam **entre dois operandos** (há um identificador ou fechamento de parêntese antes e um operando depois). Isso evita trocar a letra `e` ou a palavra `mais` quando fazem parte de outra coisa.

| Palavra | Vira | Verificado |
|---|---|---|
| `mais` | `+` | ✅ |
| `menos` | `-` | ✅ |
| `vezes` | `*` | ✅ |
| `resto` | `%` | ✅ |
| `e` | `and` | ✅ |
| `ou` | `or` | ✅ |

Outras palavras relevantes: `em` (→ `in`, e dentro de `para x em y` vira `for x in y`), `como` (→ `as`), `é` (→ `is`) e `não` (→ `not`). A palavra `igual` **sozinha** não é traduzida: use `igual a` ou `==`.

```pyrt
x = 5
se x maior que 1 e x menor que 10 ou x igual a 0:
    mostrar("ok")
se não x diferente de 5:
    mostrar("x vale 5")
```

```python
x = 5
if x > 1 and x < 10 or x == 0:
    print("ok")
if not x != 5:
    print("x vale 5")
```

```pyrt
a = 10 mais 5
b = a menos 3
c = b vezes 2
d = c resto 4
e2 = 2 elevado a 3
f = 9 dividido por 3
g = 9 divisão inteira 2
```

```python
a = 10 + 5
b = a - 3
c = b * 2
d = c % 4
e2 = 2 ** 3
f = 9 / 3
g = 9 // 2
```

```pyrt
se 3 dentro de [1, 2, 3]:
    mostrar("tem")
se 9 fora de [1, 2, 3]:
    mostrar("não tem")
```

```python
if 3 in [1, 2, 3]:
    print("tem")
if 9 not in [1, 2, 3]:
    print("não tem")
```

### 4.5 Funções embutidas

| Pyrtugues | Python |
|---|---|
| `mostrar` | `print` |
| `entrada` | `input` |
| `abrir` | `open` |
| `tamanho` | `len` |
| `intervalo` | `range` |
| `tipo` | `type` |
| `identidade` | `id` |
| `ajuda` | `help` |
| `diretório_de_atributos` | `dir` |
| `atributos` | `vars` |
| `representação` | `repr` |
| `ascii` | `ascii` |
| `formatar` | `format` |
| `ordenar` | `sorted` |
| `inverter` | `reversed` |
| `filtrar` | `filter` |
| `mapear` | `map` |
| `zipar` | `zip` |
| `enumerar` | `enumerate` |
| `todos` | `all` |
| `algum` | `any` |
| `absoluto` | `abs` |
| `arredondar` | `round` |
| `binário` | `bin` |
| `octal` | `oct` |
| `hexadecimal` | `hex` |
| `ordinal` | `ord` |
| `caractere` | `chr` |
| `somar` | `sum` |
| `máximo` | `max` |
| `mínimo` | `min` |
| `potência` | `pow` |
| `divisão_e_resto` | `divmod` |
| `hash` | `hash` |
| `é_chamável` | `callable` |
| `é_instância` | `isinstance` |
| `é_subclasse` | `issubclass` |
| `globais` | `globals` |
| `locais` | `locals` |
| `avaliar` | `eval` |
| `executar` | `exec` |
| `compilar` | `compile` |
| `ponto_de_parada` | `breakpoint` |

`pergunte(...)` e `pergunta(...)` também são traduzidos para `input(...)` (e `entrada` pelo dicionário).

```pyrt
a = decimal(pergunte("Primeiro número: "))
b = decimal(pergunte("Segundo número: "))
mostrar(a mais b)
```

```python
a = float(input("Primeiro número: "))
b = float(input("Segundo número: "))
print(a + b)
```

### 4.6 Tipos

| Pyrtugues | Python |
|---|---|
| `visão_de_memória` | `memoryview` |
| `objeto` | `object` |
| `inteiro` | `int` |
| `decimal` | `float` |
| `complexo` | `complex` |
| `booleano` | `bool` |
| `texto` | `str` |
| `bytes` | `bytes` |
| `bytearray` | `bytearray` |
| `lista` | `list` |
| `tupla` | `tuple` |
| `conjunto` | `set` |
| `conjunto_imutável` | `frozenset` |
| `dicionário` | `dict` |
| `propriedade` | `property` |
| `método_estático` | `staticmethod` |
| `método_de_classe` | `classmethod` |
| `super` | `super` |

Os tipos **não** são traduzidos quando aparecem como objeto antes de um ponto (por exemplo, uma variável chamada `lista` seguida de `.algo`). Isso protege variáveis que usam o nome de um tipo.

```pyrt
x = inteiro("5")
y = texto(5)
z = lista((1, 2))
mostrar(tipo(x))
```

```python
x = int("5")
y = str(5)
z = list((1, 2))
print(type(x))
```

### 4.7 Exceções

| Pyrtugues | Python |
|---|---|
| `exceção` | `Exception` |
| `exceção_base` | `BaseException` |
| `erro_aritmético` | `ArithmeticError` |
| `erro_de_busca` | `LookupError` |
| `erro_de_afirmação` | `AssertionError` |
| `erro_de_atributo` | `AttributeError` |
| `erro_de_fim_de_arquivo` | `EOFError` |
| `erro_de_ponto_flutuante` | `FloatingPointError` |
| `saída_de_gerador` | `GeneratorExit` |
| `erro_de_importação` | `ImportError` |
| `erro_de_índice` | `IndexError` |
| `erro_de_chave` | `KeyError` |
| `interrupção_do_teclado` | `KeyboardInterrupt` |
| `erro_de_memória` | `MemoryError` |
| `erro_de_nome` | `NameError` |
| `não_implementado_erro` | `NotImplementedError` |
| `erro_do_sistema_operacional` | `OSError` |
| `erro_de_transbordamento` | `OverflowError` |
| `erro_de_referência` | `ReferenceError` |
| `erro_de_execução` | `RuntimeError` |
| `fim_de_iteração_assíncrona` | `StopAsyncIteration` |
| `fim_de_iteração` | `StopIteration` |
| `erro_de_sintaxe` | `SyntaxError` |
| `erro_do_sistema` | `SystemError` |
| `saída_do_sistema` | `SystemExit` |
| `erro_de_tipo` | `TypeError` |
| `erro_de_local_não_ligado` | `UnboundLocalError` |
| `erro_de_unicode` | `UnicodeError` |
| `erro_de_decodificação_unicode` | `UnicodeDecodeError` |
| `erro_de_codificação_unicode` | `UnicodeEncodeError` |
| `erro_de_tradução_unicode` | `UnicodeTranslateError` |
| `erro_de_valor` | `ValueError` |
| `divisão_por_zero` | `ZeroDivisionError` |

```pyrt
tentar:
    x = 1 dividido por 0
exceto divisão_por_zero como erro:
    mostrar("Não dá para dividir por zero")
finalmente:
    mostrar("Fim")
```

```python
try:
    x = 1 / 0
except ZeroDivisionError as get_error:
    print("Não dá para dividir por zero")
finally:
    print("Fim")
```

### 4.8 Métodos

Os 75 métodos abaixo só são traduzidos **depois de um ponto e antes de um parêntese**, como em `texto.maiúsculas()`. Eles cobrem textos, listas, dicionários, widgets gráficos (Tkinter/CustomTkinter), o relógio do Pygame e superfícies/retângulos/vetores do Pygame.

| Pyrtugues (depois do ponto) | Python | Verificado (modo edu) |
|---|---|---|
| `maiúsculas` | `upper` | ✅ |
| `minúsculas` | `lower` | ✅ |
| `capitalizar` | `capitalize` | ✅ |
| `título` | `title` | ✅ |
| `trocar` | `replace` | ✅ |
| `dividir` | `split` | ✅ |
| `juntar` | `join` | ✅ |
| `tirar espaços` | `strip` | ✅ |
| `começa com` | `startswith` | ⚠️ gera `x.começa with()` |
| `termina com` | `endswith` | ⚠️ gera `x.termina with()` |
| `encontrar` | `find` | ✅ |
| `contar` | `count` | ✅ |
| `é dígito` | `isdigit` | ⚠️ gera `x.is dígito()` |
| `é letra` | `isalpha` | ⚠️ gera `x.is letra()` |
| `é espaço` | `isspace` | ⚠️ gera `x.is espaço()` |
| `adicionar` | `append` | ✅ |
| `estender` | `extend` | ✅ |
| `inserir` | `insert` | ✅ |
| `remover` | `remove` | ✅ |
| `tirar` | `pop` | ✅ |
| `limpar` | `clear` | ✅ |
| `copiar` | `copy` | ✅ |
| `índice` | `index` | ✅ |
| `ordenar em ordem` | `sort` | ⚠️ gera `x.sorted in ordem()` |
| `inverter ordem` | `reverse` | ⚠️ gera `x.reversed ordem()` |
| `chaves` | `keys` | ✅ |
| `valores` | `values` | ✅ |
| `itens` | `items` | ✅ |
| `pegar` | `get` | ✅ |
| `atualizar` | `update` | ✅ |
| `configurar` | `configure` | ✅ |
| `obter configuração` | `cget` | ✅ |
| `vincular` | `bind` | ✅ |
| `desvincular` | `unbind` | ✅ |
| `empacotar` | `pack` | ✅ |
| `configurar empacotamento` | `pack_configure` | ✅ |
| `esquecer empacotamento` | `pack_forget` | ✅ |
| `propagar empacotamento` | `pack_propagate` | ✅ |
| `grade` | `grid` | ✅ |
| `configurar grade` | `grid_configure` | ✅ |
| `esquecer grade` | `grid_forget` | ✅ |
| `remover grade` | `grid_remove` | ✅ |
| `propagar grade` | `grid_propagate` | ✅ |
| `posicionar` | `place` | ✅ |
| `configurar posição` | `place_configure` | ✅ |
| `esquecer posição` | `place_forget` | ✅ |
| `foco` | `focus` | ✅ |
| `definir foco` | `focus_set` | ✅ |
| `destruir` | `destroy` | ✅ |
| `obter` | `get` | ✅ |
| `definir` | `set` | ✅ |
| `ver` | `see` | ✅ |
| `marcar_fps` | `tick` | ✅ |
| `marcar_fps_bruto` | `tick_busy_loop` | ✅ |
| `fps_atual` | `get_fps` | ✅ |
| `tempo_quadro` | `get_time` | ✅ |
| `tempo_bruto` | `get_rawtime` | ✅ |
| `esperar_ms` | `delay` | ✅ |
| `esperar` | `wait` | ✅ |
| `preencher` | `fill` | ✅ |
| `colar` | `blit` | ✅ |
| `converter` | `convert` | ✅ |
| `converter_alpha` | `convert_alpha` | ✅ |
| `obter_retângulo` | `get_rect` | ✅ |
| `obter_tamanho` | `get_size` | ✅ |
| `largura` | `get_width` | ✅ |
| `altura` | `get_height` | ✅ |
| `mover` | `move` | ✅ |
| `mover_em` | `move_ip` | ✅ |
| `prender` | `clamp` | ✅ |
| `colidir_ponto` | `collidepoint` | ✅ |
| `colidir_retângulo` | `colliderect` | ✅ |
| `obter_centro` | `center` | ✅ |
| `obter_x` | `x` | ✅ |
| `obter_y` | `y` | ✅ |

```pyrt
frase = "olá mundo"
mostrar(frase.maiúsculas())
mostrar(frase.trocar("o", "0"))
mostrar(frase.dividir(" "))
```

```python
frase = "olá mundo"
print(frase.upper())
print(frase.replace("o", "0"))
print(frase.split(" "))
```

```pyrt
notas = [3, 1, 2]
notas.adicionar(4)
notas.remover(1)
notas.tirar()
```

```python
notas = [3, 1, 2]
notas.append(4)
notas.remove(1)
notas.pop()
```

```pyrt
aluno = {"nome": "Ana", "idade": 12}
mostrar(aluno.chaves())
mostrar(aluno.itens())
mostrar(aluno.pegar("nome"))
```

```python
aluno = {"nome": "Ana", "idade": 12}
print(aluno.keys())
print(aluno.items())
print(aluno.get("nome"))
```

Dos 75 métodos, 7 não funcionam como esperado no modo EDU (marcados com ⚠️ acima). Veja a [seção 13](#13-pontos-de-atenção-e-comportamentos-observados).

### 4.9 Módulos

Os nomes abaixo funcionam depois de `importar` / `de` e também como prefixo de um ponto (`matemática.sqrt(...)`).

| Pyrtugues | Módulo Python | Verificado |
|---|---|---|
| `matemática` | `math` | ✅ |
| `aleatório` | `random` | ✅ |
| `data e hora` | `datetime` | ⚠️ gera `import data and time` |
| `tempo` | `time` | ✅ |
| `sistema` | `os` | ✅ |
| `expressão regular` | `re` | ✅ |
| `jogo` | `pygame` | ✅ |
| `ctk` | `customtkinter` | ✅ |
| `numerico` | `numpy` | ✅ |
| `tabelas` | `pandas` | ✅ |
| `grafico` | `matplotlib.pyplot` | ✅ |
| `requisicoes` | `requests` | ✅ |
| `cliente_http` | `httpx` | ✅ |
| `servidor_web` | `flask` | ✅ |
| `api_web` | `fastapi` | ✅ |
| `banco_dados` | `sqlalchemy` | ✅ |
| `planilha` | `openpyxl` | ✅ |
| `imagens_pillow` | `PIL.Image` | ✅ |
| `visao_cv` | `cv2` | ✅ |
| `dados_rapidos` | `polars` | ✅ |
| `grafico_interativo` | `plotly.express` | ✅ |
| `cientifico` | `scipy` | ✅ |

```pyrt
importar matemática
importar aleatório
mostrar(matemática.sqrt(16))
```

```python
import math
import random
print(math.sqrt(16))
```

### 4.10 Bibliotecas com nomes em português (aliases)

O tradutor traz 111 aliases qualificados, aplicados **antes** das regras genéricas:

- **Pygame**, com o prefixo `jogo` (65 aliases);
- **CustomTkinter**, com o prefixo `ctk` (28 aliases);
- **Outras bibliotecas** populares: NumPy, Pandas, Matplotlib, Requests, HTTPX, Flask, FastAPI, SQLAlchemy, OpenPyXL, Pillow e OpenCV (18 aliases).

As tabelas completas estão no [Apêndice A](#apêndice-a--aliases-de-bibliotecas). Dois exemplos:

```pyrt
importar jogo
jogo.iniciar()
tela = jogo.display.criar_janela((800, 600))
relogio = jogo.tempo.relógio()
relogio.marcar_fps(60)
jogo.sair()
```

```python
import pygame
pygame.init()
tela = pygame.display.set_mode((800, 600))
relogio = pygame.time.Clock()
relogio.tick(60)
pygame.quit()
```

```pyrt
importar ctk
janela = ctk.janela()
botao = ctk.botao(janela, text="Clique")
botao.empacotar()
```

```python
import customtkinter
janela = customtkinter.CTk()
botao = customtkinter.CTkButton(janela, text="Clique")
botao.pack()
```

### 4.11 Biblioteca padrão pelo dicionário

Além dos módulos da tabela da seção 4.9, os dicionários traduzem **nomes específicos da biblioteca padrão** do Python seguindo uma convenção de nomes achatada com sublinhado:

```
<nome do módulo em português>_<nome em português do item>  →  módulo.Item
```

Exemplos reais do dicionário EDU:

| Pyrtugues | Python |
|---|---|
| `argumentos_de_terminal` | `argparse` |
| `argumentos_de_terminal_argumento_analisador` | `argparse.ArgumentParser` |
| `árvore_sintática_nome` | `ast.Name` |
| `codificação_base64_b_64_codificar` | `base64.b64encode` |

O [Apêndice B](#apêndice-b--módulos-da-biblioteca-padrão-cobertos) lista os 78 módulos da biblioteca padrão que têm nome em português no dicionário EDU.

### 4.12 f-strings

Dentro de `f"..."`, **somente o que está entre chaves** é traduzido; o texto fora das chaves permanece intacto. Chaves literais escritas em dobro (como em qualquer f-string do Python) e strings aninhadas dentro das expressões são preservadas.

```pyrt
x = 4
mostrar(f"Dobro: {x vezes 2} | maior? {x maior que 3}")
```

```python
x = 4
print(f"Dobro: {x * 2} | maior? {x > 3}")
```

### 4.13 Comentários e strings

```pyrt
x = "se maior que"  # se maior que e ou
mostrar("e ou mais")
```

```python
x = "se maior que"  # se maior que e ou
print("e ou mais")
```

### 4.14 Variáveis e funções com nome igual a uma palavra do dicionário

Antes de traduzir, o tradutor procura **atribuições simples** (`nome = ...`) e **definições de função** (`função nome(...)`) cujo nome também seja uma chave do dicionário. Esses nomes são protegidos e **não são traduzidos em nenhum lugar do programa**. Assim você pode chamar uma variável de `tipo` ou uma função de `somar` sem que elas virem `type` e `sum`.

```pyrt
tipo = "A"
mostrar(tipo)

função somar(a, b):
    retornar a mais b

mostrar(somar(1, 2))
```

```python
tipo = "A"
print(tipo)

def somar(a, b):
    return a + b

print(somar(1, 2))
```

A proteção cobre apenas atribuições no começo da linha e nomes de função. Parâmetros, variáveis de laço e desempacotamentos não entram nessa lista (veja a [seção 13](#13-pontos-de-atenção-e-comportamentos-observados)).

### 4.15 Estruturas avançadas

Assíncrono, `match`/`case` e decoradores também têm tradução:

```pyrt
assíncrono função buscar():
    aguardar outra()
```

```python
async def buscar():
    await outra()
```

```pyrt
correspondência cor:
    caso "verde":
        mostrar("siga")
    caso _:
        mostrar("pare")
```

```python
match Color:
    case "verde":
        print("siga")
    case _:
        print("pare")
```

```pyrt
@propriedade
função area(self):
    retornar self.l vezes self.l
```

```python
@property
def area(self):
    return self.l * self.l
```

Classes e arquivos:

```pyrt
classe Pessoa:
    função __init__(self, nome):
        self.nome = nome

    função falar(self):
        mostrar(f"Oi, sou {self.nome}")

p = Pessoa("Ana")
p.falar()
```

```python
class Pessoa:
    def __init__(self, nome):
        self.nome = nome

    def falar(self):
        print(f"Oi, sou {self.nome}")

p = Pessoa("Ana")
p.falar()
```

```pyrt
com abrir("notas.txt", "r", encoding="utf-8") como arquivo:
    conteudo = arquivo.read()
```

```python
with open("notas.txt", "r", encoding="utf-8") as arquivo:
    conteudo = arquivo.read()
```

---

## 5. Os dicionários

### 5.1 Formato do arquivo

Os dois dicionários são arquivos JSON com uma única chave de topo, `portugues`, que contém pares **palavra em português → destino em Python**:

```json
{
  "portugues": {
    "se": "if",
    "senão": "else",
    "mostrar": "print",
    "intervalo": "range"
  }
}
```

Chaves que começam com `_secao_` não são palavras: são **comentários de seção** e são descartadas ao carregar. Cada dicionário tem três:

| Chave | Texto (EDU) |
|---|---|
| `_secao_jogos` | Aliases naturais para Pygame: jogos, eventos, display, desenho, entrada, teclado, mouse, sprites e áudio. |
| `_secao_ctk` | Aliases naturais para CustomTkinter: ctk.janela(), ctk.botao(), ctk.entrada(), ctk.quadro() e demais widgets. |
| `_secao_outras_bibliotecas` | Aliases de módulos populares: NumPy, Pandas, Matplotlib, Requests, HTTPX, Flask, FastAPI, SQLAlchemy, OpenPyXL, Pillow, OpenCV e Polars. |

No COMPLETO, o texto da seção de outras bibliotecas também menciona Plotly e SciPy.

### 5.2 Como o arquivo é organizado

1. **Núcleo da linguagem:** palavras de controle, constantes, funções embutidas, tipos e exceções (130 entradas no EDU e 248 no COMPLETO).
2. **Biblioteca padrão:** centenas de módulos, módulo por módulo, usando a convenção de nomes da [seção 4.11](#411-biblioteca-padrão-pelo-dicionário).
3. **Bibliotecas de terceiros:** as três chaves de seção aparecem juntas e são seguidas pelas entradas de Pygame (`jogo_*`), CustomTkinter (`ctk_*`) e das demais bibliotecas.

### 5.3 O filtro aplicado ao carregar

Ao ativar um modo, o tradutor remove do dicionário:

- as chaves `_secao_*`;
- qualquer chave que **já seja uma palavra nativa do Python** (palavras reservadas, nomes de `builtins`, `True`, `False`, `None`).

O motivo está documentado no código: o dicionário COMPLETO contém entradas do tipo `"if" → "If"` ou `"int" → "INT"`, e, como o tradutor vai de português para Python, essas entradas não podem ser reaplicadas depois que uma palavra já foi convertida. O resultado é o número de **entradas ativas**: 2671 no EDU e 9358 no COMPLETO.

### 5.4 Diferenças entre EDU e COMPLETO

Todas as chaves do EDU existem no COMPLETO. As únicas chaves com valor diferente são:

| Chave | EDU | COMPLETO |
|---|---|---|
| `eventos` | `event` | `events` |
| `imagem` | `image` | `Image` |
| `versão_python` | `get_py_version` | `version` |
| `erro` | `get_error` | `ERR` |
| `vetor` | `Vector2` | `ndarray` |
| `cor` | `Color` | `color` |
| `grupo` | `Group` | `group` |

O COMPLETO tem ainda 118 entradas de núcleo que o EDU não tem (por exemplo, `getattr`, métodos especiais como `__init__`, mais classes de exceção e de aviso). A lista está no [Apêndice C](#apêndice-c--entradas-de-núcleo-exclusivas-do-completo).

### 5.5 Onde o tradutor procura os dicionários

Ordem de prioridade (a primeira pasta que tiver o arquivo vence):

1. a pasta passada em `--dicionarios` (na extensão: configuração `pyrtugues.pastaDicionarios`);
2. a pasta indicada pela variável de ambiente `PYRTUGUES_DICIONARIOS`;
3. a pasta onde está `pyrtugues_core.py` (na extensão, a pasta `python/`).

Nomes aceitos: no EDU, `dicionario.json`; no COMPLETO, `dicionario_completo.json` **ou** `dicionario_completo_json` (o nome sem ponto usado no aplicativo original). O JSON é lido com `utf-8-sig`, então arquivos com BOM funcionam.

### 5.6 Como adicionar ou alterar palavras

1. Edite o JSON e acrescente `"palavra": "destino"` dentro de `portugues`.
2. Palavras são casadas como **palavra inteira**, sem diferenciar maiúsculas de minúsculas, e as chaves **maiores são aplicadas primeiro** (`senão_se` antes de `senão`).
3. Se o destino tiver ponto (`argparse.ArgumentParser`), ele é protegido contra nova tradução por chaves menores.
4. Evite palavras comuns que também servem de nome de variável (como `nome` ou `valor`), porque a tradução é feita sem entender o contexto; o próprio gerador de gramática deixa essas palavras sem destaque de propósito.
5. Depois de mudar os dicionários, regenere o destaque de sintaxe da extensão: `python tools/gerar_gramatica.py`.
6. Teste algumas traduções com a [linha de comando](#7-linha-de-comando-pyrtugues_clipy) nos dois modos antes de publicar.

---

## 6. O tradutor por dentro

### 6.1 Pipeline da função `traduzir(codigo_br)`

| Passo | O que acontece |
|---|---|
| 1 | **Proteção de nomes.** Procura atribuições simples e definições de função cujo nome esteja no dicionário e troca cada ocorrência por um token `__PYRT_VAR_n__` |
| 2 | **f-strings.** Traduz apenas as expressões entre chaves (pula strings sem `{`, por desempenho) |
| 3 | **Strings e comentários.** Um scanner caractere a caractere troca strings (simples, triplas, com prefixos `r`, `u`, `b`, `f`) e comentários por tokens `__PYRT_STR_n__`; funciona mesmo com código incompleto, útil durante a digitação |
| 4 | **Traduções base** (`_aplicar_traducoes_base`, detalhada abaixo) |
| 5 | `pergunte(` e `pergunta(` viram `input(` (se não vierem depois de um ponto) |
| 6 | Restaura as strings e os comentários originais |
| 7 | Restaura os nomes protegidos |

### 6.2 Etapas de `_aplicar_traducoes_base`

1. **Aliases de bibliotecas**, do mais longo para o mais curto, com proteção da saída (`__PYRT_OUT_n__`) para que `jogo.desenho.retângulo` → `pygame.draw.rect` não seja retraduzido.
2. **Expressões compostas** (`maior ou igual a`, `dividido por`, `senão se`…), sem diferenciar caixa.
3. **Palavras soltas do dicionário**, das chaves maiores para as menores. Ficam de fora dessa etapa os métodos (só traduzidos depois de ponto) e os módulos (regras próprias). Tipos usam uma regra que evita traduzir quando seguidos de ponto.
4. **Traduções contextuais:** `for X em Y` → `for X in Y`; módulos em `import`/`from` e como prefixo de ponto; métodos depois de ponto e antes de parêntese; operadores `e`, `ou`, `mais`, `menos`, `vezes` e `resto` quando estão entre operandos.
5. **Restauração** das saídas qualificadas protegidas.

### 6.3 Usando o tradutor como biblioteca Python

```python
import sys
sys.path.insert(0, "python")          # pasta com pyrtugues_core.py e os dicionários
import pyrtugues_core as core

core.definir_modo("edu")              # retorna quantas palavras ficaram ativas
print(core.traduzir('mostrar("oi")')) # print("oi")
```

| Item | Descrição |
|---|---|
| `definir_modo(modo="edu", pasta_extra=None)` | Ativa o dicionário do modo (`"edu"` ou `"completo"`). Retorna a quantidade de palavras carregadas; **0 significa dicionário ausente ou vazio**. Modo inválido levanta `ValueError` |
| `traduzir(codigo_br)` | Recebe texto Pyrtugues e devolve texto Python |
| `pastas_de_busca(pasta_extra=None)` | Lista as pastas onde os dicionários são procurados, em ordem |
| `MODOS` | Tupla com os modos aceitos: `("edu", "completo")` |
| `BASE_DIR` | Pasta do módulo (usada como última opção de busca) |
| `DICIONARIO` / `DICIONARIOS` | Dicionário ativo e dicionários já carregados por modo |

---

## 7. Linha de comando (`pyrtugues_cli.py`)

Programa em `python/pyrtugues_cli.py`, usado pela extensão e útil também no terminal e em scripts.

### 7.1 Uso

```
python pyrtugues_cli.py traduzir <arquivo|-> [--modo edu|completo] [--dicionarios PASTA]
python pyrtugues_cli.py executar <arquivo>   [--modo edu|completo] [--dicionarios PASTA]
```

| Argumento | Descrição |
|---|---|
| `traduzir` | Imprime na saída padrão o Python gerado. Use `-` no lugar do arquivo para ler da entrada padrão |
| `executar` | Traduz e executa o arquivo `.pyrt` |
| `--modo` | `edu` (padrão) ou `completo` |
| `--dicionarios` | Pasta com os dicionários (veja a [seção 5.5](#55-onde-o-tradutor-procura-os-dicionários)) |

Os arquivos são lidos em UTF-8 (com ou sem BOM). Quando a saída ou a entrada não é um terminal (por exemplo, um *pipe*), o programa força UTF-8 para não quebrar os acentos.

### 7.2 Códigos de saída

| Código | Significado |
|---|---|
| `0` | Tudo certo |
| `1` | O programa do usuário terminou com erro |
| `2` | Uso incorreto ou arquivo não encontrado |
| `3` | Dicionário ausente ou vazio |
| `4` | Falha ao traduzir o código |
| `130` | Execução interrompida pelo usuário (Ctrl+C) |

### 7.3 Como `executar` funciona

1. Carrega o dicionário do modo e lê o arquivo.
2. Traduz o código para Python.
3. Remove a pasta da extensão do `sys.path` e coloca no lugar a **pasta do programa do usuário**, para que `import` de arquivos vizinhos funcione. `sys.argv` fica `[caminho_do_arquivo]`.
4. Compila o código traduzido com o nome de arquivo virtual `<pyrtugues>` e o executa com `__name__ == "__main__"` e `__file__` apontando para o arquivo original.
5. Ao final, imprime uma linha de 50 sinais de `=` e, se tudo deu certo, `✅ Código finalizado.`

Como a tradução preserva as linhas, os erros são mostrados com **a linha do código em português**. Exemplo real, para um arquivo cuja 3ª linha é `mostrar(x dividido por 0)`:

```
❌ Erro na linha 3:
   mostrar(x dividido por 0)

   Detalhes: ZeroDivisionError: division by zero
```

Mensagens de erro vão para a saída de erro (`stderr`); `SystemExit` com número vira o código de saída do processo.

---

## 8. Extensão para VS Code

**Pyrtugues — Python em português** (`pyrtugues.pyrtugues`, versão 1.5.0). Requer VS Code **1.80** ou superior e Python 3.8+. Categorias: *Programming Languages*, *Snippets* e *Education*.

### 8.1 Recursos

- Destaque de sintaxe para `.pyrt` (palavras de controle, operadores por extenso, f-strings, módulos, métodos, números, decoradores).
- **Executar arquivo** no terminal integrado, com `pergunte()` funcionando no próprio terminal.
- **Ver Python gerado** ao lado do código, com **atualização ao vivo** enquanto você digita.
- **Exportar como arquivo `.py`**.
- **Modo `edu` / `completo`**, alternável pela barra de status ou pelas configurações.
- **Snippets** em português.
- Erros que mostram a **linha do código em português**.
- Tema de ícones próprio para arquivos `.pyrt` e demo de jogo incluída.

### 8.2 Comandos

| Comando (ID) | Título na paleta | Onde aparece |
|---|---|---|
| `pyrtugues.executar` | Pyrtugues: Executar arquivo | Botão ▶ no topo do editor, menu de contexto, paleta e **Ctrl+F5** (somente em arquivos Pyrtugues) |
| `pyrtugues.pararExecucao` | Pyrtugues: Parar execução | Paleta |
| `pyrtugues.verPython` | Pyrtugues: Ver Python gerado | Botão no topo do editor, menu de contexto e paleta (somente em arquivos Pyrtugues) |
| `pyrtugues.exportarPython` | Pyrtugues: Exportar como arquivo .py | Paleta (somente em arquivos Pyrtugues) |
| `pyrtugues.alternarModo` | Pyrtugues: Alternar modo (edu / completo) | Paleta e clique no item da barra de status |
| `pyrtugues.abrirDemoBoss` | Pyrtugues: Abrir demo: Desafio do Chefão | Paleta |

O único atalho de teclado definido é **Ctrl+F5** para `pyrtugues.executar`, ativo quando o foco está no editor e a linguagem é Pyrtugues (no macOS também é `ctrl+f5`).

### 8.3 Configurações

| Configuração | Tipo / valores | Padrão | O que faz |
|---|---|---|---|
| `pyrtugues.modo` | `edu` \| `completo` | `edu` | Dicionário usado na tradução |
| `pyrtugues.caminhoPython` | texto | vazio | Executável do Python (3.8+). Vazio = detecção automática |
| `pyrtugues.pastaDicionarios` | texto | vazio | Pasta com `dicionario.json` e `dicionario_completo.json`. Vazio = usa a pasta `python/` da extensão |

### 8.4 Detecção do Python

Se `pyrtugues.caminhoPython` estiver vazio, a extensão testa, nesta ordem:

| Sistema | Candidatos |
|---|---|
| Windows | `py -3`, `python`, `python3` |
| Linux e macOS | `python3`, `python` |

Cada candidato é testado executando um pequeno comando (limite de 8 segundos) e só é aceito se for **Python 3.8 ou superior**. O resultado fica em cache até a configuração mudar. Sem Python válido, aparece um erro com o botão **Abrir configuração**.

### 8.5 Executar

- Arquivos **salvos** são gravados antes da execução; arquivos **não salvos** (ou sem sistema de arquivos) são gravados como `programa.pyrt` em uma pasta temporária `pyrtugues-*`, apagada quando a extensão é desativada.
- A pasta de trabalho é a do arquivo; para arquivos não salvos, a primeira pasta aberta no workspace.
- A execução é uma *Task* do VS Code (tipo `shell`, origem "Pyrtugues") com o comando `python -u pyrtugues_cli.py executar <arquivo> --modo <modo> [--dicionarios <pasta>]`, mostrando o terminal com foco, limpando o conteúdo anterior e usando o painel compartilhado.
- Uma nova execução **encerra a anterior** antes de começar (espera até 3 segundos).
- **Parar execução** termina a tarefa atual; sem execução em andamento, mostra um aviso informativo.

### 8.6 Ver Python gerado (preview ao vivo)

- O comando abre um documento virtual `NOME (Python).py` (esquema `pyrtugues-python`) **ao lado** do código, sem roubar o foco.
- Enquanto você digita, o preview é atualizado com um atraso de **400 ms**. Nessas atualizações automáticas os erros **não são exibidos**, porque o usuário ainda pode estar no meio de uma frase.
- Trocar o modo ou qualquer configuração `pyrtugues.*` atualiza todos os previews abertos.
- Fechar o documento de preview remove o vínculo.
- A tradução tem limite de 15 segundos por chamada.

### 8.7 Exportar `.py`

Abre uma janela de salvar com o nome sugerido igual ao do arquivo de origem trocando a extensão por `.py` (ou `programa.py` na pasta pessoal, para arquivos não salvos), grava o Python traduzido em UTF-8 com uma única quebra de linha ao final e confirma com uma mensagem.

### 8.8 Barra de status

Item no canto inferior direito com o texto `Pyrtugues: edu` ou `Pyrtugues: completo`. Ele só aparece quando o editor ativo é um arquivo Pyrtugues. Clicar alterna o modo e grava a escolha nas configurações **globais** do usuário.

### 8.9 Snippets

| Prefixo(s) | Descrição | Corpo (⏎ = nova linha, → = indentação) |
|---|---|---|
| `se` | Condicional se | `se ${1:condição}:⏎→$0` |
| `senão`, `senao` | Bloco senão | `senão:⏎→$0` |
| `senãose`, `senaose` | Bloco senão se | `senão se ${1:condição}:⏎→$0` |
| `para` | Laço para ... em | `para ${1:item} em ${2:itens}:⏎→$0` |
| `paraintervalo`, `parai` | Laço para com intervalo() | `para ${1:i} em intervalo(${2:0}, ${3:10}):⏎→$0` |
| `enquanto` | Laço enquanto | `enquanto ${1:condição}:⏎→$0` |
| `função`, `funcao` | Definir função | `função ${1:nome}(${2:parâmetros}):⏎→$0` |
| `classe` | Definir classe | `classe ${1:Nome}:⏎→função __init__(self${2:, parâmetros}):⏎→→$0` |
| `tentar` | Tratamento de erros | `tentar:⏎→$1⏎exceto ${2:Exception}:⏎→$0` |
| `comabrir`, `arquivo` | Abrir arquivo com com/como | `com abrir("${1:arquivo.txt}", "${2:r}", encoding="utf-8") como ${3:arquivo}:⏎→$0` |
| `mostrar` | Mostrar na tela | `mostrar($1)` |
| `pergunte` | Ler valor digitado | `${1:resposta} = pergunte("${2:Digite um valor: }")` |

### 8.10 Destaque de sintaxe

A gramática TextMate (`source.pyrtugues`) é **gerada** por `tools/gerar_gramatica.py`. O gerador lê os dois dicionários e destaca somente as palavras que viram palavra-chave, constante, função embutida ou exceção do Python; palavras comuns como `nome` ou `valor` ficam sem destaque de propósito, porque também servem de nome de variável. As regras são aplicadas sem diferenciar maiúsculas de minúsculas.

| Regra | Escopo | O que destaca |
|---|---|---|
| `comentario` | `comment.line.number-sign` | Comentários com `#` |
| `strings` | `string.quoted.*` | Strings simples e triplas, com prefixos `r`, `u`, `b`, `f` |
| `interior-fstring` | `meta.embedded.expression` | Expressões entre chaves em f-strings (destacadas recursivamente) |
| `escape` | `constant.character.escape` | Sequências de escape (`\n`, `\x41`, `\u00e9`…) |
| `decorador` | `entity.name.function.decorator` | `@nome` no início da linha |
| `definicoes` | `storage.type.function`, `entity.name.function`, `storage.type.class`, `entity.name.type.class` | `função nome` (ou `funcao`) e `classe Nome` |
| `constantes` | `constant.language`, `variable.language.self` | `verdadeiro`, `falso`, `nulo`, `self` e `cls` |
| `excecoes` | `support.class.exception` | Nomes de exceções em português e em Python |
| `operadores-palavra` | `keyword.operator.word` | `maior que`, `dividido por`, `mais`, `e`, `ou`… |
| `palavras-chave` | `keyword.control` | `se`, `senão`, `para`, `enquanto`, `retornar`… |
| `modulos` | `support.module` | Módulos depois de `importar`/`de` e como prefixo de ponto |
| `metodos` | `support.function.method` | Métodos traduzidos depois de ponto |
| `tipos-e-funcoes` | `support.type`, `support.function.builtin` | Tipos e funções embutidas seguidos de `(` |
| `numeros` | `constant.numeric` | Números |
| `operadores` | `keyword.operator` | Operadores simbólicos |

Todos os escopos terminam com o sufixo `.pyrtugues`.

### 8.11 Configuração da linguagem

- **Comentários:** linha com `#`; bloco com `"""`.
- **Pares automáticos:** `{}`, `[]`, `()`, `""` e `''` (aspas não fecham automaticamente dentro de strings e comentários).
- **Indentação ao pressionar Enter:** aumenta depois de uma linha que termina em `:`; diminui depois de linhas que começam com `passar`, `quebrar`, `continuar`, `retornar` ou `levantar`.
- **Dobra de código** baseada em indentação (`offSide`).

### 8.12 Ícones

O tema **Pyrtugues Icons** associa `.pyrt` ao ícone `icons/pyrtugues.svg`. O ícone da extensão é `icon.png`.

### 8.13 Desenvolvimento, empacotamento e publicação

- **Testar:** abra a pasta da extensão no VS Code e aperte **F5**. A configuração `Testar extensão` abre uma nova janela com a extensão carregada.
- **Gerar o instalador:** `npx @vscode/vsce package` gera o `.vsix`. Para instalar: *Extensões → ⋯ → Instalar do VSIX…*.
- **Antes de empacotar:** confira `publisher` no `package.json` e coloque o arquivo `LICENSE` do projeto na raiz (o `package.json` aponta para ele com `SEE LICENSE IN LICENSE`).
- **Arquivos fora do pacote** (`.vscodeignore`): `.vscode/**`, `**/__pycache__/**`, `*.pyc`, `*.zip` e `*.vsix`.
- **Nova versão:** aumente `version` no `package.json`, empacote e publique com a ferramenta `vsce`.
- **Se mudar os dicionários:** rode `python tools/gerar_gramatica.py` para o destaque acompanhar as palavras novas.

### 8.14 Observações de uso

- Bibliotecas externas (`pygame`, `customtkinter`, `numpy`…) precisam estar instaladas no **mesmo Python** usado pela extensão.
- Para usar a extensão em arquivo com outra extensão, mude o modo de linguagem do editor para **Pyrtugues**.
- Para usar dicionários próprios, aponte `pyrtugues.pastaDicionarios`; se o arquivo não estiver lá, a extensão usa o que veio embutido.

---

## 9. Aplicativo desktop (`curso.py`)

Aplicativo em **CustomTkinter** (classe `JanelaBR`, 61 métodos) que reúne editor, terminal, biblioteca de exemplos, curso e página *Sobre* em uma única janela. Ele também contém o tradutor original (funções `traduzir` e auxiliares) e todos os dados do curso.

### 9.1 Janela e identidade visual

- Título: **Pyrtugues — Python em português**; tamanho inicial 1240×860, mínimo 980×720; tema escuro.
- Barra superior com a marca "P", o nome, o subtítulo *Programação em português*, a navegação (**Editor**, **Exemplos**, **Curso**, **Sobre**), o rótulo `PYRTUGUES • v1.4.0` e um indicador de status (`● Pronto`, `Executando`, `Erro`, `Interrompido`…).
- As páginas são alternadas dentro da mesma janela; nenhuma abre janela nova (exceto a caixa de entrada de dados e o `ver_python`, descritos adiante).

Paleta usada pelo aplicativo:

| Variável | Cor |
|---|---|
| `c_bg` | `#070B12` |
| `c_panel` | `#0E1624` |
| `c_card` | `#101A2A` |
| `c_editor` | `#0B1320` |
| `c_border` | `#22324A` |
| `c_text` | `#F8FAFC` |
| `c_muted` | `#94A3B8` |
| `c_dim` | `#5F718A` |
| `c_green` | `#10B981` |
| `c_green_hover` | `#059669` |
| `c_green_soft` | `#6EE7B7` |
| `c_red` | `#7F1D1D` |

### 9.2 Páginas

| Página | O que faz |
|---|---|
| **Seleção inicial** | Aparece ao abrir. Mostra cartões **EDU** e **COMPLETO** (com a quantidade de aulas de cada um) e o botão *Começar com …*. A mensagem na tela lembra que dá para trocar de modo depois, na página *Curso* |
| **Editor** | Código em português à esquerda, Python traduzido à direita e terminal embaixo |
| **Exemplos** | Biblioteca com 6 exemplos em cartões, cada um com o botão *Carregar no editor* |
| **Curso** | Aulas organizadas por módulo, com busca e acompanhamento de conclusão |
| **Sobre** | Texto sobre o projeto, o criador, a proposta e um passo a passo de uso em 4 etapas (Escreva, Execute, Veja, Experimente) |

Os 6 exemplos da biblioteca: **Olá, mundo**, **Variáveis**, **Condição**, **Repetição**, **Função** e **Calculadora**.

### 9.3 O editor

**Rótulos e botões**

| Elemento | Função |
|---|---|
| *Seu Código (.pyrt)* / *Português Nativo* | Área de edição |
| *Tradução em Tempo Real* / *Python* | Painel somente leitura com o Python gerado |
| **Copiar** | Copia o Python gerado para a área de transferência |
| **Baixar .py** | Salva o Python gerado em arquivo (nome sugerido `programa.py`) |
| **▶ Executar código** | Executa o programa (também com **Ctrl+Enter**) |
| **🔄 Traduzir** | Força a atualização do painel Python |
| **⏹ Parar** | Interrompe a execução |
| **💡 Exemplos** / **📚 Curso** | Atalhos para as respectivas páginas |
| **🗑 Limpar saída** | Apaga o conteúdo do terminal |
| *Saída do Terminal* / *Execução Interativa* | Área onde aparece a saída do programa |

**Tradução em tempo real:** a cada tecla solta, o painel Python é atualizado após uma pausa de 50 ms. Se o código estiver incompleto e a tradução falhar, o painel **mantém a última tradução válida** em vez de interromper a digitação.

**Recursos do editor**

| Tecla / situação | Comportamento |
|---|---|
| **Tab** | Insere 4 espaços; com seleção, indenta todas as linhas selecionadas |
| **Shift+Tab** | Remove até 4 espaços do início da linha |
| **Enter** | Mantém a indentação da linha atual; depois de `:` adiciona 4 espaços; entre `()`, `[]` ou `{}` abre uma linha interna e deixa o fechamento na linha de baixo |
| **Abrir `(`, `[`, `{`, `"`, `'`** | Fecha automaticamente; com texto selecionado, envolve a seleção |
| **Digitar o fechamento** | Se o caractere de fechamento já está à frente, apenas avança o cursor |
| **Backspace** entre um par vazio | Apaga abertura e fechamento de uma vez |
| Margem esquerda | Numeração de linhas sincronizada com a rolagem |
| Linha do cursor | Destacada suavemente |

### 9.4 Execução e entrada interativa

O aplicativo **não executa o código dentro dele mesmo**: usa um Python instalado no sistema.

1. O código é traduzido.
2. O aplicativo procura um Python externo: no Windows testa `py -3`, depois `python` e `python3`; nos demais sistemas, `python` e `python3`. Cada candidato é testado com um comando de até 5 segundos. O Python escolhido é mostrado no status (`Executando: <caminho>`).
3. Cria um **script temporário** (`pyrtugues_exec_*.py`) que redefine `input()` e executa o código traduzido compilado como `<pyrtugues>`, para que os erros apontem para a linha em português.
4. Inicia o processo com saída padrão e erro combinados, lendo a saída linha a linha e exibindo no terminal do aplicativo.
5. Quando o programa chama `input()`, o script imprime uma linha especial (um token único seguido do texto do prompt em JSON). O aplicativo reconhece essa linha, abre a janela **Pyrtugues — Entrada de dados** (modal, 460×235) e devolve a resposta ao processo pela entrada padrão. Cancelar a janela devolve texto vazio.
6. Ao final, mostra `✅ Código finalizado.` ou, em caso de erro, `❌ O Python externo encerrou com código N` com a dica de instalar a biblioteca no mesmo Python mostrado no status quando aparecer `ModuleNotFoundError`.
7. **Parar** encerra o processo, cancela pedidos de entrada pendentes e fecha a janela de entrada aberta. O script temporário é apagado no final.

Sem Python instalado, o aplicativo avisa para instalar o Python e adicioná-lo ao PATH, e para instalar as bibliotecas desejadas com `pip`.

### 9.5 Estado da aplicação

| Atributo | Para que serve |
|---|---|
| `modo_aplicativo` / `modo_curso` | Modo ativo (`edu` ou `completo`); trocar o modo atualiza dicionário, curso e preview |
| `aulas_concluidas` | Conjuntos de aulas concluídas, um por modo; **fica só na memória** e é perdido ao fechar o aplicativo |
| `executando`, `parar_evento` | Controle de execução e de parada |
| `_input_requests`, `_input_atual`, `_input_janela` | Fila e janela de pedidos de entrada |
| `_processo_execucao` | Processo do Python externo em andamento |
| `_timer_traducao` | Temporizador da tradução em tempo real |

### 9.6 Código legado

O arquivo tem uma seção "Backend original" com `ver_python()` (janela *Pyrtugues → Python* com *Copiar Python* e *Fechar*), `_trace_execucao`, `print_gui`, `write` e `flush`, do tempo em que o programa rodava dentro do próprio aplicativo. Nenhum desses métodos é chamado hoje em outro ponto do arquivo, então podem ser removidos ou reaproveitados sem afetar o fluxo atual (o botão **Traduzir** usa `_atualizar_preview_python`).

---

## 10. O curso integrado

O curso fica na página **Curso** do aplicativo e ensina Python usando o Pyrtugues como ponte. Há dois conjuntos de aulas, um por modo:

| Modo | Aulas | Módulos | Observação |
|---|---|---|---|
| EDU | 61 | 15 | Fundamentos até projetos |
| COMPLETO | 125 | 31 | As 61 aulas EDU mais 64 aulas de nível COMPLETO |

### 10.1 Como o curso funciona

- Botões **EDU** e **COMPLETO** alternam o conjunto de aulas (e o dicionário do aplicativo).
- A lista lateral tem **busca** (campo *Pesquisar aula, módulo…*), que procura no módulo, no título e na descrição sem diferenciar maiúsculas de minúsculas, e marca as aulas concluídas.
- Cada aula mostra: módulo e número (`Aula N de total`), título, descrição, **📖 Conteúdo**, **🟢 Exemplo em Pyrtugues**, **🐍 Equivalente em Python**, **🧠 Explicação**, **✏️ Exercício**, **🚀 Desafio** e uma **💡 Dica**.
- Botões: **← Anterior**, **✓ Marcar como concluída** (vira **✓ Desmarcar concluída** depois de marcada), **📝 Abrir no Editor** (carrega o exemplo da aula no editor), **Próxima →** (na última aula vira **Curso concluído →**) e **↑ Voltar à lista de aulas**.
- Contador de progresso do tipo `N/total concluídas` por modo.

### 10.2 Estrutura de uma aula

Cada aula é um dicionário Python dentro de `DADOS_CURSO[modo]` com estes campos:

| Campo | Conteúdo |
|---|---|
| `modulo` | Nome do módulo (ex.: `Módulo 1 — Fundamentos`) |
| `titulo` | Título da aula |
| `descricao` | Resumo de uma frase |
| `conteudo` | Texto completo (objetivo, explicação, exercício guiado e desafio) |
| `pyrtugues` | Exemplo de código em Pyrtugues |
| `python` | Equivalente em Python |
| `explicacao` | Explicação do conceito |
| `exercicio` | Exercício proposto |
| `desafio` | Desafio extra |
| `dica` | Dica curta |
| `ordem` | Número da aula, de 1 até o total do modo |
| `nivel` | `EDU` ou `COMPLETO` |

### 10.3 Conteúdo do modo EDU

| Módulo | Aulas | Nível | Títulos das aulas |
|---|---|---|---|
| Módulo 1 — Fundamentos | 1–4 | EDU | O que é programação; Seu primeiro programa; Comentários; Indentação e blocos |
| Módulo 2 — Variáveis e tipos | 5–8 | EDU | Variáveis; Nomes e atribuição; Inteiros e decimais; Textos, booleanos e None |
| Módulo 3 — Entrada e saída | 9–12 | EDU | Mostrar resultados com mostrar(); Entrada com pergunte(); Conversão de entrada; F-strings |
| Módulo 4 — Operadores | 13–16 | EDU | Operações matemáticas; Comparações; Operadores lógicos; Atribuição composta e precedência |
| Módulo 5 — Condições | 17–20 | EDU | if com se; Múltiplos caminhos com senão_se; Alternativa com senão; Condições aninhadas |
| Módulo 6 — Repetição | 21–24 | EDU | for e intervalos; while com enquanto; quebrar, continuar e passar; Contadores e acumuladores |
| Módulo 7 — Textos | 25–28 | EDU | Índices de strings; Fatiamento de textos; Métodos de texto; Buscar, substituir, dividir e juntar |
| Módulo 8 — Listas | 29–32 | EDU | Criando e acessando listas; Alterando elementos; append e extend; insert, remove, pop, sort e reverse |
| Módulo 9 — Tuplas | 33–36 | EDU | Criando tuplas; Desempacotamento; Percorrendo tuplas; Lista ou tupla? |
| Módulo 10 — Conjuntos | 37–40 | EDU | Criando conjuntos; Adicionar e remover elementos; União e interseção; Diferença e pertencimento |
| Módulo 11 — Dicionários | 41–45 | EDU | Criando dicionários; Ler e alterar valores; keys, values, items; get e update; Percorrendo dicionários |
| Módulo 12 — Funções | 46–49 | EDU | Criando funções; Parâmetros e argumentos; Retorno; Escopo e reutilização |
| Módulo 13 — Erros e exceções | 50–53 | EDU | Erros de sintaxe, execução e lógica; try e except; else e finalmente; levantar e afirmar |
| Módulo 14 — Módulos e biblioteca padrão | 54–57 | EDU | importar; de e como; random, datetime e time; os e expressões regulares |
| Módulo 15 — Projetos EDU | 58–61 | EDU | Projeto: calculadora; Projeto: conversor; Projeto: quiz; Projeto: lista de tarefas |

### 10.4 Conteúdo do modo COMPLETO

| Módulo | Aulas | Nível | Títulos das aulas |
|---|---|---|---|
| Módulo 1 — Fundamentos | 1–4 | EDU | O que é programação; Seu primeiro programa; Comentários; Indentação e blocos |
| Módulo 2 — Variáveis e tipos | 5–8 | EDU | Variáveis; Nomes e atribuição; Inteiros e decimais; Textos, booleanos e None |
| Módulo 3 — Entrada e saída | 9–12 | EDU | Mostrar resultados com mostrar(); Entrada com pergunte(); Conversão de entrada; F-strings |
| Módulo 4 — Operadores | 13–16 | EDU | Operações matemáticas; Comparações; Operadores lógicos; Atribuição composta e precedência |
| Módulo 5 — Condições | 17–20 | EDU | if com se; Múltiplos caminhos com senão_se; Alternativa com senão; Condições aninhadas |
| Módulo 6 — Repetição | 21–24 | EDU | for e intervalos; while com enquanto; quebrar, continuar e passar; Contadores e acumuladores |
| Módulo 7 — Textos | 25–28 | EDU | Índices de strings; Fatiamento de textos; Métodos de texto; Buscar, substituir, dividir e juntar |
| Módulo 8 — Listas | 29–32 | EDU | Criando e acessando listas; Alterando elementos; append e extend; insert, remove, pop, sort e reverse |
| Módulo 9 — Tuplas | 33–36 | EDU | Criando tuplas; Desempacotamento; Percorrendo tuplas; Lista ou tupla? |
| Módulo 10 — Conjuntos | 37–40 | EDU | Criando conjuntos; Adicionar e remover elementos; União e interseção; Diferença e pertencimento |
| Módulo 11 — Dicionários | 41–45 | EDU | Criando dicionários; Ler e alterar valores; keys, values, items; get e update; Percorrendo dicionários |
| Módulo 12 — Funções | 46–49 | EDU | Criando funções; Parâmetros e argumentos; Retorno; Escopo e reutilização |
| Módulo 13 — Erros e exceções | 50–53 | EDU | Erros de sintaxe, execução e lógica; try e except; else e finalmente; levantar e afirmar |
| Módulo 14 — Módulos e biblioteca padrão | 54–57 | EDU | importar; de e como; random, datetime e time; os e expressões regulares |
| Módulo 15 — Projetos EDU | 58–61 | EDU | Projeto: calculadora; Projeto: conversor; Projeto: quiz; Projeto: lista de tarefas |
| Módulo 16 — Funções avançadas | 62–65 | COMPLETO | Parâmetros padrão; Argumentos nomeados; *args; **kwargs |
| Módulo 17 — Comprehensions | 66–69 | COMPLETO | List comprehension básica; List comprehension com condição; Set comprehension; Dict comprehension |
| Módulo 18 — Programação funcional | 70–73 | COMPLETO | mapear(); filtrar(); zipar() e enumerar(); todos() e algum() |
| Módulo 19 — Iteradores e generators | 74–77 | COMPLETO | Iteradores com iter() e next(); Primeiro generator com produzir; Generator expression; Iterator personalizado |
| Módulo 20 — Arquivos | 78–81 | COMPLETO | Abrindo arquivos; Escrevendo arquivos; with para fechamento automático; Caminhos e pathlib |
| Módulo 21 — Dados e formatos | 82–85 | COMPLETO | JSON para dados estruturados; JSON em arquivo; CSV; serialização e desserialização |
| Módulo 22 — Exceções avançadas | 86–89 | COMPLETO | Hierarquia de exceções; raise from; Exceções personalizadas; finally para limpeza |
| Módulo 23 — Programação orientada a objetos | 90–93 | COMPLETO | Classes e objetos; __init__ e self; Métodos de instância; Atributos de classe |
| Módulo 24 — OOP avançada | 94–97 | COMPLETO | Herança; super(); Polimorfismo; Encapsulamento e property |
| Módulo 25 — Decoradores e métodos especiais | 98–101 | COMPLETO | staticmethod; classmethod; Decoradores simples; Métodos especiais |
| Módulo 26 — Expressões regulares | 102–105 | COMPLETO | re e search; findall; Grupos e captura; sub e substituição |
| Módulo 27 — Biblioteca padrão | 106–109 | COMPLETO | os e sys; datetime e calendar; collections; functools |
| Módulo 28 — Algoritmos e utilitários | 110–113 | COMPLETO | bisect; statistics; math; random |
| Módulo 29 — Organização e programas de terminal | 114–117 | COMPLETO | __name__ e ponto de entrada; argparse; configparser; Módulos e pacotes |
| Módulo 30 — Debugging, testes e qualidade | 118–121 | COMPLETO | Lendo traceback; assert como teste rápido; Testes unitários; Boas práticas e legibilidade |
| Módulo 31 — Projetos avançados | 122–125 | COMPLETO | Projeto: agenda em arquivo; Projeto: tarefas com JSON; Projeto: inventário com classes; Projeto final: sistema de estudos |

### 10.5 Como adicionar uma aula

1. Em `curso.py`, localize `DADOS_CURSO` e o conjunto do modo desejado.
2. Acrescente um dicionário com **todos** os campos da seção 10.2.
3. Mantenha `ordem` sequencial e use o mesmo texto de `modulo` das aulas vizinhas para agrupar no módulo certo.
4. Confira o exemplo `pyrtugues` com a [linha de comando](#7-linha-de-comando-pyrtugues_clipy) para garantir que ele traduz para o `python` informado.

---

## 11. Demo: Desafio do Chefão

Jogo 2D de chefe final escrito **inteiramente em Pyrtugues** (`demos/chefao.pyrt`, 224 linhas), usando Pygame pelo alias `jogo`. É um boss original, inspirado no ritmo de jogos de ação/run-and-gun, com desenhos feitos só por código do próprio projeto. Para abrir: paleta de comandos → **Pyrtugues: Abrir demo: Desafio do Chefão**.

**Requisito:** `pygame` instalado no mesmo Python usado pela extensão (`pip install pygame`).

| Controle | Ação |
|---|---|
| **Setas** esquerda/direita | Mover |
| **Espaço** | Pular (só no chão) |
| **Enter** ou clique do mouse | Atirar |
| **Esc** ou fechar a janela | Sair |

**Regras:** o jogador começa com **5 de vida** e o Chefão com **40**. O Chefão dispara projéteis, o jogador tem um breve período de invulnerabilidade ao ser atingido e os acertos soltam partículas. Quando a vida do Chefão chega a zero aparece **CHEFÃO DERROTADO!**; quando a do jogador chega a zero, o jogo encerra.

A demo é um bom exemplo de código real que mistura recursos: `importar jogo`, `importar aleatório`, `importar matemática`, laços `para ... em intervalo(...)`, funções (`def`), `global`, listas de dicionários, f-strings e métodos como `.adicionar()`, `.remover()`, `.preencher()` e `.colidir_retângulo()`.

---

## 12. Exemplos completos

Todos os blocos abaixo foram traduzidos pelo tradutor real (modo EDU).

### 12.1 Sistema de notas (o exemplo que o aplicativo carrega no editor)

```pyrt
função calcular_media(nota1, nota2):
    media = (nota1 + nota2) / 2
    retornar media

função classificar(media):
    se media maior ou igual 7:
        retornar "Aprovado"
    senão se media maior ou igual 5:
        retornar "Recuperação"
    senão:
        retornar "Reprovado"

mostrar("=== SISTEMA DE NOTAS ===")

nome = pergunte("Nome do aluno: ")
nota1 = decimal(pergunte("Nota 1: "))
nota2 = decimal(pergunte("Nota 2: "))

media = calcular_media(nota1, nota2)
situacao = classificar(media)

mostrar(f"\nAluno: {nome}")
mostrar(f"Média: {media}")
mostrar(f"Situação: {situacao}")
```

```python
def calcular_media(nota1, nota2):
    media = (nota1 + nota2) / 2
    return media

def classificar(media):
    if media >= 7:
        return "Aprovado"
    elif media >= 5:
        return "Recuperação"
    else:
        return "Reprovado"

print("=== SISTEMA DE NOTAS ===")

nome = input("Nome do aluno: ")
nota1 = float(input("Nota 1: "))
nota2 = float(input("Nota 2: "))

media = calcular_media(nota1, nota2)
situacao = classificar(media)

print(f"\nAluno: {nome}")
print(f"Média: {media}")
print(f"Situação: {situacao}")
```

### 12.2 Lista de tarefas

```pyrt
tarefas = []

função adicionar_tarefa(titulo):
    tarefas.adicionar({"titulo": titulo, "feita": falso})

função concluir_tarefa(posicao):
    tarefas[posicao]["feita"] = verdadeiro

função mostrar_tarefas():
    para posicao, tarefa em enumerar(tarefas):
        marca = "x" se tarefa["feita"] senão " "
        mostrar(f"[{marca}] {posicao}: {tarefa['titulo']}")

adicionar_tarefa("Estudar Pyrtugues")
adicionar_tarefa("Fazer o desafio")
concluir_tarefa(0)
mostrar_tarefas()
```

```python
tarefas = []

def adicionar_tarefa(titulo):
    tarefas.append({"titulo": titulo, "feita": False})

def concluir_tarefa(posicao):
    tarefas[posicao]["feita"] = True

def mostrar_tarefas():
    for posicao, tarefa in enumerate(tarefas):
        marca = "x" if tarefa["feita"] else " "
        print(f"[{marca}] {posicao}: {tarefa['titulo']}")

adicionar_tarefa("Estudar Pyrtugues")
adicionar_tarefa("Fazer o desafio")
concluir_tarefa(0)
mostrar_tarefas()
```

### 12.3 Área do círculo com módulo

```pyrt
importar matemática

função area_circulo(r):
    retornar matemática.pi vezes r elevado a 2

mostrar(area_circulo(2))
```

```python
import math

def area_circulo(r):
    return math.pi * r ** 2

print(area_circulo(2))
```

---

## 13. Pontos de atenção e comportamentos observados

Esta seção reúne comportamentos que apareceram ao **rodar o tradutor** enviado com o projeto (o `pyrtugues_core.py` da extensão, que tem a mesma lógica da v1.4.0 do aplicativo). Cada item traz um exemplo reproduzível e um jeito de contornar hoje. Alguns podem ser intencionais; estão aqui para que quem escreve programas, e quem mantém o projeto, saiba o que esperar.

### 13.1 Modo COMPLETO renomeia identificadores

O dicionário COMPLETO tem entradas para letras soltas e para palavras comuns de nome de variável. Os identificadores são renomeados de forma consistente em todo o programa, então o código costuma continuar funcionando, mas o Python gerado fica diferente do que foi digitado.

Letras que o COMPLETO converte para maiúscula (11 no total):

| Chave | COMPLETO |
|---|---|
| `a` | `A` |
| `i` | `I` |
| `l` | `L` |
| `m` | `M` |
| `s` | `S` |
| `u` | `U` |
| `x` | `X` |
| `t` | `T` |
| `n` | `N` |
| `w` | `W` |
| `y` | `Y` |
| `f` | `f` |
| `k` | `k` |
| `q` | `q` |
| `v` | `v` |
| `c` | `c` |
| `p` | `p` |

Outros exemplos do COMPLETO: `self` → `Self`, `nome` → `name`, `valor` → `Value`.

```pyrt
função contar(n):
    total = 0
    para i em intervalo(n):
        total mais igual i
    retornar total
```

```python
def contar(N):
    total = 0
    for I in range(N):
        total += I
    return total
```

```pyrt
classe Conta:
    função __init__(self, saldo):
        self.saldo = saldo
    função sacar(self, valor):
        self.saldo menos igual valor
        retornar self.saldo
```

```python
class Conta:
    def __init__(Self, saldo):
        Self.saldo = saldo
    def sacar(Self, Value):
        Self.saldo -= Value
        return Self.saldo
```

**Efeito:** nomes que precisam coincidir com algo externo (argumentos nomeados de uma biblioteca, atributos acessados por outro código) podem deixar de coincidir. **Contorno:** use o modo EDU para código geral; no COMPLETO, confira sempre o resultado em *Ver Python gerado*.

### 13.2 `resto` vira `__mod__` no modo COMPLETO

No EDU, `resto` é o operador `%`. No COMPLETO o dicionário traduz a palavra para `__mod__` antes da regra de operadores, e o resultado não é Python válido:

```pyrt
mostrar(10 resto 3)
```

```python
print(10 __mod__ 3)
```

**Contorno:** no COMPLETO, use `%` diretamente.

### 13.3 Variável com nome do dicionário "consome" a palavra em frases como `igual a`

Como a [seção 4.14](#414-variáveis-e-funções-com-nome-igual-a-uma-palavra-do-dicionário) explica, nomes atribuídos que existem no dicionário são protegidos em todo o programa. No COMPLETO, `a` é uma chave; se o programa tem `a = ...`, **toda ocorrência isolada de `a`** é protegida, inclusive a das frases `igual a`, `elevado a` e `maior ou igual a`, que então deixam de ser reconhecidas. No exemplo, `elevado a` ficou intacto e `igual` sozinho virou `__eq__` (no COMPLETO, essa é a tradução da palavra isolada):

```pyrt
a = 1
b = 3
mostrar(b elevado a 2)
se b igual a 3:
    mostrar("três")
```

```python
a = 1
b = 3
print(b elevado a 2)
if b __eq__ a 3:
    print("três")
```

**Contorno:** evite variáveis de uma letra no COMPLETO, ou use os símbolos (`==`, `**`, `>=`).

### 13.4 Métodos de várias palavras que não funcionam

7 dos 75 métodos da tabela da seção 4.8 não são traduzidos como esperado no modo EDU (`começa com`, `termina com`, `é dígito`, `é letra`, `é espaço`, `ordenar em ordem` e `inverter ordem`). O motivo é a ordem das etapas: palavras como `com`, `é`, `em` e `ordenar` já foram trocadas pelo dicionário quando a regra de métodos é aplicada.

```pyrt
valores = [3, 1, 2]
valores.ordenar em ordem()
```

```python
valores = [3, 1, 2]
valores.sorted in ordem()
```

Já `tirar espaços` funciona:

```pyrt
texto_a = "  oi  "
mostrar(texto_a.tirar espaços())
```

```python
texto_a = "  oi  "
print(texto_a.strip())
```

**Contorno:** use o nome Python do método, que passa sem alteração: `.startswith(...)`, `.endswith(...)`, `.isdigit()`, `.isalpha()`, `.isspace()`, `.sort()` e `.reverse()`.

### 13.5 `potência igual` e `igual` sozinho

`potência igual` gera `** igual` (a palavra `potência` é aplicada antes da expressão composta mais longa), e, no modo EDU, a palavra `igual` isolada não é traduzida (no COMPLETO ela vira `__eq__`); as demais atribuições compostas (`mais igual`, `menos igual`, `vezes igual`, `dividido igual`, `resto igual`) funcionam. **Contorno:** use `**=` e `igual a` (ou `==`).

### 13.6 Importar `data e hora`

A frase `data e hora` está na tabela de módulos, mas `e` e `hora` são trocadas pelo dicionário (`and` e `time`) antes da regra de módulos, e o resultado não é um `import` válido:

```pyrt
importar data e hora
importar datetime
```

```python
import data and time
import datetime
```

**Contorno:** use `importar datetime`, que funciona.

### 13.7 Parâmetros e variáveis de laço não são protegidos

A proteção da [seção 4.14](#414-variáveis-e-funções-com-nome-igual-a-uma-palavra-do-dicionário) só vê atribuições simples e nomes de função. Um **parâmetro** com nome de palavra do dicionário é traduzido (de forma consistente dentro da função), o que pode sombrear uma função embutida do Python:

```pyrt
função repetir(texto, vezes_n):
    retornar texto vezes vezes_n
```

```python
def repetir(str, vezes_n):
    return str * vezes_n
```

**Contorno:** escolha nomes de parâmetro que não estejam no dicionário (por exemplo, `frase` no lugar de `texto`).

### 13.8 Outros pontos

| Tema | Observação |
|---|---|
| Versões | O aplicativo mostra **1.4.0**, o núcleo da extensão declara a lógica da **v1.4.0** e a extensão está na **1.5.0** |
| `LICENSE` | O `package.json` aponta para `SEE LICENSE IN LICENSE`, mas o arquivo `LICENSE` não estava no pacote enviado; lembre de incluí-lo antes de empacotar |
| `__pycache__` | O pacote enviado contém `python/__pycache__/*.pyc`; o `.vscodeignore` já os exclui do `.vsix` |
| Nome do dicionário COMPLETO | No aplicativo é `dicionario_completo_json` (sem ponto); na extensão é `dicionario_completo.json`. O núcleo aceita os dois nomes |
| Progresso do curso | `aulas_concluidas` fica só na memória e é perdido ao fechar o aplicativo |
| Código legado | `ver_python`, `_trace_execucao`, `print_gui`, `write` e `flush` em `curso.py` não são chamados atualmente |
| Dois tradutores | A lógica de tradução existe em `curso.py` e em `python/pyrtugues_core.py`; correções precisam ser levadas aos dois lugares |
| Tradução e ordem | O resultado depende da ordem das regras (maiores primeiro, depois contextuais); ao adicionar palavras, teste nos dois modos |

---

## 14. Licença e publicação

### 14.1 Licença

O Pyrtugues usa a licença própria **Pyrtugues Personal & Individual Educational License**, que substituiu a MIT usada antes. Ela **restringe o uso institucional e comercial sem autorização prévia do autor**. O texto oficial é o do arquivo `LICENSE` do repositório; esta documentação não substitui a licença.

### 14.2 Identidade do projeto

O nome é **Pyrtugues**, escrito exatamente assim (não "Pyrtuguês"). Repositório oficial: https://github.com/pyrtugues/Pyrtugues.

### 14.3 Checklist para lançar uma nova versão da extensão

1. Se mudou algum dicionário, rode `python tools/gerar_gramatica.py`.
2. Teste com **F5** (janela *Testar extensão*) nos dois modos.
3. Aumente `version` no `package.json`.
4. Confirme que o `LICENSE` está na raiz e que `publisher` está correto.
5. Gere o pacote com `npx @vscode/vsce package` e instale o `.vsix` para um teste final.
6. Publique a nova versão com a ferramenta `vsce`.

---

## 15. Apêndices

### Apêndice A — Aliases de bibliotecas

#### A.1 Pygame (`jogo`)

| Pyrtugues | Python | Verificado |
|---|---|---|
| `jogo.iniciar` | `pygame.init` | ✅ |
| `jogo.sair` | `pygame.quit` | ✅ |
| `jogo.display.criar_janela` | `pygame.display.set_mode` | ✅ |
| `jogo.display.definir_título` | `pygame.display.set_caption` | ✅ |
| `jogo.display.obter_título` | `pygame.display.get_caption` | ✅ |
| `jogo.display.atualizar_tela` | `pygame.display.flip` | ✅ |
| `jogo.display.atualizar` | `pygame.display.update` | ✅ |
| `jogo.display.obter_tela` | `pygame.display.get_surface` | ✅ |
| `jogo.display.obter_tamanho` | `pygame.display.get_window_size` | ✅ |
| `jogo.display.definir_ícone` | `pygame.display.set_icon` | ✅ |
| `jogo.eventos.obter` | `pygame.event.get` | ✅ |
| `jogo.eventos.pegar` | `pygame.event.poll` | ✅ |
| `jogo.eventos.esperar` | `pygame.event.wait` | ✅ |
| `jogo.eventos.limpar` | `pygame.event.clear` | ✅ |
| `jogo.eventos.criar` | `pygame.event.Event` | ✅ |
| `jogo.desenho.linha` | `pygame.draw.line` | ✅ |
| `jogo.desenho.linhas` | `pygame.draw.lines` | ✅ |
| `jogo.desenho.círculo` | `pygame.draw.circle` | ✅ |
| `jogo.desenho.retângulo` | `pygame.draw.rect` | ✅ |
| `jogo.desenho.elipse` | `pygame.draw.ellipse` | ✅ |
| `jogo.desenho.polígono` | `pygame.draw.polygon` | ✅ |
| `jogo.desenho.arco` | `pygame.draw.arc` | ✅ |
| `jogo.imagem.carregar` | `pygame.image.load` | ✅ |
| `jogo.imagem.salvar` | `pygame.image.save` | ✅ |
| `jogo.transformação.escala` | `pygame.transform.scale` | ✅ |
| `jogo.transformação.escala_suave` | `pygame.transform.smoothscale` | ✅ |
| `jogo.transformação.rotacionar` | `pygame.transform.rotate` | ✅ |
| `jogo.transformação.espelhar` | `pygame.transform.flip` | ✅ |
| `jogo.fonte.carregar` | `pygame.font.Font` | ✅ |
| `jogo.fonte.sistema` | `pygame.font.SysFont` | ✅ |
| `jogo.fonte.padrão` | `pygame.font.get_default_font` | ✅ |
| `jogo.mixer.iniciar` | `pygame.mixer.init` | ✅ |
| `jogo.mixer.som` | `pygame.mixer.Sound` | ✅ |
| `jogo.musica.carregar` | `pygame.mixer.music.load` | ✅ |
| `jogo.musica.tocar` | `pygame.mixer.music.play` | ✅ |
| `jogo.musica.parar` | `pygame.mixer.music.stop` | ✅ |
| `jogo.tempo.relógio` | `pygame.time.Clock` | ✅ |
| `jogo.tempo.milissegundos` | `pygame.time.get_ticks` | ✅ |
| `jogo.tempo.temporizador` | `pygame.time.set_timer` | ✅ |
| `jogo.mouse.posição` | `pygame.mouse.get_pos` | ✅ |
| `jogo.mouse.movimento` | `pygame.mouse.get_rel` | ✅ |
| `jogo.mouse.botões` | `pygame.mouse.get_pressed` | ✅ |
| `jogo.mouse.ir_para` | `pygame.mouse.set_pos` | ✅ |
| `jogo.mouse.visível` | `pygame.mouse.set_visible` | ✅ |
| `jogo.teclado.pressionadas` | `pygame.key.get_pressed` | ✅ |
| `jogo.teclado.nome` | `pygame.key.name` | ✅ |
| `jogo.joystick.contagem` | `pygame.joystick.get_count` | ✅ |
| `jogo.sprite.grupo` | `pygame.sprite.Group` | ✅ |
| `jogo.sprite.sprite` | `pygame.sprite.Sprite` | ✅ |
| `jogo.retângulo` | `pygame.Rect` | ✅ |
| `jogo.vetor` | `pygame.Vector2` | ✅ |
| `jogo.cor` | `pygame.Color` | ✅ |
| `jogo.sair_evento` | `pygame.QUIT` | ✅ |
| `jogo.tecla_pressionada_evento` | `pygame.KEYDOWN` | ✅ |
| `jogo.tecla_solta_evento` | `pygame.KEYUP` | ✅ |
| `jogo.movimento_mouse_evento` | `pygame.MOUSEMOTION` | ✅ |
| `jogo.mouse_clicou` | `pygame.MOUSEBUTTONDOWN` | ✅ |
| `jogo.mouse_soltou` | `pygame.MOUSEBUTTONUP` | ✅ |
| `jogo.esquerda` | `pygame.K_LEFT` | ✅ |
| `jogo.direita` | `pygame.K_RIGHT` | ✅ |
| `jogo.cima` | `pygame.K_UP` | ✅ |
| `jogo.baixo` | `pygame.K_DOWN` | ✅ |
| `jogo.espaco` | `pygame.K_SPACE` | ✅ |
| `jogo.enter` | `pygame.K_RETURN` | ✅ |
| `jogo.esc` | `pygame.K_ESCAPE` | ✅ |

#### A.2 CustomTkinter (`ctk`)

| Pyrtugues | Python | Verificado |
|---|---|---|
| `ctk.janela` | `customtkinter.CTk` | ✅ |
| `ctk.janela_extra` | `customtkinter.CTkToplevel` | ✅ |
| `ctk.quadro` | `customtkinter.CTkFrame` | ✅ |
| `ctk.rotulo` | `customtkinter.CTkLabel` | ✅ |
| `ctk.botao` | `customtkinter.CTkButton` | ✅ |
| `ctk.entrada` | `customtkinter.CTkEntry` | ✅ |
| `ctk.caixa_texto` | `customtkinter.CTkTextbox` | ✅ |
| `ctk.caixa_selecao` | `customtkinter.CTkCheckBox` | ✅ |
| `ctk.interruptor` | `customtkinter.CTkSwitch` | ✅ |
| `ctk.deslizante` | `customtkinter.CTkSlider` | ✅ |
| `ctk.barra_progresso` | `customtkinter.CTkProgressBar` | ✅ |
| `ctk.menu` | `customtkinter.CTkOptionMenu` | ✅ |
| `ctk.combo` | `customtkinter.CTkComboBox` | ✅ |
| `ctk.abas` | `customtkinter.CTkTabview` | ✅ |
| `ctk.rolagem` | `customtkinter.CTkScrollableFrame` | ✅ |
| `ctk.barra_rolagem` | `customtkinter.CTkScrollbar` | ✅ |
| `ctk.segmentado` | `customtkinter.CTkSegmentedButton` | ✅ |
| `ctk.radio` | `customtkinter.CTkRadioButton` | ✅ |
| `ctk.dialogo` | `customtkinter.CTkInputDialog` | ✅ |
| `ctk.imagem` | `customtkinter.CTkImage` | ✅ |
| `ctk.fonte` | `customtkinter.CTkFont` | ✅ |
| `ctk.modo_aparencia` | `customtkinter.set_appearance_mode` | ✅ |
| `ctk.obter_modo_aparencia` | `customtkinter.get_appearance_mode` | ✅ |
| `ctk.tema` | `customtkinter.set_default_color_theme` | ✅ |
| `ctk.escala_widget` | `customtkinter.set_widget_scaling` | ✅ |
| `ctk.obter_escala_widget` | `customtkinter.get_widget_scaling` | ✅ |
| `ctk.escala_janela` | `customtkinter.set_window_scaling` | ✅ |
| `ctk.obter_escala_janela` | `customtkinter.get_window_scaling` | ✅ |

#### A.3 Outras bibliotecas

| Pyrtugues | Python | Verificado |
|---|---|---|
| `numerico.array` | `numpy.array` | ✅ |
| `numerico.zeros` | `numpy.zeros` | ✅ |
| `numerico.ones` | `numpy.ones` | ✅ |
| `numerico.média` | `numpy.mean` | ✅ |
| `tabelas.ler_csv` | `pandas.read_csv` | ✅ |
| `tabelas.ler_excel` | `pandas.read_excel` | ✅ |
| `tabelas.salvar_csv` | `pandas.DataFrame.to_csv` | ✅ |
| `grafico.linha` | `matplotlib.pyplot.plot` | ✅ |
| `grafico.mostrar` | `matplotlib.pyplot.show` | ✅ |
| `requisicoes.obter` | `requests.get` | ✅ |
| `requisicoes.enviar` | `requests.post` | ✅ |
| `cliente_http.obter` | `httpx.get` | ✅ |
| `api_web.aplicação` | `fastapi.FastAPI` | ✅ |
| `servidor_web.aplicação` | `flask.Flask` | ✅ |
| `banco_dados.engine` | `sqlalchemy.create_engine` | ✅ |
| `planilha.abrir` | `openpyxl.load_workbook` | ✅ |
| `imagens_pillow.abrir` | `PIL.Image.open` | ✅ |
| `visao_cv.abrir` | `cv2.imread` | ✅ |

### Apêndice B — Módulos da biblioteca padrão cobertos

Módulos da biblioteca padrão que têm nome em português no dicionário EDU (78 módulos). Cada módulo também tem entradas para seus itens, seguindo a convenção da [seção 4.11](#411-biblioteca-padrão-pelo-dicionário). A coluna mostra até 4 nomes em português por módulo.

| Módulo Python | Nome(s) em português no dicionário EDU |
|---|---|
| `argparse` | `argumentos_de_terminal` |
| `ast` | `árvore_sintática` |
| `base64` | `base_64`, `codificação_base64` |
| `binascii` | `binascii` |
| `bisect` | `busca_binária` |
| `builtins` | `builtins` |
| `bz2` | `bz_2`, `compactação_bz2` |
| `calendar` | `calendário` |
| `codecs` | `codificadors`, `codificadores` |
| `collections` | `coleções` |
| `concurrent` | `concorrente` |
| `configparser` | `configurador` |
| `contextlib` | `gerenciador_de_contexto`, `gerenciamento_de_contexto` |
| `copy` | `cópia`, `copiar` |
| `csv` | `csv` |
| `dataclasses` | `classes_de_dados` |
| `datetime` | `data_e_hora` |
| `decimal` | `decimal_exato` |
| `difflib` | `difflib`, `diferenças_de_texto` |
| `dis` | `dis`, `desmontador` |
| `email` | `email` |
| `enum` | `enumeração` |
| `fractions` | `frações` |
| `functools` | `funções_utilitárias` |
| `gc` | `gc` |
| `glob` | `listar_por_padrão`, `expansão_de_caminhos` |
| `gzip` | `compactação_gzip` |
| `hashlib` | `hashes` |
| `heapq` | `fila_de_monte` |
| `hmac` | `hmac` |
| `html` | `html` |
| `http` | `http` |
| `importlib` | `importlib`, `importação` |
| `inspect` | `inspeção` |
| `io` | `entrada_e_saída` |
| `itertools` | `iteradores` |
| `json` | `json` |
| `logging` | `registro`, `registro_de_eventos` |
| `lzma` | `compactação_lzma` |
| `math` | `math`, `matemática` |
| `mimetypes` | `tipos_mime` |
| `mmap` | `mmap`, `memória_mapeada` |
| `multiprocessing` | `multiprocessamento` |
| `numbers` | `números`, `tipos_numéricos` |
| `operator` | `operadores` |
| `os` | `sistema_operacional` |
| `pathlib` | `caminhos` |
| `pickle` | `serialização` |
| `platform` | `plataforma` |
| `pprint` | `impressão_bonita` |
| `queue` | `fila` |
| `random` | `aleatório` |
| `re` | `expressões_regulares` |
| `secrets` | `segredos` |
| `selectors` | `seletores`, `seletores_de_entrada_saída` |
| `shutil` | `utilitários_de_arquivo`, `utilitários_de_arquivos` |
| `signal` | `sinal`, `sinais` |
| `socket` | `soquetes` |
| `sqlite3` | `sqlite3` |
| `statistics` | `estatística` |
| `struct` | `struct`, `dados_binários` |
| `subprocess` | `subprocessos` |
| `sys` | `sistema_python` |
| `tarfile` | `arquivo_tar` |
| `tempfile` | `arquivo_temporário`, `arquivos_temporários` |
| `textwrap` | `textwrap`, `quebra_de_texto` |
| `threading` | `encadeamento` |
| `time` | `hora`, `tempo` |
| `timeit` | `timeit`, `cronômetro_de_código` |
| `traceback` | `rastreamento_de_erro`, `rastreamento_de_erros` |
| `types` | `tipos` |
| `typing` | `tipagem` |
| `unittest` | `testes_unitários` |
| `urllib` | `urllib`, `endereços_web` |
| `warnings` | `avisos` |
| `weakref` | `referências_fracas` |
| `xml` | `xml` |
| `zipfile` | `arquivo_zip` |

### Apêndice C — Entradas de núcleo exclusivas do COMPLETO

As 118 entradas do núcleo do dicionário COMPLETO que não existem no EDU:

| Pyrtugues | Python |
|---|---|
| `reticências` | `Ellipsis` |
| `não_implementado` | `NotImplemented` |
| `obter_atributo` | `getattr` |
| `definir_atributo` | `setattr` |
| `excluir_atributo` | `delattr` |
| `tem_atributo` | `hasattr` |
| `fatia` | `slice` |
| `erro_de_buffer` | `BufferError` |
| `erro_de_ambiente` | `EnvironmentError` |
| `módulo_não_encontrado` | `ModuleNotFoundError` |
| `erro_de_recursão` | `RecursionError` |
| `erro_de_indentação` | `IndentationError` |
| `erro_de_tabulação` | `TabError` |
| `aviso` | `Warning` |
| `aviso_do_usuário` | `UserWarning` |
| `aviso_de_obsolescência` | `DeprecationWarning` |
| `aviso_de_obsolescência_pendente` | `PendingDeprecationWarning` |
| `aviso_de_sintaxe` | `SyntaxWarning` |
| `aviso_de_execução` | `RuntimeWarning` |
| `aviso_de_futuro` | `FutureWarning` |
| `aviso_de_importação` | `ImportWarning` |
| `aviso_de_bytes` | `BytesWarning` |
| `aviso_de_recurso` | `ResourceWarning` |
| `aviso_de_codificação` | `EncodingWarning` |
| `chaves_de_dicionário` | `dict_keys` |
| `valores_de_dicionário` | `dict_values` |
| `itens_de_dicionário` | `dict_items` |
| `inicializar` | `__init__` |
| `criar_novo` | `__new__` |
| `texto_objeto` | `__str__` |
| `converter_para_bytes` | `__bytes__` |
| `formatar_objeto` | `__format__` |
| `calcular_hash` | `__hash__` |
| `valor_booleano` | `__bool__` |
| `iterar` | `__iter__` |
| `próximo` | `__next__` |
| `obter_item` | `__getitem__` |
| `definir_item` | `__setitem__` |
| `excluir_item` | `__delitem__` |
| `conter` | `__contains__` |
| `chamar` | `__call__` |
| `entrar` | `__enter__` |
| `sair` | `pygame.quit` |
| `entrar_assíncrono` | `__aenter__` |
| `sair_assíncrono` | `__aexit__` |
| `igual` | `__eq__` |
| `diferente` | `__ne__` |
| `menor_que` | `__lt__` |
| `menor_ou_igual` | `__le__` |
| `maior_que` | `__gt__` |
| `maior_ou_igual` | `__ge__` |
| `subtrair` | `__sub__` |
| `multiplicar` | `__mul__` |
| `multiplicar_matriz` | `__matmul__` |
| `dividir` | `__truediv__` |
| `dividir_inteiro` | `__floordiv__` |
| `resto` | `__mod__` |
| `potenciar` | `__pow__` |
| `negativo` | `__neg__` |
| `positivo` | `__pos__` |
| `valor_absoluto` | `__abs__` |
| `e_bit` | `__and__` |
| `ou_bit` | `__or__` |
| `xor_bit` | `__xor__` |
| `deslocar_esquerda` | `__lshift__` |
| `deslocar_direita` | `__rshift__` |
| `somar_no_lugar` | `__iadd__` |
| `subtrair_no_lugar` | `__isub__` |
| `multiplicar_no_lugar` | `__imul__` |
| `matriz_no_lugar` | `__imatmul__` |
| `dividir_no_lugar` | `__itruediv__` |
| `dividir_inteiro_no_lugar` | `__ifloordiv__` |
| `resto_no_lugar` | `__imod__` |
| `potência_no_lugar` | `__ipow__` |
| `e_bit_no_lugar` | `__iand__` |
| `ou_bit_no_lugar` | `__ior__` |
| `xor_no_lugar` | `__ixor__` |
| `deslocar_esquerda_no_lugar` | `__ilshift__` |
| `deslocar_direita_no_lugar` | `__irshift__` |
| `listar_atributos` | `__dir__` |
| `obter_atributo_especial` | `__getattr__` |
| `definir_atributo_especial` | `__setattr__` |
| `excluir_atributo_especial` | `__delattr__` |
| `compartimentos` | `__slots__` |
| `anotações` | `__annotations__` |
| `obter_item_da_classe` | `__class_getitem__` |
| `inicializar_subclasse` | `__init_subclass__` |
| `entradas_da_mro` | `__mro_entries__` |
| `argumentos_de_correspondência` | `__match_args__` |
| `classe_de_correspondência` | `__match_class__` |
| `preparar_classe` | `__prepare__` |
| `verificar_instância` | `__instancecheck__` |
| `verificar_subclasse` | `__subclasscheck__` |
| `gancho_de_subclasse` | `__subclasshook__` |
| `caminho_do_sistema_de_arquivos` | `__fspath__` |
| `aguardar_corrotina` | `__await__` |
| `iterar_assíncrono` | `__aiter__` |
| `próximo_assíncrono` | `__anext__` |
| `não_é` | `is not` |
| `fora_de` | `not in` |
| `mais` | `+` |
| `menos` | `-` |
| `vezes` | `*` |
| `dividido_por` | `/` |
| `divisão_inteira` | `//` |
| `igual_a` | `==` |
| `diferente_de` | `!=` |
| `inverter_bits` | `~` |
| `atribuição` | `=` |
| `mais_igual` | `+=` |
| `menos_igual` | `-=` |
| `vezes_igual` | `*=` |
| `dividido_igual` | `/=` |
| `resto_igual` | `%=` |
| `potência_igual` | `**=` |
| `divisão_inteira_igual` | `//=` |
| `classes_base_abstratas` | `abc` |
| `introspecção_de_anotações` | `annotationlib` |

### Apêndice D — Referência do código de `curso.py`

#### D.1 Funções de módulo (tradutor e curso)

| Função | Linha | Descrição (docstring) |
|---|---|---|
| `_carregar_dicionario(caminho)` | 18 |  |
| `_preparar_dicionario(traducao)` | 34 |  |
| `_escape_regex(texto)` | 61 |  |
| `_aplicar_aliases_bibliotecas(resultado, proteger_saida)` | 254 | Aplica aliases qualificados antes das traduções de módulo/palavra. |
| `_substituir_palavra(texto, original, destino)` | 281 |  |
| `_traduzir_expressao_fstring(expressao)` | 290 |  |
| `_traduzir_fstring(match)` | 298 |  |
| `_proteger_strings_e_comentarios(codigo)` | 358 | Protege strings e comentários antes das traduções. |
| `_aplicar_traducoes_base(codigo)` | 439 |  |
| `proteger_strings(codigo)` | 614 | Mantém strings, f-strings e comentários fora das substituições do tradutor. |
| `restaurar_strings(codigo, strings)` | 619 |  |
| `traduzir_fstrings(codigo)` | 625 |  |
| `_traduzir_fstring_rapido(match)` | 632 | Versão otimizada: só processa se tiver { dentro. |
| `traduzir(codigo_br)` | 643 |  |
| `_curso_aulas(modo)` | 5769 |  |

#### D.2 Classe `JanelaBR`

| Método | Linha | Descrição (docstring) |
|---|---|---|
| `__init__()` | 5773 |  |
| `_construir_pagina_selecao()` | 5920 | Tela inicial de seleção EDU/COMPLETO, sem depender de sys.stdin. |
| `_entrar_modo_inicial(modo)` | 6000 |  |
| `_construir_pagina_editor()` | 6004 | Monta o workspace principal: editor + Python lado a lado, terminal abaixo. |
| `_construir_pagina_exemplos()` | 6328 | Biblioteca de exemplos dentro do mesmo app, sem abrir outra janela. |
| `_construir_pagina_curso()` | 6409 | Constrói o curso dentro da mesma janela do Pyrtugues. |
| `_definir_modo_aplicativo(modo)` | 6532 | Troca o dicionário ativo e mantém curso e tradutor sincronizados. |
| `_mostrar_seletor_inicial()` | 6554 | Mostra uma seleção visual e moderna para escolher EDU ou COMPLETO. |
| `_selecionar_modo_curso(modo)` | 6689 |  |
| `_atualizar_botoes_modo_curso()` | 6700 |  |
| `_aulas_filtradas_curso()` | 6717 |  |
| `_atualizar_lista_aulas()` | 6734 | Reconstrói a lista lateral sem abrir outra janela. |
| `_curso_limpar_conteudo()` | 6791 |  |
| `_curso_label(parent, text)` | 6795 |  |
| `_curso_caixa_texto(parent, texto, altura, cor)` | 6806 |  |
| `_mostrar_aula_curso(indice)` | 6825 |  |
| `_alternar_conclusao_curso()` | 7079 |  |
| `_curso_anterior()` | 7088 |  |
| `_curso_proxima()` | 7094 |  |
| `_abrir_aula_no_editor()` | 7102 |  |
| `_construir_pagina_sobre()` | 7111 | Página Sobre integrada ao app, sem Toplevel. |
| `_mostrar_pagina(nome)` | 7231 | Troca os frames principais sem abrir novas janelas. |
| `_ir_para_editor()` | 7272 |  |
| `_atualizar_preview_python(event)` | 7279 | Atualiza a tradução visual sem alterar o código do usuário. |
| `copiar_python()` | 7293 |  |
| `baixar_python()` | 7302 |  |
| `_carregar_codigo(codigo)` | 7321 |  |
| `abrir_exemplos()` | 7328 | Mostra a biblioteca de exemplos na página interna do app. |
| `_configurar_editor_interno()` | 7332 | Configura detalhes do Tk Text que o CTkTextbox não expõe no tema. |
| `_sincronizar_scroll_editor(first, last)` | 7350 | Mantém scrollbar, editor e gutter sincronizados em tempo real. |
| `atualizar_numeros_linha(event)` | 7360 | Atualiza o gutter com o mesmo espaçamento vertical do editor. |
| `sincronizar_numeros_linha(event)` | 7382 | Sincroniza o gutter com a posição vertical real do editor. |
| `_atualizar_linha_atual(event)` | 7393 | Destaca suavemente a linha onde o cursor está. |
| `_editor_cursor_changed(event)` | 7408 |  |
| `_editor_keyrelease(event)` | 7413 |  |
| `_editor_indentacao(linha_texto)` | 7425 | Retorna a indentação inicial e uma indentação adicional de 4 espaços. |
| `_selecionar_linhas()` | 7430 | Obtém o intervalo de linhas selecionadas, quando houver seleção. |
| `_editor_keypress(event)` | 7439 | Atalhos de editor: pares, indentação, Enter e navegação. |
| `ver_python()` | 7545 | Mostra o código Python gerado pelo tradutor. |
| `input_gui(prompt)` | 7603 | Entrada segura para código executado em background, com modal criado no thread do Tk. |
| `_estilizar_modal_entrada(janela, prompt, entrada, confirmar, cancelar)` | 7618 | Monta uma caixa de entrada visual consistente com o Pyrtugues. |
| `_abrir_input_modal(prompt)` | 7685 | Entrada manual bonita para chamadas feitas na thread principal. |
| `_processar_pedido_input()` | 7715 |  |
| `_cancelar_pedidos_input()` | 7757 |  |
| `abrir_sobre()` | 7770 | Mostra a página Sobre integrada ao app. |
| `_trace_execucao(frame, evento, arg)` | 7774 |  |
| `_atualizar_status(texto, cor)` | 7779 |  |
| `_encontrar_python_externo()` | 7785 | Encontra um Python instalado no sistema, fora do executável do Pyrtugues. |
| `_criar_script_execucao_externa(codigo_py)` | 7817 | Cria um bootstrap que permite input() pelo modal do Pyrtugues. |
| `executar_codigo()` | 7845 |  |
| `_executar_em_background(codigo_br)` | 7869 | Executa o código traduzido usando o Python instalado no computador. |
| `_mostrar_erro_execucao_externo(retorno, linhas_br)` | 7954 |  |
| `_finalizar_execucao_sucesso(namespace)` | 7966 |  |
| `_finalizar_execucao_parado()` | 7975 |  |
| `_mostrar_erro_execucao(erro, linha_erro, linhas_br)` | 7984 |  |
| `parar_execucao()` | 7997 |  |
| `print_gui()` | 8020 | Versão de print compatível com o editor, enviada para a saída do app. |
| `write(texto)` | 8028 |  |
| `flush()` | 8031 |  |
| `escrever_saida(texto)` | 8034 |  |
| `carregar_exemplo()` | 8048 |  |

### Apêndice E — Glossário

| Termo | Significado |
|---|---|
| **Pyrtugues** | O projeto: tradutor de português para Python com editor, curso e extensão |
| **`.pyrt`** | Extensão dos arquivos de código em Pyrtugues |
| **Modo EDU** | Dicionário educacional, menor, voltado a aprender |
| **Modo COMPLETO** | Dicionário amplo, com muito mais nomes da biblioteca padrão e do Python |
| **Dicionário** | Arquivo JSON que liga palavras em português aos nomes do Python |
| **Alias** | Nome em português para algo qualificado de uma biblioteca (`jogo.desenho.linha` → `pygame.draw.line`) |
| **Núcleo** | Parte do dicionário com palavras de controle, constantes, funções, tipos e exceções |
| **Token protegido** | Marcador temporário (`__PYRT_STR_n__`, `__PYRT_VAR_n__`, `__PYRT_OUT_n__`) que impede o tradutor de mexer em strings, comentários, nomes e saídas já traduzidas |
| **Preview ao vivo** | Painel (ou documento) com o Python gerado, atualizado enquanto se digita |
| **CLI** | `pyrtugues_cli.py`, interface de linha de comando usada pela extensão |
