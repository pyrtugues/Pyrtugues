import re
import threading
from queue import Queue, Empty
import customtkinter as ctk
from tkinter import messagebox, filedialog
import sys
from pathlib import Path
import json
import keyword
import builtins

# Pasta onde o aplicativo/arquivos empacotados estão.
# Isso funciona tanto no .py quanto no executável gerado pelo PyInstaller.
BASE_DIR = Path(__file__).resolve().parent

def _carregar_dicionario(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict):
            return {"portugues": {}}
        dados.setdefault("portugues", {})
        return dados
    except FileNotFoundError:
        print(f"ERRO: {caminho} não encontrado!")
        return {"portugues": {}}
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido em {caminho}: {e}")
        return {"portugues": {}}


def _preparar_dicionario(traducao):
    return {
        k: v for k, v in traducao.get("portugues", {}).items()
        if not k.startswith("_secao_")
        and k not in _PALAVRAS_PYTHON_NATIVAS
    }


# Os dois dicionários ficam disponíveis no próprio programa. A seleção inicial
# agora acontece em uma interface gráfica bonita, em vez de pelo console.
TRADUCAO_EDU = _carregar_dicionario(BASE_DIR / "dicionario.json")
TRADUCAO_COMPLETO = _carregar_dicionario(BASE_DIR / "dicionario_completo_json")

# Filtra chaves de seção e evita reprocessar palavras que já são Python.
# O dicionário COMPLETO possui algumas entradas em inglês/nomes nativos de
# Python (por exemplo: "if" -> "If", "int" -> "INT", "str" -> "Str").
# Como o tradutor é Português -> Python, essas entradas não podem ser
# aplicadas depois que uma palavra portuguesa já foi convertida.
_PALAVRAS_PYTHON_NATIVAS = set(keyword.kwlist) | set(dir(builtins)) | {"True", "False", "None"}
DICIONARIOS = {
    "edu": _preparar_dicionario(TRADUCAO_EDU),
    "completo": _preparar_dicionario(TRADUCAO_COMPLETO),
}
DICIONARIO = DICIONARIOS["edu"]



def _escape_regex(texto):
    return re.escape(texto)


_METODOS = {
    "maiúsculas": "upper", "minúsculas": "lower", "capitalizar": "capitalize", "título": "title",
    "trocar": "replace", "dividir": "split", "juntar": "join", "tirar espaços": "strip",
    "começa com": "startswith", "termina com": "endswith", "encontrar": "find", "contar": "count",
    "é dígito": "isdigit", "é letra": "isalpha", "é espaço": "isspace",
    "adicionar": "append", "estender": "extend", "inserir": "insert", "remover": "remove",
    "tirar": "pop", "limpar": "clear", "copiar": "copy", "índice": "index",
    "ordenar em ordem": "sort", "inverter ordem": "reverse",
    "chaves": "keys", "valores": "values", "itens": "items", "pegar": "get", "atualizar": "update",
}
_TIPOS_CONTEXTUAIS = {
    "inteiro",
    "decimal",
    "número_complexo",
    "texto",
    "booleano",
    "bytes",
    "bytearray",
    "memória",
    "lista",
    "tupla",
    "conjunto",
    "conjunto_imutável",
    "dicionário",
    "iterador",
    "objeto",
}

_MODULOS = {
    "matemática": "math", "aleatório": "random", "data e hora": "datetime",
    "tempo": "time", "sistema": "os", "expressão regular": "re",
}

_SKIP_DIRETO = {
    "e", "ou", "em", "pergunte", "pergunta", "mais", "menos", "vezes", "resto", "potência", "é",
    *(_METODOS.keys()), *(_MODULOS.keys()), "caminho", "arquivo", "requisição", "resposta",
}


def _substituir_palavra(texto, original, destino):
    return re.sub(
        rf'(?<![A-Za-zÀ-ÿ0-9_]){_escape_regex(original)}(?![A-Za-zÀ-ÿ0-9_])',
        lambda _m: destino,
        texto,
        flags=re.IGNORECASE,
    )


def _traduzir_expressao_fstring(expressao):
    protegido, blocos = _proteger_strings_e_comentarios(expressao)
    resultado = _aplicar_traducoes_base(protegido)
    for i, bloco in enumerate(blocos):
        resultado = resultado.replace(f"__PYRT_STR_{i}__", bloco)
    return resultado


def _traduzir_fstring(match):
    texto = match.group(0)
    inicio = re.match(r'^([rRuUbBfF]{0,2})("""|\'\'\'|"|\')', texto)
    if not inicio or 'f' not in inicio.group(1).lower():
        return texto

    prefixo, quote = inicio.groups()
    if not texto.endswith(quote):
        return texto

    corpo = texto[len(prefixo) + len(quote):-len(quote)]
    partes = []
    i = 0

    while i < len(corpo):
        if corpo.startswith('{{', i):
            partes.append('{{')
            i += 2
            continue
        if corpo.startswith('}}', i):
            partes.append('}}')
            i += 2
            continue
        if corpo[i] != '{':
            partes.append(corpo[i])
            i += 1
            continue

        profundidade = 1
        j = i + 1
        string_atual = None
        escape = False
        while j < len(corpo) and profundidade:
            c = corpo[j]
            if string_atual:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == string_atual:
                    string_atual = None
            else:
                if c in ('"', "'"):
                    string_atual = c
                elif c == '{':
                    profundidade += 1
                elif c == '}':
                    profundidade -= 1
            j += 1

        if profundidade:
            partes.append(corpo[i:])
            break

        partes.append('{' + _traduzir_expressao_fstring(corpo[i + 1:j - 1]) + '}')
        i = j

    return prefixo + quote + ''.join(partes) + quote


def _proteger_strings_e_comentarios(codigo):
    """Protege strings e comentários antes das traduções.

    O scanner percorre o código caractere por caractere, permitindo
    proteger strings normais, strings multilinha e comentários mesmo
    quando o usuário ainda está digitando um código incompleto.
    """

    blocos = []
    resultado = []
    i = 0
    tamanho = len(codigo)

    def guardar(texto):
        indice = len(blocos)
        blocos.append(texto)
        return f"__PYRT_STR_{indice}__"

    while i < tamanho:

        # Comentário: tudo depois de # até o fim da linha fica protegido.
        if codigo[i] == "#":
            inicio = i
            while i < tamanho and codigo[i] != "\n":
                i += 1
            resultado.append(guardar(codigo[inicio:i]))
            continue

        # Prefixos de strings: r, u, b, f e combinações válidas.
        inicio_string = i
        if codigo[i] in "rRuUbBfF":
            j = i
            while j < tamanho and codigo[j] in "rRuUbBfF":
                j += 1
            if j < tamanho and codigo[j] in '"\'':
                inicio_string = i
                i = j
            else:
                i = inicio_string

        # String normal ou multilinha.
        if i < tamanho and codigo[i] in '"\'':
            quote = codigo[i]
            tripla = (
                i + 2 < tamanho
                and codigo[i:i + 3] == quote * 3
            )

            if tripla:
                delimitador = quote * 3
                i += 3
                while i < tamanho:
                    if codigo[i:i + 3] == delimitador:
                        i += 3
                        break
                    i += 1
                resultado.append(guardar(codigo[inicio_string:i]))
                continue

            i += 1
            escape = False
            while i < tamanho:
                caractere = codigo[i]
                if escape:
                    escape = False
                elif caractere == "\\":
                    escape = True
                elif caractere == quote:
                    i += 1
                    break
                i += 1

            resultado.append(guardar(codigo[inicio_string:i]))
            continue

        resultado.append(codigo[i])
        i += 1

    return "".join(resultado), blocos


def _aplicar_traducoes_base(codigo):
    resultado = codigo
    
    # ═══════════════════════════════════════════════════
    # ETAPA 1: TRADUZIR EXPRESSÕES COMPOSTAS (ANTES de tudo)
    # ═══════════════════════════════════════════════════
    expressoes_compostas = {
        # Comparações compostas (mais longas primeiro)
        "maior ou igual a": ">=",
        "menor ou igual a": "<=",
        "maior ou igual": ">=",
        "menor ou igual": "<=",
        "maior que": ">",
        "menor que": "<",
        "diferente de": "!=",
        "igual a": "==",
        "fora de": "not in",
        "dentro de": "in",
        
        # Operadores matemáticos
        "dividido por": "/",
        "elevado a": "**",
        "potência": "**",
        "divisão inteira": "//",
        "mais igual": "+=",
        "menos igual": "-=",
        "vezes igual": "*=",
        "dividido igual": "/=",
        "resto igual": "%=",
        "potência igual": "**=",
        
        # Lógicos
        "e também": "and",
        "ou então": "or",
        "não é": "is not",
        
        # Controle
        "senão se": "elif",
        "para cada": "for",
        "enquanto verdadeiro": "while True",
    }
    
    for pt, py in expressoes_compostas.items():
        resultado = re.sub(
            rf'(?<![A-Za-zÀ-ÿ0-9_]){re.escape(pt)}(?![A-Za-zÀ-ÿ0-9_])',
            py,
            resultado,
            flags=re.IGNORECASE,
        )
    
    # ═══════════════════════════════════════════════════
    # ETAPA 2: TRADUZIR PALAVRAS SOLTAS
    # ═══════════════════════════════════════════════════
    chaves = sorted(
        DICIONARIO.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )
    
    for br, py in chaves:
        if br not in resultado:
            continue

        # Métodos só podem ser traduzidos depois do ponto.
        if br in _METODOS:
            continue

        # Módulos possuem regras próprias na etapa contextual.
        if br in _MODULOS:
            continue

        # Tipos: não traduza quando estiverem sendo usados
        # como objeto/variável antes de um ponto.
        if br in _TIPOS_CONTEXTUAIS:
            resultado = re.sub(
                rf'(?<![A-Za-zÀ-ÿ0-9_])'
                rf'{_escape_regex(br)}'
                rf'(?![A-Za-zÀ-ÿ0-9_])'
                rf'(?!\s*\.)',
                py,
                resultado,
                flags=re.IGNORECASE,
            )
            continue

        resultado = _substituir_palavra(resultado, br, py)
    
    # ═══════════════════════════════════════════════════
    # ETAPA 3: TRADUÇÕES CONTEXTUAIS
    # ═══════════════════════════════════════════════════
    
    # "for X em Y" → "for X in Y"
    resultado = re.sub(
        r'\bfor\s+([A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*)\s+em\b',
        r'for \1 in',
        resultado,
        flags=re.IGNORECASE
    )
    
    # Módulos em import/from
    for br, py in sorted(_MODULOS.items(), key=lambda item: len(item[0]), reverse=True):
        resultado = re.sub(
            rf'\b(import|from)\s+{_escape_regex(br)}\b',
            lambda m, py=py: f'{m.group(1)} {py}',
            resultado,
            flags=re.IGNORECASE
        )
        resultado = re.sub(
            rf'(?<![A-Za-zÀ-ÿ0-9_]){_escape_regex(br)}(?=\s*\.)',
            py,
            resultado,
            flags=re.IGNORECASE
        )
    
    # Métodos só depois de ponto
    for br, py in sorted(_METODOS.items(), key=lambda item: len(item[0]), reverse=True):
        resultado = re.sub(
            rf'(?<=\.)\s*{_escape_regex(br)}(?=\s*\()',
            py,
            resultado,
            flags=re.IGNORECASE
        )
    
    # Operadores contextuais (com contexto)
    def operador_contextual(palavra, destino):
        nonlocal resultado
        resultado = re.sub(
            rf'(?<![A-Za-zÀ-ÿ0-9_])'
            rf'([A-Za-zÀ-ÿ0-9_\]\)\}}]+)'
            rf'\s+{_escape_regex(palavra)}'
            rf'(?=\s+[A-Za-zÀ-ÿ0-9_\(\[\{{+!\-])',
            rf'\1 {destino}',
            resultado,
            flags=re.IGNORECASE
        )
    
    operador_contextual("e", "and")
    operador_contextual("ou", "or")
    operador_contextual("mais", "+")
    operador_contextual("menos", "-")
    operador_contextual("vezes", "*")
    operador_contextual("resto", "%")
    
    return resultado


def proteger_strings(codigo):
    """Mantém strings, f-strings e comentários fora das substituições do tradutor."""
    return _proteger_strings_e_comentarios(codigo)


def restaurar_strings(codigo, strings):
    for i, texto in enumerate(strings):
        codigo = codigo.replace(f"__PYRT_STR_{i}__", texto)
    return codigo


def traduzir_fstrings(codigo):
    protegido, blocos = _proteger_strings_e_comentarios(codigo)
    resultado = protegido
    for i, bloco in enumerate(blocos):
        resultado = resultado.replace(f"__PYRT_STR_{i}__", bloco)
    return resultado

def _traduzir_fstring_rapido(match):
    """Versão otimizada: só processa se tiver { dentro."""
    texto = match.group(0)
    
    # ⬇️ OTIMIZAÇÃO: se não tem {, não processa
    if '{' not in texto:
        return texto
    
    # Senão, chama a função original
    return _traduzir_fstring(match)

def traduzir(codigo_br):
    # PASSO 1: Proteger variáveis (atribuição + referências)
    # PASSO 1: Proteger variáveis E funções
    variaveis_protegidas = {}

    # 1.1: Encontra nomes de variáveis E funções
    nomes_encontrados = set()

    # Variáveis
    for linha in codigo_br.split('\n'):
        if '=' in linha and not linha.strip().startswith('#'):
            match = re.match(r'^(\s*)([A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*)\s*=', linha)
            if match:
                nome = match.group(2)
                if nome in DICIONARIO:
                    nomes_encontrados.add(nome)

    # Funções (linha "função nome(...)")
    for linha in codigo_br.split('\n'):
        match = re.match(r'^\s*função\s+([A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*)', linha)
        if match:
            nome = match.group(1)
            if nome in DICIONARIO:
                nomes_encontrados.add(nome)

    # 1.2: Substitui CADA referência
    for i, nome in enumerate(nomes_encontrados):
        token = f"__PYRT_VAR_{i}__"
        variaveis_protegidas[token] = nome
        codigo_br = re.sub(
            rf'(?<![A-Za-zÀ-ÿ0-9_]){re.escape(nome)}(?![A-Za-zÀ-ÿ0-9_])',
            token,
            codigo_br
        )
    # ═══════════════════════════════════════════════════
    # PASSO 2: Traduzir conteúdo das f-strings
    # ═══════════════════════════════════════════════════
    codigo_br = re.sub(
        r'f(["\'])((?:\\.|(?!\1).)*)\1',
        _traduzir_fstring_rapido,
        codigo_br,
        flags=re.DOTALL
    )
    
    
    # ═══════════════════════════════════════════════════
    # PASSO 3: Proteger strings e comentários
    # ═══════════════════════════════════════════════════
    protegido, blocos = _proteger_strings_e_comentarios(codigo_br)
    
    # ═══════════════════════════════════════════════════
    # PASSO 4: Traduzir o resto
    # ═══════════════════════════════════════════════════
    resultado = _aplicar_traducoes_base(protegido)
    
    # ═══════════════════════════════════════════════════
    # PASSO 5: pergunte/pergunta → input
    # ═══════════════════════════════════════════════════
    resultado = re.sub(
        r'(?<![A-Za-zÀ-ÿ0-9_.])(pergunte|pergunta)\s*\(',
        'input(',
        resultado,
        flags=re.IGNORECASE,
    )
    
    # ═══════════════════════════════════════════════════
    # PASSO 6: Restaurar strings
    # ═══════════════════════════════════════════════════
    resultado = restaurar_strings(resultado, blocos)
    
    # ═══════════════════════════════════════════════════
    # PASSO 7: Restaurar variáveis
    # ═══════════════════════════════════════════════════
    for token, nome in variaveis_protegidas.items():
        resultado = resultado.replace(token, nome)
    
    return resultado


# ============================================================
# CURSO INTEGRADO — PYRTUGUES
# O conteúdo abaixo fica dentro do próprio .py para funcionar
# offline e sem depender de arquivos externos de aulas.
# ============================================================

DADOS_CURSO = {'edu': [{'modulo': 'Módulo 1 — Fundamentos',
          'titulo': 'O que é programação',
          'descricao': 'Entenda programação, algoritmo e instruções.',
          'conteudo': 'Objetivo: Entenda programação, algoritmo e instruções.\n'
                      '\n'
                      'Programar é transformar um problema em uma sequência de passos que um computador consiga '
                      'executar. Um algoritmo descreve esses passos de forma organizada; Python é a linguagem que '
                      'usaremos para escrever muitos deles.\n'
                      '\n'
                      'Exercício guiado: Escreva três instruções em Pyrtugues para descrever uma tarefa cotidiana.\n'
                      '\n'
                      'Desafio: Transforme a tarefa de preparar um lanche em um algoritmo com pelo menos cinco '
                      'passos.',
          'pyrtugues': 'mostrar("Programação é dar instruções ao computador.")',
          'python': 'print("Programação é dar instruções ao computador.")',
          'explicacao': 'Programar é transformar um problema em uma sequência de passos que um computador consiga '
                        'executar. Um algoritmo descreve esses passos de forma organizada; Python é a linguagem que '
                        'usaremos para escrever muitos deles.',
          'exercicio': 'Escreva três instruções em Pyrtugues para descrever uma tarefa cotidiana.',
          'desafio': 'Transforme a tarefa de preparar um lanche em um algoritmo com pelo menos cinco passos.',
          'dica': 'Pense em cada linha como uma instrução que pode ser executada em ordem.',
          'ordem': 1,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 1 — Fundamentos',
          'titulo': 'Seu primeiro programa',
          'descricao': 'Crie o primeiro programa executável do curso.',
          'conteudo': 'Objetivo: Crie o primeiro programa executável do curso.\n'
                      '\n'
                      'A função mostrar() é a forma do Pyrtugues para chamar print(). Ela envia uma mensagem para a '
                      'saída do programa e é uma das primeiras funções que você usará.\n'
                      '\n'
                      'Exercício guiado: Troque a mensagem por seu nome ou uma frase sobre o que você quer '
                      'aprender.\n'
                      '\n'
                      'Desafio: Mostre três mensagens diferentes, uma em cada linha.',
          'pyrtugues': 'mostrar("Olá, mundo!")',
          'python': 'print("Olá, mundo!")',
          'explicacao': 'A função mostrar() é a forma do Pyrtugues para chamar print(). Ela envia uma mensagem para '
                        'a saída do programa e é uma das primeiras funções que você usará.',
          'exercicio': 'Troque a mensagem por seu nome ou uma frase sobre o que você quer aprender.',
          'desafio': 'Mostre três mensagens diferentes, uma em cada linha.',
          'dica': 'Uma chamada de função normalmente aparece com parênteses.',
          'ordem': 2,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 1 — Fundamentos',
          'titulo': 'Comentários',
          'descricao': 'Aprenda a deixar anotações no código sem executá-las.',
          'conteudo': 'Objetivo: Aprenda a deixar anotações no código sem executá-las.\n'
                      '\n'
                      'Comentários começam com # e são ignorados pelo interpretador. Eles são úteis para explicar '
                      'decisões, lembrar o objetivo de um trecho ou separar partes de um projeto.\n'
                      '\n'
                      'Exercício guiado: Adicione dois comentários ao seu programa anterior.\n'
                      '\n'
                      'Desafio: Escreva um comentário explicando o objetivo de cada linha de um pequeno programa.',
          'pyrtugues': '# Esta linha é um comentário\nmostrar("Código executável")',
          'python': '# Esta linha é um comentário\nprint("Código executável")',
          'explicacao': 'Comentários começam com # e são ignorados pelo interpretador. Eles são úteis para explicar '
                        'decisões, lembrar o objetivo de um trecho ou separar partes de um projeto.',
          'exercicio': 'Adicione dois comentários ao seu programa anterior.',
          'desafio': 'Escreva um comentário explicando o objetivo de cada linha de um pequeno programa.',
          'dica': 'Prefira comentários que expliquem o porquê, não apenas o que já está evidente.',
          'ordem': 3,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 1 — Fundamentos',
          'titulo': 'Indentação e blocos',
          'descricao': 'Veja por que espaços à esquerda fazem parte da sintaxe Python.',
          'conteudo': 'Objetivo: Veja por que espaços à esquerda fazem parte da sintaxe Python.\n'
                      '\n'
                      'Python usa indentação para indicar que uma linha pertence a um bloco. No Pyrtugues, a '
                      'estrutura visual é a mesma: depois dos dois-pontos, as linhas internas recebem indentação.\n'
                      '\n'
                      'Exercício guiado: Crie um if que mostre uma mensagem somente quando uma variável for maior '
                      'que 20.\n'
                      '\n'
                      'Desafio: Faça um bloco dentro de outro bloco e observe como a indentação revela a estrutura.',
          'pyrtugues': 'idade = 15\nse idade maior que 10:\n    mostrar("Pode continuar")',
          'python': 'idade = 15\nif idade > 10:\n    print("Pode continuar")',
          'explicacao': 'Python usa indentação para indicar que uma linha pertence a um bloco. No Pyrtugues, a '
                        'estrutura visual é a mesma: depois dos dois-pontos, as linhas internas recebem indentação.',
          'exercicio': 'Crie um if que mostre uma mensagem somente quando uma variável for maior que 20.',
          'desafio': 'Faça um bloco dentro de outro bloco e observe como a indentação revela a estrutura.',
          'dica': 'Mantenha quatro espaços por nível de indentação.',
          'ordem': 4,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 2 — Variáveis e tipos',
          'titulo': 'Variáveis',
          'descricao': 'Armazene valores em nomes que o programa pode reutilizar.',
          'conteudo': 'Objetivo: Armazene valores em nomes que o programa pode reutilizar.\n'
                      '\n'
                      'Uma variável é um nome associado a um valor. A atribuição usa = e permite guardar dados para '
                      'usar depois em cálculos, condições e funções.\n'
                      '\n'
                      'Exercício guiado: Crie variáveis para nome, idade e cidade e mostre as três.\n'
                      '\n'
                      'Desafio: Crie cinco variáveis diferentes e use todas em uma mesma mensagem.',
          'pyrtugues': 'nome = "Ana"\nidade = 12\nmostrar(nome)\nmostrar(idade)',
          'python': 'nome = "Ana"\nidade = 12\nprint(nome)\nprint(idade)',
          'explicacao': 'Uma variável é um nome associado a um valor. A atribuição usa = e permite guardar dados '
                        'para usar depois em cálculos, condições e funções.',
          'exercicio': 'Crie variáveis para nome, idade e cidade e mostre as três.',
          'desafio': 'Crie cinco variáveis diferentes e use todas em uma mesma mensagem.',
          'dica': 'Escolha nomes que indiquem claramente o que cada variável representa.',
          'ordem': 5,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 2 — Variáveis e tipos',
          'titulo': 'Nomes e atribuição',
          'descricao': 'Aprenda regras e boas práticas para nomear variáveis.',
          'conteudo': 'Objetivo: Aprenda regras e boas práticas para nomear variáveis.\n'
                      '\n'
                      'Nomes de variáveis podem usar letras, números e _, mas não devem começar por número. Em '
                      'Python, nomes são sensíveis a maiúsculas e minúsculas; usar snake_case costuma deixar o '
                      'código mais legível.\n'
                      '\n'
                      'Exercício guiado: Crie três variáveis com nomes descritivos e use-as em uma mensagem.\n'
                      '\n'
                      'Desafio: Renomeie variáveis pouco claras de um exercício anterior para nomes melhores.',
          'pyrtugues': 'nome_aluno = "Lia"\nnota_final = 8\nmostrar(f"{nome_aluno}: {nota_final}")',
          'python': 'nome_aluno = "Lia"\nnota_final = 8\nprint(f"{nome_aluno}: {nota_final}")',
          'explicacao': 'Nomes de variáveis podem usar letras, números e _, mas não devem começar por número. Em '
                        'Python, nomes são sensíveis a maiúsculas e minúsculas; usar snake_case costuma deixar o '
                        'código mais legível.',
          'exercicio': 'Crie três variáveis com nomes descritivos e use-as em uma mensagem.',
          'desafio': 'Renomeie variáveis pouco claras de um exercício anterior para nomes melhores.',
          'dica': 'Evite nomes como x, y e z quando o significado puder ficar mais claro.',
          'ordem': 6,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 2 — Variáveis e tipos',
          'titulo': 'Inteiros e decimais',
          'descricao': 'Diferencie números inteiros e de ponto flutuante.',
          'conteudo': 'Objetivo: Diferencie números inteiros e de ponto flutuante.\n'
                      '\n'
                      'Inteiros representam números sem parte decimal; floats representam valores com casas '
                      'decimais. O tipo interfere no resultado de operações e em como o valor é exibido.\n'
                      '\n'
                      'Exercício guiado: Crie uma quantidade inteira e um preço decimal e calcule o total.\n'
                      '\n'
                      'Desafio: Monte um pequeno cálculo de compra com três itens e um valor decimal.',
          'pyrtugues': 'quantidade = 7\npreco = 12.5\nmostrar(quantidade)\nmostrar(preco)',
          'python': 'quantidade = 7\npreco = 12.5\nprint(quantidade)\nprint(preco)',
          'explicacao': 'Inteiros representam números sem parte decimal; floats representam valores com casas '
                        'decimais. O tipo interfere no resultado de operações e em como o valor é exibido.',
          'exercicio': 'Crie uma quantidade inteira e um preço decimal e calcule o total.',
          'desafio': 'Monte um pequeno cálculo de compra com três itens e um valor decimal.',
          'dica': 'Use nomes de variáveis que indiquem a unidade quando isso ajudar.',
          'ordem': 7,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 2 — Variáveis e tipos',
          'titulo': 'Textos, booleanos e None',
          'descricao': 'Conheça str, bool e None e quando cada um é usado.',
          'conteudo': 'Objetivo: Conheça str, bool e None e quando cada um é usado.\n'
                      '\n'
                      'Textos guardam caracteres, booleanos representam verdadeiro ou falso e None representa '
                      'ausência de valor. Esses tipos aparecem constantemente em condições, cadastros e funções.\n'
                      '\n'
                      'Exercício guiado: Crie um cadastro com nome, ativo e um campo inicialmente sem valor.\n'
                      '\n'
                      'Desafio: Atualize o campo None quando uma condição for atendida.',
          'pyrtugues': 'nome = "Rafa"\n'
                       'ativo = verdadeiro\n'
                       'resultado = nulo\n'
                       'mostrar(nome)\n'
                       'mostrar(ativo)\n'
                       'mostrar(resultado)',
          'python': 'nome = "Rafa"\nativo = True\nresultado = None\nprint(nome)\nprint(ativo)\nprint(resultado)',
          'explicacao': 'Textos guardam caracteres, booleanos representam verdadeiro ou falso e None representa '
                        'ausência de valor. Esses tipos aparecem constantemente em condições, cadastros e funções.',
          'exercicio': 'Crie um cadastro com nome, ativo e um campo inicialmente sem valor.',
          'desafio': 'Atualize o campo None quando uma condição for atendida.',
          'dica': 'Observe que True, False e None são valores, não textos entre aspas.',
          'ordem': 8,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 3 — Entrada e saída',
          'titulo': 'Mostrar resultados com mostrar()',
          'descricao': 'Use a saída para acompanhar o que o programa está fazendo.',
          'conteudo': 'Objetivo: Use a saída para acompanhar o que o programa está fazendo.\n'
                      '\n'
                      'mostrar() aceita vários argumentos e escreve o resultado na saída. Isso permite combinar '
                      'valores sem precisar montar uma única string em todas as situações.\n'
                      '\n'
                      'Exercício guiado: Mostre uma frase com nome, idade e cidade usando três argumentos.\n'
                      '\n'
                      'Desafio: Monte um pequeno recibo com várias linhas de saída.',
          'pyrtugues': 'nome = "Bia"\nmostrar("Olá,", nome)',
          'python': 'nome = "Bia"\nprint("Olá,", nome)',
          'explicacao': 'mostrar() aceita vários argumentos e escreve o resultado na saída. Isso permite combinar '
                        'valores sem precisar montar uma única string em todas as situações.',
          'exercicio': 'Mostre uma frase com nome, idade e cidade usando três argumentos.',
          'desafio': 'Monte um pequeno recibo com várias linhas de saída.',
          'dica': 'Teste diferentes separações entre argumentos.',
          'ordem': 9,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 3 — Entrada e saída',
          'titulo': 'Entrada com pergunte()',
          'descricao': 'Receba texto digitado pelo usuário.',
          'conteudo': 'Objetivo: Receba texto digitado pelo usuário.\n'
                      '\n'
                      'No editor do Pyrtugues, pergunte() é convertido para input(). A resposta recebida é '
                      'inicialmente texto, então cálculos numéricos exigem conversão.\n'
                      '\n'
                      'Exercício guiado: Peça o nome e a cidade do usuário e mostre os dois.\n'
                      '\n'
                      'Desafio: Crie uma apresentação que faça três perguntas antes de mostrar a resposta final.',
          'pyrtugues': 'nome = pergunte("Qual é seu nome? ")\nmostrar(f"Olá, {nome}!")',
          'python': 'nome = input("Qual é seu nome? ")\nprint(f"Olá, {nome}!")',
          'explicacao': 'No editor do Pyrtugues, pergunte() é convertido para input(). A resposta recebida é '
                        'inicialmente texto, então cálculos numéricos exigem conversão.',
          'exercicio': 'Peça o nome e a cidade do usuário e mostre os dois.',
          'desafio': 'Crie uma apresentação que faça três perguntas antes de mostrar a resposta final.',
          'dica': 'Sempre deixe o prompt claro para o usuário.',
          'ordem': 10,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 3 — Entrada e saída',
          'titulo': 'Conversão de entrada',
          'descricao': 'Transforme texto recebido em números e outros tipos.',
          'conteudo': 'Objetivo: Transforme texto recebido em números e outros tipos.\n'
                      '\n'
                      'input() devolve texto. Funções como int() e float() convertem esse texto para tipos numéricos '
                      'quando o conteúdo for válido.\n'
                      '\n'
                      'Exercício guiado: Peça dois números decimais e mostre a soma.\n'
                      '\n'
                      'Desafio: Peça três notas, calcule a média e mostre o resultado.',
          'pyrtugues': 'idade = inteiro(pergunte("Idade: "))\n'
                       'altura = decimal(pergunte("Altura: "))\n'
                       'mostrar(idade + 1)\n'
                       'mostrar(altura)',
          'python': 'idade = int(input("Idade: "))\n'
                    'altura = float(input("Altura: "))\n'
                    'print(idade + 1)\n'
                    'print(altura)',
          'explicacao': 'input() devolve texto. Funções como int() e float() convertem esse texto para tipos '
                        'numéricos quando o conteúdo for válido.',
          'exercicio': 'Peça dois números decimais e mostre a soma.',
          'desafio': 'Peça três notas, calcule a média e mostre o resultado.',
          'dica': 'Uma conversão falha se o texto não puder representar o tipo desejado.',
          'ordem': 11,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 3 — Entrada e saída',
          'titulo': 'F-strings',
          'descricao': 'Monte mensagens usando variáveis dentro de uma string.',
          'conteudo': 'Objetivo: Monte mensagens usando variáveis dentro de uma string.\n'
                      '\n'
                      'F-strings permitem colocar expressões entre chaves dentro de textos. O tradutor do Pyrtugues '
                      'preserva a string e traduz as expressões internas quando necessário.\n'
                      '\n'
                      'Exercício guiado: Crie uma frase com pelo menos quatro variáveis usando uma f-string.\n'
                      '\n'
                      'Desafio: Monte uma mensagem de cadastro em duas linhas usando f-strings.',
          'pyrtugues': 'nome = "Bia"\nidade = 13\nmostrar(f"{nome} tem {idade} anos.")',
          'python': 'nome = "Bia"\nidade = 13\nprint(f"{nome} tem {idade} anos.")',
          'explicacao': 'F-strings permitem colocar expressões entre chaves dentro de textos. O tradutor do '
                        'Pyrtugues preserva a string e traduz as expressões internas quando necessário.',
          'exercicio': 'Crie uma frase com pelo menos quatro variáveis usando uma f-string.',
          'desafio': 'Monte uma mensagem de cadastro em duas linhas usando f-strings.',
          'dica': 'As expressões dentro de { } são avaliadas antes da mensagem ser exibida.',
          'ordem': 12,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 4 — Operadores',
          'titulo': 'Operações matemáticas',
          'descricao': 'Aprenda os operadores aritméticos básicos.',
          'conteudo': 'Objetivo: Aprenda os operadores aritméticos básicos.\n'
                      '\n'
                      'Os operadores aritméticos permitem calcular valores. O Pyrtugues oferece formas como vezes e '
                      'dividido por para tornar certas expressões mais próximas da linguagem natural.\n'
                      '\n'
                      'Exercício guiado: Calcule soma, subtração, multiplicação e divisão de dois números.\n'
                      '\n'
                      'Desafio: Acrescente divisão inteira, resto e potência ao programa.',
          'pyrtugues': 'a = 10\nb = 3\nmostrar(a + b)\nmostrar(a - b)\nmostrar(a vezes b)\nmostrar(a dividido por b)',
          'python': 'a = 10\nb = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)',
          'explicacao': 'Os operadores aritméticos permitem calcular valores. O Pyrtugues oferece formas como vezes '
                        'e dividido por para tornar certas expressões mais próximas da linguagem natural.',
          'exercicio': 'Calcule soma, subtração, multiplicação e divisão de dois números.',
          'desafio': 'Acrescente divisão inteira, resto e potência ao programa.',
          'dica': 'Cuidado com divisão por zero.',
          'ordem': 13,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 4 — Operadores',
          'titulo': 'Comparações',
          'descricao': 'Produza valores booleanos comparando expressões.',
          'conteudo': 'Objetivo: Produza valores booleanos comparando expressões.\n'
                      '\n'
                      'Comparações devolvem True ou False e são a base das decisões. O Pyrtugues aceita formas '
                      'compostas como maior que, menor ou igual e diferente de.\n'
                      '\n'
                      'Exercício guiado: Compare duas notas e descubra qual é maior.\n'
                      '\n'
                      'Desafio: Crie cinco comparações diferentes e mostre os resultados.',
          'pyrtugues': 'idade = 17\n'
                       'mostrar(idade maior que 18)\n'
                       'mostrar(idade menor ou igual a 17)\n'
                       'mostrar(idade igual a 17)\n'
                       'mostrar(idade diferente de 10)',
          'python': 'idade = 17\nprint(idade > 18)\nprint(idade <= 17)\nprint(idade == 17)\nprint(idade != 10)',
          'explicacao': 'Comparações devolvem True ou False e são a base das decisões. O Pyrtugues aceita formas '
                        'compostas como maior que, menor ou igual e diferente de.',
          'exercicio': 'Compare duas notas e descubra qual é maior.',
          'desafio': 'Crie cinco comparações diferentes e mostre os resultados.',
          'dica': 'Confirme sempre se você precisa comparar valores ou atribuir um valor.',
          'ordem': 14,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 4 — Operadores',
          'titulo': 'Operadores lógicos',
          'descricao': 'Combine condições com e, ou e não.',
          'conteudo': 'Objetivo: Combine condições com e, ou e não.\n'
                      '\n'
                      'and exige que as duas condições sejam verdadeiras; or precisa de apenas uma; not inverte um '
                      'booleano. Essas combinações deixam as decisões mais precisas.\n'
                      '\n'
                      'Exercício guiado: Monte uma condição que exija idade mínima e autorização.\n'
                      '\n'
                      'Desafio: Crie um cenário com três condições e use and e or de maneira legível.',
          'pyrtugues': 'idade = 16\n'
                       'tem_autorizacao = verdadeiro\n'
                       'se idade maior que 14 e tem_autorizacao:\n'
                       '    mostrar("Entrada permitida")',
          'python': 'idade = 16\n'
                    'tem_autorizacao = True\n'
                    'if idade > 14 and tem_autorizacao:\n'
                    '    print("Entrada permitida")',
          'explicacao': 'and exige que as duas condições sejam verdadeiras; or precisa de apenas uma; not inverte um '
                        'booleano. Essas combinações deixam as decisões mais precisas.',
          'exercicio': 'Monte uma condição que exija idade mínima e autorização.',
          'desafio': 'Crie um cenário com três condições e use and e or de maneira legível.',
          'dica': 'Separe condições complexas em variáveis quando isso melhorar a leitura.',
          'ordem': 15,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 4 — Operadores',
          'titulo': 'Atribuição composta e precedência',
          'descricao': 'Reduza operações repetidas e entenda a ordem dos cálculos.',
          'conteudo': 'Objetivo: Reduza operações repetidas e entenda a ordem dos cálculos.\n'
                      '\n'
                      'Operadores como += e *= atualizam uma variável usando seu valor anterior. Parênteses podem '
                      'deixar a ordem de avaliação explícita e evitam ambiguidades.\n'
                      '\n'
                      'Exercício guiado: Comece com um saldo e aplique três atualizações.\n'
                      '\n'
                      'Desafio: Combine parênteses e operadores para construir uma fórmula de preço com desconto.',
          'pyrtugues': 'total = 10\ntotal mais igual 5\ntotal vezes igual 2\nmostrar(total)',
          'python': 'total = 10\ntotal += 5\ntotal *= 2\nprint(total)',
          'explicacao': 'Operadores como += e *= atualizam uma variável usando seu valor anterior. Parênteses podem '
                        'deixar a ordem de avaliação explícita e evitam ambiguidades.',
          'exercicio': 'Comece com um saldo e aplique três atualizações.',
          'desafio': 'Combine parênteses e operadores para construir uma fórmula de preço com desconto.',
          'dica': 'Quando a ordem importar, use parênteses em vez de depender da memória da precedência.',
          'ordem': 16,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 5 — Condições',
          'titulo': 'if com se',
          'descricao': 'Execute um bloco somente quando uma condição for verdadeira.',
          'conteudo': 'Objetivo: Execute um bloco somente quando uma condição for verdadeira.\n'
                      '\n'
                      'O bloco iniciado por se é executado quando a condição resulta em verdadeiro. Os dois-pontos '
                      'marcam o começo do bloco indentado.\n'
                      '\n'
                      'Exercício guiado: Crie uma condição para liberar uma ação quando a idade for 16 ou mais.\n'
                      '\n'
                      'Desafio: Faça duas verificações independentes no mesmo programa.',
          'pyrtugues': 'idade = 18\nse idade maior ou igual a 18:\n    mostrar("Maior de idade")',
          'python': 'idade = 18\nif idade >= 18:\n    print("Maior de idade")',
          'explicacao': 'O bloco iniciado por se é executado quando a condição resulta em verdadeiro. Os dois-pontos '
                        'marcam o começo do bloco indentado.',
          'exercicio': 'Crie uma condição para liberar uma ação quando a idade for 16 ou mais.',
          'desafio': 'Faça duas verificações independentes no mesmo programa.',
          'dica': 'Leia a condição como uma frase antes de codificá-la.',
          'ordem': 17,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 5 — Condições',
          'titulo': 'Múltiplos caminhos com senão_se',
          'descricao': 'Escolha entre várias faixas de uma mesma decisão.',
          'conteudo': 'Objetivo: Escolha entre várias faixas de uma mesma decisão.\n'
                      '\n'
                      'senão_se representa elif. O Python testa as condições em ordem e para no primeiro bloco '
                      'verdadeiro.\n'
                      '\n'
                      'Exercício guiado: Classifique uma nota em quatro faixas.\n'
                      '\n'
                      'Desafio: Crie uma classificação que trate também notas abaixo de 5.',
          'pyrtugues': 'nota = 8\n'
                       'se nota maior ou igual a 9:\n'
                       '    mostrar("Excelente")\n'
                       'senão_se nota maior ou igual a 7:\n'
                       '    mostrar("Bom")\n'
                       'senão_se nota maior ou igual a 5:\n'
                       '    mostrar("Recuperação")',
          'python': 'nota = 8\n'
                    'if nota >= 9:\n'
                    '    print("Excelente")\n'
                    'elif nota >= 7:\n'
                    '    print("Bom")\n'
                    'elif nota >= 5:\n'
                    '    print("Recuperação")',
          'explicacao': 'senão_se representa elif. O Python testa as condições em ordem e para no primeiro bloco '
                        'verdadeiro.',
          'exercicio': 'Classifique uma nota em quatro faixas.',
          'desafio': 'Crie uma classificação que trate também notas abaixo de 5.',
          'dica': 'Organize as condições da faixa mais específica para a mais geral.',
          'ordem': 18,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 5 — Condições',
          'titulo': 'Alternativa com senão',
          'descricao': 'Defina o caminho quando nenhuma condição anterior for verdadeira.',
          'conteudo': 'Objetivo: Defina o caminho quando nenhuma condição anterior for verdadeira.\n'
                      '\n'
                      'senão representa else e funciona como o caminho alternativo da decisão. Ele só é executado se '
                      'o bloco anterior não tiver sido escolhido.\n'
                      '\n'
                      'Exercício guiado: Crie uma verificação de senha correta ou incorreta.\n'
                      '\n'
                      'Desafio: Combine se, senão_se e senão em uma decisão completa.',
          'pyrtugues': 'saldo = 20\n'
                       'se saldo maior ou igual a 50:\n'
                       '    mostrar("Compra liberada")\n'
                       'senão:\n'
                       '    mostrar("Saldo insuficiente")',
          'python': 'saldo = 20\n'
                    'if saldo >= 50:\n'
                    '    print("Compra liberada")\n'
                    'else:\n'
                    '    print("Saldo insuficiente")',
          'explicacao': 'senão representa else e funciona como o caminho alternativo da decisão. Ele só é executado '
                        'se o bloco anterior não tiver sido escolhido.',
          'exercicio': 'Crie uma verificação de senha correta ou incorreta.',
          'desafio': 'Combine se, senão_se e senão em uma decisão completa.',
          'dica': 'Deixe o caso padrão claro para quem ler o código.',
          'ordem': 19,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 5 — Condições',
          'titulo': 'Condições aninhadas',
          'descricao': 'Coloque uma decisão dentro de outra quando os critérios dependem entre si.',
          'conteudo': 'Objetivo: Coloque uma decisão dentro de outra quando os critérios dependem entre si.\n'
                      '\n'
                      'Condições aninhadas são úteis quando uma decisão só faz sentido depois que outra foi '
                      'atendida. Porém, muitos níveis podem deixar o código difícil de ler.\n'
                      '\n'
                      'Exercício guiado: Faça uma verificação de login e depois uma verificação de permissão.\n'
                      '\n'
                      'Desafio: Refatore uma condição muito aninhada usando uma expressão lógica única.',
          'pyrtugues': 'idade = 20\n'
                       'tem_ingresso = verdadeiro\n'
                       'se idade maior ou igual a 18:\n'
                       '    se tem_ingresso:\n'
                       '        mostrar("Pode entrar")\n'
                       '    senão:\n'
                       '        mostrar("Compre um ingresso")\n'
                       'senão:\n'
                       '    mostrar("Entrada restrita")',
          'python': 'idade = 20\n'
                    'tem_ingresso = True\n'
                    'if idade >= 18:\n'
                    '    if tem_ingresso:\n'
                    '        print("Pode entrar")\n'
                    '    else:\n'
                    '        print("Compre um ingresso")\n'
                    'else:\n'
                    '    print("Entrada restrita")',
          'explicacao': 'Condições aninhadas são úteis quando uma decisão só faz sentido depois que outra foi '
                        'atendida. Porém, muitos níveis podem deixar o código difícil de ler.',
          'exercicio': 'Faça uma verificação de login e depois uma verificação de permissão.',
          'desafio': 'Refatore uma condição muito aninhada usando uma expressão lógica única.',
          'dica': 'Antes de aninhar, veja se and ou or resolvem o problema com menos níveis.',
          'ordem': 20,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 6 — Repetição',
          'titulo': 'for e intervalos',
          'descricao': 'Repita um bloco usando um conjunto conhecido de passos.',
          'conteudo': 'Objetivo: Repita um bloco usando um conjunto conhecido de passos.\n'
                      '\n'
                      'for percorre valores de uma sequência ou iterável. intervalo() corresponde a range() e é '
                      'muito útil para repetir uma ação um número conhecido de vezes.\n'
                      '\n'
                      'Exercício guiado: Mostre os números de 1 a 10.\n'
                      '\n'
                      'Desafio: Mostre somente os números pares de 0 a 20.',
          'pyrtugues': 'para i em intervalo(1, 6):\n    mostrar(i)',
          'python': 'for i in range(1, 6):\n    print(i)',
          'explicacao': 'for percorre valores de uma sequência ou iterável. intervalo() corresponde a range() e é '
                        'muito útil para repetir uma ação um número conhecido de vezes.',
          'exercicio': 'Mostre os números de 1 a 10.',
          'desafio': 'Mostre somente os números pares de 0 a 20.',
          'dica': 'Lembre que o segundo limite de range() não é incluído.',
          'ordem': 21,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 6 — Repetição',
          'titulo': 'while com enquanto',
          'descricao': 'Repita enquanto uma condição continuar verdadeira.',
          'conteudo': 'Objetivo: Repita enquanto uma condição continuar verdadeira.\n'
                      '\n'
                      'while continua executando enquanto a condição for verdadeira. É essencial atualizar alguma '
                      'variável de controle para evitar um laço infinito quando esse controle depender do loop.\n'
                      '\n'
                      'Exercício guiado: Conte de 5 até 1.\n'
                      '\n'
                      'Desafio: Crie um menu que continue aparecendo até o usuário escolher sair.',
          'pyrtugues': 'contador = 1\n'
                       'enquanto contador menor ou igual a 5:\n'
                       '    mostrar(contador)\n'
                       '    contador mais igual 1',
          'python': 'contador = 1\nwhile contador <= 5:\n    print(contador)\n    contador += 1',
          'explicacao': 'while continua executando enquanto a condição for verdadeira. É essencial atualizar alguma '
                        'variável de controle para evitar um laço infinito quando esse controle depender do loop.',
          'exercicio': 'Conte de 5 até 1.',
          'desafio': 'Crie um menu que continue aparecendo até o usuário escolher sair.',
          'dica': 'Teste mentalmente como a variável de controle muda a cada volta.',
          'ordem': 22,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 6 — Repetição',
          'titulo': 'quebrar, continuar e passar',
          'descricao': 'Controle o fluxo de um laço em situações específicas.',
          'conteudo': 'Objetivo: Controle o fluxo de um laço em situações específicas.\n'
                      '\n'
                      'quebrar interrompe o laço; continuar pula para a próxima iteração; passar não faz nada e '
                      'serve como marcador temporário de bloco.\n'
                      '\n'
                      'Exercício guiado: Faça um loop que ignore um número e pare em outro.\n'
                      '\n'
                      'Desafio: Use passar em um bloco ainda não implementado e depois substitua pelo comportamento '
                      'real.',
          'pyrtugues': 'para i em intervalo(1, 8):\n'
                       '    se i igual a 4:\n'
                       '        continuar\n'
                       '    se i igual a 7:\n'
                       '        quebrar\n'
                       '    mostrar(i)',
          'python': 'for i in range(1, 8):\n'
                    '    if i == 4:\n'
                    '        continue\n'
                    '    if i == 7:\n'
                    '        break\n'
                    '    print(i)',
          'explicacao': 'quebrar interrompe o laço; continuar pula para a próxima iteração; passar não faz nada e '
                        'serve como marcador temporário de bloco.',
          'exercicio': 'Faça um loop que ignore um número e pare em outro.',
          'desafio': 'Use passar em um bloco ainda não implementado e depois substitua pelo comportamento real.',
          'dica': 'Use break e continue com moderação para manter a lógica fácil de acompanhar.',
          'ordem': 23,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 6 — Repetição',
          'titulo': 'Contadores e acumuladores',
          'descricao': 'Use variáveis que acumulam informações durante um laço.',
          'conteudo': 'Objetivo: Use variáveis que acumulam informações durante um laço.\n'
                      '\n'
                      'Um acumulador começa com um valor inicial e recebe novos valores a cada repetição. Um '
                      'contador é um caso simples desse padrão e costuma começar em zero ou um.\n'
                      '\n'
                      'Exercício guiado: Calcule a soma de 1 a 100.\n'
                      '\n'
                      'Desafio: Conte quantos números entre 1 e 100 são divisíveis por 3.',
          'pyrtugues': 'soma = 0\npara numero em intervalo(1, 6):\n    soma mais igual numero\nmostrar(soma)',
          'python': 'soma = 0\nfor numero in range(1, 6):\n    soma += numero\nprint(soma)',
          'explicacao': 'Um acumulador começa com um valor inicial e recebe novos valores a cada repetição. Um '
                        'contador é um caso simples desse padrão e costuma começar em zero ou um.',
          'exercicio': 'Calcule a soma de 1 a 100.',
          'desafio': 'Conte quantos números entre 1 e 100 são divisíveis por 3.',
          'dica': 'Escolha a inicialização correta antes de iniciar o laço.',
          'ordem': 24,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 7 — Textos',
          'titulo': 'Índices de strings',
          'descricao': 'Acesse caracteres específicos de um texto.',
          'conteudo': 'Objetivo: Acesse caracteres específicos de um texto.\n'
                      '\n'
                      'Strings são sequências e podem ser acessadas por índice. O primeiro caractere está na posição '
                      '0 e índices negativos contam a partir do final.\n'
                      '\n'
                      'Exercício guiado: Mostre a primeira e a última letra de uma palavra.\n'
                      '\n'
                      'Desafio: Monte uma verificação que compare a primeira letra de uma palavra com outra.',
          'pyrtugues': 'texto = "PYRTUGUES"\nmostrar(texto[0])\nmostrar(texto[-1])',
          'python': 'texto = "PYRTUGUES"\nprint(texto[0])\nprint(texto[-1])',
          'explicacao': 'Strings são sequências e podem ser acessadas por índice. O primeiro caractere está na '
                        'posição 0 e índices negativos contam a partir do final.',
          'exercicio': 'Mostre a primeira e a última letra de uma palavra.',
          'desafio': 'Monte uma verificação que compare a primeira letra de uma palavra com outra.',
          'dica': 'Lembre que o maior índice válido depende do tamanho da string.',
          'ordem': 25,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 7 — Textos',
          'titulo': 'Fatiamento de textos',
          'descricao': 'Extraia partes de uma string usando slicing.',
          'conteudo': 'Objetivo: Extraia partes de uma string usando slicing.\n'
                      '\n'
                      'O slicing usa início e fim, mas o índice final não entra no trecho. Ele é útil para extrair '
                      'prefixos, sufixos e partes estruturadas de uma string.\n'
                      '\n'
                      'Exercício guiado: Extraia os três primeiros caracteres de uma palavra.\n'
                      '\n'
                      'Desafio: Pegue o domínio ou parte final de um endereço de texto simples.',
          'pyrtugues': 'texto = "Python em português"\nmostrar(texto[0:6])\nmostrar(texto[7:9])',
          'python': 'texto = "Python em português"\nprint(texto[0:6])\nprint(texto[7:9])',
          'explicacao': 'O slicing usa início e fim, mas o índice final não entra no trecho. Ele é útil para extrair '
                        'prefixos, sufixos e partes estruturadas de uma string.',
          'exercicio': 'Extraia os três primeiros caracteres de uma palavra.',
          'desafio': 'Pegue o domínio ou parte final de um endereço de texto simples.',
          'dica': 'Experimente também índices negativos para entender os limites.',
          'ordem': 26,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 7 — Textos',
          'titulo': 'Métodos de texto',
          'descricao': 'Use métodos para transformar e testar strings.',
          'conteudo': 'Objetivo: Use métodos para transformar e testar strings.\n'
                      '\n'
                      'Métodos são funções associadas a um objeto e chamadas depois de um ponto. O tradutor possui '
                      'um conjunto de métodos em português, como maiúsculas(), minúsculas() e capitalizar().\n'
                      '\n'
                      'Exercício guiado: Normalize um nome para começar com letra maiúscula.\n'
                      '\n'
                      'Desafio: Crie um pequeno formatador de títulos para três textos.',
          'pyrtugues': 'texto = "python"\n'
                       'mostrar(texto.maiúsculas())\n'
                       'mostrar(texto.minúsculas())\n'
                       'mostrar(texto.capitalizar())',
          'python': 'texto = "python"\nprint(texto.upper())\nprint(texto.lower())\nprint(texto.capitalize())',
          'explicacao': 'Métodos são funções associadas a um objeto e chamadas depois de um ponto. O tradutor possui '
                        'um conjunto de métodos em português, como maiúsculas(), minúsculas() e capitalizar().',
          'exercicio': 'Normalize um nome para começar com letra maiúscula.',
          'desafio': 'Crie um pequeno formatador de títulos para três textos.',
          'dica': 'Métodos de string geralmente devolvem um novo texto em vez de alterar o original.',
          'ordem': 27,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 7 — Textos',
          'titulo': 'Buscar, substituir, dividir e juntar',
          'descricao': 'Trabalhe com conteúdo textual mais estruturado.',
          'conteudo': 'Objetivo: Trabalhe com conteúdo textual mais estruturado.\n'
                      '\n'
                      'split() quebra um texto em partes; join() une uma coleção com um separador; find() procura '
                      'uma posição; replace() troca ocorrências. Esses métodos são úteis para tratar dados simples.\n'
                      '\n'
                      'Exercício guiado: Separe um texto com nomes usando vírgula e mostre cada parte.\n'
                      '\n'
                      'Desafio: Crie um normalizador que troque uma palavra proibida por outra.',
          'pyrtugues': 'texto = "ana,bruno,carla"\n'
                       'mostrar(texto.dividir(","))\n'
                       'mostrar("-".juntar ["A", "B", "C"])\n'
                       'mostrar(texto.encontrar("bruno"))\n'
                       'mostrar(texto.trocar("carla", "Duda"))',
          'python': 'texto = "ana,bruno,carla"\n'
                    'print(texto.split(","))\n'
                    'print("-".join(["A", "B", "C"]))\n'
                    'print(texto.find("bruno"))\n'
                    'print(texto.replace("carla", "Duda"))',
          'explicacao': 'split() quebra um texto em partes; join() une uma coleção com um separador; find() procura '
                        'uma posição; replace() troca ocorrências. Esses métodos são úteis para tratar dados '
                        'simples.',
          'exercicio': 'Separe um texto com nomes usando vírgula e mostre cada parte.',
          'desafio': 'Crie um normalizador que troque uma palavra proibida por outra.',
          'dica': 'Observe os valores devolvidos por find() quando o trecho não existe.',
          'ordem': 28,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 8 — Listas',
          'titulo': 'Criando e acessando listas',
          'descricao': 'Armazene vários valores em uma única coleção ordenada.',
          'conteudo': 'Objetivo: Armazene vários valores em uma única coleção ordenada.\n'
                      '\n'
                      'Listas mantêm uma sequência de elementos e são mutáveis. Você pode acessar cada posição, '
                      'alterar itens e usar métodos para adicionar ou remover valores.\n'
                      '\n'
                      'Exercício guiado: Crie uma lista com cinco matérias e mostre a terceira.\n'
                      '\n'
                      'Desafio: Monte uma lista de compras e altere um item depois de criá-la.',
          'pyrtugues': 'frutas = ["maçã", "banana", "uva"]\nmostrar(frutas)\nmostrar(frutas[1])',
          'python': 'frutas = ["maçã", "banana", "uva"]\nprint(frutas)\nprint(frutas[1])',
          'explicacao': 'Listas mantêm uma sequência de elementos e são mutáveis. Você pode acessar cada posição, '
                        'alterar itens e usar métodos para adicionar ou remover valores.',
          'exercicio': 'Crie uma lista com cinco matérias e mostre a terceira.',
          'desafio': 'Monte uma lista de compras e altere um item depois de criá-la.',
          'dica': 'Índices de listas também começam em zero.',
          'ordem': 29,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 8 — Listas',
          'titulo': 'Alterando elementos',
          'descricao': 'Troque valores de uma lista por índice.',
          'conteudo': 'Objetivo: Troque valores de uma lista por índice.\n'
                      '\n'
                      'Como listas são mutáveis, uma posição pode receber um novo valor. Isso permite atualizar '
                      'dados sem recriar toda a lista.\n'
                      '\n'
                      'Exercício guiado: Crie uma lista de notas e corrija uma delas.\n'
                      '\n'
                      'Desafio: Implemente uma atualização de estoque alterando a quantidade de um item em uma '
                      'posição conhecida.',
          'pyrtugues': 'cores = ["azul", "verde", "vermelho"]\ncores[1] = "amarelo"\nmostrar(cores)',
          'python': 'cores = ["azul", "verde", "vermelho"]\ncores[1] = "amarelo"\nprint(cores)',
          'explicacao': 'Como listas são mutáveis, uma posição pode receber um novo valor. Isso permite atualizar '
                        'dados sem recriar toda a lista.',
          'exercicio': 'Crie uma lista de notas e corrija uma delas.',
          'desafio': 'Implemente uma atualização de estoque alterando a quantidade de um item em uma posição '
                     'conhecida.',
          'dica': 'Tenha cuidado para não usar um índice que não existe.',
          'ordem': 30,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 8 — Listas',
          'titulo': 'append e extend',
          'descricao': 'Adicione um ou vários elementos ao final de uma lista.',
          'conteudo': 'Objetivo: Adicione um ou vários elementos ao final de uma lista.\n'
                      '\n'
                      'append() adiciona um elemento; extend() acrescenta os elementos de outra coleção. No '
                      'tradutor, os métodos são escritos como adicionar() e estender().\n'
                      '\n'
                      'Exercício guiado: Comece com uma lista vazia e adicione cinco nomes.\n'
                      '\n'
                      'Desafio: Monte duas listas e una o conteúdo usando extend().',
          'pyrtugues': 'numeros = [1, 2]\nnumeros.adicionar(3)\nnumeros.estender([4, 5])\nmostrar(numeros)',
          'python': 'numeros = [1, 2]\nnumeros.append(3)\nnumeros.extend([4, 5])\nprint(numeros)',
          'explicacao': 'append() adiciona um elemento; extend() acrescenta os elementos de outra coleção. No '
                        'tradutor, os métodos são escritos como adicionar() e estender().',
          'exercicio': 'Comece com uma lista vazia e adicione cinco nomes.',
          'desafio': 'Monte duas listas e una o conteúdo usando extend().',
          'dica': 'append adiciona um único objeto; extend percorre outra coleção.',
          'ordem': 31,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 8 — Listas',
          'titulo': 'insert, remove, pop, sort e reverse',
          'descricao': 'Use métodos comuns para organizar e editar listas.',
          'conteudo': 'Objetivo: Use métodos comuns para organizar e editar listas.\n'
                      '\n'
                      'insert() adiciona em uma posição; remove() apaga um valor; pop() remove e devolve um item; '
                      'sort() ordena a própria lista; reverse() inverte a ordem.\n'
                      '\n'
                      'Exercício guiado: Crie uma lista de números, ordene, remova um valor e retire o último.\n'
                      '\n'
                      'Desafio: Faça um pequeno ranking que adicione participantes e ordene o resultado.',
          'pyrtugues': 'numeros = [4, 2, 7, 1]\n'
                       'numeros.inserir(1, 9)\n'
                       'numeros.remover(7)\n'
                       'ultimo = numeros.tirar()\n'
                       'ordenar(numeros)\n'
                       'lista(inverter(numeros))\n'
                       'mostrar(numeros)\n'
                       'mostrar(ultimo)',
          'python': 'numeros = [4, 2, 7, 1]\n'
                    'numeros.insert(1, 9)\n'
                    'numeros.remove(7)\n'
                    'ultimo = numeros.pop()\n'
                    'numeros.sort()\n'
                    'numeros.reverse()\n'
                    'print(numeros)\n'
                    'print(ultimo)',
          'explicacao': 'insert() adiciona em uma posição; remove() apaga um valor; pop() remove e devolve um item; '
                        'sort() ordena a própria lista; reverse() inverte a ordem.',
          'exercicio': 'Crie uma lista de números, ordene, remova um valor e retire o último.',
          'desafio': 'Faça um pequeno ranking que adicione participantes e ordene o resultado.',
          'dica': 'Leia a documentação do método mentalmente: alguns alteram a lista e outros devolvem um valor.',
          'ordem': 32,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 9 — Tuplas',
          'titulo': 'Criando tuplas',
          'descricao': 'Aprenda uma coleção ordenada que não deve ser alterada.',
          'conteudo': 'Objetivo: Aprenda uma coleção ordenada que não deve ser alterada.\n'
                      '\n'
                      'Tuplas são sequências imutáveis. Elas são úteis para representar conjuntos fixos de valores '
                      'que não precisam mudar durante a execução.\n'
                      '\n'
                      'Exercício guiado: Crie uma tupla para representar largura e altura.\n'
                      '\n'
                      'Desafio: Crie uma tupla com dados de um aluno e mostre cada posição.',
          'pyrtugues': 'ponto = (10, 20)\nmostrar(ponto[0])\nmostrar(ponto[1])',
          'python': 'ponto = (10, 20)\nprint(ponto[0])\nprint(ponto[1])',
          'explicacao': 'Tuplas são sequências imutáveis. Elas são úteis para representar conjuntos fixos de valores '
                        'que não precisam mudar durante a execução.',
          'exercicio': 'Crie uma tupla para representar largura e altura.',
          'desafio': 'Crie uma tupla com dados de um aluno e mostre cada posição.',
          'dica': 'Use tuplas quando a imutabilidade fizer sentido para o problema.',
          'ordem': 33,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 9 — Tuplas',
          'titulo': 'Desempacotamento',
          'descricao': 'Distribua os valores de uma tupla em variáveis.',
          'conteudo': 'Objetivo: Distribua os valores de uma tupla em variáveis.\n'
                      '\n'
                      'Desempacotamento permite atribuir várias variáveis em uma única instrução. A quantidade e a '
                      'posição dos nomes precisam combinar com os valores, salvo formas especiais de '
                      'desempacotamento.\n'
                      '\n'
                      'Exercício guiado: Desempacote nome, idade e cidade de uma tupla.\n'
                      '\n'
                      'Desafio: Use *restante em Python para separar parte dos valores e compare com o '
                      'desempacotamento simples.',
          'pyrtugues': 'ponto = (10, 20)\nx, y = ponto\nmostrar(x)\nmostrar(y)',
          'python': 'ponto = (10, 20)\nx, y = ponto\nprint(x)\nprint(y)',
          'explicacao': 'Desempacotamento permite atribuir várias variáveis em uma única instrução. A quantidade e a '
                        'posição dos nomes precisam combinar com os valores, salvo formas especiais de '
                        'desempacotamento.',
          'exercicio': 'Desempacote nome, idade e cidade de uma tupla.',
          'desafio': 'Use *restante em Python para separar parte dos valores e compare com o desempacotamento '
                     'simples.',
          'dica': 'Desempacotamento funciona com outras sequências além de tuplas.',
          'ordem': 34,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 9 — Tuplas',
          'titulo': 'Percorrendo tuplas',
          'descricao': 'Use laços para ler os elementos de uma tupla.',
          'conteudo': 'Objetivo: Use laços para ler os elementos de uma tupla.\n'
                      '\n'
                      'Como tuplas são iteráveis, podem ser percorridas com for. O loop lê cada elemento na ordem em '
                      'que ele foi armazenado.\n'
                      '\n'
                      'Exercício guiado: Mostre todos os meses de um trimestre usando uma tupla.\n'
                      '\n'
                      'Desafio: Combine enumerate() com uma tupla para mostrar posição e valor.',
          'pyrtugues': 'cores = ("azul", "verde", "vermelho")\npara cor em cores:\n    mostrar(cor)',
          'python': 'cores = ("azul", "verde", "vermelho")\nfor cor in cores:\n    print(cor)',
          'explicacao': 'Como tuplas são iteráveis, podem ser percorridas com for. O loop lê cada elemento na ordem '
                        'em que ele foi armazenado.',
          'exercicio': 'Mostre todos os meses de um trimestre usando uma tupla.',
          'desafio': 'Combine enumerate() com uma tupla para mostrar posição e valor.',
          'dica': 'Use enumerar() quando a posição também for necessária.',
          'ordem': 35,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 9 — Tuplas',
          'titulo': 'Lista ou tupla?',
          'descricao': 'Compare mutabilidade, intenção e uso das duas estruturas.',
          'conteudo': 'Objetivo: Compare mutabilidade, intenção e uso das duas estruturas.\n'
                      '\n'
                      'Listas são adequadas para dados que mudam; tuplas são úteis para valores fixos. A escolha '
                      'comunica a intenção do código e pode evitar alterações acidentais.\n'
                      '\n'
                      'Exercício guiado: Converta uma lista de opções em uma tupla fixa.\n'
                      '\n'
                      'Desafio: Escolha estrutura para cinco cenários diferentes e explique a decisão.',
          'pyrtugues': 'nomes = ["Ana", "Bia"]\n'
                       'coordenadas = (10, 20)\n'
                       'nomes[0] = "Lia"\n'
                       'mostrar(nomes)\n'
                       'mostrar(coordenadas)',
          'python': 'nomes = ["Ana", "Bia"]\n'
                    'coordenadas = (10, 20)\n'
                    'nomes[0] = "Lia"\n'
                    'print(nomes)\n'
                    'print(coordenadas)',
          'explicacao': 'Listas são adequadas para dados que mudam; tuplas são úteis para valores fixos. A escolha '
                        'comunica a intenção do código e pode evitar alterações acidentais.',
          'exercicio': 'Converta uma lista de opções em uma tupla fixa.',
          'desafio': 'Escolha estrutura para cinco cenários diferentes e explique a decisão.',
          'dica': 'Pergunte primeiro: esse conjunto de dados precisa mudar?',
          'ordem': 36,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 10 — Conjuntos',
          'titulo': 'Criando conjuntos',
          'descricao': 'Armazene valores únicos sem depender de uma ordem.',
          'conteudo': 'Objetivo: Armazene valores únicos sem depender de uma ordem.\n'
                      '\n'
                      'Sets eliminam duplicatas automaticamente e são úteis para testar pertencimento e fazer '
                      'operações de conjuntos. A ordem de exibição não deve ser tratada como garantida.\n'
                      '\n'
                      'Exercício guiado: Crie um conjunto com números repetidos e observe o resultado.\n'
                      '\n'
                      'Desafio: Use um conjunto para descobrir quantos nomes diferentes aparecem em uma lista.',
          'pyrtugues': 'nomes = {"Ana", "Bia", "Ana"}\nmostrar(nomes)',
          'python': 'nomes = {"Ana", "Bia", "Ana"}\nprint(nomes)',
          'explicacao': 'Sets eliminam duplicatas automaticamente e são úteis para testar pertencimento e fazer '
                        'operações de conjuntos. A ordem de exibição não deve ser tratada como garantida.',
          'exercicio': 'Crie um conjunto com números repetidos e observe o resultado.',
          'desafio': 'Use um conjunto para descobrir quantos nomes diferentes aparecem em uma lista.',
          'dica': 'Não dependa da ordem visual de um set.',
          'ordem': 37,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 10 — Conjuntos',
          'titulo': 'Adicionar e remover elementos',
          'descricao': 'Atualize um conjunto com operações apropriadas.',
          'conteudo': 'Objetivo: Atualize um conjunto com operações apropriadas.\n'
                      '\n'
                      'Conjuntos são mutáveis e podem receber ou perder elementos. O método remove() gera erro se o '
                      'item não existir, então em situações incertas considere verificar antes.\n'
                      '\n'
                      'Exercício guiado: Adicione três elementos e remova um deles.\n'
                      '\n'
                      'Desafio: Crie uma rotina que só remova um item quando ele estiver presente.',
          'pyrtugues': 'itens = {"a", "b"}\nitens.adicionar("c")\nitens.remover("a")\nmostrar(itens)',
          'python': 'itens = {"a", "b"}\nitens.add("c")\nitens.remove("a")\nprint(itens)',
          'explicacao': 'Conjuntos são mutáveis e podem receber ou perder elementos. O método remove() gera erro se '
                        'o item não existir, então em situações incertas considere verificar antes.',
          'exercicio': 'Adicione três elementos e remova um deles.',
          'desafio': 'Crie uma rotina que só remova um item quando ele estiver presente.',
          'dica': 'O operador in é útil para verificar pertencimento antes de remover.',
          'ordem': 38,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 10 — Conjuntos',
          'titulo': 'União e interseção',
          'descricao': 'Combine conjuntos ou descubra elementos em comum.',
          'conteudo': 'Objetivo: Combine conjuntos ou descubra elementos em comum.\n'
                      '\n'
                      'A união reúne valores dos dois conjuntos; a interseção mantém apenas os elementos presentes '
                      'em ambos. Essas operações são úteis para comparar grupos.\n'
                      '\n'
                      'Exercício guiado: Descubra participantes totais e participantes em comum de duas listas '
                      'convertidas em sets.\n'
                      '\n'
                      'Desafio: Adicione também diferença e diferença simétrica ao relatório.',
          'pyrtugues': 'turma_a = {"Ana", "Bia", "Caio"}\n'
                       'turma_b = {"Bia", "Duda", "Caio"}\n'
                       'mostrar(turma_a | turma_b)\n'
                       'mostrar(turma_a & turma_b)',
          'python': 'turma_a = {"Ana", "Bia", "Caio"}\n'
                    'turma_b = {"Bia", "Duda", "Caio"}\n'
                    'print(turma_a | turma_b)\n'
                    'print(turma_a & turma_b)',
          'explicacao': 'A união reúne valores dos dois conjuntos; a interseção mantém apenas os elementos presentes '
                        'em ambos. Essas operações são úteis para comparar grupos.',
          'exercicio': 'Descubra participantes totais e participantes em comum de duas listas convertidas em sets.',
          'desafio': 'Adicione também diferença e diferença simétrica ao relatório.',
          'dica': 'Use a estrutura que representa naturalmente o problema.',
          'ordem': 39,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 10 — Conjuntos',
          'titulo': 'Diferença e pertencimento',
          'descricao': 'Descubra o que existe em um conjunto e não em outro.',
          'conteudo': 'Objetivo: Descubra o que existe em um conjunto e não em outro.\n'
                      '\n'
                      'A diferença mantém elementos que aparecem no primeiro conjunto e não no segundo. O operador '
                      'em testa pertencimento e funciona de forma muito natural com sets.\n'
                      '\n'
                      'Exercício guiado: Descubra quem está inscrito mas ainda não compareceu.\n'
                      '\n'
                      'Desafio: Monte um controle de acesso usando conjunto de usuários autorizados.',
          'pyrtugues': 'presentes = {"Ana", "Bia", "Caio"}\n'
                       'inscritos = {"Ana", "Bia", "Caio", "Duda"}\n'
                       'mostrar(inscritos - presentes)\n'
                       'mostrar("Duda" em inscritos)',
          'python': 'presentes = {"Ana", "Bia", "Caio"}\n'
                    'inscritos = {"Ana", "Bia", "Caio", "Duda"}\n'
                    'print(inscritos - presentes)\n'
                    'print("Duda" in inscritos)',
          'explicacao': 'A diferença mantém elementos que aparecem no primeiro conjunto e não no segundo. O operador '
                        'em testa pertencimento e funciona de forma muito natural com sets.',
          'exercicio': 'Descubra quem está inscrito mas ainda não compareceu.',
          'desafio': 'Monte um controle de acesso usando conjunto de usuários autorizados.',
          'dica': 'Leia a operação como uma frase: inscritos - presentes.',
          'ordem': 40,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 11 — Dicionários',
          'titulo': 'Criando dicionários',
          'descricao': 'Associe chaves a valores.',
          'conteudo': 'Objetivo: Associe chaves a valores.\n'
                      '\n'
                      'Dicionários armazenam pares chave-valor e são ideais para dados nomeados. As chaves precisam '
                      'ser únicas e permitem acessar valores sem depender de posição numérica.\n'
                      '\n'
                      'Exercício guiado: Crie um dicionário para um produto com nome, preço e estoque.\n'
                      '\n'
                      'Desafio: Crie um cadastro com cinco campos diferentes.',
          'pyrtugues': 'aluno = {\n    "nome": "Ana",\n    "idade": 15\n}\nmostrar(aluno["nome"])',
          'python': 'aluno = {\n    "nome": "Ana",\n    "idade": 15\n}\nprint(aluno["nome"])',
          'explicacao': 'Dicionários armazenam pares chave-valor e são ideais para dados nomeados. As chaves '
                        'precisam ser únicas e permitem acessar valores sem depender de posição numérica.',
          'exercicio': 'Crie um dicionário para um produto com nome, preço e estoque.',
          'desafio': 'Crie um cadastro com cinco campos diferentes.',
          'dica': 'Use chaves descritivas e consistentes.',
          'ordem': 41,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 11 — Dicionários',
          'titulo': 'Ler e alterar valores',
          'descricao': 'Atualize campos de um dicionário.',
          'conteudo': 'Objetivo: Atualize campos de um dicionário.\n'
                      '\n'
                      'Atribuir a uma chave existente altera o valor; usar uma chave nova cria um novo par. Isso '
                      'torna dicionários úteis para estados que mudam durante o programa.\n'
                      '\n'
                      'Exercício guiado: Atualize estoque e preço de um produto.\n'
                      '\n'
                      'Desafio: Crie um registro de usuário que receba novos campos ao longo do programa.',
          'pyrtugues': 'aluno = {"nome": "Ana", "nota": 7}\n'
                       'aluno["nota"] = 9\n'
                       'aluno["aprovado"] = verdadeiro\n'
                       'mostrar(aluno)',
          'python': 'aluno = {"nome": "Ana", "nota": 7}\naluno["nota"] = 9\naluno["aprovado"] = True\nprint(aluno)',
          'explicacao': 'Atribuir a uma chave existente altera o valor; usar uma chave nova cria um novo par. Isso '
                        'torna dicionários úteis para estados que mudam durante o programa.',
          'exercicio': 'Atualize estoque e preço de um produto.',
          'desafio': 'Crie um registro de usuário que receba novos campos ao longo do programa.',
          'dica': 'Acesse uma chave pelo nome, não pelo índice.',
          'ordem': 42,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 11 — Dicionários',
          'titulo': 'keys, values, items',
          'descricao': 'Percorra partes diferentes de um dicionário.',
          'conteudo': 'Objetivo: Percorra partes diferentes de um dicionário.\n'
                      '\n'
                      'keys(), values() e items() permitem percorrer chaves, valores ou pares. No Pyrtugues, esses '
                      'métodos são escritos como chaves(), valores() e itens().\n'
                      '\n'
                      'Exercício guiado: Mostre todas as chaves e valores de um cadastro.\n'
                      '\n'
                      'Desafio: Use itens() em um laço para mostrar `chave: valor`.',
          'pyrtugues': 'aluno = {"nome": "Ana", "nota": 9}\n'
                       'mostrar(aluno.chaves())\n'
                       'mostrar(aluno.valores())\n'
                       'mostrar(aluno.itens())',
          'python': 'aluno = {"nome": "Ana", "nota": 9}\n'
                    'print(aluno.keys())\n'
                    'print(aluno.values())\n'
                    'print(aluno.items())',
          'explicacao': 'keys(), values() e items() permitem percorrer chaves, valores ou pares. No Pyrtugues, esses '
                        'métodos são escritos como chaves(), valores() e itens().',
          'exercicio': 'Mostre todas as chaves e valores de um cadastro.',
          'desafio': 'Use itens() em um laço para mostrar `chave: valor`.',
          'dica': 'items() é especialmente útil quando você precisa das duas partes ao mesmo tempo.',
          'ordem': 43,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 11 — Dicionários',
          'titulo': 'get e update',
          'descricao': 'Acesse dados opcionais e atualize vários campos.',
          'conteudo': 'Objetivo: Acesse dados opcionais e atualize vários campos.\n'
                      '\n'
                      'get() permite buscar uma chave sem causar erro quando ela não existe; update() incorpora '
                      'vários pares de uma vez. Esses métodos tornam atualizações mais seguras e compactas.\n'
                      '\n'
                      'Exercício guiado: Busque uma chave opcional de um cadastro usando get().\n'
                      '\n'
                      'Desafio: Atualize várias configurações de uma vez e mostre o resultado.',
          'pyrtugues': 'config = {"tema": "escuro"}\n'
                       'mostrar(config.pegar("idioma"))\n'
                       'config.atualizar({"idioma": "pt-BR", "fonte": 14})\n'
                       'mostrar(config)',
          'python': 'config = {"tema": "escuro"}\n'
                    'print(config.get("idioma"))\n'
                    'config.update({"idioma": "pt-BR", "fonte": 14})\n'
                    'print(config)',
          'explicacao': 'get() permite buscar uma chave sem causar erro quando ela não existe; update() incorpora '
                        'vários pares de uma vez. Esses métodos tornam atualizações mais seguras e compactas.',
          'exercicio': 'Busque uma chave opcional de um cadastro usando get().',
          'desafio': 'Atualize várias configurações de uma vez e mostre o resultado.',
          'dica': 'Escolha um valor padrão ao usar get quando isso fizer sentido.',
          'ordem': 44,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 11 — Dicionários',
          'titulo': 'Percorrendo dicionários',
          'descricao': 'Combine for com chaves e valores para processar registros.',
          'conteudo': 'Objetivo: Combine for com chaves e valores para processar registros.\n'
                      '\n'
                      'Percorrer um dicionário diretamente produz suas chaves. A partir da chave, você pode obter o '
                      'valor e construir relatórios ou cálculos.\n'
                      '\n'
                      'Exercício guiado: Some os valores de um dicionário de preços.\n'
                      '\n'
                      'Desafio: Mostre apenas os itens com preço acima de 3.',
          'pyrtugues': 'precos = {"maçã": 3.5, "banana": 2.0}\npara nome em precos:\n    mostrar(nome, precos[nome])',
          'python': 'precos = {"maçã": 3.5, "banana": 2.0}\nfor nome in precos:\n    print(nome, precos[nome])',
          'explicacao': 'Percorrer um dicionário diretamente produz suas chaves. A partir da chave, você pode obter '
                        'o valor e construir relatórios ou cálculos.',
          'exercicio': 'Some os valores de um dicionário de preços.',
          'desafio': 'Mostre apenas os itens com preço acima de 3.',
          'dica': 'Quando precisar de chave e valor juntos, considere items().',
          'ordem': 45,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 12 — Funções',
          'titulo': 'Criando funções',
          'descricao': 'Encapsule uma tarefa em uma função reutilizável.',
          'conteudo': 'Objetivo: Encapsule uma tarefa em uma função reutilizável.\n'
                      '\n'
                      'Uma função agrupa instruções sob um nome. Definí-la não executa seu corpo; a execução '
                      'acontece quando ela é chamada.\n'
                      '\n'
                      'Exercício guiado: Crie uma função que mostre uma mensagem de boas-vindas.\n'
                      '\n'
                      'Desafio: Faça três funções pequenas para organizar um programa maior.',
          'pyrtugues': 'função saudar():\n    mostrar("Olá!")\n\nsaudar()',
          'python': 'def saudar():\n    print("Olá!")\n\nsaudar()',
          'explicacao': 'Uma função agrupa instruções sob um nome. Definí-la não executa seu corpo; a execução '
                        'acontece quando ela é chamada.',
          'exercicio': 'Crie uma função que mostre uma mensagem de boas-vindas.',
          'desafio': 'Faça três funções pequenas para organizar um programa maior.',
          'dica': 'Nomeie funções com verbos que indiquem ação.',
          'ordem': 46,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 12 — Funções',
          'titulo': 'Parâmetros e argumentos',
          'descricao': 'Passe dados para uma função.',
          'conteudo': 'Objetivo: Passe dados para uma função.\n'
                      '\n'
                      'Parâmetros são os nomes definidos na função; argumentos são os valores enviados na chamada. '
                      'Essa separação permite reutilizar a mesma lógica com dados diferentes.\n'
                      '\n'
                      'Exercício guiado: Crie uma função que receba nome e cidade.\n'
                      '\n'
                      'Desafio: Faça uma função que receba três números e mostre o maior.',
          'pyrtugues': 'função saudar(nome):\n    mostrar(f"Olá, {nome}!")\n\nsaudar("Pyrtugues")',
          'python': 'def saudar(nome):\n    print(f"Olá, {nome}!")\n\nsaudar("Pyrtugues")',
          'explicacao': 'Parâmetros são os nomes definidos na função; argumentos são os valores enviados na chamada. '
                        'Essa separação permite reutilizar a mesma lógica com dados diferentes.',
          'exercicio': 'Crie uma função que receba nome e cidade.',
          'desafio': 'Faça uma função que receba três números e mostre o maior.',
          'dica': 'Use parâmetros para evitar copiar a mesma lógica.',
          'ordem': 47,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 12 — Funções',
          'titulo': 'Retorno',
          'descricao': 'Faça uma função devolver um resultado com retornar.',
          'conteudo': 'Objetivo: Faça uma função devolver um resultado com retornar.\n'
                      '\n'
                      'return encerra a execução da função e devolve um valor para quem chamou. Isso permite '
                      'construir programas em camadas, em que uma função calcula e outra decide o que fazer com o '
                      'resultado.\n'
                      '\n'
                      'Exercício guiado: Crie funções para calcular área e perímetro de um retângulo.\n'
                      '\n'
                      'Desafio: Combine duas funções, fazendo a segunda receber o retorno da primeira.',
          'pyrtugues': 'função somar(a, b):\n    retornar a + b\n\nresultado = somar(4, 5)\nmostrar(resultado)',
          'python': 'def somar(a, b):\n    return a + b\n\nresultado = somar(4, 5)\nprint(resultado)',
          'explicacao': 'return encerra a execução da função e devolve um valor para quem chamou. Isso permite '
                        'construir programas em camadas, em que uma função calcula e outra decide o que fazer com o '
                        'resultado.',
          'exercicio': 'Crie funções para calcular área e perímetro de um retângulo.',
          'desafio': 'Combine duas funções, fazendo a segunda receber o retorno da primeira.',
          'dica': 'Diferencie mostrar na tela de retornar um valor.',
          'ordem': 48,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 12 — Funções',
          'titulo': 'Escopo e reutilização',
          'descricao': 'Entenda a diferença entre variáveis locais e o restante do programa.',
          'conteudo': 'Objetivo: Entenda a diferença entre variáveis locais e o restante do programa.\n'
                      '\n'
                      'Uma variável criada dentro de uma função normalmente pertence ao escopo local daquela função. '
                      'Manter dados locais reduz interferências e torna funções mais previsíveis.\n'
                      '\n'
                      'Exercício guiado: Crie uma função com uma variável local e outra global ao módulo.\n'
                      '\n'
                      'Desafio: Experimente retornar um valor em vez de depender de uma variável global.',
          'pyrtugues': 'definir = 0\n'
                       'função criar():\n'
                       '    mensagem = "local"\n'
                       '    mostrar(mensagem)\n'
                       '\n'
                       'criar()\n'
                       'mostrar(definir)',
          'python': 'definir = 0\n'
                    'def criar():\n'
                    '    mensagem = "local"\n'
                    '    print(mensagem)\n'
                    '\n'
                    'criar()\n'
                    'print(definir)',
          'explicacao': 'Uma variável criada dentro de uma função normalmente pertence ao escopo local daquela '
                        'função. Manter dados locais reduz interferências e torna funções mais previsíveis.',
          'exercicio': 'Crie uma função com uma variável local e outra global ao módulo.',
          'desafio': 'Experimente retornar um valor em vez de depender de uma variável global.',
          'dica': 'Prefira passar parâmetros e usar retorno em vez de espalhar estado global.',
          'ordem': 49,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 13 — Erros e exceções',
          'titulo': 'Erros de sintaxe, execução e lógica',
          'descricao': 'Aprenda a diferenciar tipos de problemas.',
          'conteudo': 'Objetivo: Aprenda a diferenciar tipos de problemas.\n'
                      '\n'
                      'Erros de sintaxe impedem o Python de entender o código; erros de execução acontecem durante o '
                      'programa; erros lógicos fazem o programa rodar com resultado errado. Saber qual tipo ocorreu '
                      'ajuda a escolher a correção.\n'
                      '\n'
                      'Exercício guiado: Liste um exemplo de cada tipo de erro.\n'
                      '\n'
                      'Desafio: Pegue um pequeno programa que produz resultado errado e descubra por quê.',
          'pyrtugues': 'mostrar("Começo")\n'
                       '# Exemplo conceitual de erro lógico:\n'
                       'resultado = 2 + 2\n'
                       'mostrar(resultado)',
          'python': 'print("Começo")\n# Exemplo conceitual de erro lógico:\nresultado = 2 + 2\nprint(resultado)',
          'explicacao': 'Erros de sintaxe impedem o Python de entender o código; erros de execução acontecem durante '
                        'o programa; erros lógicos fazem o programa rodar com resultado errado. Saber qual tipo '
                        'ocorreu ajuda a escolher a correção.',
          'exercicio': 'Liste um exemplo de cada tipo de erro.',
          'desafio': 'Pegue um pequeno programa que produz resultado errado e descubra por quê.',
          'dica': 'Leia a mensagem de erro antes de começar a mudar várias linhas.',
          'ordem': 50,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 13 — Erros e exceções',
          'titulo': 'try e except',
          'descricao': 'Trate uma falha previsível sem encerrar todo o programa.',
          'conteudo': 'Objetivo: Trate uma falha previsível sem encerrar todo o programa.\n'
                      '\n'
                      'try abriga o trecho que pode falhar e except define o tratamento para uma exceção específica. '
                      'Capturar apenas os erros esperados costuma deixar o comportamento mais claro.\n'
                      '\n'
                      'Exercício guiado: Trate uma entrada que pode não ser numérica.\n'
                      '\n'
                      'Desafio: Trate dois tipos de erro de entrada com mensagens diferentes.',
          'pyrtugues': 'tentar:\n'
                       '    numero = inteiro(pergunte("Número: "))\n'
                       '    mostrar(numero * 2)\n'
                       'exceto ValueError:\n'
                       '    mostrar("Digite um número válido.")',
          'python': 'try:\n'
                    '    numero = int(input("Número: "))\n'
                    '    print(numero * 2)\n'
                    'except ValueError:\n'
                    '    print("Digite um número válido.")',
          'explicacao': 'try abriga o trecho que pode falhar e except define o tratamento para uma exceção '
                        'específica. Capturar apenas os erros esperados costuma deixar o comportamento mais claro.',
          'exercicio': 'Trate uma entrada que pode não ser numérica.',
          'desafio': 'Trate dois tipos de erro de entrada com mensagens diferentes.',
          'dica': 'Evite capturar Exception sem necessidade em exercícios pequenos.',
          'ordem': 51,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 13 — Erros e exceções',
          'titulo': 'else e finalmente',
          'descricao': 'Entenda os blocos complementares do tratamento de exceções.',
          'conteudo': 'Objetivo: Entenda os blocos complementares do tratamento de exceções.\n'
                      '\n'
                      'else roda quando não houve exceção; finally roda sempre, tenha ocorrido erro ou não. finally '
                      'é útil para garantir que uma etapa de limpeza seja tentada.\n'
                      '\n'
                      'Exercício guiado: Faça um programa que mostre uma mensagem de sucesso no else e uma mensagem '
                      'final no finally.\n'
                      '\n'
                      'Desafio: Use finally para garantir uma mensagem de encerramento mesmo quando houver erro.',
          'pyrtugues': 'tentar:\n'
                       '    numero = inteiro(pergunte("Número: "))\n'
                       'exceto ValueError:\n'
                       '    mostrar("Valor inválido")\n'
                       'senão:\n'
                       '    mostrar(numero * 2)\n'
                       'finalmente:\n'
                       '    mostrar("Fim da tentativa")',
          'python': 'try:\n'
                    '    numero = int(input("Número: "))\n'
                    'except ValueError:\n'
                    '    print("Valor inválido")\n'
                    'else:\n'
                    '    print(numero * 2)\n'
                    'finally:\n'
                    '    print("Fim da tentativa")',
          'explicacao': 'else roda quando não houve exceção; finally roda sempre, tenha ocorrido erro ou não. '
                        'finally é útil para garantir que uma etapa de limpeza seja tentada.',
          'exercicio': 'Faça um programa que mostre uma mensagem de sucesso no else e uma mensagem final no finally.',
          'desafio': 'Use finally para garantir uma mensagem de encerramento mesmo quando houver erro.',
          'dica': 'Pense no fluxo: try → except ou else → finally.',
          'ordem': 52,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 13 — Erros e exceções',
          'titulo': 'levantar e afirmar',
          'descricao': 'Gere e verifique condições de erro de propósito.',
          'conteudo': 'Objetivo: Gere e verifique condições de erro de propósito.\n'
                      '\n'
                      'raise cria uma exceção de forma explícita; assert verifica uma condição que deveria ser '
                      'verdadeira. Os dois recursos ajudam a detectar estados inválidos.\n'
                      '\n'
                      'Exercício guiado: Crie uma função que levante ValueError quando uma idade for negativa.\n'
                      '\n'
                      'Desafio: Adicione asserts a uma função de cálculo para validar resultados importantes.',
          'pyrtugues': 'função dividir(a, b):\n'
                       '    se b igual a 0:\n'
                       '        levantar ValueError("Divisor não pode ser zero")\n'
                       '    retornar a / b\n'
                       '\n'
                       'afirmar dividir(10, 2) == 5',
          'python': 'def dividir(a, b):\n'
                    '    if b == 0:\n'
                    '        raise ValueError("Divisor não pode ser zero")\n'
                    '    return a / b\n'
                    '\n'
                    'assert dividir(10, 2) == 5',
          'explicacao': 'raise cria uma exceção de forma explícita; assert verifica uma condição que deveria ser '
                        'verdadeira. Os dois recursos ajudam a detectar estados inválidos.',
          'exercicio': 'Crie uma função que levante ValueError quando uma idade for negativa.',
          'desafio': 'Adicione asserts a uma função de cálculo para validar resultados importantes.',
          'dica': 'Use assert como verificação de invariantes, não como substituto de validação de entrada do '
                  'usuário.',
          'ordem': 53,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
          'titulo': 'importar',
          'descricao': 'Use código de módulos da biblioteca padrão.',
          'conteudo': 'Objetivo: Use código de módulos da biblioteca padrão.\n'
                      '\n'
                      'importar traz um módulo para o programa. O dicionário do Pyrtugues oferece o nome matemática '
                      'para math, permitindo escrever importações de forma mais natural.\n'
                      '\n'
                      'Exercício guiado: Importe matemática e calcule uma raiz quadrada.\n'
                      '\n'
                      'Desafio: Use duas funções de math no mesmo programa.',
          'pyrtugues': 'importar matemática\nmostrar(matemática.sqrt(25))',
          'python': 'import math\nprint(math.sqrt(25))',
          'explicacao': 'importar traz um módulo para o programa. O dicionário do Pyrtugues oferece o nome '
                        'matemática para math, permitindo escrever importações de forma mais natural.',
          'exercicio': 'Importe matemática e calcule uma raiz quadrada.',
          'desafio': 'Use duas funções de math no mesmo programa.',
          'dica': 'Depois de importar um módulo, os recursos ficam acessíveis pelo nome do módulo.',
          'ordem': 54,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
          'titulo': 'de e como',
          'descricao': 'Controle de onde um recurso é importado e crie aliases.',
          'conteudo': 'Objetivo: Controle de onde um recurso é importado e crie aliases.\n'
                      '\n'
                      'from importa um recurso específico; as cria um nome alternativo. O Pyrtugues usa de e como '
                      'para essas construções.\n'
                      '\n'
                      'Exercício guiado: Importe uma função de math com alias em português.\n'
                      '\n'
                      'Desafio: Crie dois aliases de funções diferentes e compare a leitura do código.',
          'pyrtugues': 'de matemática importar sqrt como raiz\nmostrar(raiz(81))',
          'python': 'from math import sqrt as raiz\nprint(raiz(81))',
          'explicacao': 'from importa um recurso específico; as cria um nome alternativo. O Pyrtugues usa de e como '
                        'para essas construções.',
          'exercicio': 'Importe uma função de math com alias em português.',
          'desafio': 'Crie dois aliases de funções diferentes e compare a leitura do código.',
          'dica': 'Aliases devem tornar o código mais claro, não mais confuso.',
          'ordem': 55,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
          'titulo': 'random, datetime e time',
          'descricao': 'Conheça módulos úteis para programas interativos.',
          'conteudo': 'Objetivo: Conheça módulos úteis para programas interativos.\n'
                      '\n'
                      'random gera valores pseudoaleatórios; datetime trabalha com datas e horários; time fornece '
                      'recursos relacionados a tempo. Esses módulos aparecem em jogos, agendas e programas de '
                      'automação.\n'
                      '\n'
                      'Exercício guiado: Gere um número aleatório e mostre a data atual.\n'
                      '\n'
                      'Desafio: Crie um pequeno jogo que use um número aleatório e uma contagem de tentativas.',
          'pyrtugues': 'importar aleatório\n'
                       'importar datetime\n'
                       'importar tempo\n'
                       '\n'
                       'mostrar(aleatório.randint(1, 10))\n'
                       'mostrar(datetime.datetime.now())',
          'python': 'import random\n'
                    'import datetime\n'
                    'import time\n'
                    '\n'
                    'print(random.randint(1, 10))\n'
                    'print(datetime.datetime.now())',
          'explicacao': 'random gera valores pseudoaleatórios; datetime trabalha com datas e horários; time fornece '
                        'recursos relacionados a tempo. Esses módulos aparecem em jogos, agendas e programas de '
                        'automação.',
          'exercicio': 'Gere um número aleatório e mostre a data atual.',
          'desafio': 'Crie um pequeno jogo que use um número aleatório e uma contagem de tentativas.',
          'dica': 'Use o módulo adequado ao tipo de problema.',
          'ordem': 56,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
          'titulo': 'os e expressões regulares',
          'descricao': 'Conheça recursos básicos para sistema e busca textual.',
          'conteudo': 'Objetivo: Conheça recursos básicos para sistema e busca textual.\n'
                      '\n'
                      'os oferece operações do sistema operacional; re trabalha com expressões regulares. O '
                      'dicionário inclui os módulos e vários recursos, embora nem toda função avançada do tradutor '
                      'tenha um nome contextual.\n'
                      '\n'
                      'Exercício guiado: Mostre o diretório atual e encontre números dentro de um texto.\n'
                      '\n'
                      'Desafio: Crie um verificador simples que encontre padrões de telefone em um texto.',
          'pyrtugues': 'importar sistema\n'
                       'importar re\n'
                       '\n'
                       'mostrar(sistema.getcwd())\n'
                       'padrao = re.compilar(r"\\d+")\n'
                       'mostrar(padrao.findall("A12 B34"))',
          'python': 'import os\n'
                    'import re\n'
                    '\n'
                    'print(os.getcwd())\n'
                    'padrao = re.compile(r"\\d+")\n'
                    'print(padrao.findall("A12 B34"))',
          'explicacao': 'os oferece operações do sistema operacional; re trabalha com expressões regulares. O '
                        'dicionário inclui os módulos e vários recursos, embora nem toda função avançada do tradutor '
                        'tenha um nome contextual.',
          'exercicio': 'Mostre o diretório atual e encontre números dentro de um texto.',
          'desafio': 'Crie um verificador simples que encontre padrões de telefone em um texto.',
          'dica': 'Use regex com padrões pequenos antes de tentar expressões muito complexas.',
          'ordem': 57,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 15 — Projetos EDU',
          'titulo': 'Projeto: calculadora',
          'descricao': 'Combine entrada, conversão, funções e decisões em uma calculadora.',
          'conteudo': 'Objetivo: Combine entrada, conversão, funções e decisões em uma calculadora.\n'
                      '\n'
                      'O objetivo é reunir várias ideias do curso: entrada, conversão, função, condições e exceções. '
                      'Separar o cálculo em uma função deixa o programa mais fácil de testar e ampliar.\n'
                      '\n'
                      'Exercício guiado: Implemente as quatro operações e teste casos normais.\n'
                      '\n'
                      'Desafio: Adicione potência, resto e tratamento para divisão por zero.',
          'pyrtugues': 'função calcular(a, b, operador):\n'
                       '    se operador == "+":\n'
                       '        retornar a + b\n'
                       '    senão se operador == "-":\n'
                       '        retornar a - b\n'
                       '    senão se operador == "*":\n'
                       '        retornar a * b\n'
                       '    senão se operador == "/":\n'
                       '        retornar a / b\n'
                       '    senão:\n'
                       '        levantar ValueError("Operador inválido")\n'
                       '\n'
                       'a = decimal(pergunte("Primeiro: "))\n'
                       'b = decimal(pergunte("Segundo: "))\n'
                       'op = pergunte("Operação (+,-,*,/): ")\n'
                       'mostrar(calcular(a, b, op))',
          'python': 'def calcular(a, b, operador):\n'
                    '    if operador == "+":\n'
                    '        return a + b\n'
                    '    elif operador == "-":\n'
                    '        return a - b\n'
                    '    elif operador == "*":\n'
                    '        return a * b\n'
                    '    elif operador == "/":\n'
                    '        return a / b\n'
                    '    else:\n'
                    '        raise ValueError("Operador inválido")\n'
                    '\n'
                    'a = float(input("Primeiro: "))\n'
                    'b = float(input("Segundo: "))\n'
                    'op = input("Operação (+,-,*,/): ")\n'
                    'print(calcular(a, b, op))',
          'explicacao': 'O objetivo é reunir várias ideias do curso: entrada, conversão, função, condições e '
                        'exceções. Separar o cálculo em uma função deixa o programa mais fácil de testar e ampliar.',
          'exercicio': 'Implemente as quatro operações e teste casos normais.',
          'desafio': 'Adicione potência, resto e tratamento para divisão por zero.',
          'dica': 'Faça primeiro a versão mínima e depois amplie.',
          'ordem': 58,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 15 — Projetos EDU',
          'titulo': 'Projeto: conversor',
          'descricao': 'Transforme valores entre duas unidades usando funções.',
          'conteudo': 'Objetivo: Transforme valores entre duas unidades usando funções.\n'
                      '\n'
                      'Projetos de conversão são excelentes para praticar fórmulas, funções e entrada. A função deve '
                      'receber o valor e devolver o resultado, enquanto a interface cuida das mensagens.\n'
                      '\n'
                      'Exercício guiado: Crie um conversor de quilômetros para milhas.\n'
                      '\n'
                      'Desafio: Permita escolher entre três tipos de conversão.',
          'pyrtugues': 'função c_para_f(celsius):\n'
                       '    retornar celsius * 9 / 5 + 32\n'
                       '\n'
                       'c = decimal(pergunte("Temperatura em C: "))\n'
                       'mostrar(f"{c} C = {c_para_f(c)} F")',
          'python': 'def c_para_f(celsius):\n'
                    '    return celsius * 9 / 5 + 32\n'
                    '\n'
                    'c = float(input("Temperatura em C: "))\n'
                    'print(f"{c} C = {c_para_f(c)} F")',
          'explicacao': 'Projetos de conversão são excelentes para praticar fórmulas, funções e entrada. A função '
                        'deve receber o valor e devolver o resultado, enquanto a interface cuida das mensagens.',
          'exercicio': 'Crie um conversor de quilômetros para milhas.',
          'desafio': 'Permita escolher entre três tipos de conversão.',
          'dica': 'Mantenha a fórmula isolada em funções pequenas.',
          'ordem': 59,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 15 — Projetos EDU',
          'titulo': 'Projeto: quiz',
          'descricao': 'Monte perguntas simples usando listas, condições e pontuação.',
          'conteudo': 'Objetivo: Monte perguntas simples usando listas, condições e pontuação.\n'
                      '\n'
                      'Um quiz usa coleções para guardar perguntas e respostas e um acumulador para contar acertos. '
                      'O mesmo padrão pode crescer para várias perguntas e diferentes regras.\n'
                      '\n'
                      'Exercício guiado: Adicione cinco perguntas e conte os acertos.\n'
                      '\n'
                      'Desafio: Mostre uma mensagem diferente de acordo com a porcentagem de acertos.',
          'pyrtugues': 'perguntas = ["2 + 2 = ?"]\n'
                       'respostas = ["4"]\n'
                       'pontuacao = 0\n'
                       '\n'
                       'para i em intervalo(0, tamanho(perguntas)):\n'
                       '    resposta = pergunte(perguntas[i] + " ")\n'
                       '    se resposta == respostas[i]:\n'
                       '        pontuacao mais igual 1\n'
                       '\n'
                       'mostrar(f"Pontuação: {pontuacao}/{tamanho(perguntas)}")',
          'python': 'perguntas = ["2 + 2 = ?"]\n'
                    'respostas = ["4"]\n'
                    'pontuacao = 0\n'
                    '\n'
                    'for i in range(0, len(perguntas)):\n'
                    '    resposta = input(perguntas[i] + " ")\n'
                    '    if resposta == respostas[i]:\n'
                    '        pontuacao += 1\n'
                    '\n'
                    'print(f"Pontuação: {pontuacao}/{len(perguntas)}")',
          'explicacao': 'Um quiz usa coleções para guardar perguntas e respostas e um acumulador para contar '
                        'acertos. O mesmo padrão pode crescer para várias perguntas e diferentes regras.',
          'exercicio': 'Adicione cinco perguntas e conte os acertos.',
          'desafio': 'Mostre uma mensagem diferente de acordo com a porcentagem de acertos.',
          'dica': 'Separar perguntas e respostas em estruturas paralelas é simples, mas dicionários podem ser usados '
                  'em versões futuras.',
          'ordem': 60,
          'nivel': 'EDU'},
         {'modulo': 'Módulo 15 — Projetos EDU',
          'titulo': 'Projeto: lista de tarefas',
          'descricao': 'Crie uma lista de tarefas e um menu básico.',
          'conteudo': 'Objetivo: Crie uma lista de tarefas e um menu básico.\n'
                      '\n'
                      'Este projeto combina while, if/elif/else, listas e input. Um menu é um padrão importante em '
                      'programas de terminal porque mantém o usuário dentro de um fluxo interativo.\n'
                      '\n'
                      'Exercício guiado: Adicione remoção e marcação de tarefas concluídas.\n'
                      '\n'
                      'Desafio: Transforme cada tarefa em um dicionário com texto e status.',
          'pyrtugues': 'tarefas = []\n'
                       '\n'
                       'enquanto verdadeiro:\n'
                       '    mostrar("1 - adicionar")\n'
                       '    mostrar("2 - listar")\n'
                       '    mostrar("3 - sair")\n'
                       '    opcao = pergunte("Opção: ")\n'
                       '\n'
                       '    se opcao == "1":\n'
                       '        tarefa = pergunte("Tarefa: ")\n'
                       '        tarefas.adicionar(tarefa)\n'
                       '    senão se opcao == "2":\n'
                       '        para tarefa em tarefas:\n'
                       '            mostrar(tarefa)\n'
                       '    senão:\n'
                       '        quebrar\n'
                       '\n'
                       'mostrar("Fim")',
          'python': 'tarefas = []\n'
                    '\n'
                    'while True:\n'
                    '    print("1 - adicionar")\n'
                    '    print("2 - listar")\n'
                    '    print("3 - sair")\n'
                    '    opcao = input("Opção: ")\n'
                    '\n'
                    '    if opcao == "1":\n'
                    '        tarefa = input("Tarefa: ")\n'
                    '        tarefas.append(tarefa)\n'
                    '    elif opcao == "2":\n'
                    '        for tarefa in tarefas:\n'
                    '            print(tarefa)\n'
                    '    else:\n'
                    '        break\n'
                    '\n'
                    'print("Fim")',
          'explicacao': 'Este projeto combina while, if/elif/else, listas e input. Um menu é um padrão importante em '
                        'programas de terminal porque mantém o usuário dentro de um fluxo interativo.',
          'exercicio': 'Adicione remoção e marcação de tarefas concluídas.',
          'desafio': 'Transforme cada tarefa em um dicionário com texto e status.',
          'dica': 'Evite aumentar a complexidade até a versão básica funcionar.',
          'ordem': 61,
          'nivel': 'EDU'}],
 'completo': [{'modulo': 'Módulo 1 — Fundamentos',
               'titulo': 'O que é programação',
               'descricao': 'Entenda programação, algoritmo e instruções.',
               'conteudo': 'Objetivo: Entenda programação, algoritmo e instruções.\n'
                           '\n'
                           'Programar é transformar um problema em uma sequência de passos que um computador consiga '
                           'executar. Um algoritmo descreve esses passos de forma organizada; Python é a linguagem '
                           'que usaremos para escrever muitos deles.\n'
                           '\n'
                           'Exercício guiado: Escreva três instruções em Pyrtugues para descrever uma tarefa '
                           'cotidiana.\n'
                           '\n'
                           'Desafio: Transforme a tarefa de preparar um lanche em um algoritmo com pelo menos cinco '
                           'passos.',
               'pyrtugues': 'mostrar("Programação é dar instruções ao computador.")',
               'python': 'print("Programação é dar instruções ao computador.")',
               'explicacao': 'Programar é transformar um problema em uma sequência de passos que um computador '
                             'consiga executar. Um algoritmo descreve esses passos de forma organizada; Python é a '
                             'linguagem que usaremos para escrever muitos deles.',
               'exercicio': 'Escreva três instruções em Pyrtugues para descrever uma tarefa cotidiana.',
               'desafio': 'Transforme a tarefa de preparar um lanche em um algoritmo com pelo menos cinco passos.',
               'dica': 'Pense em cada linha como uma instrução que pode ser executada em ordem.',
               'ordem': 1,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 1 — Fundamentos',
               'titulo': 'Seu primeiro programa',
               'descricao': 'Crie o primeiro programa executável do curso.',
               'conteudo': 'Objetivo: Crie o primeiro programa executável do curso.\n'
                           '\n'
                           'A função mostrar() é a forma do Pyrtugues para chamar print(). Ela envia uma mensagem '
                           'para a saída do programa e é uma das primeiras funções que você usará.\n'
                           '\n'
                           'Exercício guiado: Troque a mensagem por seu nome ou uma frase sobre o que você quer '
                           'aprender.\n'
                           '\n'
                           'Desafio: Mostre três mensagens diferentes, uma em cada linha.',
               'pyrtugues': 'mostrar("Olá, mundo!")',
               'python': 'print("Olá, mundo!")',
               'explicacao': 'A função mostrar() é a forma do Pyrtugues para chamar print(). Ela envia uma mensagem '
                             'para a saída do programa e é uma das primeiras funções que você usará.',
               'exercicio': 'Troque a mensagem por seu nome ou uma frase sobre o que você quer aprender.',
               'desafio': 'Mostre três mensagens diferentes, uma em cada linha.',
               'dica': 'Uma chamada de função normalmente aparece com parênteses.',
               'ordem': 2,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 1 — Fundamentos',
               'titulo': 'Comentários',
               'descricao': 'Aprenda a deixar anotações no código sem executá-las.',
               'conteudo': 'Objetivo: Aprenda a deixar anotações no código sem executá-las.\n'
                           '\n'
                           'Comentários começam com # e são ignorados pelo interpretador. Eles são úteis para '
                           'explicar decisões, lembrar o objetivo de um trecho ou separar partes de um projeto.\n'
                           '\n'
                           'Exercício guiado: Adicione dois comentários ao seu programa anterior.\n'
                           '\n'
                           'Desafio: Escreva um comentário explicando o objetivo de cada linha de um pequeno '
                           'programa.',
               'pyrtugues': '# Esta linha é um comentário\nmostrar("Código executável")',
               'python': '# Esta linha é um comentário\nprint("Código executável")',
               'explicacao': 'Comentários começam com # e são ignorados pelo interpretador. Eles são úteis para '
                             'explicar decisões, lembrar o objetivo de um trecho ou separar partes de um projeto.',
               'exercicio': 'Adicione dois comentários ao seu programa anterior.',
               'desafio': 'Escreva um comentário explicando o objetivo de cada linha de um pequeno programa.',
               'dica': 'Prefira comentários que expliquem o porquê, não apenas o que já está evidente.',
               'ordem': 3,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 1 — Fundamentos',
               'titulo': 'Indentação e blocos',
               'descricao': 'Veja por que espaços à esquerda fazem parte da sintaxe Python.',
               'conteudo': 'Objetivo: Veja por que espaços à esquerda fazem parte da sintaxe Python.\n'
                           '\n'
                           'Python usa indentação para indicar que uma linha pertence a um bloco. No Pyrtugues, a '
                           'estrutura visual é a mesma: depois dos dois-pontos, as linhas internas recebem '
                           'indentação.\n'
                           '\n'
                           'Exercício guiado: Crie um if que mostre uma mensagem somente quando uma variável for '
                           'maior que 20.\n'
                           '\n'
                           'Desafio: Faça um bloco dentro de outro bloco e observe como a indentação revela a '
                           'estrutura.',
               'pyrtugues': 'idade = 15\nse idade maior que 10:\n    mostrar("Pode continuar")',
               'python': 'idade = 15\nif idade > 10:\n    print("Pode continuar")',
               'explicacao': 'Python usa indentação para indicar que uma linha pertence a um bloco. No Pyrtugues, a '
                             'estrutura visual é a mesma: depois dos dois-pontos, as linhas internas recebem '
                             'indentação.',
               'exercicio': 'Crie um if que mostre uma mensagem somente quando uma variável for maior que 20.',
               'desafio': 'Faça um bloco dentro de outro bloco e observe como a indentação revela a estrutura.',
               'dica': 'Mantenha quatro espaços por nível de indentação.',
               'ordem': 4,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 2 — Variáveis e tipos',
               'titulo': 'Variáveis',
               'descricao': 'Armazene valores em nomes que o programa pode reutilizar.',
               'conteudo': 'Objetivo: Armazene valores em nomes que o programa pode reutilizar.\n'
                           '\n'
                           'Uma variável é um nome associado a um valor. A atribuição usa = e permite guardar dados '
                           'para usar depois em cálculos, condições e funções.\n'
                           '\n'
                           'Exercício guiado: Crie variáveis para nome, idade e cidade e mostre as três.\n'
                           '\n'
                           'Desafio: Crie cinco variáveis diferentes e use todas em uma mesma mensagem.',
               'pyrtugues': 'nome = "Ana"\nidade = 12\nmostrar(nome)\nmostrar(idade)',
               'python': 'nome = "Ana"\nidade = 12\nprint(nome)\nprint(idade)',
               'explicacao': 'Uma variável é um nome associado a um valor. A atribuição usa = e permite guardar '
                             'dados para usar depois em cálculos, condições e funções.',
               'exercicio': 'Crie variáveis para nome, idade e cidade e mostre as três.',
               'desafio': 'Crie cinco variáveis diferentes e use todas em uma mesma mensagem.',
               'dica': 'Escolha nomes que indiquem claramente o que cada variável representa.',
               'ordem': 5,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 2 — Variáveis e tipos',
               'titulo': 'Nomes e atribuição',
               'descricao': 'Aprenda regras e boas práticas para nomear variáveis.',
               'conteudo': 'Objetivo: Aprenda regras e boas práticas para nomear variáveis.\n'
                           '\n'
                           'Nomes de variáveis podem usar letras, números e _, mas não devem começar por número. Em '
                           'Python, nomes são sensíveis a maiúsculas e minúsculas; usar snake_case costuma deixar o '
                           'código mais legível.\n'
                           '\n'
                           'Exercício guiado: Crie três variáveis com nomes descritivos e use-as em uma mensagem.\n'
                           '\n'
                           'Desafio: Renomeie variáveis pouco claras de um exercício anterior para nomes melhores.',
               'pyrtugues': 'nome_aluno = "Lia"\nnota_final = 8\nmostrar(f"{nome_aluno}: {nota_final}")',
               'python': 'nome_aluno = "Lia"\nnota_final = 8\nprint(f"{nome_aluno}: {nota_final}")',
               'explicacao': 'Nomes de variáveis podem usar letras, números e _, mas não devem começar por número. '
                             'Em Python, nomes são sensíveis a maiúsculas e minúsculas; usar snake_case costuma '
                             'deixar o código mais legível.',
               'exercicio': 'Crie três variáveis com nomes descritivos e use-as em uma mensagem.',
               'desafio': 'Renomeie variáveis pouco claras de um exercício anterior para nomes melhores.',
               'dica': 'Evite nomes como x, y e z quando o significado puder ficar mais claro.',
               'ordem': 6,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 2 — Variáveis e tipos',
               'titulo': 'Inteiros e decimais',
               'descricao': 'Diferencie números inteiros e de ponto flutuante.',
               'conteudo': 'Objetivo: Diferencie números inteiros e de ponto flutuante.\n'
                           '\n'
                           'Inteiros representam números sem parte decimal; floats representam valores com casas '
                           'decimais. O tipo interfere no resultado de operações e em como o valor é exibido.\n'
                           '\n'
                           'Exercício guiado: Crie uma quantidade inteira e um preço decimal e calcule o total.\n'
                           '\n'
                           'Desafio: Monte um pequeno cálculo de compra com três itens e um valor decimal.',
               'pyrtugues': 'quantidade = 7\npreco = 12.5\nmostrar(quantidade)\nmostrar(preco)',
               'python': 'quantidade = 7\npreco = 12.5\nprint(quantidade)\nprint(preco)',
               'explicacao': 'Inteiros representam números sem parte decimal; floats representam valores com casas '
                             'decimais. O tipo interfere no resultado de operações e em como o valor é exibido.',
               'exercicio': 'Crie uma quantidade inteira e um preço decimal e calcule o total.',
               'desafio': 'Monte um pequeno cálculo de compra com três itens e um valor decimal.',
               'dica': 'Use nomes de variáveis que indiquem a unidade quando isso ajudar.',
               'ordem': 7,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 2 — Variáveis e tipos',
               'titulo': 'Textos, booleanos e None',
               'descricao': 'Conheça str, bool e None e quando cada um é usado.',
               'conteudo': 'Objetivo: Conheça str, bool e None e quando cada um é usado.\n'
                           '\n'
                           'Textos guardam caracteres, booleanos representam verdadeiro ou falso e None representa '
                           'ausência de valor. Esses tipos aparecem constantemente em condições, cadastros e '
                           'funções.\n'
                           '\n'
                           'Exercício guiado: Crie um cadastro com nome, ativo e um campo inicialmente sem valor.\n'
                           '\n'
                           'Desafio: Atualize o campo None quando uma condição for atendida.',
               'pyrtugues': 'nome = "Rafa"\n'
                            'ativo = verdadeiro\n'
                            'resultado = nulo\n'
                            'mostrar(nome)\n'
                            'mostrar(ativo)\n'
                            'mostrar(resultado)',
               'python': 'nome = "Rafa"\nativo = True\nresultado = None\nprint(nome)\nprint(ativo)\nprint(resultado)',
               'explicacao': 'Textos guardam caracteres, booleanos representam verdadeiro ou falso e None representa '
                             'ausência de valor. Esses tipos aparecem constantemente em condições, cadastros e '
                             'funções.',
               'exercicio': 'Crie um cadastro com nome, ativo e um campo inicialmente sem valor.',
               'desafio': 'Atualize o campo None quando uma condição for atendida.',
               'dica': 'Observe que True, False e None são valores, não textos entre aspas.',
               'ordem': 8,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 3 — Entrada e saída',
               'titulo': 'Mostrar resultados com mostrar()',
               'descricao': 'Use a saída para acompanhar o que o programa está fazendo.',
               'conteudo': 'Objetivo: Use a saída para acompanhar o que o programa está fazendo.\n'
                           '\n'
                           'mostrar() aceita vários argumentos e escreve o resultado na saída. Isso permite combinar '
                           'valores sem precisar montar uma única string em todas as situações.\n'
                           '\n'
                           'Exercício guiado: Mostre uma frase com nome, idade e cidade usando três argumentos.\n'
                           '\n'
                           'Desafio: Monte um pequeno recibo com várias linhas de saída.',
               'pyrtugues': 'nome = "Bia"\nmostrar("Olá,", nome)',
               'python': 'nome = "Bia"\nprint("Olá,", nome)',
               'explicacao': 'mostrar() aceita vários argumentos e escreve o resultado na saída. Isso permite '
                             'combinar valores sem precisar montar uma única string em todas as situações.',
               'exercicio': 'Mostre uma frase com nome, idade e cidade usando três argumentos.',
               'desafio': 'Monte um pequeno recibo com várias linhas de saída.',
               'dica': 'Teste diferentes separações entre argumentos.',
               'ordem': 9,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 3 — Entrada e saída',
               'titulo': 'Entrada com pergunte()',
               'descricao': 'Receba texto digitado pelo usuário.',
               'conteudo': 'Objetivo: Receba texto digitado pelo usuário.\n'
                           '\n'
                           'No editor do Pyrtugues, pergunte() é convertido para input(). A resposta recebida é '
                           'inicialmente texto, então cálculos numéricos exigem conversão.\n'
                           '\n'
                           'Exercício guiado: Peça o nome e a cidade do usuário e mostre os dois.\n'
                           '\n'
                           'Desafio: Crie uma apresentação que faça três perguntas antes de mostrar a resposta '
                           'final.',
               'pyrtugues': 'nome = pergunte("Qual é seu nome? ")\nmostrar(f"Olá, {nome}!")',
               'python': 'nome = input("Qual é seu nome? ")\nprint(f"Olá, {nome}!")',
               'explicacao': 'No editor do Pyrtugues, pergunte() é convertido para input(). A resposta recebida é '
                             'inicialmente texto, então cálculos numéricos exigem conversão.',
               'exercicio': 'Peça o nome e a cidade do usuário e mostre os dois.',
               'desafio': 'Crie uma apresentação que faça três perguntas antes de mostrar a resposta final.',
               'dica': 'Sempre deixe o prompt claro para o usuário.',
               'ordem': 10,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 3 — Entrada e saída',
               'titulo': 'Conversão de entrada',
               'descricao': 'Transforme texto recebido em números e outros tipos.',
               'conteudo': 'Objetivo: Transforme texto recebido em números e outros tipos.\n'
                           '\n'
                           'input() devolve texto. Funções como int() e float() convertem esse texto para tipos '
                           'numéricos quando o conteúdo for válido.\n'
                           '\n'
                           'Exercício guiado: Peça dois números decimais e mostre a soma.\n'
                           '\n'
                           'Desafio: Peça três notas, calcule a média e mostre o resultado.',
               'pyrtugues': 'idade = inteiro(pergunte("Idade: "))\n'
                            'altura = decimal(pergunte("Altura: "))\n'
                            'mostrar(idade + 1)\n'
                            'mostrar(altura)',
               'python': 'idade = int(input("Idade: "))\n'
                         'altura = float(input("Altura: "))\n'
                         'print(idade + 1)\n'
                         'print(altura)',
               'explicacao': 'input() devolve texto. Funções como int() e float() convertem esse texto para tipos '
                             'numéricos quando o conteúdo for válido.',
               'exercicio': 'Peça dois números decimais e mostre a soma.',
               'desafio': 'Peça três notas, calcule a média e mostre o resultado.',
               'dica': 'Uma conversão falha se o texto não puder representar o tipo desejado.',
               'ordem': 11,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 3 — Entrada e saída',
               'titulo': 'F-strings',
               'descricao': 'Monte mensagens usando variáveis dentro de uma string.',
               'conteudo': 'Objetivo: Monte mensagens usando variáveis dentro de uma string.\n'
                           '\n'
                           'F-strings permitem colocar expressões entre chaves dentro de textos. O tradutor do '
                           'Pyrtugues preserva a string e traduz as expressões internas quando necessário.\n'
                           '\n'
                           'Exercício guiado: Crie uma frase com pelo menos quatro variáveis usando uma f-string.\n'
                           '\n'
                           'Desafio: Monte uma mensagem de cadastro em duas linhas usando f-strings.',
               'pyrtugues': 'nome = "Bia"\nidade = 13\nmostrar(f"{nome} tem {idade} anos.")',
               'python': 'nome = "Bia"\nidade = 13\nprint(f"{nome} tem {idade} anos.")',
               'explicacao': 'F-strings permitem colocar expressões entre chaves dentro de textos. O tradutor do '
                             'Pyrtugues preserva a string e traduz as expressões internas quando necessário.',
               'exercicio': 'Crie uma frase com pelo menos quatro variáveis usando uma f-string.',
               'desafio': 'Monte uma mensagem de cadastro em duas linhas usando f-strings.',
               'dica': 'As expressões dentro de { } são avaliadas antes da mensagem ser exibida.',
               'ordem': 12,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 4 — Operadores',
               'titulo': 'Operações matemáticas',
               'descricao': 'Aprenda os operadores aritméticos básicos.',
               'conteudo': 'Objetivo: Aprenda os operadores aritméticos básicos.\n'
                           '\n'
                           'Os operadores aritméticos permitem calcular valores. O Pyrtugues oferece formas como '
                           'vezes e dividido por para tornar certas expressões mais próximas da linguagem natural.\n'
                           '\n'
                           'Exercício guiado: Calcule soma, subtração, multiplicação e divisão de dois números.\n'
                           '\n'
                           'Desafio: Acrescente divisão inteira, resto e potência ao programa.',
               'pyrtugues': 'a = 10\n'
                            'b = 3\n'
                            'mostrar(a + b)\n'
                            'mostrar(a - b)\n'
                            'mostrar(a vezes b)\n'
                            'mostrar(a dividido por b)',
               'python': 'a = 10\nb = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)',
               'explicacao': 'Os operadores aritméticos permitem calcular valores. O Pyrtugues oferece formas como '
                             'vezes e dividido por para tornar certas expressões mais próximas da linguagem natural.',
               'exercicio': 'Calcule soma, subtração, multiplicação e divisão de dois números.',
               'desafio': 'Acrescente divisão inteira, resto e potência ao programa.',
               'dica': 'Cuidado com divisão por zero.',
               'ordem': 13,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 4 — Operadores',
               'titulo': 'Comparações',
               'descricao': 'Produza valores booleanos comparando expressões.',
               'conteudo': 'Objetivo: Produza valores booleanos comparando expressões.\n'
                           '\n'
                           'Comparações devolvem True ou False e são a base das decisões. O Pyrtugues aceita formas '
                           'compostas como maior que, menor ou igual e diferente de.\n'
                           '\n'
                           'Exercício guiado: Compare duas notas e descubra qual é maior.\n'
                           '\n'
                           'Desafio: Crie cinco comparações diferentes e mostre os resultados.',
               'pyrtugues': 'idade = 17\n'
                            'mostrar(idade maior que 18)\n'
                            'mostrar(idade menor ou igual a 17)\n'
                            'mostrar(idade igual a 17)\n'
                            'mostrar(idade diferente de 10)',
               'python': 'idade = 17\nprint(idade > 18)\nprint(idade <= 17)\nprint(idade == 17)\nprint(idade != 10)',
               'explicacao': 'Comparações devolvem True ou False e são a base das decisões. O Pyrtugues aceita '
                             'formas compostas como maior que, menor ou igual e diferente de.',
               'exercicio': 'Compare duas notas e descubra qual é maior.',
               'desafio': 'Crie cinco comparações diferentes e mostre os resultados.',
               'dica': 'Confirme sempre se você precisa comparar valores ou atribuir um valor.',
               'ordem': 14,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 4 — Operadores',
               'titulo': 'Operadores lógicos',
               'descricao': 'Combine condições com e, ou e não.',
               'conteudo': 'Objetivo: Combine condições com e, ou e não.\n'
                           '\n'
                           'and exige que as duas condições sejam verdadeiras; or precisa de apenas uma; not inverte '
                           'um booleano. Essas combinações deixam as decisões mais precisas.\n'
                           '\n'
                           'Exercício guiado: Monte uma condição que exija idade mínima e autorização.\n'
                           '\n'
                           'Desafio: Crie um cenário com três condições e use and e or de maneira legível.',
               'pyrtugues': 'idade = 16\n'
                            'tem_autorizacao = verdadeiro\n'
                            'se idade maior que 14 e tem_autorizacao:\n'
                            '    mostrar("Entrada permitida")',
               'python': 'idade = 16\n'
                         'tem_autorizacao = True\n'
                         'if idade > 14 and tem_autorizacao:\n'
                         '    print("Entrada permitida")',
               'explicacao': 'and exige que as duas condições sejam verdadeiras; or precisa de apenas uma; not '
                             'inverte um booleano. Essas combinações deixam as decisões mais precisas.',
               'exercicio': 'Monte uma condição que exija idade mínima e autorização.',
               'desafio': 'Crie um cenário com três condições e use and e or de maneira legível.',
               'dica': 'Separe condições complexas em variáveis quando isso melhorar a leitura.',
               'ordem': 15,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 4 — Operadores',
               'titulo': 'Atribuição composta e precedência',
               'descricao': 'Reduza operações repetidas e entenda a ordem dos cálculos.',
               'conteudo': 'Objetivo: Reduza operações repetidas e entenda a ordem dos cálculos.\n'
                           '\n'
                           'Operadores como += e *= atualizam uma variável usando seu valor anterior. Parênteses '
                           'podem deixar a ordem de avaliação explícita e evitam ambiguidades.\n'
                           '\n'
                           'Exercício guiado: Comece com um saldo e aplique três atualizações.\n'
                           '\n'
                           'Desafio: Combine parênteses e operadores para construir uma fórmula de preço com '
                           'desconto.',
               'pyrtugues': 'total = 10\ntotal mais igual 5\ntotal vezes igual 2\nmostrar(total)',
               'python': 'total = 10\ntotal += 5\ntotal *= 2\nprint(total)',
               'explicacao': 'Operadores como += e *= atualizam uma variável usando seu valor anterior. Parênteses '
                             'podem deixar a ordem de avaliação explícita e evitam ambiguidades.',
               'exercicio': 'Comece com um saldo e aplique três atualizações.',
               'desafio': 'Combine parênteses e operadores para construir uma fórmula de preço com desconto.',
               'dica': 'Quando a ordem importar, use parênteses em vez de depender da memória da precedência.',
               'ordem': 16,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 5 — Condições',
               'titulo': 'if com se',
               'descricao': 'Execute um bloco somente quando uma condição for verdadeira.',
               'conteudo': 'Objetivo: Execute um bloco somente quando uma condição for verdadeira.\n'
                           '\n'
                           'O bloco iniciado por se é executado quando a condição resulta em verdadeiro. Os '
                           'dois-pontos marcam o começo do bloco indentado.\n'
                           '\n'
                           'Exercício guiado: Crie uma condição para liberar uma ação quando a idade for 16 ou '
                           'mais.\n'
                           '\n'
                           'Desafio: Faça duas verificações independentes no mesmo programa.',
               'pyrtugues': 'idade = 18\nse idade maior ou igual a 18:\n    mostrar("Maior de idade")',
               'python': 'idade = 18\nif idade >= 18:\n    print("Maior de idade")',
               'explicacao': 'O bloco iniciado por se é executado quando a condição resulta em verdadeiro. Os '
                             'dois-pontos marcam o começo do bloco indentado.',
               'exercicio': 'Crie uma condição para liberar uma ação quando a idade for 16 ou mais.',
               'desafio': 'Faça duas verificações independentes no mesmo programa.',
               'dica': 'Leia a condição como uma frase antes de codificá-la.',
               'ordem': 17,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 5 — Condições',
               'titulo': 'Múltiplos caminhos com senão_se',
               'descricao': 'Escolha entre várias faixas de uma mesma decisão.',
               'conteudo': 'Objetivo: Escolha entre várias faixas de uma mesma decisão.\n'
                           '\n'
                           'senão_se representa elif. O Python testa as condições em ordem e para no primeiro bloco '
                           'verdadeiro.\n'
                           '\n'
                           'Exercício guiado: Classifique uma nota em quatro faixas.\n'
                           '\n'
                           'Desafio: Crie uma classificação que trate também notas abaixo de 5.',
               'pyrtugues': 'nota = 8\n'
                            'se nota maior ou igual a 9:\n'
                            '    mostrar("Excelente")\n'
                            'senão_se nota maior ou igual a 7:\n'
                            '    mostrar("Bom")\n'
                            'senão_se nota maior ou igual a 5:\n'
                            '    mostrar("Recuperação")',
               'python': 'nota = 8\n'
                         'if nota >= 9:\n'
                         '    print("Excelente")\n'
                         'elif nota >= 7:\n'
                         '    print("Bom")\n'
                         'elif nota >= 5:\n'
                         '    print("Recuperação")',
               'explicacao': 'senão_se representa elif. O Python testa as condições em ordem e para no primeiro '
                             'bloco verdadeiro.',
               'exercicio': 'Classifique uma nota em quatro faixas.',
               'desafio': 'Crie uma classificação que trate também notas abaixo de 5.',
               'dica': 'Organize as condições da faixa mais específica para a mais geral.',
               'ordem': 18,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 5 — Condições',
               'titulo': 'Alternativa com senão',
               'descricao': 'Defina o caminho quando nenhuma condição anterior for verdadeira.',
               'conteudo': 'Objetivo: Defina o caminho quando nenhuma condição anterior for verdadeira.\n'
                           '\n'
                           'senão representa else e funciona como o caminho alternativo da decisão. Ele só é '
                           'executado se o bloco anterior não tiver sido escolhido.\n'
                           '\n'
                           'Exercício guiado: Crie uma verificação de senha correta ou incorreta.\n'
                           '\n'
                           'Desafio: Combine se, senão_se e senão em uma decisão completa.',
               'pyrtugues': 'saldo = 20\n'
                            'se saldo maior ou igual a 50:\n'
                            '    mostrar("Compra liberada")\n'
                            'senão:\n'
                            '    mostrar("Saldo insuficiente")',
               'python': 'saldo = 20\n'
                         'if saldo >= 50:\n'
                         '    print("Compra liberada")\n'
                         'else:\n'
                         '    print("Saldo insuficiente")',
               'explicacao': 'senão representa else e funciona como o caminho alternativo da decisão. Ele só é '
                             'executado se o bloco anterior não tiver sido escolhido.',
               'exercicio': 'Crie uma verificação de senha correta ou incorreta.',
               'desafio': 'Combine se, senão_se e senão em uma decisão completa.',
               'dica': 'Deixe o caso padrão claro para quem ler o código.',
               'ordem': 19,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 5 — Condições',
               'titulo': 'Condições aninhadas',
               'descricao': 'Coloque uma decisão dentro de outra quando os critérios dependem entre si.',
               'conteudo': 'Objetivo: Coloque uma decisão dentro de outra quando os critérios dependem entre si.\n'
                           '\n'
                           'Condições aninhadas são úteis quando uma decisão só faz sentido depois que outra foi '
                           'atendida. Porém, muitos níveis podem deixar o código difícil de ler.\n'
                           '\n'
                           'Exercício guiado: Faça uma verificação de login e depois uma verificação de permissão.\n'
                           '\n'
                           'Desafio: Refatore uma condição muito aninhada usando uma expressão lógica única.',
               'pyrtugues': 'idade = 20\n'
                            'tem_ingresso = verdadeiro\n'
                            'se idade maior ou igual a 18:\n'
                            '    se tem_ingresso:\n'
                            '        mostrar("Pode entrar")\n'
                            '    senão:\n'
                            '        mostrar("Compre um ingresso")\n'
                            'senão:\n'
                            '    mostrar("Entrada restrita")',
               'python': 'idade = 20\n'
                         'tem_ingresso = True\n'
                         'if idade >= 18:\n'
                         '    if tem_ingresso:\n'
                         '        print("Pode entrar")\n'
                         '    else:\n'
                         '        print("Compre um ingresso")\n'
                         'else:\n'
                         '    print("Entrada restrita")',
               'explicacao': 'Condições aninhadas são úteis quando uma decisão só faz sentido depois que outra foi '
                             'atendida. Porém, muitos níveis podem deixar o código difícil de ler.',
               'exercicio': 'Faça uma verificação de login e depois uma verificação de permissão.',
               'desafio': 'Refatore uma condição muito aninhada usando uma expressão lógica única.',
               'dica': 'Antes de aninhar, veja se and ou or resolvem o problema com menos níveis.',
               'ordem': 20,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 6 — Repetição',
               'titulo': 'for e intervalos',
               'descricao': 'Repita um bloco usando um conjunto conhecido de passos.',
               'conteudo': 'Objetivo: Repita um bloco usando um conjunto conhecido de passos.\n'
                           '\n'
                           'for percorre valores de uma sequência ou iterável. intervalo() corresponde a range() e é '
                           'muito útil para repetir uma ação um número conhecido de vezes.\n'
                           '\n'
                           'Exercício guiado: Mostre os números de 1 a 10.\n'
                           '\n'
                           'Desafio: Mostre somente os números pares de 0 a 20.',
               'pyrtugues': 'para i em intervalo(1, 6):\n    mostrar(i)',
               'python': 'for i in range(1, 6):\n    print(i)',
               'explicacao': 'for percorre valores de uma sequência ou iterável. intervalo() corresponde a range() e '
                             'é muito útil para repetir uma ação um número conhecido de vezes.',
               'exercicio': 'Mostre os números de 1 a 10.',
               'desafio': 'Mostre somente os números pares de 0 a 20.',
               'dica': 'Lembre que o segundo limite de range() não é incluído.',
               'ordem': 21,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 6 — Repetição',
               'titulo': 'while com enquanto',
               'descricao': 'Repita enquanto uma condição continuar verdadeira.',
               'conteudo': 'Objetivo: Repita enquanto uma condição continuar verdadeira.\n'
                           '\n'
                           'while continua executando enquanto a condição for verdadeira. É essencial atualizar '
                           'alguma variável de controle para evitar um laço infinito quando esse controle depender '
                           'do loop.\n'
                           '\n'
                           'Exercício guiado: Conte de 5 até 1.\n'
                           '\n'
                           'Desafio: Crie um menu que continue aparecendo até o usuário escolher sair.',
               'pyrtugues': 'contador = 1\n'
                            'enquanto contador menor ou igual a 5:\n'
                            '    mostrar(contador)\n'
                            '    contador mais igual 1',
               'python': 'contador = 1\nwhile contador <= 5:\n    print(contador)\n    contador += 1',
               'explicacao': 'while continua executando enquanto a condição for verdadeira. É essencial atualizar '
                             'alguma variável de controle para evitar um laço infinito quando esse controle depender '
                             'do loop.',
               'exercicio': 'Conte de 5 até 1.',
               'desafio': 'Crie um menu que continue aparecendo até o usuário escolher sair.',
               'dica': 'Teste mentalmente como a variável de controle muda a cada volta.',
               'ordem': 22,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 6 — Repetição',
               'titulo': 'quebrar, continuar e passar',
               'descricao': 'Controle o fluxo de um laço em situações específicas.',
               'conteudo': 'Objetivo: Controle o fluxo de um laço em situações específicas.\n'
                           '\n'
                           'quebrar interrompe o laço; continuar pula para a próxima iteração; passar não faz nada e '
                           'serve como marcador temporário de bloco.\n'
                           '\n'
                           'Exercício guiado: Faça um loop que ignore um número e pare em outro.\n'
                           '\n'
                           'Desafio: Use passar em um bloco ainda não implementado e depois substitua pelo '
                           'comportamento real.',
               'pyrtugues': 'para i em intervalo(1, 8):\n'
                            '    se i igual a 4:\n'
                            '        continuar\n'
                            '    se i igual a 7:\n'
                            '        quebrar\n'
                            '    mostrar(i)',
               'python': 'for i in range(1, 8):\n'
                         '    if i == 4:\n'
                         '        continue\n'
                         '    if i == 7:\n'
                         '        break\n'
                         '    print(i)',
               'explicacao': 'quebrar interrompe o laço; continuar pula para a próxima iteração; passar não faz nada '
                             'e serve como marcador temporário de bloco.',
               'exercicio': 'Faça um loop que ignore um número e pare em outro.',
               'desafio': 'Use passar em um bloco ainda não implementado e depois substitua pelo comportamento real.',
               'dica': 'Use break e continue com moderação para manter a lógica fácil de acompanhar.',
               'ordem': 23,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 6 — Repetição',
               'titulo': 'Contadores e acumuladores',
               'descricao': 'Use variáveis que acumulam informações durante um laço.',
               'conteudo': 'Objetivo: Use variáveis que acumulam informações durante um laço.\n'
                           '\n'
                           'Um acumulador começa com um valor inicial e recebe novos valores a cada repetição. Um '
                           'contador é um caso simples desse padrão e costuma começar em zero ou um.\n'
                           '\n'
                           'Exercício guiado: Calcule a soma de 1 a 100.\n'
                           '\n'
                           'Desafio: Conte quantos números entre 1 e 100 são divisíveis por 3.',
               'pyrtugues': 'soma = 0\npara numero em intervalo(1, 6):\n    soma mais igual numero\nmostrar(soma)',
               'python': 'soma = 0\nfor numero in range(1, 6):\n    soma += numero\nprint(soma)',
               'explicacao': 'Um acumulador começa com um valor inicial e recebe novos valores a cada repetição. Um '
                             'contador é um caso simples desse padrão e costuma começar em zero ou um.',
               'exercicio': 'Calcule a soma de 1 a 100.',
               'desafio': 'Conte quantos números entre 1 e 100 são divisíveis por 3.',
               'dica': 'Escolha a inicialização correta antes de iniciar o laço.',
               'ordem': 24,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 7 — Textos',
               'titulo': 'Índices de strings',
               'descricao': 'Acesse caracteres específicos de um texto.',
               'conteudo': 'Objetivo: Acesse caracteres específicos de um texto.\n'
                           '\n'
                           'Strings são sequências e podem ser acessadas por índice. O primeiro caractere está na '
                           'posição 0 e índices negativos contam a partir do final.\n'
                           '\n'
                           'Exercício guiado: Mostre a primeira e a última letra de uma palavra.\n'
                           '\n'
                           'Desafio: Monte uma verificação que compare a primeira letra de uma palavra com outra.',
               'pyrtugues': 'texto = "PYRTUGUES"\nmostrar(texto[0])\nmostrar(texto[-1])',
               'python': 'texto = "PYRTUGUES"\nprint(texto[0])\nprint(texto[-1])',
               'explicacao': 'Strings são sequências e podem ser acessadas por índice. O primeiro caractere está na '
                             'posição 0 e índices negativos contam a partir do final.',
               'exercicio': 'Mostre a primeira e a última letra de uma palavra.',
               'desafio': 'Monte uma verificação que compare a primeira letra de uma palavra com outra.',
               'dica': 'Lembre que o maior índice válido depende do tamanho da string.',
               'ordem': 25,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 7 — Textos',
               'titulo': 'Fatiamento de textos',
               'descricao': 'Extraia partes de uma string usando slicing.',
               'conteudo': 'Objetivo: Extraia partes de uma string usando slicing.\n'
                           '\n'
                           'O slicing usa início e fim, mas o índice final não entra no trecho. Ele é útil para '
                           'extrair prefixos, sufixos e partes estruturadas de uma string.\n'
                           '\n'
                           'Exercício guiado: Extraia os três primeiros caracteres de uma palavra.\n'
                           '\n'
                           'Desafio: Pegue o domínio ou parte final de um endereço de texto simples.',
               'pyrtugues': 'texto = "Python em português"\nmostrar(texto[0:6])\nmostrar(texto[7:9])',
               'python': 'texto = "Python em português"\nprint(texto[0:6])\nprint(texto[7:9])',
               'explicacao': 'O slicing usa início e fim, mas o índice final não entra no trecho. Ele é útil para '
                             'extrair prefixos, sufixos e partes estruturadas de uma string.',
               'exercicio': 'Extraia os três primeiros caracteres de uma palavra.',
               'desafio': 'Pegue o domínio ou parte final de um endereço de texto simples.',
               'dica': 'Experimente também índices negativos para entender os limites.',
               'ordem': 26,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 7 — Textos',
               'titulo': 'Métodos de texto',
               'descricao': 'Use métodos para transformar e testar strings.',
               'conteudo': 'Objetivo: Use métodos para transformar e testar strings.\n'
                           '\n'
                           'Métodos são funções associadas a um objeto e chamadas depois de um ponto. O tradutor '
                           'possui um conjunto de métodos em português, como maiúsculas(), minúsculas() e '
                           'capitalizar().\n'
                           '\n'
                           'Exercício guiado: Normalize um nome para começar com letra maiúscula.\n'
                           '\n'
                           'Desafio: Crie um pequeno formatador de títulos para três textos.',
               'pyrtugues': 'texto = "python"\n'
                            'mostrar(texto.maiúsculas())\n'
                            'mostrar(texto.minúsculas())\n'
                            'mostrar(texto.capitalizar())',
               'python': 'texto = "python"\nprint(texto.upper())\nprint(texto.lower())\nprint(texto.capitalize())',
               'explicacao': 'Métodos são funções associadas a um objeto e chamadas depois de um ponto. O tradutor '
                             'possui um conjunto de métodos em português, como maiúsculas(), minúsculas() e '
                             'capitalizar().',
               'exercicio': 'Normalize um nome para começar com letra maiúscula.',
               'desafio': 'Crie um pequeno formatador de títulos para três textos.',
               'dica': 'Métodos de string geralmente devolvem um novo texto em vez de alterar o original.',
               'ordem': 27,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 7 — Textos',
               'titulo': 'Buscar, substituir, dividir e juntar',
               'descricao': 'Trabalhe com conteúdo textual mais estruturado.',
               'conteudo': 'Objetivo: Trabalhe com conteúdo textual mais estruturado.\n'
                           '\n'
                           'split() quebra um texto em partes; join() une uma coleção com um separador; find() '
                           'procura uma posição; replace() troca ocorrências. Esses métodos são úteis para tratar '
                           'dados simples.\n'
                           '\n'
                           'Exercício guiado: Separe um texto com nomes usando vírgula e mostre cada parte.\n'
                           '\n'
                           'Desafio: Crie um normalizador que troque uma palavra proibida por outra.',
               'pyrtugues': 'texto = "ana,bruno,carla"\n'
                            'mostrar(texto.dividir(","))\n'
                            'mostrar("-".juntar ["A", "B", "C"])\n'
                            'mostrar(texto.encontrar("bruno"))\n'
                            'mostrar(texto.trocar("carla", "Duda"))',
               'python': 'texto = "ana,bruno,carla"\n'
                         'print(texto.split(","))\n'
                         'print("-".join(["A", "B", "C"]))\n'
                         'print(texto.find("bruno"))\n'
                         'print(texto.replace("carla", "Duda"))',
               'explicacao': 'split() quebra um texto em partes; join() une uma coleção com um separador; find() '
                             'procura uma posição; replace() troca ocorrências. Esses métodos são úteis para tratar '
                             'dados simples.',
               'exercicio': 'Separe um texto com nomes usando vírgula e mostre cada parte.',
               'desafio': 'Crie um normalizador que troque uma palavra proibida por outra.',
               'dica': 'Observe os valores devolvidos por find() quando o trecho não existe.',
               'ordem': 28,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 8 — Listas',
               'titulo': 'Criando e acessando listas',
               'descricao': 'Armazene vários valores em uma única coleção ordenada.',
               'conteudo': 'Objetivo: Armazene vários valores em uma única coleção ordenada.\n'
                           '\n'
                           'Listas mantêm uma sequência de elementos e são mutáveis. Você pode acessar cada posição, '
                           'alterar itens e usar métodos para adicionar ou remover valores.\n'
                           '\n'
                           'Exercício guiado: Crie uma lista com cinco matérias e mostre a terceira.\n'
                           '\n'
                           'Desafio: Monte uma lista de compras e altere um item depois de criá-la.',
               'pyrtugues': 'frutas = ["maçã", "banana", "uva"]\nmostrar(frutas)\nmostrar(frutas[1])',
               'python': 'frutas = ["maçã", "banana", "uva"]\nprint(frutas)\nprint(frutas[1])',
               'explicacao': 'Listas mantêm uma sequência de elementos e são mutáveis. Você pode acessar cada '
                             'posição, alterar itens e usar métodos para adicionar ou remover valores.',
               'exercicio': 'Crie uma lista com cinco matérias e mostre a terceira.',
               'desafio': 'Monte uma lista de compras e altere um item depois de criá-la.',
               'dica': 'Índices de listas também começam em zero.',
               'ordem': 29,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 8 — Listas',
               'titulo': 'Alterando elementos',
               'descricao': 'Troque valores de uma lista por índice.',
               'conteudo': 'Objetivo: Troque valores de uma lista por índice.\n'
                           '\n'
                           'Como listas são mutáveis, uma posição pode receber um novo valor. Isso permite atualizar '
                           'dados sem recriar toda a lista.\n'
                           '\n'
                           'Exercício guiado: Crie uma lista de notas e corrija uma delas.\n'
                           '\n'
                           'Desafio: Implemente uma atualização de estoque alterando a quantidade de um item em uma '
                           'posição conhecida.',
               'pyrtugues': 'cores = ["azul", "verde", "vermelho"]\ncores[1] = "amarelo"\nmostrar(cores)',
               'python': 'cores = ["azul", "verde", "vermelho"]\ncores[1] = "amarelo"\nprint(cores)',
               'explicacao': 'Como listas são mutáveis, uma posição pode receber um novo valor. Isso permite '
                             'atualizar dados sem recriar toda a lista.',
               'exercicio': 'Crie uma lista de notas e corrija uma delas.',
               'desafio': 'Implemente uma atualização de estoque alterando a quantidade de um item em uma posição '
                          'conhecida.',
               'dica': 'Tenha cuidado para não usar um índice que não existe.',
               'ordem': 30,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 8 — Listas',
               'titulo': 'append e extend',
               'descricao': 'Adicione um ou vários elementos ao final de uma lista.',
               'conteudo': 'Objetivo: Adicione um ou vários elementos ao final de uma lista.\n'
                           '\n'
                           'append() adiciona um elemento; extend() acrescenta os elementos de outra coleção. No '
                           'tradutor, os métodos são escritos como adicionar() e estender().\n'
                           '\n'
                           'Exercício guiado: Comece com uma lista vazia e adicione cinco nomes.\n'
                           '\n'
                           'Desafio: Monte duas listas e una o conteúdo usando extend().',
               'pyrtugues': 'numeros = [1, 2]\nnumeros.adicionar(3)\nnumeros.estender([4, 5])\nmostrar(numeros)',
               'python': 'numeros = [1, 2]\nnumeros.append(3)\nnumeros.extend([4, 5])\nprint(numeros)',
               'explicacao': 'append() adiciona um elemento; extend() acrescenta os elementos de outra coleção. No '
                             'tradutor, os métodos são escritos como adicionar() e estender().',
               'exercicio': 'Comece com uma lista vazia e adicione cinco nomes.',
               'desafio': 'Monte duas listas e una o conteúdo usando extend().',
               'dica': 'append adiciona um único objeto; extend percorre outra coleção.',
               'ordem': 31,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 8 — Listas',
               'titulo': 'insert, remove, pop, sort e reverse',
               'descricao': 'Use métodos comuns para organizar e editar listas.',
               'conteudo': 'Objetivo: Use métodos comuns para organizar e editar listas.\n'
                           '\n'
                           'insert() adiciona em uma posição; remove() apaga um valor; pop() remove e devolve um '
                           'item; sort() ordena a própria lista; reverse() inverte a ordem.\n'
                           '\n'
                           'Exercício guiado: Crie uma lista de números, ordene, remova um valor e retire o último.\n'
                           '\n'
                           'Desafio: Faça um pequeno ranking que adicione participantes e ordene o resultado.',
               'pyrtugues': 'numeros = [4, 2, 7, 1]\n'
                            'numeros.inserir(1, 9)\n'
                            'numeros.remover(7)\n'
                            'ultimo = numeros.tirar()\n'
                            'ordenar(numeros)\n'
                            'lista(inverter(numeros))\n'
                            'mostrar(numeros)\n'
                            'mostrar(ultimo)',
               'python': 'numeros = [4, 2, 7, 1]\n'
                         'numeros.insert(1, 9)\n'
                         'numeros.remove(7)\n'
                         'ultimo = numeros.pop()\n'
                         'numeros.sort()\n'
                         'numeros.reverse()\n'
                         'print(numeros)\n'
                         'print(ultimo)',
               'explicacao': 'insert() adiciona em uma posição; remove() apaga um valor; pop() remove e devolve um '
                             'item; sort() ordena a própria lista; reverse() inverte a ordem.',
               'exercicio': 'Crie uma lista de números, ordene, remova um valor e retire o último.',
               'desafio': 'Faça um pequeno ranking que adicione participantes e ordene o resultado.',
               'dica': 'Leia a documentação do método mentalmente: alguns alteram a lista e outros devolvem um '
                       'valor.',
               'ordem': 32,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 9 — Tuplas',
               'titulo': 'Criando tuplas',
               'descricao': 'Aprenda uma coleção ordenada que não deve ser alterada.',
               'conteudo': 'Objetivo: Aprenda uma coleção ordenada que não deve ser alterada.\n'
                           '\n'
                           'Tuplas são sequências imutáveis. Elas são úteis para representar conjuntos fixos de '
                           'valores que não precisam mudar durante a execução.\n'
                           '\n'
                           'Exercício guiado: Crie uma tupla para representar largura e altura.\n'
                           '\n'
                           'Desafio: Crie uma tupla com dados de um aluno e mostre cada posição.',
               'pyrtugues': 'ponto = (10, 20)\nmostrar(ponto[0])\nmostrar(ponto[1])',
               'python': 'ponto = (10, 20)\nprint(ponto[0])\nprint(ponto[1])',
               'explicacao': 'Tuplas são sequências imutáveis. Elas são úteis para representar conjuntos fixos de '
                             'valores que não precisam mudar durante a execução.',
               'exercicio': 'Crie uma tupla para representar largura e altura.',
               'desafio': 'Crie uma tupla com dados de um aluno e mostre cada posição.',
               'dica': 'Use tuplas quando a imutabilidade fizer sentido para o problema.',
               'ordem': 33,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 9 — Tuplas',
               'titulo': 'Desempacotamento',
               'descricao': 'Distribua os valores de uma tupla em variáveis.',
               'conteudo': 'Objetivo: Distribua os valores de uma tupla em variáveis.\n'
                           '\n'
                           'Desempacotamento permite atribuir várias variáveis em uma única instrução. A quantidade '
                           'e a posição dos nomes precisam combinar com os valores, salvo formas especiais de '
                           'desempacotamento.\n'
                           '\n'
                           'Exercício guiado: Desempacote nome, idade e cidade de uma tupla.\n'
                           '\n'
                           'Desafio: Use *restante em Python para separar parte dos valores e compare com o '
                           'desempacotamento simples.',
               'pyrtugues': 'ponto = (10, 20)\nx, y = ponto\nmostrar(x)\nmostrar(y)',
               'python': 'ponto = (10, 20)\nx, y = ponto\nprint(x)\nprint(y)',
               'explicacao': 'Desempacotamento permite atribuir várias variáveis em uma única instrução. A '
                             'quantidade e a posição dos nomes precisam combinar com os valores, salvo formas '
                             'especiais de desempacotamento.',
               'exercicio': 'Desempacote nome, idade e cidade de uma tupla.',
               'desafio': 'Use *restante em Python para separar parte dos valores e compare com o desempacotamento '
                          'simples.',
               'dica': 'Desempacotamento funciona com outras sequências além de tuplas.',
               'ordem': 34,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 9 — Tuplas',
               'titulo': 'Percorrendo tuplas',
               'descricao': 'Use laços para ler os elementos de uma tupla.',
               'conteudo': 'Objetivo: Use laços para ler os elementos de uma tupla.\n'
                           '\n'
                           'Como tuplas são iteráveis, podem ser percorridas com for. O loop lê cada elemento na '
                           'ordem em que ele foi armazenado.\n'
                           '\n'
                           'Exercício guiado: Mostre todos os meses de um trimestre usando uma tupla.\n'
                           '\n'
                           'Desafio: Combine enumerate() com uma tupla para mostrar posição e valor.',
               'pyrtugues': 'cores = ("azul", "verde", "vermelho")\npara cor em cores:\n    mostrar(cor)',
               'python': 'cores = ("azul", "verde", "vermelho")\nfor cor in cores:\n    print(cor)',
               'explicacao': 'Como tuplas são iteráveis, podem ser percorridas com for. O loop lê cada elemento na '
                             'ordem em que ele foi armazenado.',
               'exercicio': 'Mostre todos os meses de um trimestre usando uma tupla.',
               'desafio': 'Combine enumerate() com uma tupla para mostrar posição e valor.',
               'dica': 'Use enumerar() quando a posição também for necessária.',
               'ordem': 35,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 9 — Tuplas',
               'titulo': 'Lista ou tupla?',
               'descricao': 'Compare mutabilidade, intenção e uso das duas estruturas.',
               'conteudo': 'Objetivo: Compare mutabilidade, intenção e uso das duas estruturas.\n'
                           '\n'
                           'Listas são adequadas para dados que mudam; tuplas são úteis para valores fixos. A '
                           'escolha comunica a intenção do código e pode evitar alterações acidentais.\n'
                           '\n'
                           'Exercício guiado: Converta uma lista de opções em uma tupla fixa.\n'
                           '\n'
                           'Desafio: Escolha estrutura para cinco cenários diferentes e explique a decisão.',
               'pyrtugues': 'nomes = ["Ana", "Bia"]\n'
                            'coordenadas = (10, 20)\n'
                            'nomes[0] = "Lia"\n'
                            'mostrar(nomes)\n'
                            'mostrar(coordenadas)',
               'python': 'nomes = ["Ana", "Bia"]\n'
                         'coordenadas = (10, 20)\n'
                         'nomes[0] = "Lia"\n'
                         'print(nomes)\n'
                         'print(coordenadas)',
               'explicacao': 'Listas são adequadas para dados que mudam; tuplas são úteis para valores fixos. A '
                             'escolha comunica a intenção do código e pode evitar alterações acidentais.',
               'exercicio': 'Converta uma lista de opções em uma tupla fixa.',
               'desafio': 'Escolha estrutura para cinco cenários diferentes e explique a decisão.',
               'dica': 'Pergunte primeiro: esse conjunto de dados precisa mudar?',
               'ordem': 36,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 10 — Conjuntos',
               'titulo': 'Criando conjuntos',
               'descricao': 'Armazene valores únicos sem depender de uma ordem.',
               'conteudo': 'Objetivo: Armazene valores únicos sem depender de uma ordem.\n'
                           '\n'
                           'Sets eliminam duplicatas automaticamente e são úteis para testar pertencimento e fazer '
                           'operações de conjuntos. A ordem de exibição não deve ser tratada como garantida.\n'
                           '\n'
                           'Exercício guiado: Crie um conjunto com números repetidos e observe o resultado.\n'
                           '\n'
                           'Desafio: Use um conjunto para descobrir quantos nomes diferentes aparecem em uma lista.',
               'pyrtugues': 'nomes = {"Ana", "Bia", "Ana"}\nmostrar(nomes)',
               'python': 'nomes = {"Ana", "Bia", "Ana"}\nprint(nomes)',
               'explicacao': 'Sets eliminam duplicatas automaticamente e são úteis para testar pertencimento e fazer '
                             'operações de conjuntos. A ordem de exibição não deve ser tratada como garantida.',
               'exercicio': 'Crie um conjunto com números repetidos e observe o resultado.',
               'desafio': 'Use um conjunto para descobrir quantos nomes diferentes aparecem em uma lista.',
               'dica': 'Não dependa da ordem visual de um set.',
               'ordem': 37,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 10 — Conjuntos',
               'titulo': 'Adicionar e remover elementos',
               'descricao': 'Atualize um conjunto com operações apropriadas.',
               'conteudo': 'Objetivo: Atualize um conjunto com operações apropriadas.\n'
                           '\n'
                           'Conjuntos são mutáveis e podem receber ou perder elementos. O método remove() gera erro '
                           'se o item não existir, então em situações incertas considere verificar antes.\n'
                           '\n'
                           'Exercício guiado: Adicione três elementos e remova um deles.\n'
                           '\n'
                           'Desafio: Crie uma rotina que só remova um item quando ele estiver presente.',
               'pyrtugues': 'itens = {"a", "b"}\nitens.adicionar("c")\nitens.remover("a")\nmostrar(itens)',
               'python': 'itens = {"a", "b"}\nitens.add("c")\nitens.remove("a")\nprint(itens)',
               'explicacao': 'Conjuntos são mutáveis e podem receber ou perder elementos. O método remove() gera '
                             'erro se o item não existir, então em situações incertas considere verificar antes.',
               'exercicio': 'Adicione três elementos e remova um deles.',
               'desafio': 'Crie uma rotina que só remova um item quando ele estiver presente.',
               'dica': 'O operador in é útil para verificar pertencimento antes de remover.',
               'ordem': 38,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 10 — Conjuntos',
               'titulo': 'União e interseção',
               'descricao': 'Combine conjuntos ou descubra elementos em comum.',
               'conteudo': 'Objetivo: Combine conjuntos ou descubra elementos em comum.\n'
                           '\n'
                           'A união reúne valores dos dois conjuntos; a interseção mantém apenas os elementos '
                           'presentes em ambos. Essas operações são úteis para comparar grupos.\n'
                           '\n'
                           'Exercício guiado: Descubra participantes totais e participantes em comum de duas listas '
                           'convertidas em sets.\n'
                           '\n'
                           'Desafio: Adicione também diferença e diferença simétrica ao relatório.',
               'pyrtugues': 'turma_a = {"Ana", "Bia", "Caio"}\n'
                            'turma_b = {"Bia", "Duda", "Caio"}\n'
                            'mostrar(turma_a | turma_b)\n'
                            'mostrar(turma_a & turma_b)',
               'python': 'turma_a = {"Ana", "Bia", "Caio"}\n'
                         'turma_b = {"Bia", "Duda", "Caio"}\n'
                         'print(turma_a | turma_b)\n'
                         'print(turma_a & turma_b)',
               'explicacao': 'A união reúne valores dos dois conjuntos; a interseção mantém apenas os elementos '
                             'presentes em ambos. Essas operações são úteis para comparar grupos.',
               'exercicio': 'Descubra participantes totais e participantes em comum de duas listas convertidas em '
                            'sets.',
               'desafio': 'Adicione também diferença e diferença simétrica ao relatório.',
               'dica': 'Use a estrutura que representa naturalmente o problema.',
               'ordem': 39,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 10 — Conjuntos',
               'titulo': 'Diferença e pertencimento',
               'descricao': 'Descubra o que existe em um conjunto e não em outro.',
               'conteudo': 'Objetivo: Descubra o que existe em um conjunto e não em outro.\n'
                           '\n'
                           'A diferença mantém elementos que aparecem no primeiro conjunto e não no segundo. O '
                           'operador em testa pertencimento e funciona de forma muito natural com sets.\n'
                           '\n'
                           'Exercício guiado: Descubra quem está inscrito mas ainda não compareceu.\n'
                           '\n'
                           'Desafio: Monte um controle de acesso usando conjunto de usuários autorizados.',
               'pyrtugues': 'presentes = {"Ana", "Bia", "Caio"}\n'
                            'inscritos = {"Ana", "Bia", "Caio", "Duda"}\n'
                            'mostrar(inscritos - presentes)\n'
                            'mostrar("Duda" em inscritos)',
               'python': 'presentes = {"Ana", "Bia", "Caio"}\n'
                         'inscritos = {"Ana", "Bia", "Caio", "Duda"}\n'
                         'print(inscritos - presentes)\n'
                         'print("Duda" in inscritos)',
               'explicacao': 'A diferença mantém elementos que aparecem no primeiro conjunto e não no segundo. O '
                             'operador em testa pertencimento e funciona de forma muito natural com sets.',
               'exercicio': 'Descubra quem está inscrito mas ainda não compareceu.',
               'desafio': 'Monte um controle de acesso usando conjunto de usuários autorizados.',
               'dica': 'Leia a operação como uma frase: inscritos - presentes.',
               'ordem': 40,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 11 — Dicionários',
               'titulo': 'Criando dicionários',
               'descricao': 'Associe chaves a valores.',
               'conteudo': 'Objetivo: Associe chaves a valores.\n'
                           '\n'
                           'Dicionários armazenam pares chave-valor e são ideais para dados nomeados. As chaves '
                           'precisam ser únicas e permitem acessar valores sem depender de posição numérica.\n'
                           '\n'
                           'Exercício guiado: Crie um dicionário para um produto com nome, preço e estoque.\n'
                           '\n'
                           'Desafio: Crie um cadastro com cinco campos diferentes.',
               'pyrtugues': 'aluno = {\n    "nome": "Ana",\n    "idade": 15\n}\nmostrar(aluno["nome"])',
               'python': 'aluno = {\n    "nome": "Ana",\n    "idade": 15\n}\nprint(aluno["nome"])',
               'explicacao': 'Dicionários armazenam pares chave-valor e são ideais para dados nomeados. As chaves '
                             'precisam ser únicas e permitem acessar valores sem depender de posição numérica.',
               'exercicio': 'Crie um dicionário para um produto com nome, preço e estoque.',
               'desafio': 'Crie um cadastro com cinco campos diferentes.',
               'dica': 'Use chaves descritivas e consistentes.',
               'ordem': 41,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 11 — Dicionários',
               'titulo': 'Ler e alterar valores',
               'descricao': 'Atualize campos de um dicionário.',
               'conteudo': 'Objetivo: Atualize campos de um dicionário.\n'
                           '\n'
                           'Atribuir a uma chave existente altera o valor; usar uma chave nova cria um novo par. '
                           'Isso torna dicionários úteis para estados que mudam durante o programa.\n'
                           '\n'
                           'Exercício guiado: Atualize estoque e preço de um produto.\n'
                           '\n'
                           'Desafio: Crie um registro de usuário que receba novos campos ao longo do programa.',
               'pyrtugues': 'aluno = {"nome": "Ana", "nota": 7}\n'
                            'aluno["nota"] = 9\n'
                            'aluno["aprovado"] = verdadeiro\n'
                            'mostrar(aluno)',
               'python': 'aluno = {"nome": "Ana", "nota": 7}\n'
                         'aluno["nota"] = 9\n'
                         'aluno["aprovado"] = True\n'
                         'print(aluno)',
               'explicacao': 'Atribuir a uma chave existente altera o valor; usar uma chave nova cria um novo par. '
                             'Isso torna dicionários úteis para estados que mudam durante o programa.',
               'exercicio': 'Atualize estoque e preço de um produto.',
               'desafio': 'Crie um registro de usuário que receba novos campos ao longo do programa.',
               'dica': 'Acesse uma chave pelo nome, não pelo índice.',
               'ordem': 42,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 11 — Dicionários',
               'titulo': 'keys, values, items',
               'descricao': 'Percorra partes diferentes de um dicionário.',
               'conteudo': 'Objetivo: Percorra partes diferentes de um dicionário.\n'
                           '\n'
                           'keys(), values() e items() permitem percorrer chaves, valores ou pares. No Pyrtugues, '
                           'esses métodos são escritos como chaves(), valores() e itens().\n'
                           '\n'
                           'Exercício guiado: Mostre todas as chaves e valores de um cadastro.\n'
                           '\n'
                           'Desafio: Use itens() em um laço para mostrar `chave: valor`.',
               'pyrtugues': 'aluno = {"nome": "Ana", "nota": 9}\n'
                            'mostrar(aluno.chaves())\n'
                            'mostrar(aluno.valores())\n'
                            'mostrar(aluno.itens())',
               'python': 'aluno = {"nome": "Ana", "nota": 9}\n'
                         'print(aluno.keys())\n'
                         'print(aluno.values())\n'
                         'print(aluno.items())',
               'explicacao': 'keys(), values() e items() permitem percorrer chaves, valores ou pares. No Pyrtugues, '
                             'esses métodos são escritos como chaves(), valores() e itens().',
               'exercicio': 'Mostre todas as chaves e valores de um cadastro.',
               'desafio': 'Use itens() em um laço para mostrar `chave: valor`.',
               'dica': 'items() é especialmente útil quando você precisa das duas partes ao mesmo tempo.',
               'ordem': 43,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 11 — Dicionários',
               'titulo': 'get e update',
               'descricao': 'Acesse dados opcionais e atualize vários campos.',
               'conteudo': 'Objetivo: Acesse dados opcionais e atualize vários campos.\n'
                           '\n'
                           'get() permite buscar uma chave sem causar erro quando ela não existe; update() incorpora '
                           'vários pares de uma vez. Esses métodos tornam atualizações mais seguras e compactas.\n'
                           '\n'
                           'Exercício guiado: Busque uma chave opcional de um cadastro usando get().\n'
                           '\n'
                           'Desafio: Atualize várias configurações de uma vez e mostre o resultado.',
               'pyrtugues': 'config = {"tema": "escuro"}\n'
                            'mostrar(config.pegar("idioma"))\n'
                            'config.atualizar({"idioma": "pt-BR", "fonte": 14})\n'
                            'mostrar(config)',
               'python': 'config = {"tema": "escuro"}\n'
                         'print(config.get("idioma"))\n'
                         'config.update({"idioma": "pt-BR", "fonte": 14})\n'
                         'print(config)',
               'explicacao': 'get() permite buscar uma chave sem causar erro quando ela não existe; update() '
                             'incorpora vários pares de uma vez. Esses métodos tornam atualizações mais seguras e '
                             'compactas.',
               'exercicio': 'Busque uma chave opcional de um cadastro usando get().',
               'desafio': 'Atualize várias configurações de uma vez e mostre o resultado.',
               'dica': 'Escolha um valor padrão ao usar get quando isso fizer sentido.',
               'ordem': 44,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 11 — Dicionários',
               'titulo': 'Percorrendo dicionários',
               'descricao': 'Combine for com chaves e valores para processar registros.',
               'conteudo': 'Objetivo: Combine for com chaves e valores para processar registros.\n'
                           '\n'
                           'Percorrer um dicionário diretamente produz suas chaves. A partir da chave, você pode '
                           'obter o valor e construir relatórios ou cálculos.\n'
                           '\n'
                           'Exercício guiado: Some os valores de um dicionário de preços.\n'
                           '\n'
                           'Desafio: Mostre apenas os itens com preço acima de 3.',
               'pyrtugues': 'precos = {"maçã": 3.5, "banana": 2.0}\n'
                            'para nome em precos:\n'
                            '    mostrar(nome, precos[nome])',
               'python': 'precos = {"maçã": 3.5, "banana": 2.0}\nfor nome in precos:\n    print(nome, precos[nome])',
               'explicacao': 'Percorrer um dicionário diretamente produz suas chaves. A partir da chave, você pode '
                             'obter o valor e construir relatórios ou cálculos.',
               'exercicio': 'Some os valores de um dicionário de preços.',
               'desafio': 'Mostre apenas os itens com preço acima de 3.',
               'dica': 'Quando precisar de chave e valor juntos, considere items().',
               'ordem': 45,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 12 — Funções',
               'titulo': 'Criando funções',
               'descricao': 'Encapsule uma tarefa em uma função reutilizável.',
               'conteudo': 'Objetivo: Encapsule uma tarefa em uma função reutilizável.\n'
                           '\n'
                           'Uma função agrupa instruções sob um nome. Definí-la não executa seu corpo; a execução '
                           'acontece quando ela é chamada.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que mostre uma mensagem de boas-vindas.\n'
                           '\n'
                           'Desafio: Faça três funções pequenas para organizar um programa maior.',
               'pyrtugues': 'função saudar():\n    mostrar("Olá!")\n\nsaudar()',
               'python': 'def saudar():\n    print("Olá!")\n\nsaudar()',
               'explicacao': 'Uma função agrupa instruções sob um nome. Definí-la não executa seu corpo; a execução '
                             'acontece quando ela é chamada.',
               'exercicio': 'Crie uma função que mostre uma mensagem de boas-vindas.',
               'desafio': 'Faça três funções pequenas para organizar um programa maior.',
               'dica': 'Nomeie funções com verbos que indiquem ação.',
               'ordem': 46,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 12 — Funções',
               'titulo': 'Parâmetros e argumentos',
               'descricao': 'Passe dados para uma função.',
               'conteudo': 'Objetivo: Passe dados para uma função.\n'
                           '\n'
                           'Parâmetros são os nomes definidos na função; argumentos são os valores enviados na '
                           'chamada. Essa separação permite reutilizar a mesma lógica com dados diferentes.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que receba nome e cidade.\n'
                           '\n'
                           'Desafio: Faça uma função que receba três números e mostre o maior.',
               'pyrtugues': 'função saudar(nome):\n    mostrar(f"Olá, {nome}!")\n\nsaudar("Pyrtugues")',
               'python': 'def saudar(nome):\n    print(f"Olá, {nome}!")\n\nsaudar("Pyrtugues")',
               'explicacao': 'Parâmetros são os nomes definidos na função; argumentos são os valores enviados na '
                             'chamada. Essa separação permite reutilizar a mesma lógica com dados diferentes.',
               'exercicio': 'Crie uma função que receba nome e cidade.',
               'desafio': 'Faça uma função que receba três números e mostre o maior.',
               'dica': 'Use parâmetros para evitar copiar a mesma lógica.',
               'ordem': 47,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 12 — Funções',
               'titulo': 'Retorno',
               'descricao': 'Faça uma função devolver um resultado com retornar.',
               'conteudo': 'Objetivo: Faça uma função devolver um resultado com retornar.\n'
                           '\n'
                           'return encerra a execução da função e devolve um valor para quem chamou. Isso permite '
                           'construir programas em camadas, em que uma função calcula e outra decide o que fazer com '
                           'o resultado.\n'
                           '\n'
                           'Exercício guiado: Crie funções para calcular área e perímetro de um retângulo.\n'
                           '\n'
                           'Desafio: Combine duas funções, fazendo a segunda receber o retorno da primeira.',
               'pyrtugues': 'função somar(a, b):\n    retornar a + b\n\nresultado = somar(4, 5)\nmostrar(resultado)',
               'python': 'def somar(a, b):\n    return a + b\n\nresultado = somar(4, 5)\nprint(resultado)',
               'explicacao': 'return encerra a execução da função e devolve um valor para quem chamou. Isso permite '
                             'construir programas em camadas, em que uma função calcula e outra decide o que fazer '
                             'com o resultado.',
               'exercicio': 'Crie funções para calcular área e perímetro de um retângulo.',
               'desafio': 'Combine duas funções, fazendo a segunda receber o retorno da primeira.',
               'dica': 'Diferencie mostrar na tela de retornar um valor.',
               'ordem': 48,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 12 — Funções',
               'titulo': 'Escopo e reutilização',
               'descricao': 'Entenda a diferença entre variáveis locais e o restante do programa.',
               'conteudo': 'Objetivo: Entenda a diferença entre variáveis locais e o restante do programa.\n'
                           '\n'
                           'Uma variável criada dentro de uma função normalmente pertence ao escopo local daquela '
                           'função. Manter dados locais reduz interferências e torna funções mais previsíveis.\n'
                           '\n'
                           'Exercício guiado: Crie uma função com uma variável local e outra global ao módulo.\n'
                           '\n'
                           'Desafio: Experimente retornar um valor em vez de depender de uma variável global.',
               'pyrtugues': 'definir = 0\n'
                            'função criar():\n'
                            '    mensagem = "local"\n'
                            '    mostrar(mensagem)\n'
                            '\n'
                            'criar()\n'
                            'mostrar(definir)',
               'python': 'definir = 0\n'
                         'def criar():\n'
                         '    mensagem = "local"\n'
                         '    print(mensagem)\n'
                         '\n'
                         'criar()\n'
                         'print(definir)',
               'explicacao': 'Uma variável criada dentro de uma função normalmente pertence ao escopo local daquela '
                             'função. Manter dados locais reduz interferências e torna funções mais previsíveis.',
               'exercicio': 'Crie uma função com uma variável local e outra global ao módulo.',
               'desafio': 'Experimente retornar um valor em vez de depender de uma variável global.',
               'dica': 'Prefira passar parâmetros e usar retorno em vez de espalhar estado global.',
               'ordem': 49,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 13 — Erros e exceções',
               'titulo': 'Erros de sintaxe, execução e lógica',
               'descricao': 'Aprenda a diferenciar tipos de problemas.',
               'conteudo': 'Objetivo: Aprenda a diferenciar tipos de problemas.\n'
                           '\n'
                           'Erros de sintaxe impedem o Python de entender o código; erros de execução acontecem '
                           'durante o programa; erros lógicos fazem o programa rodar com resultado errado. Saber '
                           'qual tipo ocorreu ajuda a escolher a correção.\n'
                           '\n'
                           'Exercício guiado: Liste um exemplo de cada tipo de erro.\n'
                           '\n'
                           'Desafio: Pegue um pequeno programa que produz resultado errado e descubra por quê.',
               'pyrtugues': 'mostrar("Começo")\n'
                            '# Exemplo conceitual de erro lógico:\n'
                            'resultado = 2 + 2\n'
                            'mostrar(resultado)',
               'python': 'print("Começo")\n# Exemplo conceitual de erro lógico:\nresultado = 2 + 2\nprint(resultado)',
               'explicacao': 'Erros de sintaxe impedem o Python de entender o código; erros de execução acontecem '
                             'durante o programa; erros lógicos fazem o programa rodar com resultado errado. Saber '
                             'qual tipo ocorreu ajuda a escolher a correção.',
               'exercicio': 'Liste um exemplo de cada tipo de erro.',
               'desafio': 'Pegue um pequeno programa que produz resultado errado e descubra por quê.',
               'dica': 'Leia a mensagem de erro antes de começar a mudar várias linhas.',
               'ordem': 50,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 13 — Erros e exceções',
               'titulo': 'try e except',
               'descricao': 'Trate uma falha previsível sem encerrar todo o programa.',
               'conteudo': 'Objetivo: Trate uma falha previsível sem encerrar todo o programa.\n'
                           '\n'
                           'try abriga o trecho que pode falhar e except define o tratamento para uma exceção '
                           'específica. Capturar apenas os erros esperados costuma deixar o comportamento mais '
                           'claro.\n'
                           '\n'
                           'Exercício guiado: Trate uma entrada que pode não ser numérica.\n'
                           '\n'
                           'Desafio: Trate dois tipos de erro de entrada com mensagens diferentes.',
               'pyrtugues': 'tentar:\n'
                            '    numero = inteiro(pergunte("Número: "))\n'
                            '    mostrar(numero * 2)\n'
                            'exceto ValueError:\n'
                            '    mostrar("Digite um número válido.")',
               'python': 'try:\n'
                         '    numero = int(input("Número: "))\n'
                         '    print(numero * 2)\n'
                         'except ValueError:\n'
                         '    print("Digite um número válido.")',
               'explicacao': 'try abriga o trecho que pode falhar e except define o tratamento para uma exceção '
                             'específica. Capturar apenas os erros esperados costuma deixar o comportamento mais '
                             'claro.',
               'exercicio': 'Trate uma entrada que pode não ser numérica.',
               'desafio': 'Trate dois tipos de erro de entrada com mensagens diferentes.',
               'dica': 'Evite capturar Exception sem necessidade em exercícios pequenos.',
               'ordem': 51,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 13 — Erros e exceções',
               'titulo': 'else e finalmente',
               'descricao': 'Entenda os blocos complementares do tratamento de exceções.',
               'conteudo': 'Objetivo: Entenda os blocos complementares do tratamento de exceções.\n'
                           '\n'
                           'else roda quando não houve exceção; finally roda sempre, tenha ocorrido erro ou não. '
                           'finally é útil para garantir que uma etapa de limpeza seja tentada.\n'
                           '\n'
                           'Exercício guiado: Faça um programa que mostre uma mensagem de sucesso no else e uma '
                           'mensagem final no finally.\n'
                           '\n'
                           'Desafio: Use finally para garantir uma mensagem de encerramento mesmo quando houver '
                           'erro.',
               'pyrtugues': 'tentar:\n'
                            '    numero = inteiro(pergunte("Número: "))\n'
                            'exceto ValueError:\n'
                            '    mostrar("Valor inválido")\n'
                            'senão:\n'
                            '    mostrar(numero * 2)\n'
                            'finalmente:\n'
                            '    mostrar("Fim da tentativa")',
               'python': 'try:\n'
                         '    numero = int(input("Número: "))\n'
                         'except ValueError:\n'
                         '    print("Valor inválido")\n'
                         'else:\n'
                         '    print(numero * 2)\n'
                         'finally:\n'
                         '    print("Fim da tentativa")',
               'explicacao': 'else roda quando não houve exceção; finally roda sempre, tenha ocorrido erro ou não. '
                             'finally é útil para garantir que uma etapa de limpeza seja tentada.',
               'exercicio': 'Faça um programa que mostre uma mensagem de sucesso no else e uma mensagem final no '
                            'finally.',
               'desafio': 'Use finally para garantir uma mensagem de encerramento mesmo quando houver erro.',
               'dica': 'Pense no fluxo: try → except ou else → finally.',
               'ordem': 52,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 13 — Erros e exceções',
               'titulo': 'levantar e afirmar',
               'descricao': 'Gere e verifique condições de erro de propósito.',
               'conteudo': 'Objetivo: Gere e verifique condições de erro de propósito.\n'
                           '\n'
                           'raise cria uma exceção de forma explícita; assert verifica uma condição que deveria ser '
                           'verdadeira. Os dois recursos ajudam a detectar estados inválidos.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que levante ValueError quando uma idade for negativa.\n'
                           '\n'
                           'Desafio: Adicione asserts a uma função de cálculo para validar resultados importantes.',
               'pyrtugues': 'função dividir(a, b):\n'
                            '    se b igual a 0:\n'
                            '        levantar ValueError("Divisor não pode ser zero")\n'
                            '    retornar a / b\n'
                            '\n'
                            'afirmar dividir(10, 2) == 5',
               'python': 'def dividir(a, b):\n'
                         '    if b == 0:\n'
                         '        raise ValueError("Divisor não pode ser zero")\n'
                         '    return a / b\n'
                         '\n'
                         'assert dividir(10, 2) == 5',
               'explicacao': 'raise cria uma exceção de forma explícita; assert verifica uma condição que deveria '
                             'ser verdadeira. Os dois recursos ajudam a detectar estados inválidos.',
               'exercicio': 'Crie uma função que levante ValueError quando uma idade for negativa.',
               'desafio': 'Adicione asserts a uma função de cálculo para validar resultados importantes.',
               'dica': 'Use assert como verificação de invariantes, não como substituto de validação de entrada do '
                       'usuário.',
               'ordem': 53,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
               'titulo': 'importar',
               'descricao': 'Use código de módulos da biblioteca padrão.',
               'conteudo': 'Objetivo: Use código de módulos da biblioteca padrão.\n'
                           '\n'
                           'importar traz um módulo para o programa. O dicionário do Pyrtugues oferece o nome '
                           'matemática para math, permitindo escrever importações de forma mais natural.\n'
                           '\n'
                           'Exercício guiado: Importe matemática e calcule uma raiz quadrada.\n'
                           '\n'
                           'Desafio: Use duas funções de math no mesmo programa.',
               'pyrtugues': 'importar matemática\nmostrar(matemática.sqrt(25))',
               'python': 'import math\nprint(math.sqrt(25))',
               'explicacao': 'importar traz um módulo para o programa. O dicionário do Pyrtugues oferece o nome '
                             'matemática para math, permitindo escrever importações de forma mais natural.',
               'exercicio': 'Importe matemática e calcule uma raiz quadrada.',
               'desafio': 'Use duas funções de math no mesmo programa.',
               'dica': 'Depois de importar um módulo, os recursos ficam acessíveis pelo nome do módulo.',
               'ordem': 54,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
               'titulo': 'de e como',
               'descricao': 'Controle de onde um recurso é importado e crie aliases.',
               'conteudo': 'Objetivo: Controle de onde um recurso é importado e crie aliases.\n'
                           '\n'
                           'from importa um recurso específico; as cria um nome alternativo. O Pyrtugues usa de e '
                           'como para essas construções.\n'
                           '\n'
                           'Exercício guiado: Importe uma função de math com alias em português.\n'
                           '\n'
                           'Desafio: Crie dois aliases de funções diferentes e compare a leitura do código.',
               'pyrtugues': 'de matemática importar sqrt como raiz\nmostrar(raiz(81))',
               'python': 'from math import sqrt as raiz\nprint(raiz(81))',
               'explicacao': 'from importa um recurso específico; as cria um nome alternativo. O Pyrtugues usa de e '
                             'como para essas construções.',
               'exercicio': 'Importe uma função de math com alias em português.',
               'desafio': 'Crie dois aliases de funções diferentes e compare a leitura do código.',
               'dica': 'Aliases devem tornar o código mais claro, não mais confuso.',
               'ordem': 55,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
               'titulo': 'random, datetime e time',
               'descricao': 'Conheça módulos úteis para programas interativos.',
               'conteudo': 'Objetivo: Conheça módulos úteis para programas interativos.\n'
                           '\n'
                           'random gera valores pseudoaleatórios; datetime trabalha com datas e horários; time '
                           'fornece recursos relacionados a tempo. Esses módulos aparecem em jogos, agendas e '
                           'programas de automação.\n'
                           '\n'
                           'Exercício guiado: Gere um número aleatório e mostre a data atual.\n'
                           '\n'
                           'Desafio: Crie um pequeno jogo que use um número aleatório e uma contagem de tentativas.',
               'pyrtugues': 'importar aleatório\n'
                            'importar datetime\n'
                            'importar tempo\n'
                            '\n'
                            'mostrar(aleatório.randint(1, 10))\n'
                            'mostrar(datetime.datetime.now())',
               'python': 'import random\n'
                         'import datetime\n'
                         'import time\n'
                         '\n'
                         'print(random.randint(1, 10))\n'
                         'print(datetime.datetime.now())',
               'explicacao': 'random gera valores pseudoaleatórios; datetime trabalha com datas e horários; time '
                             'fornece recursos relacionados a tempo. Esses módulos aparecem em jogos, agendas e '
                             'programas de automação.',
               'exercicio': 'Gere um número aleatório e mostre a data atual.',
               'desafio': 'Crie um pequeno jogo que use um número aleatório e uma contagem de tentativas.',
               'dica': 'Use o módulo adequado ao tipo de problema.',
               'ordem': 56,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 14 — Módulos e biblioteca padrão',
               'titulo': 'os e expressões regulares',
               'descricao': 'Conheça recursos básicos para sistema e busca textual.',
               'conteudo': 'Objetivo: Conheça recursos básicos para sistema e busca textual.\n'
                           '\n'
                           'os oferece operações do sistema operacional; re trabalha com expressões regulares. O '
                           'dicionário inclui os módulos e vários recursos, embora nem toda função avançada do '
                           'tradutor tenha um nome contextual.\n'
                           '\n'
                           'Exercício guiado: Mostre o diretório atual e encontre números dentro de um texto.\n'
                           '\n'
                           'Desafio: Crie um verificador simples que encontre padrões de telefone em um texto.',
               'pyrtugues': 'importar sistema\n'
                            'importar re\n'
                            '\n'
                            'mostrar(sistema.getcwd())\n'
                            'padrao = re.compilar(r"\\d+")\n'
                            'mostrar(padrao.findall("A12 B34"))',
               'python': 'import os\n'
                         'import re\n'
                         '\n'
                         'print(os.getcwd())\n'
                         'padrao = re.compile(r"\\d+")\n'
                         'print(padrao.findall("A12 B34"))',
               'explicacao': 'os oferece operações do sistema operacional; re trabalha com expressões regulares. O '
                             'dicionário inclui os módulos e vários recursos, embora nem toda função avançada do '
                             'tradutor tenha um nome contextual.',
               'exercicio': 'Mostre o diretório atual e encontre números dentro de um texto.',
               'desafio': 'Crie um verificador simples que encontre padrões de telefone em um texto.',
               'dica': 'Use regex com padrões pequenos antes de tentar expressões muito complexas.',
               'ordem': 57,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 15 — Projetos EDU',
               'titulo': 'Projeto: calculadora',
               'descricao': 'Combine entrada, conversão, funções e decisões em uma calculadora.',
               'conteudo': 'Objetivo: Combine entrada, conversão, funções e decisões em uma calculadora.\n'
                           '\n'
                           'O objetivo é reunir várias ideias do curso: entrada, conversão, função, condições e '
                           'exceções. Separar o cálculo em uma função deixa o programa mais fácil de testar e '
                           'ampliar.\n'
                           '\n'
                           'Exercício guiado: Implemente as quatro operações e teste casos normais.\n'
                           '\n'
                           'Desafio: Adicione potência, resto e tratamento para divisão por zero.',
               'pyrtugues': 'função calcular(a, b, operador):\n'
                            '    se operador == "+":\n'
                            '        retornar a + b\n'
                            '    senão se operador == "-":\n'
                            '        retornar a - b\n'
                            '    senão se operador == "*":\n'
                            '        retornar a * b\n'
                            '    senão se operador == "/":\n'
                            '        retornar a / b\n'
                            '    senão:\n'
                            '        levantar ValueError("Operador inválido")\n'
                            '\n'
                            'a = decimal(pergunte("Primeiro: "))\n'
                            'b = decimal(pergunte("Segundo: "))\n'
                            'op = pergunte("Operação (+,-,*,/): ")\n'
                            'mostrar(calcular(a, b, op))',
               'python': 'def calcular(a, b, operador):\n'
                         '    if operador == "+":\n'
                         '        return a + b\n'
                         '    elif operador == "-":\n'
                         '        return a - b\n'
                         '    elif operador == "*":\n'
                         '        return a * b\n'
                         '    elif operador == "/":\n'
                         '        return a / b\n'
                         '    else:\n'
                         '        raise ValueError("Operador inválido")\n'
                         '\n'
                         'a = float(input("Primeiro: "))\n'
                         'b = float(input("Segundo: "))\n'
                         'op = input("Operação (+,-,*,/): ")\n'
                         'print(calcular(a, b, op))',
               'explicacao': 'O objetivo é reunir várias ideias do curso: entrada, conversão, função, condições e '
                             'exceções. Separar o cálculo em uma função deixa o programa mais fácil de testar e '
                             'ampliar.',
               'exercicio': 'Implemente as quatro operações e teste casos normais.',
               'desafio': 'Adicione potência, resto e tratamento para divisão por zero.',
               'dica': 'Faça primeiro a versão mínima e depois amplie.',
               'ordem': 58,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 15 — Projetos EDU',
               'titulo': 'Projeto: conversor',
               'descricao': 'Transforme valores entre duas unidades usando funções.',
               'conteudo': 'Objetivo: Transforme valores entre duas unidades usando funções.\n'
                           '\n'
                           'Projetos de conversão são excelentes para praticar fórmulas, funções e entrada. A função '
                           'deve receber o valor e devolver o resultado, enquanto a interface cuida das mensagens.\n'
                           '\n'
                           'Exercício guiado: Crie um conversor de quilômetros para milhas.\n'
                           '\n'
                           'Desafio: Permita escolher entre três tipos de conversão.',
               'pyrtugues': 'função c_para_f(celsius):\n'
                            '    retornar celsius * 9 / 5 + 32\n'
                            '\n'
                            'c = decimal(pergunte("Temperatura em C: "))\n'
                            'mostrar(f"{c} C = {c_para_f(c)} F")',
               'python': 'def c_para_f(celsius):\n'
                         '    return celsius * 9 / 5 + 32\n'
                         '\n'
                         'c = float(input("Temperatura em C: "))\n'
                         'print(f"{c} C = {c_para_f(c)} F")',
               'explicacao': 'Projetos de conversão são excelentes para praticar fórmulas, funções e entrada. A '
                             'função deve receber o valor e devolver o resultado, enquanto a interface cuida das '
                             'mensagens.',
               'exercicio': 'Crie um conversor de quilômetros para milhas.',
               'desafio': 'Permita escolher entre três tipos de conversão.',
               'dica': 'Mantenha a fórmula isolada em funções pequenas.',
               'ordem': 59,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 15 — Projetos EDU',
               'titulo': 'Projeto: quiz',
               'descricao': 'Monte perguntas simples usando listas, condições e pontuação.',
               'conteudo': 'Objetivo: Monte perguntas simples usando listas, condições e pontuação.\n'
                           '\n'
                           'Um quiz usa coleções para guardar perguntas e respostas e um acumulador para contar '
                           'acertos. O mesmo padrão pode crescer para várias perguntas e diferentes regras.\n'
                           '\n'
                           'Exercício guiado: Adicione cinco perguntas e conte os acertos.\n'
                           '\n'
                           'Desafio: Mostre uma mensagem diferente de acordo com a porcentagem de acertos.',
               'pyrtugues': 'perguntas = ["2 + 2 = ?"]\n'
                            'respostas = ["4"]\n'
                            'pontuacao = 0\n'
                            '\n'
                            'para i em intervalo(0, tamanho(perguntas)):\n'
                            '    resposta = pergunte(perguntas[i] + " ")\n'
                            '    se resposta == respostas[i]:\n'
                            '        pontuacao mais igual 1\n'
                            '\n'
                            'mostrar(f"Pontuação: {pontuacao}/{tamanho(perguntas)}")',
               'python': 'perguntas = ["2 + 2 = ?"]\n'
                         'respostas = ["4"]\n'
                         'pontuacao = 0\n'
                         '\n'
                         'for i in range(0, len(perguntas)):\n'
                         '    resposta = input(perguntas[i] + " ")\n'
                         '    if resposta == respostas[i]:\n'
                         '        pontuacao += 1\n'
                         '\n'
                         'print(f"Pontuação: {pontuacao}/{len(perguntas)}")',
               'explicacao': 'Um quiz usa coleções para guardar perguntas e respostas e um acumulador para contar '
                             'acertos. O mesmo padrão pode crescer para várias perguntas e diferentes regras.',
               'exercicio': 'Adicione cinco perguntas e conte os acertos.',
               'desafio': 'Mostre uma mensagem diferente de acordo com a porcentagem de acertos.',
               'dica': 'Separar perguntas e respostas em estruturas paralelas é simples, mas dicionários podem ser '
                       'usados em versões futuras.',
               'ordem': 60,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 15 — Projetos EDU',
               'titulo': 'Projeto: lista de tarefas',
               'descricao': 'Crie uma lista de tarefas e um menu básico.',
               'conteudo': 'Objetivo: Crie uma lista de tarefas e um menu básico.\n'
                           '\n'
                           'Este projeto combina while, if/elif/else, listas e input. Um menu é um padrão importante '
                           'em programas de terminal porque mantém o usuário dentro de um fluxo interativo.\n'
                           '\n'
                           'Exercício guiado: Adicione remoção e marcação de tarefas concluídas.\n'
                           '\n'
                           'Desafio: Transforme cada tarefa em um dicionário com texto e status.',
               'pyrtugues': 'tarefas = []\n'
                            '\n'
                            'enquanto verdadeiro:\n'
                            '    mostrar("1 - adicionar")\n'
                            '    mostrar("2 - listar")\n'
                            '    mostrar("3 - sair")\n'
                            '    opcao = pergunte("Opção: ")\n'
                            '\n'
                            '    se opcao == "1":\n'
                            '        tarefa = pergunte("Tarefa: ")\n'
                            '        tarefas.adicionar(tarefa)\n'
                            '    senão se opcao == "2":\n'
                            '        para tarefa em tarefas:\n'
                            '            mostrar(tarefa)\n'
                            '    senão:\n'
                            '        quebrar\n'
                            '\n'
                            'mostrar("Fim")',
               'python': 'tarefas = []\n'
                         '\n'
                         'while True:\n'
                         '    print("1 - adicionar")\n'
                         '    print("2 - listar")\n'
                         '    print("3 - sair")\n'
                         '    opcao = input("Opção: ")\n'
                         '\n'
                         '    if opcao == "1":\n'
                         '        tarefa = input("Tarefa: ")\n'
                         '        tarefas.append(tarefa)\n'
                         '    elif opcao == "2":\n'
                         '        for tarefa in tarefas:\n'
                         '            print(tarefa)\n'
                         '    else:\n'
                         '        break\n'
                         '\n'
                         'print("Fim")',
               'explicacao': 'Este projeto combina while, if/elif/else, listas e input. Um menu é um padrão '
                             'importante em programas de terminal porque mantém o usuário dentro de um fluxo '
                             'interativo.',
               'exercicio': 'Adicione remoção e marcação de tarefas concluídas.',
               'desafio': 'Transforme cada tarefa em um dicionário com texto e status.',
               'dica': 'Evite aumentar a complexidade até a versão básica funcionar.',
               'ordem': 61,
               'nivel': 'EDU'},
              {'modulo': 'Módulo 16 — Funções avançadas',
               'titulo': 'Parâmetros padrão',
               'descricao': 'Defina valores usados quando um argumento não é enviado.',
               'conteudo': 'Objetivo: Defina valores usados quando um argumento não é enviado.\n'
                           '\n'
                           'Parâmetros padrão tornam funções mais convenientes sem obrigar o chamador a repetir '
                           'valores comuns. O argumento enviado explicitamente substitui o valor padrão.\n'
                           '\n'
                           'Exercício guiado: Crie uma função de desconto com uma porcentagem padrão.\n'
                           '\n'
                           'Desafio: Use dois parâmetros opcionais em uma função de relatório.',
               'pyrtugues': 'função saudar(nome, saudacao="Olá"):\n'
                            '    retornar f"{saudacao}, {nome}!"\n'
                            '\n'
                            'mostrar(saudar("Ana"))\n'
                            'mostrar(saudar("Ana", "Bom dia"))',
               'python': 'def saudar(nome, saudacao="Olá"):\n'
                         '    return f"{saudacao}, {nome}!"\n'
                         '\n'
                         'print(saudar("Ana"))\n'
                         'print(saudar("Ana", "Bom dia"))',
               'explicacao': 'Parâmetros padrão tornam funções mais convenientes sem obrigar o chamador a repetir '
                             'valores comuns. O argumento enviado explicitamente substitui o valor padrão.',
               'exercicio': 'Crie uma função de desconto com uma porcentagem padrão.',
               'desafio': 'Use dois parâmetros opcionais em uma função de relatório.',
               'dica': 'Defina padrões estáveis e fáceis de entender.',
               'ordem': 62,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 16 — Funções avançadas',
               'titulo': 'Argumentos nomeados',
               'descricao': 'Passe argumentos por nome para deixar chamadas explícitas.',
               'conteudo': 'Objetivo: Passe argumentos por nome para deixar chamadas explícitas.\n'
                           '\n'
                           'Argumentos nomeados associam um valor ao parâmetro pelo nome. Isso reduz a chance de '
                           'trocar a ordem de argumentos e pode deixar chamadas longas mais legíveis.\n'
                           '\n'
                           'Exercício guiado: Refaça uma chamada de função usando argumentos nomeados.\n'
                           '\n'
                           'Desafio: Crie uma função com quatro parâmetros e chame-a em duas ordens diferentes '
                           'usando nomes.',
               'pyrtugues': 'função ficha(nome, idade, cidade):\n'
                            '    retornar f"{nome} - {idade} - {cidade}"\n'
                            '\n'
                            'mostrar(ficha(cidade="SP", idade=14, nome="Lia"))',
               'python': 'def ficha(nome, idade, cidade):\n'
                         '    return f"{nome} - {idade} - {cidade}"\n'
                         '\n'
                         'print(ficha(cidade="SP", idade=14, nome="Lia"))',
               'explicacao': 'Argumentos nomeados associam um valor ao parâmetro pelo nome. Isso reduz a chance de '
                             'trocar a ordem de argumentos e pode deixar chamadas longas mais legíveis.',
               'exercicio': 'Refaça uma chamada de função usando argumentos nomeados.',
               'desafio': 'Crie uma função com quatro parâmetros e chame-a em duas ordens diferentes usando nomes.',
               'dica': 'Use argumentos posicionais para casos simples e nomeados quando clareza valer a pena.',
               'ordem': 63,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 16 — Funções avançadas',
               'titulo': '*args',
               'descricao': 'Receba uma quantidade variável de argumentos posicionais.',
               'conteudo': 'Objetivo: Receba uma quantidade variável de argumentos posicionais.\n'
                           '\n'
                           'O parâmetro com * reúne argumentos posicionais em uma tupla. Isso é útil quando a '
                           'quantidade de entradas pode variar.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que calcule a média de qualquer quantidade de notas.\n'
                           '\n'
                           'Desafio: Adicione uma validação para impedir uma média sem valores.',
               'pyrtugues': 'função somar_todos(*numeros):\n'
                            '    total = 0\n'
                            '    para numero em numeros:\n'
                            '        total mais igual numero\n'
                            '    retornar total\n'
                            '\n'
                            'mostrar(somar_todos(1, 2, 3, 4))',
               'python': 'def somar_todos(*numeros):\n'
                         '    total = 0\n'
                         '    for numero in numeros:\n'
                         '        total += numero\n'
                         '    return total\n'
                         '\n'
                         'print(somar_todos(1, 2, 3, 4))',
               'explicacao': 'O parâmetro com * reúne argumentos posicionais em uma tupla. Isso é útil quando a '
                             'quantidade de entradas pode variar.',
               'exercicio': 'Crie uma função que calcule a média de qualquer quantidade de notas.',
               'desafio': 'Adicione uma validação para impedir uma média sem valores.',
               'dica': 'Lembre que dentro da função o parâmetro *args é uma tupla.',
               'ordem': 64,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 16 — Funções avançadas',
               'titulo': '**kwargs',
               'descricao': 'Receba argumentos nomeados de quantidade variável.',
               'conteudo': 'Objetivo: Receba argumentos nomeados de quantidade variável.\n'
                           '\n'
                           'O parâmetro ** reúne argumentos nomeados em um dicionário. Esse padrão é comum em APIs, '
                           'configurações e funções adaptáveis.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que aceite opções de usuário.\n'
                           '\n'
                           'Desafio: Combine parâmetros normais, *args e **kwargs em uma função.',
               'pyrtugues': 'função configurar(**opcoes):\n'
                            '    mostrar(opcoes)\n'
                            '\n'
                            'configurar(tema="escuro", fonte=14)',
               'python': 'def configurar(**opcoes):\n    print(opcoes)\n\nconfigurar(tema="escuro", fonte=14)',
               'explicacao': 'O parâmetro ** reúne argumentos nomeados em um dicionário. Esse padrão é comum em '
                             'APIs, configurações e funções adaptáveis.',
               'exercicio': 'Crie uma função que aceite opções de usuário.',
               'desafio': 'Combine parâmetros normais, *args e **kwargs em uma função.',
               'dica': 'Use **kwargs quando as chaves forem realmente dinâmicas.',
               'ordem': 65,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 17 — Comprehensions',
               'titulo': 'List comprehension básica',
               'descricao': 'Crie uma lista transformando cada elemento de uma sequência.',
               'conteudo': 'Objetivo: Crie uma lista transformando cada elemento de uma sequência.\n'
                           '\n'
                           'List comprehensions condensam um padrão de criar lista a partir de outra coleção. Elas '
                           'continuam obedecendo a mesma lógica do for tradicional.\n'
                           '\n'
                           'Exercício guiado: Crie uma lista com os quadrados de 1 a 10.\n'
                           '\n'
                           'Desafio: Converta uma lista de nomes para maiúsculas em uma comprehension.',
               'pyrtugues': 'numeros = [1, 2, 3, 4]\ndobros = [numero * 2 para numero em numeros]\nmostrar(dobros)',
               'python': 'numeros = [1, 2, 3, 4]\ndobros = [numero * 2 for numero in numeros]\nprint(dobros)',
               'explicacao': 'List comprehensions condensam um padrão de criar lista a partir de outra coleção. Elas '
                             'continuam obedecendo a mesma lógica do for tradicional.',
               'exercicio': 'Crie uma lista com os quadrados de 1 a 10.',
               'desafio': 'Converta uma lista de nomes para maiúsculas em uma comprehension.',
               'dica': 'Use comprehension quando ela ficar mais legível que um laço equivalente.',
               'ordem': 66,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 17 — Comprehensions',
               'titulo': 'List comprehension com condição',
               'descricao': 'Filtre itens durante a criação da lista.',
               'conteudo': 'Objetivo: Filtre itens durante a criação da lista.\n'
                           '\n'
                           'Uma comprehension pode incluir if no final para selecionar quais elementos entram. É o '
                           'equivalente compacto de um for com condição e append().\n'
                           '\n'
                           'Exercício guiado: Crie uma lista somente com números maiores que 10.\n'
                           '\n'
                           'Desafio: Combine filtro e transformação na mesma expressão.',
               'pyrtugues': 'numeros = [1, 2, 3, 4, 5, 6]\n'
                            'pares = [numero para numero em numeros se numero % 2 == 0]\n'
                            'mostrar(pares)',
               'python': 'numeros = [1, 2, 3, 4, 5, 6]\n'
                         'pares = [numero for numero in numeros if numero % 2 == 0]\n'
                         'print(pares)',
               'explicacao': 'Uma comprehension pode incluir if no final para selecionar quais elementos entram. É o '
                             'equivalente compacto de um for com condição e append().',
               'exercicio': 'Crie uma lista somente com números maiores que 10.',
               'desafio': 'Combine filtro e transformação na mesma expressão.',
               'dica': 'Quando a expressão ficar longa demais, volte ao for tradicional.',
               'ordem': 67,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 17 — Comprehensions',
               'titulo': 'Set comprehension',
               'descricao': 'Construa um conjunto aplicando uma expressão.',
               'conteudo': 'Objetivo: Construa um conjunto aplicando uma expressão.\n'
                           '\n'
                           'Set comprehensions usam chaves para produzir um conjunto e eliminar duplicatas. A ideia '
                           'é semelhante à list comprehension, mas o resultado tem semântica de set.\n'
                           '\n'
                           'Exercício guiado: Extraia as primeiras letras de uma lista de palavras.\n'
                           '\n'
                           'Desafio: Crie um conjunto com categorias únicas de vários registros.',
               'pyrtugues': 'nomes = ["ana", "ana", "bia", "caio"]\n'
                            'iniciais = {nome[0] para nome em nomes}\n'
                            'mostrar(iniciais)',
               'python': 'nomes = ["ana", "ana", "bia", "caio"]\n'
                         'iniciais = {nome[0] for nome in nomes}\n'
                         'print(iniciais)',
               'explicacao': 'Set comprehensions usam chaves para produzir um conjunto e eliminar duplicatas. A '
                             'ideia é semelhante à list comprehension, mas o resultado tem semântica de set.',
               'exercicio': 'Extraia as primeiras letras de uma lista de palavras.',
               'desafio': 'Crie um conjunto com categorias únicas de vários registros.',
               'dica': 'Confirme se você precisa da unicidade antes de escolher set.',
               'ordem': 68,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 17 — Comprehensions',
               'titulo': 'Dict comprehension',
               'descricao': 'Construa dicionários de forma compacta.',
               'conteudo': 'Objetivo: Construa dicionários de forma compacta.\n'
                           '\n'
                           'Dict comprehensions produzem pares chave-valor. Elas são úteis para índices, tabelas de '
                           'conversão e transformações rápidas.\n'
                           '\n'
                           'Exercício guiado: Crie um dicionário de números para seus cubos.\n'
                           '\n'
                           'Desafio: Filtre apenas números pares ao construir o dicionário.',
               'pyrtugues': 'numeros = [1, 2, 3]\n'
                            'quadrados = {numero: numero * numero para numero em numeros}\n'
                            'mostrar(quadrados)',
               'python': 'numeros = [1, 2, 3]\n'
                         'quadrados = {numero: numero * numero for numero in numeros}\n'
                         'print(quadrados)',
               'explicacao': 'Dict comprehensions produzem pares chave-valor. Elas são úteis para índices, tabelas '
                             'de conversão e transformações rápidas.',
               'exercicio': 'Crie um dicionário de números para seus cubos.',
               'desafio': 'Filtre apenas números pares ao construir o dicionário.',
               'dica': 'Escolha uma chave que tenha significado para o dado.',
               'ordem': 69,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 18 — Programação funcional',
               'titulo': 'mapear()',
               'descricao': 'Aplique uma função a cada item de uma coleção.',
               'conteudo': 'Objetivo: Aplique uma função a cada item de uma coleção.\n'
                           '\n'
                           'map() devolve um iterável produzido ao aplicar uma função a cada elemento. Ele é útil '
                           'quando a transformação é simples e pode ser expressa claramente.\n'
                           '\n'
                           'Exercício guiado: Use map() para transformar uma lista de preços em preços com imposto.\n'
                           '\n'
                           'Desafio: Compare map() com uma list comprehension equivalente.',
               'pyrtugues': 'valores = [1, 2, 3]\ndobros = mapear(lambda n: n * 2, definir)\nmostrar(lista(dobros))',
               'python': 'valores = [1, 2, 3]\ndobros = map(lambda n: n * 2, valores)\nprint(list(dobros))',
               'explicacao': 'map() devolve um iterável produzido ao aplicar uma função a cada elemento. Ele é útil '
                             'quando a transformação é simples e pode ser expressa claramente.',
               'exercicio': 'Use map() para transformar uma lista de preços em preços com imposto.',
               'desafio': 'Compare map() com uma list comprehension equivalente.',
               'dica': 'Escolha a forma mais legível para o contexto.',
               'ordem': 70,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 18 — Programação funcional',
               'titulo': 'filtrar()',
               'descricao': 'Selecione elementos que atendem a uma condição.',
               'conteudo': 'Objetivo: Selecione elementos que atendem a uma condição.\n'
                           '\n'
                           'filter() mantém apenas os elementos cujo teste resulta em True. Assim como map(), ele '
                           'produz um iterável preguiçoso.\n'
                           '\n'
                           'Exercício guiado: Filtre notas aprovadas.\n'
                           '\n'
                           'Desafio: Compare filter() com comprehension e escolha uma justificativa.',
               'pyrtugues': 'valores = [1, 2, 3, 4, 5, 6]\n'
                            'pares = filtrar(lambda n: n % 2 == 0, valores)\n'
                            'mostrar(lista(pares))',
               'python': 'valores = [1, 2, 3, 4, 5, 6]\n'
                         'pares = filter(lambda n: n % 2 == 0, valores)\n'
                         'print(list(pares))',
               'explicacao': 'filter() mantém apenas os elementos cujo teste resulta em True. Assim como map(), ele '
                             'produz um iterável preguiçoso.',
               'exercicio': 'Filtre notas aprovadas.',
               'desafio': 'Compare filter() com comprehension e escolha uma justificativa.',
               'dica': 'Lembre que filter() não cria necessariamente uma lista imediatamente.',
               'ordem': 71,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 18 — Programação funcional',
               'titulo': 'zipar() e enumerar()',
               'descricao': 'Combine coleções e acompanhe posições.',
               'conteudo': 'Objetivo: Combine coleções e acompanhe posições.\n'
                           '\n'
                           'enumerate() fornece índice e valor; zip() percorre coleções em paralelo. Eles evitam '
                           'contadores manuais e acesso por índice quando o objetivo é combinar dados.\n'
                           '\n'
                           'Exercício guiado: Combine produtos e preços usando zip().\n'
                           '\n'
                           'Desafio: Use enumerate() para numerar itens de um menu.',
               'pyrtugues': 'nomes = ["Ana", "Bia"]\n'
                            'notas = [9, 8]\n'
                            'para posicao, nome em enumerar(nomes):\n'
                            '    mostrar(posicao, nome)\n'
                            '\n'
                            'para nome, nota em zipar(nomes, notas):\n'
                            '    mostrar(nome, nota)',
               'python': 'nomes = ["Ana", "Bia"]\n'
                         'notas = [9, 8]\n'
                         'for posicao, nome in enumerate(nomes):\n'
                         '    print(posicao, nome)\n'
                         '\n'
                         'for nome, nota in zip(nomes, notas):\n'
                         '    print(nome, nota)',
               'explicacao': 'enumerate() fornece índice e valor; zip() percorre coleções em paralelo. Eles evitam '
                             'contadores manuais e acesso por índice quando o objetivo é combinar dados.',
               'exercicio': 'Combine produtos e preços usando zip().',
               'desafio': 'Use enumerate() para numerar itens de um menu.',
               'dica': 'Confirme se as coleções combinadas têm tamanhos compatíveis com o que você espera.',
               'ordem': 72,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 18 — Programação funcional',
               'titulo': 'todos() e algum()',
               'descricao': 'Faça perguntas agregadas sobre uma coleção.',
               'conteudo': 'Objetivo: Faça perguntas agregadas sobre uma coleção.\n'
                           '\n'
                           'all() verifica se todos os elementos passam no teste; any() verifica se pelo menos um '
                           'passa. Esses recursos combinam bem com expressões geradoras.\n'
                           '\n'
                           'Exercício guiado: Teste se todas as notas estão dentro de uma faixa.\n'
                           '\n'
                           'Desafio: Teste se existe pelo menos um estoque zerado.',
               'pyrtugues': 'valores = [2, 4, 6]\n'
                            'mostrar(todos(numero % 2 == 0 para numero em valores))\n'
                            'mostrar(algum(numero > 5 para numero em valores))',
               'python': 'valores = [2, 4, 6]\n'
                         'print(all(numero % 2 == 0 for numero in valores))\n'
                         'print(any(numero > 5 for numero in valores))',
               'explicacao': 'all() verifica se todos os elementos passam no teste; any() verifica se pelo menos um '
                             'passa. Esses recursos combinam bem com expressões geradoras.',
               'exercicio': 'Teste se todas as notas estão dentro de uma faixa.',
               'desafio': 'Teste se existe pelo menos um estoque zerado.',
               'dica': 'Use all e any para expressar perguntas claramente.',
               'ordem': 73,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 19 — Iteradores e generators',
               'titulo': 'Iteradores com iter() e next()',
               'descricao': 'Entenda a interface básica de um iterador.',
               'conteudo': 'Objetivo: Entenda a interface básica de um iterador.\n'
                           '\n'
                           'Um iterador entrega valores um por vez. iter() cria o iterador e next() pede o próximo '
                           'valor até que não existam mais elementos.\n'
                           '\n'
                           'Exercício guiado: Crie um iterador de uma lista e consuma todos os elementos.\n'
                           '\n'
                           'Desafio: Capture StopIteration para detectar o fim manualmente.',
               'pyrtugues': 'valores = [10, 20, 30]\nit = iter(valores)\nmostrar(next(it))\nmostrar(next(it))',
               'python': 'valores = [10, 20, 30]\nit = iter(valores)\nprint(next(it))\nprint(next(it))',
               'explicacao': 'Um iterador entrega valores um por vez. iter() cria o iterador e next() pede o próximo '
                             'valor até que não existam mais elementos.',
               'exercicio': 'Crie um iterador de uma lista e consuma todos os elementos.',
               'desafio': 'Capture StopIteration para detectar o fim manualmente.',
               'dica': 'Prefira for quando você não precisa controlar manualmente cada chamada a next().',
               'ordem': 74,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 19 — Iteradores e generators',
               'titulo': 'Primeiro generator com produzir',
               'descricao': 'Use yield para produzir valores sob demanda.',
               'conteudo': 'Objetivo: Use yield para produzir valores sob demanda.\n'
                           '\n'
                           'Generators pausam a função em yield e continuam depois a partir daquele ponto. Isso '
                           'permite processar sequências sem criar todos os resultados de uma vez.\n'
                           '\n'
                           'Exercício guiado: Crie um generator de números pares.\n'
                           '\n'
                           'Desafio: Faça um generator que produza linhas de um texto processado.',
               'pyrtugues': 'função contar(limite):\n'
                            '    numero = 1\n'
                            '    enquanto numero menor ou igual a limite:\n'
                            '        produzir numero\n'
                            '        numero mais igual 1\n'
                            '\n'
                            'para valor em contar(3):\n'
                            '    mostrar(valor)',
               'python': 'def contar(limite):\n'
                         '    numero = 1\n'
                         '    while numero <= limite:\n'
                         '        yield numero\n'
                         '        numero += 1\n'
                         '\n'
                         'for valor in contar(3):\n'
                         '    print(valor)',
               'explicacao': 'Generators pausam a função em yield e continuam depois a partir daquele ponto. Isso '
                             'permite processar sequências sem criar todos os resultados de uma vez.',
               'exercicio': 'Crie um generator de números pares.',
               'desafio': 'Faça um generator que produza linhas de um texto processado.',
               'dica': 'Pense em generators quando a sequência puder ser grande ou calculada sob demanda.',
               'ordem': 75,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 19 — Iteradores e generators',
               'titulo': 'Generator expression',
               'descricao': 'Crie um iterador sem escrever uma função completa.',
               'conteudo': 'Objetivo: Crie um iterador sem escrever uma função completa.\n'
                           '\n'
                           'Generator expressions usam parênteses e produzem valores sob demanda. Elas se encaixam '
                           'bem com sum(), all(), any() e outras operações agregadas.\n'
                           '\n'
                           'Exercício guiado: Some os quadrados de 1 a 100 usando generator expression.\n'
                           '\n'
                           'Desafio: Compare memória conceitual entre list comprehension e generator expression.',
               'pyrtugues': 'valores = (numero * 2 para numero em intervalo(5))\nmostrar(tamanho(lista(valores)))',
               'python': 'valores = (numero * 2 for numero in range(5))\nprint(len(list(valores)))',
               'explicacao': 'Generator expressions usam parênteses e produzem valores sob demanda. Elas se encaixam '
                             'bem com sum(), all(), any() e outras operações agregadas.',
               'exercicio': 'Some os quadrados de 1 a 100 usando generator expression.',
               'desafio': 'Compare memória conceitual entre list comprehension e generator expression.',
               'dica': 'Um generator é consumido conforme os valores são lidos.',
               'ordem': 76,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 19 — Iteradores e generators',
               'titulo': 'Iterator personalizado',
               'descricao': 'Implemente __iter__ e __next__ em uma classe.',
               'conteudo': 'Objetivo: Implemente __iter__ e __next__ em uma classe.\n'
                           '\n'
                           'Um objeto pode se tornar iterável implementando __iter__ e __next__. Isso ensina como o '
                           'for conversa com objetos iteradores internamente.\n'
                           '\n'
                           'Exercício guiado: Crie um iterador que conte de trás para frente.\n'
                           '\n'
                           'Desafio: Permita definir passo e início no construtor.',
               'pyrtugues': 'classe Contador:\n'
                            '    função __init__(self, limite):\n'
                            '        self.atual = 0\n'
                            '        self.limite = limite\n'
                            '\n'
                            '    função __iter__(self):\n'
                            '        retornar self\n'
                            '\n'
                            '    função __next__(self):\n'
                            '        se self.atual >= self.limite:\n'
                            '            levantar StopIteration\n'
                            '        self.atual mais igual 1\n'
                            '        retornar self.atual\n'
                            '\n'
                            'para valor em Contador(3):\n'
                            '    mostrar(valor)',
               'python': 'class Contador:\n'
                         '    def __init__(self, limite):\n'
                         '        self.atual = 0\n'
                         '        self.limite = limite\n'
                         '\n'
                         '    def __iter__(self):\n'
                         '        return self\n'
                         '\n'
                         '    def __next__(self):\n'
                         '        if self.atual >= self.limite:\n'
                         '            raise StopIteration\n'
                         '        self.atual += 1\n'
                         '        return self.atual\n'
                         '\n'
                         'for valor in Contador(3):\n'
                         '    print(valor)',
               'explicacao': 'Um objeto pode se tornar iterável implementando __iter__ e __next__. Isso ensina como '
                             'o for conversa com objetos iteradores internamente.',
               'exercicio': 'Crie um iterador que conte de trás para frente.',
               'desafio': 'Permita definir passo e início no construtor.',
               'dica': 'Use StopIteration para sinalizar o final.',
               'ordem': 77,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 20 — Arquivos',
               'titulo': 'Abrindo arquivos',
               'descricao': 'Leia um arquivo texto usando open().',
               'conteudo': 'Objetivo: Leia um arquivo texto usando open().\n'
                           '\n'
                           'open() cria uma relação com o arquivo. Depois de ler, fechar o arquivo libera o recurso; '
                           'em programas modernos, with costuma ser preferível porque fecha o arquivo '
                           'automaticamente.\n'
                           '\n'
                           'Exercício guiado: Leia um arquivo e mostre seu conteúdo.\n'
                           '\n'
                           'Desafio: Conte quantas linhas o arquivo possui.',
               'pyrtugues': 'arquivo = abrir("notas.txt", "r", encoding="utf-8")\n'
                            'conteudo = arquivo.ler()\n'
                            'arquivo.fechar()\n'
                            'mostrar(conteudo)',
               'python': 'arquivo = open("notas.txt", "r", encoding="utf-8")\n'
                         'conteudo = arquivo.read()\n'
                         'arquivo.close()\n'
                         'print(conteudo)',
               'explicacao': 'open() cria uma relação com o arquivo. Depois de ler, fechar o arquivo libera o '
                             'recurso; em programas modernos, with costuma ser preferível porque fecha o arquivo '
                             'automaticamente.',
               'exercicio': 'Leia um arquivo e mostre seu conteúdo.',
               'desafio': 'Conte quantas linhas o arquivo possui.',
               'dica': "Use encoding='utf-8' para textos em português.",
               'ordem': 78,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 20 — Arquivos',
               'titulo': 'Escrevendo arquivos',
               'descricao': 'Grave texto em um arquivo.',
               'conteudo': 'Objetivo: Grave texto em um arquivo.\n'
                           '\n'
                           'O modo w cria ou substitui o arquivo. write() grava texto; por isso é importante pensar '
                           'antes se você quer sobrescrever ou acrescentar conteúdo.\n'
                           '\n'
                           'Exercício guiado: Crie um arquivo com três linhas.\n'
                           '\n'
                           'Desafio: Faça uma função que receba uma lista e grave cada item em uma linha.',
               'pyrtugues': 'arquivo = abrir("saida.txt", "w", encoding="utf-8")\n'
                            'arquivo.escrever("Primeira linha\\n")\n'
                            'arquivo.escrever("Segunda linha\\n")\n'
                            'arquivo.fechar()',
               'python': 'arquivo = open("saida.txt", "w", encoding="utf-8")\n'
                         'arquivo.write("Primeira linha\\n")\n'
                         'arquivo.write("Segunda linha\\n")\n'
                         'arquivo.close()',
               'explicacao': 'O modo w cria ou substitui o arquivo. write() grava texto; por isso é importante '
                             'pensar antes se você quer sobrescrever ou acrescentar conteúdo.',
               'exercicio': 'Crie um arquivo com três linhas.',
               'desafio': 'Faça uma função que receba uma lista e grave cada item em uma linha.',
               'dica': 'Use a escolha do modo de abertura com cuidado.',
               'ordem': 79,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 20 — Arquivos',
               'titulo': 'with para fechamento automático',
               'descricao': 'Deixe o Python controlar o fechamento do arquivo.',
               'conteudo': 'Objetivo: Deixe o Python controlar o fechamento do arquivo.\n'
                           '\n'
                           'O gerenciador de contexto with garante que o arquivo seja fechado ao sair do bloco, '
                           'inclusive em situações de erro. Isso reduz uma classe importante de esquecimentos.\n'
                           '\n'
                           'Exercício guiado: Reescreva um exemplo anterior usando with.\n'
                           '\n'
                           'Desafio: Adicione leitura e escrita no mesmo programa com dois contextos.',
               'pyrtugues': 'com abrir("saida.txt", "w", encoding="utf-8") como arquivo:\n'
                            '    arquivo.escrever("Conteúdo seguro")',
               'python': 'with open("saida.txt", "w", encoding="utf-8") as arquivo:\n'
                         '    arquivo.write("Conteúdo seguro")',
               'explicacao': 'O gerenciador de contexto with garante que o arquivo seja fechado ao sair do bloco, '
                             'inclusive em situações de erro. Isso reduz uma classe importante de esquecimentos.',
               'exercicio': 'Reescreva um exemplo anterior usando with.',
               'desafio': 'Adicione leitura e escrita no mesmo programa com dois contextos.',
               'dica': 'Prefira with em exemplos reais de leitura e gravação de arquivos.',
               'ordem': 80,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 20 — Arquivos',
               'titulo': 'Caminhos e pathlib',
               'descricao': 'Modele caminhos com pathlib.',
               'conteudo': 'Objetivo: Modele caminhos com pathlib.\n'
                           '\n'
                           'pathlib oferece objetos para representar caminhos e operações comuns de arquivos. No '
                           'Pyrtugues, caminhos é o nome traduzido usado para o módulo pathlib.\n'
                           '\n'
                           'Exercício guiado: Descubra se um arquivo existe e mostre seu caminho absoluto.\n'
                           '\n'
                           'Desafio: Liste arquivos de uma pasta e filtre por extensão.',
               'pyrtugues': 'importar caminhos\n'
                            'pasta = caminhos.Path(".")\n'
                            'mostrar(pasta.existe())\n'
                            'mostrar(pasta.resolve())',
               'python': 'import pathlib\npasta = pathlib.Path(".")\nprint(pasta.exists())\nprint(pasta.resolve())',
               'explicacao': 'pathlib oferece objetos para representar caminhos e operações comuns de arquivos. No '
                             'Pyrtugues, caminhos é o nome traduzido usado para o módulo pathlib.',
               'exercicio': 'Descubra se um arquivo existe e mostre seu caminho absoluto.',
               'desafio': 'Liste arquivos de uma pasta e filtre por extensão.',
               'dica': 'Evite montar caminhos complexos apenas concatenando strings.',
               'ordem': 81,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 21 — Dados e formatos',
               'titulo': 'JSON para dados estruturados',
               'descricao': 'Use json para salvar estruturas simples.',
               'conteudo': 'Objetivo: Use json para salvar estruturas simples.\n'
                           '\n'
                           'JSON representa dados estruturados de forma textual. O módulo json converte dicionários, '
                           'listas e valores simples para texto e de volta para objetos Python.\n'
                           '\n'
                           'Exercício guiado: Converta um dicionário simples para JSON.\n'
                           '\n'
                           'Desafio: Faça um ciclo completo: objeto → JSON → objeto.',
               'pyrtugues': 'importar json\n'
                            '\n'
                            'dados = {"nome": "Ana", "idade": 15}\n'
                            'texto = json_serializar_para_bytes(dados, ensure_ascii=False)\n'
                            'mostrar(texto)',
               'python': 'import json\n'
                         '\n'
                         'dados = {"nome": "Ana", "idade": 15}\n'
                         'texto = json.dumps(dados, ensure_ascii=False)\n'
                         'print(texto)',
               'explicacao': 'JSON representa dados estruturados de forma textual. O módulo json converte '
                             'dicionários, listas e valores simples para texto e de volta para objetos Python.',
               'exercicio': 'Converta um dicionário simples para JSON.',
               'desafio': 'Faça um ciclo completo: objeto → JSON → objeto.',
               'dica': 'Não confunda JSON em texto com o dicionário original.',
               'ordem': 82,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 21 — Dados e formatos',
               'titulo': 'JSON em arquivo',
               'descricao': 'Grave e leia dados JSON no disco.',
               'conteudo': 'Objetivo: Grave e leia dados JSON no disco.\n'
                           '\n'
                           'dump() e load() trabalham diretamente com arquivos JSON. O uso de indent melhora a '
                           'leitura humana do arquivo.\n'
                           '\n'
                           'Exercício guiado: Salve um cadastro de alunos em JSON.\n'
                           '\n'
                           'Desafio: Adicione atualização e remoção de registros e salve novamente.',
               'pyrtugues': 'importar json\n'
                            '\n'
                            'dados = {"tarefas": ["estudar", "praticar"]}\n'
                            'com abrir("tarefas.json", "w", encoding="utf-8") como arquivo:\n'
                            '    json_serializar_para_arquivo(dados, arquivo, ensure_ascii=False, indent=2)\n'
                            '\n'
                            'com abrir("tarefas.json", "r", encoding="utf-8") como arquivo:\n'
                            '    recuperado = json_desserializar_de_arquivo(arquivo)\n'
                            '\n'
                            'mostrar(recuperado)',
               'python': 'import json\n'
                         '\n'
                         'dados = {"tarefas": ["estudar", "praticar"]}\n'
                         'with open("tarefas.json", "w", encoding="utf-8") as arquivo:\n'
                         '    json.dump(dados, arquivo, ensure_ascii=False, indent=2)\n'
                         '\n'
                         'with open("tarefas.json", "r", encoding="utf-8") as arquivo:\n'
                         '    recuperado = json.load(arquivo)\n'
                         '\n'
                         'print(recuperado)',
               'explicacao': 'dump() e load() trabalham diretamente com arquivos JSON. O uso de indent melhora a '
                             'leitura humana do arquivo.',
               'exercicio': 'Salve um cadastro de alunos em JSON.',
               'desafio': 'Adicione atualização e remoção de registros e salve novamente.',
               'dica': 'Use UTF-8 e preserve acentos quando o arquivo for humano-legível.',
               'ordem': 83,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 21 — Dados e formatos',
               'titulo': 'CSV',
               'descricao': 'Trabalhe com dados tabulares simples.',
               'conteudo': 'Objetivo: Trabalhe com dados tabulares simples.\n'
                           '\n'
                           'CSV guarda dados em linhas e colunas, sendo comum em planilhas e exportações. O módulo '
                           'csv evita que você tenha de tratar manualmente separadores e aspas.\n'
                           '\n'
                           'Exercício guiado: Crie um CSV com produtos e preços.\n'
                           '\n'
                           'Desafio: Leia o arquivo e calcule a média de uma coluna numérica.',
               'pyrtugues': 'importar csv\n'
                            '\n'
                            'com abrir("alunos.csv", "w", newline="", encoding="utf-8") como arquivo:\n'
                            '    gravador = csv.writer(arquivo)\n'
                            '    gravador.writerow(["nome", "nota"])\n'
                            '    gravador.writerow(["Ana", 9])',
               'python': 'import csv\n'
                         '\n'
                         'with open("alunos.csv", "w", newline="", encoding="utf-8") as arquivo:\n'
                         '    gravador = csv.writer(arquivo)\n'
                         '    gravador.writerow(["nome", "nota"])\n'
                         '    gravador.writerow(["Ana", 9])',
               'explicacao': 'CSV guarda dados em linhas e colunas, sendo comum em planilhas e exportações. O módulo '
                             'csv evita que você tenha de tratar manualmente separadores e aspas.',
               'exercicio': 'Crie um CSV com produtos e preços.',
               'desafio': 'Leia o arquivo e calcule a média de uma coluna numérica.',
               'dica': 'Use DictReader/DictWriter quando o cabeçalho ajudar.',
               'ordem': 84,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 21 — Dados e formatos',
               'titulo': 'serialização e desserialização',
               'descricao': 'Escolha entre formatos e tipos de dados.',
               'conteudo': 'Objetivo: Escolha entre formatos e tipos de dados.\n'
                           '\n'
                           'Serialização transforma uma estrutura em uma representação persistível ou transferível; '
                           'desserialização faz o caminho inverso. JSON é adequado para dados compostos por tipos '
                           'simples.\n'
                           '\n'
                           'Exercício guiado: Converta um registro em JSON e de volta.\n'
                           '\n'
                           'Desafio: Compare JSON com CSV e diga qual se encaixa melhor em três cenários.',
               'pyrtugues': 'importar json\n'
                            '\n'
                            'dados = {"ativo": verdadeiro, "nulos": nulo, "valores": [1, 2, 3]}\n'
                            'texto = json_serializar_para_bytes(dados)\n'
                            'recuperado = json_desserializar_de_bytes(texto)\n'
                            'mostrar(recuperado)',
               'python': 'import json\n'
                         '\n'
                         'dados = {"ativo": True, "nulos": None, "valores": [1, 2, 3]}\n'
                         'texto = json.dumps(dados)\n'
                         'recuperado = json.loads(texto)\n'
                         'print(recuperado)',
               'explicacao': 'Serialização transforma uma estrutura em uma representação persistível ou '
                             'transferível; desserialização faz o caminho inverso. JSON é adequado para dados '
                             'compostos por tipos simples.',
               'exercicio': 'Converta um registro em JSON e de volta.',
               'desafio': 'Compare JSON com CSV e diga qual se encaixa melhor em três cenários.',
               'dica': 'Escolha o formato pela estrutura dos dados, não apenas pelo hábito.',
               'ordem': 85,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 22 — Exceções avançadas',
               'titulo': 'Hierarquia de exceções',
               'descricao': 'Conheça exceções comuns e sua relação com Exception.',
               'conteudo': 'Objetivo: Conheça exceções comuns e sua relação com Exception.\n'
                           '\n'
                           'Exceções específicas permitem tratamentos diferentes. Muitas exceções herdam de '
                           'Exception, que pode ser usada para agrupar casos relacionados quando necessário.\n'
                           '\n'
                           'Exercício guiado: Trate ValueError e IndexError separadamente.\n'
                           '\n'
                           'Desafio: Crie um fluxo que também trate KeyError em um dicionário.',
               'pyrtugues': 'tentar:\n'
                            '    indice = inteiro(pergunte("Índice: "))\n'
                            '    valores = [10, 20]\n'
                            '    mostrar(valores[indice])\n'
                            'exceto ValueError:\n'
                            '    mostrar("Índice não é inteiro")\n'
                            'exceto IndexError:\n'
                            '    mostrar("Índice fora da lista")',
               'python': 'try:\n'
                         '    indice = int(input("Índice: "))\n'
                         '    valores = [10, 20]\n'
                         '    print(valores[indice])\n'
                         'except ValueError:\n'
                         '    print("Índice não é inteiro")\n'
                         'except IndexError:\n'
                         '    print("Índice fora da lista")',
               'explicacao': 'Exceções específicas permitem tratamentos diferentes. Muitas exceções herdam de '
                             'Exception, que pode ser usada para agrupar casos relacionados quando necessário.',
               'exercicio': 'Trate ValueError e IndexError separadamente.',
               'desafio': 'Crie um fluxo que também trate KeyError em um dicionário.',
               'dica': 'Capture a exceção mais específica que faça sentido.',
               'ordem': 86,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 22 — Exceções avançadas',
               'titulo': 'raise from',
               'descricao': 'Relacione um erro novo ao erro original.',
               'conteudo': 'Objetivo: Relacione um erro novo ao erro original.\n'
                           '\n'
                           'raise ... from ... preserva a relação entre a exceção nova e a causa original. Isso é '
                           'útil em camadas de abstração, quando você quer oferecer uma mensagem mais adequada ao '
                           'domínio.\n'
                           '\n'
                           'Exercício guiado: Crie uma função que transforme um ValueError em uma exceção de domínio '
                           'mais clara.\n'
                           '\n'
                           'Desafio: Mostre uma cadeia de exceções em um pequeno exemplo.',
               'pyrtugues': 'tentar:\n'
                            '    valor = inteiro("abc")\n'
                            'exceto ValueError como erro_original:\n'
                            '    levantar RuntimeError("Falha ao converter") de erro_original',
               'python': 'try:\n'
                         '    valor = int("abc")\n'
                         'except ValueError as erro_original:\n'
                         '    raise RuntimeError("Falha ao converter") from erro_original',
               'explicacao': 'raise ... from ... preserva a relação entre a exceção nova e a causa original. Isso é '
                             'útil em camadas de abstração, quando você quer oferecer uma mensagem mais adequada ao '
                             'domínio.',
               'exercicio': 'Crie uma função que transforme um ValueError em uma exceção de domínio mais clara.',
               'desafio': 'Mostre uma cadeia de exceções em um pequeno exemplo.',
               'dica': 'Use encadeamento quando a causa original realmente for útil.',
               'ordem': 87,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 22 — Exceções avançadas',
               'titulo': 'Exceções personalizadas',
               'descricao': 'Crie um tipo específico para erros do seu domínio.',
               'conteudo': 'Objetivo: Crie um tipo específico para erros do seu domínio.\n'
                           '\n'
                           'Uma exceção personalizada permite distinguir um erro do seu próprio domínio dos erros '
                           'genéricos do Python. Ela normalmente herda de Exception.\n'
                           '\n'
                           'Exercício guiado: Crie uma exceção para idade inválida.\n'
                           '\n'
                           'Desafio: Use sua exceção personalizada em um pequeno sistema de cadastro.',
               'pyrtugues': 'classe SaldoInsuficienteError(Exception):\n'
                            '    passar\n'
                            '\n'
                            'função sacar(saldo, valor):\n'
                            '    se valor maior que saldo:\n'
                            '        levantar SaldoInsuficienteError("Saldo insuficiente")\n'
                            '    retornar saldo - valor',
               'python': 'class SaldoInsuficienteError(Exception):\n'
                         '    pass\n'
                         '\n'
                         'def sacar(saldo, valor):\n'
                         '    if valor > saldo:\n'
                         '        raise SaldoInsuficienteError("Saldo insuficiente")\n'
                         '    return saldo - valor',
               'explicacao': 'Uma exceção personalizada permite distinguir um erro do seu próprio domínio dos erros '
                             'genéricos do Python. Ela normalmente herda de Exception.',
               'exercicio': 'Crie uma exceção para idade inválida.',
               'desafio': 'Use sua exceção personalizada em um pequeno sistema de cadastro.',
               'dica': 'Escolha nomes de exceção que terminem em Error.',
               'ordem': 88,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 22 — Exceções avançadas',
               'titulo': 'finally para limpeza',
               'descricao': 'Garanta uma etapa que precisa ser tentada mesmo quando ocorre erro.',
               'conteudo': 'Objetivo: Garanta uma etapa que precisa ser tentada mesmo quando ocorre erro.\n'
                           '\n'
                           'finally é executado tanto em caso de sucesso quanto de erro. Com arquivos, conexões e '
                           'outros recursos, ele pode participar da estratégia de limpeza, embora with seja '
                           'preferível quando houver um gerenciador de contexto.\n'
                           '\n'
                           'Exercício guiado: Crie um exemplo que registre uma mensagem final em qualquer cenário.\n'
                           '\n'
                           'Desafio: Compare a solução com finally e a solução com with.',
               'pyrtugues': 'arquivo = nulo\n'
                            'tentar:\n'
                            '    arquivo = abrir("dados.txt", "r", encoding="utf-8")\n'
                            '    mostrar(arquivo.ler())\n'
                            'exceto OSError:\n'
                            '    mostrar("Não foi possível abrir")\n'
                            'finalmente:\n'
                            '    mostrar("Bloco de limpeza executado")',
               'python': 'arquivo = None\n'
                         'try:\n'
                         '    arquivo = open("dados.txt", "r", encoding="utf-8")\n'
                         '    print(arquivo.read())\n'
                         'except OSError:\n'
                         '    print("Não foi possível abrir")\n'
                         'finally:\n'
                         '    print("Bloco de limpeza executado")',
               'explicacao': 'finally é executado tanto em caso de sucesso quanto de erro. Com arquivos, conexões e '
                             'outros recursos, ele pode participar da estratégia de limpeza, embora with seja '
                             'preferível quando houver um gerenciador de contexto.',
               'exercicio': 'Crie um exemplo que registre uma mensagem final em qualquer cenário.',
               'desafio': 'Compare a solução com finally e a solução com with.',
               'dica': 'Prefira abstrações automáticas de limpeza quando existirem.',
               'ordem': 89,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 23 — Programação orientada a objetos',
               'titulo': 'Classes e objetos',
               'descricao': 'Modele entidades com classes e instâncias.',
               'conteudo': 'Objetivo: Modele entidades com classes e instâncias.\n'
                           '\n'
                           'Classe é um molde para criar objetos; objeto é uma instância desse molde. A orientação a '
                           'objetos organiza dados e comportamentos relacionados.\n'
                           '\n'
                           'Exercício guiado: Crie uma classe Produto e instancie dois objetos.\n'
                           '\n'
                           'Desafio: Adicione uma mensagem ao criar objetos de tipos diferentes.',
               'pyrtugues': 'classe Pessoa:\n    passar\n\nana = Pessoa()\nmostrar(tipo(ana))',
               'python': 'class Pessoa:\n    pass\n\nana = Pessoa()\nprint(type(ana))',
               'explicacao': 'Classe é um molde para criar objetos; objeto é uma instância desse molde. A orientação '
                             'a objetos organiza dados e comportamentos relacionados.',
               'exercicio': 'Crie uma classe Produto e instancie dois objetos.',
               'desafio': 'Adicione uma mensagem ao criar objetos de tipos diferentes.',
               'dica': 'Use classes quando dados e comportamentos formarem uma unidade clara.',
               'ordem': 90,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 23 — Programação orientada a objetos',
               'titulo': '__init__ e self',
               'descricao': 'Inicialize o estado de cada objeto.',
               'conteudo': 'Objetivo: Inicialize o estado de cada objeto.\n'
                           '\n'
                           'O método __init__ roda ao criar a instância. self representa o próprio objeto e permite '
                           'guardar atributos específicos daquela instância.\n'
                           '\n'
                           'Exercício guiado: Crie uma classe Livro com título e autor.\n'
                           '\n'
                           'Desafio: Adicione validação simples no __init__.',
               'pyrtugues': 'classe Pessoa:\n'
                            '    função __init__(self, nome, idade):\n'
                            '        self.nome = nome\n'
                            '        self.idade = idade\n'
                            '\n'
                            'ana = Pessoa("Ana", 15)\n'
                            'mostrar(ana.nome)\n'
                            'mostrar(ana.idade)',
               'python': 'class Pessoa:\n'
                         '    def __init__(self, nome, idade):\n'
                         '        self.nome = nome\n'
                         '        self.idade = idade\n'
                         '\n'
                         'ana = Pessoa("Ana", 15)\n'
                         'print(ana.nome)\n'
                         'print(ana.idade)',
               'explicacao': 'O método __init__ roda ao criar a instância. self representa o próprio objeto e '
                             'permite guardar atributos específicos daquela instância.',
               'exercicio': 'Crie uma classe Livro com título e autor.',
               'desafio': 'Adicione validação simples no __init__.',
               'dica': 'Não esqueça self nos métodos de instância.',
               'ordem': 91,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 23 — Programação orientada a objetos',
               'titulo': 'Métodos de instância',
               'descricao': 'Coloque comportamentos dentro da classe.',
               'conteudo': 'Objetivo: Coloque comportamentos dentro da classe.\n'
                           '\n'
                           'Métodos de instância recebem self e podem ler ou modificar atributos do objeto. Isso '
                           'aproxima o comportamento dos dados que ele utiliza.\n'
                           '\n'
                           'Exercício guiado: Crie um método para aumentar o saldo de uma conta.\n'
                           '\n'
                           'Desafio: Separe responsabilidades em dois ou três métodos pequenos.',
               'pyrtugues': 'classe Pessoa:\n'
                            '    função __init__(self, nome):\n'
                            '        self.nome = nome\n'
                            '\n'
                            '    função apresentar(self):\n'
                            '        retornar f"Olá, sou {self.nome}"\n'
                            '\n'
                            'ana = Pessoa("Ana")\n'
                            'mostrar(ana.apresentar())',
               'python': 'class Pessoa:\n'
                         '    def __init__(self, nome):\n'
                         '        self.nome = nome\n'
                         '\n'
                         '    def apresentar(self):\n'
                         '        return f"Olá, sou {self.nome}"\n'
                         '\n'
                         'ana = Pessoa("Ana")\n'
                         'print(ana.apresentar())',
               'explicacao': 'Métodos de instância recebem self e podem ler ou modificar atributos do objeto. Isso '
                             'aproxima o comportamento dos dados que ele utiliza.',
               'exercicio': 'Crie um método para aumentar o saldo de uma conta.',
               'desafio': 'Separe responsabilidades em dois ou três métodos pequenos.',
               'dica': 'Um método deve ter uma responsabilidade compreensível.',
               'ordem': 92,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 23 — Programação orientada a objetos',
               'titulo': 'Atributos de classe',
               'descricao': 'Compartilhe um valor entre instâncias quando isso fizer sentido.',
               'conteudo': 'Objetivo: Compartilhe um valor entre instâncias quando isso fizer sentido.\n'
                           '\n'
                           'Um atributo definido na classe pode ser compartilhado por todas as instâncias, enquanto '
                           'atributos definidos em self pertencem a cada objeto. Essa diferença é importante em '
                           'modelos de domínio.\n'
                           '\n'
                           'Exercício guiado: Crie um contador de objetos usando um atributo de classe.\n'
                           '\n'
                           'Desafio: Atualize o contador ao criar novas instâncias.',
               'pyrtugues': 'classe Pessoa:\n'
                            '    especie = "humano"\n'
                            '\n'
                            '    função __init__(self, nome):\n'
                            '        self.nome = nome\n'
                            '\n'
                            'a = Pessoa("Ana")\n'
                            'b = Pessoa("Bia")\n'
                            'mostrar(a.especie)\n'
                            'mostrar(b.especie)',
               'python': 'class Pessoa:\n'
                         '    especie = "humano"\n'
                         '\n'
                         '    def __init__(self, nome):\n'
                         '        self.nome = nome\n'
                         '\n'
                         'a = Pessoa("Ana")\n'
                         'b = Pessoa("Bia")\n'
                         'print(a.especie)\n'
                         'print(b.especie)',
               'explicacao': 'Um atributo definido na classe pode ser compartilhado por todas as instâncias, '
                             'enquanto atributos definidos em self pertencem a cada objeto. Essa diferença é '
                             'importante em modelos de domínio.',
               'exercicio': 'Crie um contador de objetos usando um atributo de classe.',
               'desafio': 'Atualize o contador ao criar novas instâncias.',
               'dica': 'Não use atributo de classe quando cada objeto precisar de um valor independente.',
               'ordem': 93,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 24 — OOP avançada',
               'titulo': 'Herança',
               'descricao': 'Crie uma classe especializada a partir de outra.',
               'conteudo': 'Objetivo: Crie uma classe especializada a partir de outra.\n'
                           '\n'
                           'Herança permite reutilizar estrutura e especializar comportamento. A classe filha recebe '
                           'membros da classe pai e pode substituí-los quando necessário.\n'
                           '\n'
                           'Exercício guiado: Crie uma classe Veiculo e duas subclasses.\n'
                           '\n'
                           'Desafio: Adicione um método comum e especialize outro em cada classe.',
               'pyrtugues': 'classe Animal:\n'
                            '    função falar(self):\n'
                            '        mostrar("Som")\n'
                            '\n'
                            'classe Cachorro(Animal):\n'
                            '    função falar(self):\n'
                            '        mostrar("Au!")\n'
                            '\n'
                            'c = Cachorro()\n'
                            'c.falar()',
               'python': 'class Animal:\n'
                         '    def falar(self):\n'
                         '        print("Som")\n'
                         '\n'
                         'class Cachorro(Animal):\n'
                         '    def falar(self):\n'
                         '        print("Au!")\n'
                         '\n'
                         'c = Cachorro()\n'
                         'c.falar()',
               'explicacao': 'Herança permite reutilizar estrutura e especializar comportamento. A classe filha '
                             'recebe membros da classe pai e pode substituí-los quando necessário.',
               'exercicio': 'Crie uma classe Veiculo e duas subclasses.',
               'desafio': 'Adicione um método comum e especialize outro em cada classe.',
               'dica': 'Use herança quando houver realmente uma relação de especialização.',
               'ordem': 94,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 24 — OOP avançada',
               'titulo': 'super()',
               'descricao': 'Reutilize a inicialização e os métodos da classe base.',
               'conteudo': 'Objetivo: Reutilize a inicialização e os métodos da classe base.\n'
                           '\n'
                           'super() acessa a implementação da classe base sem repetir código. Ele é muito útil '
                           'quando uma subclasse precisa ampliar o comportamento herdado.\n'
                           '\n'
                           'Exercício guiado: Adicione mais um atributo ao Aluno sem duplicar a inicialização do '
                           'nome.\n'
                           '\n'
                           'Desafio: Crie uma cadeia simples de herança com duas camadas.',
               'pyrtugues': 'classe Pessoa:\n'
                            '    função __init__(self, nome):\n'
                            '        self.nome = nome\n'
                            '\n'
                            'classe Aluno(Pessoa):\n'
                            '    função __init__(self, nome, nota):\n'
                            '        super().__init__(nome)\n'
                            '        self.nota = nota',
               'python': 'class Pessoa:\n'
                         '    def __init__(self, nome):\n'
                         '        self.nome = nome\n'
                         '\n'
                         'class Aluno(Pessoa):\n'
                         '    def __init__(self, nome, nota):\n'
                         '        super().__init__(nome)\n'
                         '        self.nota = nota',
               'explicacao': 'super() acessa a implementação da classe base sem repetir código. Ele é muito útil '
                             'quando uma subclasse precisa ampliar o comportamento herdado.',
               'exercicio': 'Adicione mais um atributo ao Aluno sem duplicar a inicialização do nome.',
               'desafio': 'Crie uma cadeia simples de herança com duas camadas.',
               'dica': 'Chame a classe base antes de usar atributos que ela cria.',
               'ordem': 95,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 24 — OOP avançada',
               'titulo': 'Polimorfismo',
               'descricao': 'Use a mesma interface para objetos de classes diferentes.',
               'conteudo': 'Objetivo: Use a mesma interface para objetos de classes diferentes.\n'
                           '\n'
                           'Polimorfismo permite que diferentes objetos respondam ao mesmo método de acordo com sua '
                           'implementação. O código que consome os objetos pode permanecer genérico.\n'
                           '\n'
                           'Exercício guiado: Crie duas classes com o mesmo método calcular().\n'
                           '\n'
                           'Desafio: Adicione uma terceira classe sem alterar o loop principal.',
               'pyrtugues': 'classe Cachorro:\n'
                            '    função falar(self):\n'
                            '        retornar "Au"\n'
                            '\n'
                            'classe Gato:\n'
                            '    função falar(self):\n'
                            '        retornar "Miau"\n'
                            '\n'
                            'animais = [Cachorro(), Gato()]\n'
                            'para animal em animais:\n'
                            '    mostrar(animal.falar())',
               'python': 'class Cachorro:\n'
                         '    def falar(self):\n'
                         '        return "Au"\n'
                         '\n'
                         'class Gato:\n'
                         '    def falar(self):\n'
                         '        return "Miau"\n'
                         '\n'
                         'animais = [Cachorro(), Gato()]\n'
                         'for animal in animais:\n'
                         '    print(animal.falar())',
               'explicacao': 'Polimorfismo permite que diferentes objetos respondam ao mesmo método de acordo com '
                             'sua implementação. O código que consome os objetos pode permanecer genérico.',
               'exercicio': 'Crie duas classes com o mesmo método calcular().',
               'desafio': 'Adicione uma terceira classe sem alterar o loop principal.',
               'dica': 'Programe contra a interface comum, não contra detalhes desnecessários.',
               'ordem': 96,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 24 — OOP avançada',
               'titulo': 'Encapsulamento e property',
               'descricao': 'Controle como um atributo é lido e alterado.',
               'conteudo': 'Objetivo: Controle como um atributo é lido e alterado.\n'
                           '\n'
                           'Um atributo com underscore costuma sinalizar um detalhe interno. property permite expor '
                           'acesso controlado como se fosse um atributo, centralizando regras de leitura ou '
                           'escrita.\n'
                           '\n'
                           'Exercício guiado: Crie uma classe com uma propriedade de preço.\n'
                           '\n'
                           'Desafio: Adicione um setter que rejeite valores negativos.',
               'pyrtugues': 'classe Conta:\n'
                            '    função __init__(self):\n'
                            '        self._saldo = 0\n'
                            '\n'
                            '    propriedade\n'
                            '    função saldo(self):\n'
                            '        retornar self._saldo',
               'python': 'class Conta:\n'
                         '    def __init__(self):\n'
                         '        self._saldo = 0\n'
                         '\n'
                         '    @property\n'
                         '    def saldo(self):\n'
                         '        return self._saldo',
               'explicacao': 'Um atributo com underscore costuma sinalizar um detalhe interno. property permite '
                             'expor acesso controlado como se fosse um atributo, centralizando regras de leitura ou '
                             'escrita.',
               'exercicio': 'Crie uma classe com uma propriedade de preço.',
               'desafio': 'Adicione um setter que rejeite valores negativos.',
               'dica': 'Use property quando houver uma regra de acesso; não como decoração sem necessidade.',
               'ordem': 97,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 25 — Decoradores e métodos especiais',
               'titulo': 'staticmethod',
               'descricao': 'Crie um método que não dependa de self.',
               'conteudo': 'Objetivo: Crie um método que não dependa de self.\n'
                           '\n'
                           'staticmethod cria uma função organizada dentro da classe, mas que não precisa acessar a '
                           'instância. É adequado quando o comportamento está relacionado conceitualmente à classe.\n'
                           '\n'
                           'Exercício guiado: Crie um método estático para validar uma senha simples.\n'
                           '\n'
                           'Desafio: Adicione um segundo método utilitário.',
               'pyrtugues': 'classe Matematica:\n'
                            '    método_estático\n'
                            '    função dobro(valor):\n'
                            '        retornar valor * 2\n'
                            '\n'
                            'mostrar(Matematica.dobro(5))',
               'python': 'class Matematica:\n'
                         '    @staticmethod\n'
                         '    def dobro(valor):\n'
                         '        return valor * 2\n'
                         '\n'
                         'print(Matematica.dobro(5))',
               'explicacao': 'staticmethod cria uma função organizada dentro da classe, mas que não precisa acessar '
                             'a instância. É adequado quando o comportamento está relacionado conceitualmente à '
                             'classe.',
               'exercicio': 'Crie um método estático para validar uma senha simples.',
               'desafio': 'Adicione um segundo método utilitário.',
               'dica': 'Se a função não usa estado da classe nem da instância, staticmethod pode ser uma opção.',
               'ordem': 98,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 25 — Decoradores e métodos especiais',
               'titulo': 'classmethod',
               'descricao': 'Crie métodos que recebem a classe em vez de uma instância.',
               'conteudo': 'Objetivo: Crie métodos que recebem a classe em vez de uma instância.\n'
                           '\n'
                           'classmethod recebe a própria classe por meio de cls. Isso permite construir métodos de '
                           'fábrica ou acessar atributos compartilhados da classe.\n'
                           '\n'
                           'Exercício guiado: Crie um contador de instâncias acessado pela classe.\n'
                           '\n'
                           'Desafio: Implemente uma fábrica alternativa para criar objetos.',
               'pyrtugues': 'classe Pessoa:\n'
                            '    quantidade = 0\n'
                            '\n'
                            '    método_de_classe\n'
                            '    função total(cls):\n'
                            '        retornar cls.quantidade',
               'python': 'class Pessoa:\n'
                         '    quantidade = 0\n'
                         '\n'
                         '    @classmethod\n'
                         '    def total(cls):\n'
                         '        return cls.quantidade',
               'explicacao': 'classmethod recebe a própria classe por meio de cls. Isso permite construir métodos de '
                             'fábrica ou acessar atributos compartilhados da classe.',
               'exercicio': 'Crie um contador de instâncias acessado pela classe.',
               'desafio': 'Implemente uma fábrica alternativa para criar objetos.',
               'dica': 'Use classmethod quando a operação depender da classe.',
               'ordem': 99,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 25 — Decoradores e métodos especiais',
               'titulo': 'Decoradores simples',
               'descricao': 'Entenda uma função que recebe e devolve outra função.',
               'conteudo': 'Objetivo: Entenda uma função que recebe e devolve outra função.\n'
                           '\n'
                           'Decoradores envolvem uma função e adicionam comportamento sem editar seu corpo. O '
                           'símbolo @ é apenas uma forma conveniente de aplicar esse padrão.\n'
                           '\n'
                           'Exercício guiado: Crie um decorador que mostre uma mensagem antes e depois da função.\n'
                           '\n'
                           'Desafio: Use functools.wraps para preservar metadados.',
               'pyrtugues': 'função anunciar(funcao):\n'
                            '    função interna(*args, **kwargs):\n'
                            '        mostrar("Executando...")\n'
                            '        retornar funcao(*args, **kwargs)\n'
                            '    retornar interna\n'
                            '\n'
                            '@anunciar\n'
                            'função saudar():\n'
                            '    mostrar("Olá")\n'
                            '\n'
                            'saudar()',
               'python': 'def anunciar(funcao):\n'
                         '    def interna(*args, **kwargs):\n'
                         '        print("Executando...")\n'
                         '        return funcao(*args, **kwargs)\n'
                         '    return interna\n'
                         '\n'
                         '@anunciar\n'
                         'def saudar():\n'
                         '    print("Olá")\n'
                         '\n'
                         'saudar()',
               'explicacao': 'Decoradores envolvem uma função e adicionam comportamento sem editar seu corpo. O '
                             'símbolo @ é apenas uma forma conveniente de aplicar esse padrão.',
               'exercicio': 'Crie um decorador que mostre uma mensagem antes e depois da função.',
               'desafio': 'Use functools.wraps para preservar metadados.',
               'dica': 'Comece com decoradores simples antes de criar versões parametrizadas.',
               'ordem': 100,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 25 — Decoradores e métodos especiais',
               'titulo': 'Métodos especiais',
               'descricao': 'Descubra como objetos cooperam com o Python.',
               'conteudo': 'Objetivo: Descubra como objetos cooperam com o Python.\n'
                           '\n'
                           'Métodos especiais, como __repr__, permitem que classes participem naturalmente de '
                           'operações da linguagem. Eles seguem convenções do Python e devem ser implementados com '
                           'propósito claro.\n'
                           '\n'
                           'Exercício guiado: Implemente __repr__ para outra classe.\n'
                           '\n'
                           'Desafio: Experimente __len__ ou __eq__ em um objeto.',
               'pyrtugues': 'classe Produto:\n'
                            '    função __init__(self, nome, preco):\n'
                            '        self.nome = nome\n'
                            '        self.preco = preco\n'
                            '\n'
                            '    função __repr__(self):\n'
                            '        retornar f"Produto({self.nome!r}, {self.preco!r})"\n'
                            '\n'
                            'produto = Produto("Caderno", 20)\n'
                            'mostrar(produto)',
               'python': 'class Produto:\n'
                         '    def __init__(self, nome, preco):\n'
                         '        self.nome = nome\n'
                         '        self.preco = preco\n'
                         '\n'
                         '    def __repr__(self):\n'
                         '        return f"Produto({self.nome!r}, {self.preco!r})"\n'
                         '\n'
                         'produto = Produto("Caderno", 20)\n'
                         'print(produto)',
               'explicacao': 'Métodos especiais, como __repr__, permitem que classes participem naturalmente de '
                             'operações da linguagem. Eles seguem convenções do Python e devem ser implementados com '
                             'propósito claro.',
               'exercicio': 'Implemente __repr__ para outra classe.',
               'desafio': 'Experimente __len__ ou __eq__ em um objeto.',
               'dica': 'Leia a documentação do método especial antes de implementá-lo.',
               'ordem': 101,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 26 — Expressões regulares',
               'titulo': 're e search',
               'descricao': 'Procure padrões em um texto.',
               'conteudo': 'Objetivo: Procure padrões em um texto.\n'
                           '\n'
                           'Expressões regulares descrevem padrões de texto. search() procura uma ocorrência em '
                           'qualquer posição e devolve um objeto de correspondência quando encontra.\n'
                           '\n'
                           'Exercício guiado: Encontre um número dentro de uma frase.\n'
                           '\n'
                           'Desafio: Procure uma palavra que apareça no final do texto.',
               'pyrtugues': 'importar re\n'
                            '\n'
                            'texto = "Meu código é 12345"\n'
                            'encontrado = re.procurar(r"\\d+", texto)\n'
                            'mostrar(encontrado.group())',
               'python': 'import re\n'
                         '\n'
                         'texto = "Meu código é 12345"\n'
                         'encontrado = re.search(r"\\d+", texto)\n'
                         'print(encontrado.group())',
               'explicacao': 'Expressões regulares descrevem padrões de texto. search() procura uma ocorrência em '
                             'qualquer posição e devolve um objeto de correspondência quando encontra.',
               'exercicio': 'Encontre um número dentro de uma frase.',
               'desafio': 'Procure uma palavra que apareça no final do texto.',
               'dica': 'Use padrões simples antes de aumentar a complexidade.',
               'ordem': 102,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 26 — Expressões regulares',
               'titulo': 'findall',
               'descricao': 'Encontre todas as ocorrências de um padrão.',
               'conteudo': 'Objetivo: Encontre todas as ocorrências de um padrão.\n'
                           '\n'
                           'findall() devolve todas as correspondências de um padrão. É útil para extrair listas de '
                           'números, palavras ou identificadores.\n'
                           '\n'
                           'Exercício guiado: Extraia todos os números de uma mensagem.\n'
                           '\n'
                           'Desafio: Extraia todas as palavras que começam com uma letra específica.',
               'pyrtugues': 'importar re\ntexto = "A1 B22 C333"\nmostrar(re.encontrar_todos(r"\\d+", texto))',
               'python': 'import re\ntexto = "A1 B22 C333"\nprint(re.findall(r"\\d+", texto))',
               'explicacao': 'findall() devolve todas as correspondências de um padrão. É útil para extrair listas '
                             'de números, palavras ou identificadores.',
               'exercicio': 'Extraia todos os números de uma mensagem.',
               'desafio': 'Extraia todas as palavras que começam com uma letra específica.',
               'dica': 'Confira o padrão com exemplos pequenos.',
               'ordem': 103,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 26 — Expressões regulares',
               'titulo': 'Grupos e captura',
               'descricao': 'Separe partes de uma correspondência.',
               'conteudo': 'Objetivo: Separe partes de uma correspondência.\n'
                           '\n'
                           'Parênteses criam grupos de captura. group(1), group(2) e assim por diante permitem '
                           'acessar partes distintas de uma correspondência.\n'
                           '\n'
                           'Exercício guiado: Separe usuário e domínio de um e-mail simples.\n'
                           '\n'
                           'Desafio: Extraia dia, mês e ano de uma data textual.',
               'pyrtugues': 'importar re\n'
                            'padrao = re.compilar(r"(\\w+)@(\\w+\\.\\w+)")\n'
                            'resultado = padrao.search("ana@example.com")\n'
                            'mostrar(resultado.grupo(1))\n'
                            'mostrar(resultado.grupo(2))',
               'python': 'import re\n'
                         'padrao = re.compile(r"(\\w+)@(\\w+\\.\\w+)")\n'
                         'resultado = padrao.search("ana@example.com")\n'
                         'print(resultado.group(1))\n'
                         'print(resultado.group(2))',
               'explicacao': 'Parênteses criam grupos de captura. group(1), group(2) e assim por diante permitem '
                             'acessar partes distintas de uma correspondência.',
               'exercicio': 'Separe usuário e domínio de um e-mail simples.',
               'desafio': 'Extraia dia, mês e ano de uma data textual.',
               'dica': 'Regex de validação completa pode ficar complexa; comece pelo padrão que você realmente '
                       'precisa extrair.',
               'ordem': 104,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 26 — Expressões regulares',
               'titulo': 'sub e substituição',
               'descricao': 'Use regex para substituir padrões.',
               'conteudo': 'Objetivo: Use regex para substituir padrões.\n'
                           '\n'
                           'sub() procura todas as ocorrências compatíveis e substitui pelo novo texto. Isso permite '
                           'sanitizar ou normalizar grandes quantidades de texto.\n'
                           '\n'
                           'Exercício guiado: Remova números de uma frase.\n'
                           '\n'
                           'Desafio: Substitua diferentes separadores por um único separador.',
               'pyrtugues': 'importar re\ntexto = "abc123def456"\nnovo = re.sub(r"\\d+", "#", texto)\nmostrar(novo)',
               'python': 'import re\ntexto = "abc123def456"\nnovo = re.sub(r"\\d+", "#", texto)\nprint(novo)',
               'explicacao': 'sub() procura todas as ocorrências compatíveis e substitui pelo novo texto. Isso '
                             'permite sanitizar ou normalizar grandes quantidades de texto.',
               'exercicio': 'Remova números de uma frase.',
               'desafio': 'Substitua diferentes separadores por um único separador.',
               'dica': 'Teste primeiro o padrão em exemplos pequenos para não substituir demais.',
               'ordem': 105,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 27 — Biblioteca padrão',
               'titulo': 'os e sys',
               'descricao': 'Use informações do sistema operacional e do processo Python.',
               'conteudo': 'Objetivo: Use informações do sistema operacional e do processo Python.\n'
                           '\n'
                           'os e sys expõem informações e operações do ambiente onde o programa roda. Eles são úteis '
                           'quando um projeto precisa conhecer caminhos, argumentos ou detalhes do interpretador.\n'
                           '\n'
                           'Exercício guiado: Mostre diretório atual e versão do Python.\n'
                           '\n'
                           'Desafio: Use os para criar uma pequena listagem do ambiente.',
               'pyrtugues': 'importar sistema\n'
                            'importar sistema_python\n'
                            '\n'
                            'mostrar(sistema.getcwd())\n'
                            'mostrar(sistema_python.version_info)',
               'python': 'import os\nimport sys\n\nprint(os.getcwd())\nprint(sys.version_info)',
               'explicacao': 'os e sys expõem informações e operações do ambiente onde o programa roda. Eles são '
                             'úteis quando um projeto precisa conhecer caminhos, argumentos ou detalhes do '
                             'interpretador.',
               'exercicio': 'Mostre diretório atual e versão do Python.',
               'desafio': 'Use os para criar uma pequena listagem do ambiente.',
               'dica': 'Evite depender de caminhos absolutos fixos.',
               'ordem': 106,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 27 — Biblioteca padrão',
               'titulo': 'datetime e calendar',
               'descricao': 'Trabalhe com datas, horários e calendário.',
               'conteudo': 'Objetivo: Trabalhe com datas, horários e calendário.\n'
                           '\n'
                           'datetime oferece objetos e operações de data e hora; calendar traz funções relacionadas '
                           'a calendários. Juntos, eles resolvem problemas comuns de agenda e prazos.\n'
                           '\n'
                           'Exercício guiado: Mostre a data atual e quantos dias tem o mês atual.\n'
                           '\n'
                           'Desafio: Calcule quantos dias faltam para uma data futura.',
               'pyrtugues': 'importar datetime\n'
                            'importar calendário\n'
                            '\n'
                            'agora = datetime.datetime.now()\n'
                            'mostrar(agora)\n'
                            'mostrar(calendário.monthrange(2026, 10))',
               'python': 'import datetime\n'
                         'import calendar\n'
                         '\n'
                         'agora = datetime.datetime.now()\n'
                         'print(agora)\n'
                         'print(calendar.monthrange(2026, 10))',
               'explicacao': 'datetime oferece objetos e operações de data e hora; calendar traz funções '
                             'relacionadas a calendários. Juntos, eles resolvem problemas comuns de agenda e prazos.',
               'exercicio': 'Mostre a data atual e quantos dias tem o mês atual.',
               'desafio': 'Calcule quantos dias faltam para uma data futura.',
               'dica': 'Diferencie data de horário e considere fuso quando o projeto exigir.',
               'ordem': 107,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 27 — Biblioteca padrão',
               'titulo': 'collections',
               'descricao': 'Use estruturas especializadas da biblioteca collections.',
               'conteudo': 'Objetivo: Use estruturas especializadas da biblioteca collections.\n'
                           '\n'
                           'collections contém estruturas como Counter e deque que simplificam problemas frequentes. '
                           'Counter conta ocorrências; deque é eficiente para operações nas duas extremidades.\n'
                           '\n'
                           'Exercício guiado: Conte as palavras de uma lista.\n'
                           '\n'
                           'Desafio: Implemente uma fila de tarefas com deque.',
               'pyrtugues': 'importar coleções\n'
                            '\n'
                            'contagem = coleções.Counter(["a", "b", "a"])\n'
                            'mostrar(contagem)\n'
                            'fila = coleções.deque([1, 2])\n'
                            'fila.append(3)\n'
                            'mostrar(fila)',
               'python': 'import collections\n'
                         '\n'
                         'contagem = collections.Counter(["a", "b", "a"])\n'
                         'print(contagem)\n'
                         'fila = collections.deque([1, 2])\n'
                         'fila.append(3)\n'
                         'print(fila)',
               'explicacao': 'collections contém estruturas como Counter e deque que simplificam problemas '
                             'frequentes. Counter conta ocorrências; deque é eficiente para operações nas duas '
                             'extremidades.',
               'exercicio': 'Conte as palavras de uma lista.',
               'desafio': 'Implemente uma fila de tarefas com deque.',
               'dica': 'Use a estrutura especializada quando ela expressar melhor a intenção.',
               'ordem': 108,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 27 — Biblioteca padrão',
               'titulo': 'functools',
               'descricao': 'Descubra ferramentas para funções e decoradores.',
               'conteudo': 'Objetivo: Descubra ferramentas para funções e decoradores.\n'
                           '\n'
                           'functools oferece utilitários para funções, incluindo cache. lru_cache memoriza '
                           'resultados e pode acelerar funções puras com chamadas repetidas.\n'
                           '\n'
                           'Exercício guiado: Aplique cache a uma função recursiva.\n'
                           '\n'
                           'Desafio: Compare o tempo conceitual de uma versão sem cache e com cache.',
               'pyrtugues': 'importar funções_utilitárias\n'
                            '\n'
                            '@funções_utilitárias.lru_cache\n'
                            'função fib(n):\n'
                            '    se n menor que 2:\n'
                            '        retornar n\n'
                            '    retornar fib(n - 1) + fib(n - 2)\n'
                            '\n'
                            'mostrar(fib(20))',
               'python': 'import functools\n'
                         '\n'
                         '@functools.lru_cache\n'
                         'def fib(n):\n'
                         '    if n < 2:\n'
                         '        return n\n'
                         '    return fib(n - 1) + fib(n - 2)\n'
                         '\n'
                         'print(fib(20))',
               'explicacao': 'functools oferece utilitários para funções, incluindo cache. lru_cache memoriza '
                             'resultados e pode acelerar funções puras com chamadas repetidas.',
               'exercicio': 'Aplique cache a uma função recursiva.',
               'desafio': 'Compare o tempo conceitual de uma versão sem cache e com cache.',
               'dica': 'Cache depende de os argumentos serem adequados para a estratégia.',
               'ordem': 109,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 28 — Algoritmos e utilitários',
               'titulo': 'bisect',
               'descricao': 'Use busca binária para manter uma lista ordenada.',
               'conteudo': 'Objetivo: Use busca binária para manter uma lista ordenada.\n'
                           '\n'
                           'bisect trabalha com listas já ordenadas e encontra posições de inserção com busca '
                           'binária. É útil quando você precisa manter ordem sem procurar manualmente por toda a '
                           'lista.\n'
                           '\n'
                           'Exercício guiado: Encontre a posição de inserção de cinco valores.\n'
                           '\n'
                           'Desafio: Use insort para inserir mantendo a lista ordenada.',
               'pyrtugues': 'importar busca_binária\n'
                            '\n'
                            'valores = [10, 20, 30, 40]\n'
                            'posicao = busca_binária.bisect(valores, 25)\n'
                            'mostrar(posicao)',
               'python': 'import bisect\n'
                         '\n'
                         'valores = [10, 20, 30, 40]\n'
                         'posicao = bisect.bisect(valores, 25)\n'
                         'print(posicao)',
               'explicacao': 'bisect trabalha com listas já ordenadas e encontra posições de inserção com busca '
                             'binária. É útil quando você precisa manter ordem sem procurar manualmente por toda a '
                             'lista.',
               'exercicio': 'Encontre a posição de inserção de cinco valores.',
               'desafio': 'Use insort para inserir mantendo a lista ordenada.',
               'dica': 'A lista precisa estar ordenada para o resultado ser útil.',
               'ordem': 110,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 28 — Algoritmos e utilitários',
               'titulo': 'statistics',
               'descricao': 'Calcule medidas estatísticas simples.',
               'conteudo': 'Objetivo: Calcule medidas estatísticas simples.\n'
                           '\n'
                           'O módulo statistics fornece funções para média, mediana e outras medidas. Ele é útil '
                           'para relatórios simples sem precisar implementar as fórmulas manualmente.\n'
                           '\n'
                           'Exercício guiado: Calcule média e mediana de uma turma.\n'
                           '\n'
                           'Desafio: Compare média e mediana em conjuntos com valores extremos.',
               'pyrtugues': 'importar estatística\n'
                            '\n'
                            'notas = [7, 8, 9, 6]\n'
                            'mostrar(estatística.mean(notas))\n'
                            'mostrar(estatística.median(notas))',
               'python': 'import statistics\n'
                         '\n'
                         'notas = [7, 8, 9, 6]\n'
                         'print(statistics.mean(notas))\n'
                         'print(statistics.median(notas))',
               'explicacao': 'O módulo statistics fornece funções para média, mediana e outras medidas. Ele é útil '
                             'para relatórios simples sem precisar implementar as fórmulas manualmente.',
               'exercicio': 'Calcule média e mediana de uma turma.',
               'desafio': 'Compare média e mediana em conjuntos com valores extremos.',
               'dica': 'Escolha a medida de acordo com a pergunta que quer responder.',
               'ordem': 111,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 28 — Algoritmos e utilitários',
               'titulo': 'math',
               'descricao': 'Use funções matemáticas da biblioteca padrão.',
               'conteudo': 'Objetivo: Use funções matemáticas da biblioteca padrão.\n'
                           '\n'
                           'math reúne funções e constantes matemáticas. Além de sqrt, ceil e floor, o módulo possui '
                           'trigonometria, logaritmos e outras operações especializadas.\n'
                           '\n'
                           'Exercício guiado: Calcule raiz, arredondamento para cima e para baixo.\n'
                           '\n'
                           'Desafio: Crie uma função que calcule a área de um círculo.',
               'pyrtugues': 'importar matemática\n'
                            '\n'
                            'mostrar(matemática.sqrt(81))\n'
                            'mostrar(matemática.ceil(3.2))\n'
                            'mostrar(matemática.floor(3.8))',
               'python': 'import math\n\nprint(math.sqrt(81))\nprint(math.ceil(3.2))\nprint(math.floor(3.8))',
               'explicacao': 'math reúne funções e constantes matemáticas. Além de sqrt, ceil e floor, o módulo '
                             'possui trigonometria, logaritmos e outras operações especializadas.',
               'exercicio': 'Calcule raiz, arredondamento para cima e para baixo.',
               'desafio': 'Crie uma função que calcule a área de um círculo.',
               'dica': 'Pesquise a função matemática específica em vez de reinventá-la.',
               'ordem': 112,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 28 — Algoritmos e utilitários',
               'titulo': 'random',
               'descricao': 'Controle aleatoriedade para jogos e simulações.',
               'conteudo': 'Objetivo: Controle aleatoriedade para jogos e simulações.\n'
                           '\n'
                           'random oferece geração pseudoaleatória e escolha de itens. Em jogos e testes, isso '
                           'permite variar a execução de forma controlada.\n'
                           '\n'
                           'Exercício guiado: Simule um dado de seis lados.\n'
                           '\n'
                           'Desafio: Crie um sorteio sem repetir nomes.',
               'pyrtugues': 'importar aleatório\n'
                            '\n'
                            'mostrar(aleatório.randint(1, 6))\n'
                            'mostrar(aleatório.choice(["A", "B", "C"]))',
               'python': 'import random\n\nprint(random.randint(1, 6))\nprint(random.choice(["A", "B", "C"]))',
               'explicacao': 'random oferece geração pseudoaleatória e escolha de itens. Em jogos e testes, isso '
                             'permite variar a execução de forma controlada.',
               'exercicio': 'Simule um dado de seis lados.',
               'desafio': 'Crie um sorteio sem repetir nomes.',
               'dica': 'Aleatoriedade não substitui segurança criptográfica.',
               'ordem': 113,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 29 — Organização e programas de terminal',
               'titulo': '__name__ e ponto de entrada',
               'descricao': 'Separe código importável de código executado diretamente.',
               'conteudo': 'Objetivo: Separe código importável de código executado diretamente.\n'
                           '\n'
                           'A condição __name__ permite que um arquivo se comporte de modo diferente quando é '
                           'executado diretamente ou importado. É um padrão central de organização de módulos '
                           'Python.\n'
                           '\n'
                           'Exercício guiado: Crie um arquivo com uma função e uma seção principal.\n'
                           '\n'
                           'Desafio: Importe esse arquivo em outro e observe o que não deve executar '
                           'automaticamente.',
               'pyrtugues': 'se __name__ == "__main__":\n    mostrar("Executando como programa principal")',
               'python': 'if __name__ == "__main__":\n    print("Executando como programa principal")',
               'explicacao': 'A condição __name__ permite que um arquivo se comporte de modo diferente quando é '
                             'executado diretamente ou importado. É um padrão central de organização de módulos '
                             'Python.',
               'exercicio': 'Crie um arquivo com uma função e uma seção principal.',
               'desafio': 'Importe esse arquivo em outro e observe o que não deve executar automaticamente.',
               'dica': 'Mantenha o ponto de entrada pequeno.',
               'ordem': 114,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 29 — Organização e programas de terminal',
               'titulo': 'argparse',
               'descricao': 'Receba argumentos de linha de comando.',
               'conteudo': 'Objetivo: Receba argumentos de linha de comando.\n'
                           '\n'
                           'argparse transforma argumentos de terminal em dados estruturados. O dicionário do '
                           'Pyrtugues inclui vários nomes do módulo, então esse conteúdo pode ser mostrado '
                           'diretamente em sua forma traduzida.\n'
                           '\n'
                           'Exercício guiado: Crie uma opção --idade e mostre uma mensagem.\n'
                           '\n'
                           'Desafio: Adicione um argumento obrigatório e uma opção booleana.',
               'pyrtugues': 'importar argumentos_de_terminal\n'
                            '\n'
                            'analisador = argumentos_de_terminal.ArgumentParser()\n'
                            'analisador.add_argument("--nome", default="visitante")\n'
                            'args = analisador.parse_args()\n'
                            'mostrar(args.nome)',
               'python': 'import argparse\n'
                         '\n'
                         'analisador = argparse.ArgumentParser()\n'
                         'analisador.add_argument("--nome", default="visitante")\n'
                         'args = analisador.parse_args()\n'
                         'print(args.nome)',
               'explicacao': 'argparse transforma argumentos de terminal em dados estruturados. O dicionário do '
                             'Pyrtugues inclui vários nomes do módulo, então esse conteúdo pode ser mostrado '
                             'diretamente em sua forma traduzida.',
               'exercicio': 'Crie uma opção --idade e mostre uma mensagem.',
               'desafio': 'Adicione um argumento obrigatório e uma opção booleana.',
               'dica': 'Use mensagens de ajuda úteis.',
               'ordem': 115,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 29 — Organização e programas de terminal',
               'titulo': 'configparser',
               'descricao': 'Organize configurações simples em arquivos INI.',
               'conteudo': 'Objetivo: Organize configurações simples em arquivos INI.\n'
                           '\n'
                           'configparser lê e escreve arquivos de configuração no formato INI. Ele é útil quando o '
                           'usuário precisa editar opções sem alterar o código do programa.\n'
                           '\n'
                           'Exercício guiado: Crie uma seção de configurações para um aplicativo.\n'
                           '\n'
                           'Desafio: Salve e recarregue o arquivo INI.',
               'pyrtugues': 'importar configurador\n'
                            '\n'
                            'config = configurador.ConfigParser()\n'
                            'config["app"] = {"tema": "escuro", "fonte": "14"}\n'
                            'mostrar(config["app"]["tema"])',
               'python': 'import configparser\n'
                         '\n'
                         'config = configparser.ConfigParser()\n'
                         'config["app"] = {"tema": "escuro", "fonte": "14"}\n'
                         'print(config["app"]["tema"])',
               'explicacao': 'configparser lê e escreve arquivos de configuração no formato INI. Ele é útil quando o '
                             'usuário precisa editar opções sem alterar o código do programa.',
               'exercicio': 'Crie uma seção de configurações para um aplicativo.',
               'desafio': 'Salve e recarregue o arquivo INI.',
               'dica': 'Separe configurações de preferências de dados do usuário.',
               'ordem': 116,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 29 — Organização e programas de terminal',
               'titulo': 'Módulos e pacotes',
               'descricao': 'Organize projetos Python em arquivos menores.',
               'conteudo': 'Objetivo: Organize projetos Python em arquivos menores.\n'
                           '\n'
                           'Projetos maiores ficam mais fáceis de manter quando funções relacionadas são agrupadas '
                           'em módulos. Pacotes estendem essa ideia para conjuntos de módulos organizados em '
                           'diretórios.\n'
                           '\n'
                           'Exercício guiado: Separe duas funções de um projeto em um módulo utilidades.\n'
                           '\n'
                           'Desafio: Crie um pequeno pacote com dois módulos e uma função principal.',
               'pyrtugues': '# arquivo utilidades.py\n'
                            'função quadrado(n):\n'
                            '    retornar n * n\n'
                            '\n'
                            '# outro arquivo\n'
                            'importar utilidades\n'
                            'mostrar(utilidades.quadrado(5))',
               'python': '# arquivo utilidades.py\n'
                         'def quadrado(n):\n'
                         '    return n * n\n'
                         '\n'
                         '# outro arquivo\n'
                         'import utilidades\n'
                         'print(utilidades.quadrado(5))',
               'explicacao': 'Projetos maiores ficam mais fáceis de manter quando funções relacionadas são agrupadas '
                             'em módulos. Pacotes estendem essa ideia para conjuntos de módulos organizados em '
                             'diretórios.',
               'exercicio': 'Separe duas funções de um projeto em um módulo utilidades.',
               'desafio': 'Crie um pequeno pacote com dois módulos e uma função principal.',
               'dica': 'Dê nomes de módulos que descrevam o conteúdo.',
               'ordem': 117,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 30 — Debugging, testes e qualidade',
               'titulo': 'Lendo traceback',
               'descricao': 'Use o traceback para localizar a origem de um erro.',
               'conteudo': 'Objetivo: Use o traceback para localizar a origem de um erro.\n'
                           '\n'
                           'Um traceback mostra a cadeia de chamadas que levou ao erro e normalmente aponta arquivo, '
                           'linha e tipo de exceção. Aprender a ler essas informações reduz tentativas aleatórias de '
                           'correção.\n'
                           '\n'
                           'Exercício guiado: Provoque um IndexError e localize a linha no traceback.\n'
                           '\n'
                           'Desafio: Crie erros diferentes e classifique cada traceback.',
               'pyrtugues': 'valores = [10]\nmostrar(valores[5])',
               'python': 'valores = [10]\nprint(valores[5])',
               'explicacao': 'Um traceback mostra a cadeia de chamadas que levou ao erro e normalmente aponta '
                             'arquivo, linha e tipo de exceção. Aprender a ler essas informações reduz tentativas '
                             'aleatórias de correção.',
               'exercicio': 'Provoque um IndexError e localize a linha no traceback.',
               'desafio': 'Crie erros diferentes e classifique cada traceback.',
               'dica': 'Comece pela última linha do traceback e depois volte pela cadeia.',
               'ordem': 118,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 30 — Debugging, testes e qualidade',
               'titulo': 'assert como teste rápido',
               'descricao': 'Use assert para verificar invariantes e resultados.',
               'conteudo': 'Objetivo: Use assert para verificar invariantes e resultados.\n'
                           '\n'
                           'assert interrompe com AssertionError quando a condição é falsa. Ele é útil para '
                           'verificações internas e testes rápidos durante o desenvolvimento.\n'
                           '\n'
                           'Exercício guiado: Crie cinco asserts para uma função de cálculo.\n'
                           '\n'
                           'Desafio: Teste também entradas-limite.',
               'pyrtugues': 'função quadrado(n):\n'
                            '    retornar n * n\n'
                            '\n'
                            'afirmar quadrado(4) == 16\n'
                            'afirmar quadrado(-2) == 4',
               'python': 'def quadrado(n):\n    return n * n\n\nassert quadrado(4) == 16\nassert quadrado(-2) == 4',
               'explicacao': 'assert interrompe com AssertionError quando a condição é falsa. Ele é útil para '
                             'verificações internas e testes rápidos durante o desenvolvimento.',
               'exercicio': 'Crie cinco asserts para uma função de cálculo.',
               'desafio': 'Teste também entradas-limite.',
               'dica': 'Não use assert para validar dados que vêm do usuário em produção.',
               'ordem': 119,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 30 — Debugging, testes e qualidade',
               'titulo': 'Testes unitários',
               'descricao': 'Estruture pequenos testes automatizados.',
               'conteudo': 'Objetivo: Estruture pequenos testes automatizados.\n'
                           '\n'
                           'Testes unitários verificam pequenas unidades de comportamento. O módulo unittest fornece '
                           'classes e métodos para automatizar essas verificações.\n'
                           '\n'
                           'Exercício guiado: Crie um caso de teste para uma função de conversão.\n'
                           '\n'
                           'Desafio: Adicione testes para entradas válidas e inválidas.',
               'pyrtugues': 'importar testes_unitários\n'
                            '\n'
                            'classe TesteSoma(testes_unitários.TestCase):\n'
                            '    função teste_soma(self):\n'
                            '        self.assertEqual(2 + 2, 4)',
               'python': 'import unittest\n'
                         '\n'
                         'class TesteSoma(unittest.TestCase):\n'
                         '    def test_soma(self):\n'
                         '        self.assertEqual(2 + 2, 4)',
               'explicacao': 'Testes unitários verificam pequenas unidades de comportamento. O módulo unittest '
                             'fornece classes e métodos para automatizar essas verificações.',
               'exercicio': 'Crie um caso de teste para uma função de conversão.',
               'desafio': 'Adicione testes para entradas válidas e inválidas.',
               'dica': 'Um teste bom falha de forma clara quando o comportamento muda.',
               'ordem': 120,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 30 — Debugging, testes e qualidade',
               'titulo': 'Boas práticas e legibilidade',
               'descricao': 'Organize o código para que outra pessoa consiga mantê-lo.',
               'conteudo': 'Objetivo: Organize o código para que outra pessoa consiga mantê-lo.\n'
                           '\n'
                           'Código legível usa nomes claros, funções com responsabilidades pequenas e uma estrutura '
                           'previsível. Boas práticas não são enfeite: elas diminuem o custo de entender e alterar o '
                           'programa.\n'
                           '\n'
                           'Exercício guiado: Refatore um código confuso em funções pequenas.\n'
                           '\n'
                           'Desafio: Adicione nomes melhores, comentários úteis e tratamento de erros a um projeto '
                           'anterior.',
               'pyrtugues': 'função calcular_total(preco, quantidade):\n'
                            '    retornar preco * quantidade\n'
                            '\n'
                            'total = calcular_total(10, 3)\n'
                            'mostrar(total)',
               'python': 'def calcular_total(preco, quantidade):\n'
                         '    return preco * quantidade\n'
                         '\n'
                         'total = calcular_total(10, 3)\n'
                         'print(total)',
               'explicacao': 'Código legível usa nomes claros, funções com responsabilidades pequenas e uma '
                             'estrutura previsível. Boas práticas não são enfeite: elas diminuem o custo de entender '
                             'e alterar o programa.',
               'exercicio': 'Refatore um código confuso em funções pequenas.',
               'desafio': 'Adicione nomes melhores, comentários úteis e tratamento de erros a um projeto anterior.',
               'dica': 'Prefira simplicidade a abstrações que não resolvem um problema real.',
               'ordem': 121,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 31 — Projetos avançados',
               'titulo': 'Projeto: agenda em arquivo',
               'descricao': 'Construa uma agenda persistindo contatos.',
               'conteudo': 'Objetivo: Construa uma agenda persistindo contatos.\n'
                           '\n'
                           'Uma agenda combina listas de dicionários com funções. O próximo passo natural é '
                           'persistir esses registros em JSON para que o conteúdo sobreviva entre execuções.\n'
                           '\n'
                           'Exercício guiado: Implemente adicionar, listar e buscar.\n'
                           '\n'
                           'Desafio: Salve e carregue a agenda em JSON.',
               'pyrtugues': 'contatos = []\n'
                            '\n'
                            'função adicionar(nome, telefone):\n'
                            '    contatos.adicionar({"nome": nome, "telefone": telefone})\n'
                            '\n'
                            'função listar():\n'
                            '    para contato em contatos:\n'
                            '        mostrar(contato["nome"], "-", contato["telefone"])\n'
                            '\n'
                            'adicionar("Ana", "1111-1111")\n'
                            'adicionar("Bia", "2222-2222")\n'
                            'listar()',
               'python': 'contatos = []\n'
                         '\n'
                         'def adicionar(nome, telefone):\n'
                         '    contatos.append({"nome": nome, "telefone": telefone})\n'
                         '\n'
                         'def listar():\n'
                         '    for contato in contatos:\n'
                         '        print(contato["nome"], "-", contato["telefone"])\n'
                         '\n'
                         'adicionar("Ana", "1111-1111")\n'
                         'adicionar("Bia", "2222-2222")\n'
                         'listar()',
               'explicacao': 'Uma agenda combina listas de dicionários com funções. O próximo passo natural é '
                             'persistir esses registros em JSON para que o conteúdo sobreviva entre execuções.',
               'exercicio': 'Implemente adicionar, listar e buscar.',
               'desafio': 'Salve e carregue a agenda em JSON.',
               'dica': 'Mantenha leitura e escrita separadas da lógica de negócio.',
               'ordem': 122,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 31 — Projetos avançados',
               'titulo': 'Projeto: tarefas com JSON',
               'descricao': 'Construa uma lista de tarefas persistente.',
               'conteudo': 'Objetivo: Construa uma lista de tarefas persistente.\n'
                           '\n'
                           'Projetos persistentes separam estado em dados e comportamento em funções. JSON é '
                           'suficiente para uma lista simples de tarefas.\n'
                           '\n'
                           'Exercício guiado: Implemente inserir, concluir e remover.\n'
                           '\n'
                           'Desafio: Adicione filtros para abertas e concluídas.',
               'pyrtugues': 'importar json\n'
                            '\n'
                            'tarefas = [\n'
                            '    {"texto": "Estudar", "concluida": falso},\n'
                            '    {"texto": "Praticar", "concluida": verdadeiro}\n'
                            ']\n'
                            '\n'
                            'com abrir("tarefas.json", "w", encoding="utf-8") como arquivo:\n'
                            '    json_serializar_para_arquivo(tarefas, arquivo, ensure_ascii=False, indent=2)',
               'python': 'import json\n'
                         '\n'
                         'tarefas = [\n'
                         '    {"texto": "Estudar", "concluida": False},\n'
                         '    {"texto": "Praticar", "concluida": True}\n'
                         ']\n'
                         '\n'
                         'with open("tarefas.json", "w", encoding="utf-8") as arquivo:\n'
                         '    json.dump(tarefas, arquivo, ensure_ascii=False, indent=2)',
               'explicacao': 'Projetos persistentes separam estado em dados e comportamento em funções. JSON é '
                             'suficiente para uma lista simples de tarefas.',
               'exercicio': 'Implemente inserir, concluir e remover.',
               'desafio': 'Adicione filtros para abertas e concluídas.',
               'dica': 'Mantenha o formato do arquivo simples e consistente.',
               'ordem': 123,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 31 — Projetos avançados',
               'titulo': 'Projeto: inventário com classes',
               'descricao': 'Combine OOP, dicionários e persistência.',
               'conteudo': 'Objetivo: Combine OOP, dicionários e persistência.\n'
                           '\n'
                           'Um inventário orientado a objetos concentra regras de estoque no próprio objeto. Assim, '
                           'outras partes do programa chamam métodos em vez de manipular detalhes internos.\n'
                           '\n'
                           'Exercício guiado: Adicione preço, código e uma representação textual.\n'
                           '\n'
                           'Desafio: Persista o inventário em JSON usando uma camada de conversão.',
               'pyrtugues': 'classe Produto:\n'
                            '    função __init__(self, nome, estoque):\n'
                            '        self.nome = nome\n'
                            '        self.estoque = estoque\n'
                            '\n'
                            '    função adicionar(self, quantidade):\n'
                            '        self.estoque mais igual quantidade\n'
                            '\n'
                            '    função retirar(self, quantidade):\n'
                            '        se quantidade maior que self.estoque:\n'
                            '            levantar ValueError("Estoque insuficiente")\n'
                            '        self.estoque menos igual quantidade\n'
                            '\n'
                            'produto = Produto("Caderno", 10)\n'
                            'produto.retirar(3)\n'
                            'mostrar(produto.estoque)',
               'python': 'class Produto:\n'
                         '    def __init__(self, nome, estoque):\n'
                         '        self.nome = nome\n'
                         '        self.estoque = estoque\n'
                         '\n'
                         '    def adicionar(self, quantidade):\n'
                         '        self.estoque += quantidade\n'
                         '\n'
                         '    def retirar(self, quantidade):\n'
                         '        if quantidade > self.estoque:\n'
                         '            raise ValueError("Estoque insuficiente")\n'
                         '        self.estoque -= quantidade\n'
                         '\n'
                         'produto = Produto("Caderno", 10)\n'
                         'produto.retirar(3)\n'
                         'print(produto.estoque)',
               'explicacao': 'Um inventário orientado a objetos concentra regras de estoque no próprio objeto. '
                             'Assim, outras partes do programa chamam métodos em vez de manipular detalhes internos.',
               'exercicio': 'Adicione preço, código e uma representação textual.',
               'desafio': 'Persista o inventário em JSON usando uma camada de conversão.',
               'dica': 'Deixe as regras do domínio dentro dos métodos da classe.',
               'ordem': 124,
               'nivel': 'COMPLETO'},
              {'modulo': 'Módulo 31 — Projetos avançados',
               'titulo': 'Projeto final: sistema de estudos',
               'descricao': 'Combine funções, classes, arquivos, JSON, exceções e relatórios.',
               'conteudo': 'Objetivo: Combine funções, classes, arquivos, JSON, exceções e relatórios.\n'
                           '\n'
                           'O projeto final integra os principais padrões do curso: modelagem com classes, funções '
                           'para tarefas de infraestrutura, persistência em JSON e tratamento de estado. A estrutura '
                           'pode crescer para incluir pesquisa, filtros, relatórios e uma interface.\n'
                           '\n'
                           'Exercício guiado: Implemente listar, concluir, excluir e carregar do JSON.\n'
                           '\n'
                           'Desafio: Crie um relatório de progresso com percentuais e categorias.',
               'pyrtugues': 'classe Tarefa:\n'
                            '    função __init__(self, titulo, concluida=falso):\n'
                            '        self.titulo = titulo\n'
                            '        self.concluida = concluida\n'
                            '\n'
                            '    função concluir(self):\n'
                            '        self.concluida = verdadeiro\n'
                            '\n'
                            'função salvar(tarefas):\n'
                            '    dados = []\n'
                            '    para tarefa em tarefas:\n'
                            '        dados.append({"titulo": tarefa.titulo, "concluida": tarefa.concluida})\n'
                            '    com abrir("estudos.json", "w", encoding="utf-8") como arquivo:\n'
                            '        importar json\n'
                            '        json_serializar_para_arquivo(dados, arquivo, ensure_ascii=False, indent=2)\n'
                            '\n'
                            'tarefas = [Tarefa("Python"), Tarefa("Projeto")]\n'
                            'tarefas[0].concluir()\n'
                            'salvar(tarefas)',
               'python': 'class Tarefa:\n'
                         '    def __init__(self, titulo, concluida=False):\n'
                         '        self.titulo = titulo\n'
                         '        self.concluida = concluida\n'
                         '\n'
                         '    def concluir(self):\n'
                         '        self.concluida = True\n'
                         '\n'
                         'def salvar(tarefas):\n'
                         '    dados = []\n'
                         '    for tarefa in tarefas:\n'
                         '        dados.append({"titulo": tarefa.titulo, "concluida": tarefa.concluida})\n'
                         '    with open("estudos.json", "w", encoding="utf-8") as arquivo:\n'
                         '        import json\n'
                         '        json.dump(dados, arquivo, ensure_ascii=False, indent=2)\n'
                         '\n'
                         'tarefas = [Tarefa("Python"), Tarefa("Projeto")]\n'
                         'tarefas[0].concluir()\n'
                         'salvar(tarefas)',
               'explicacao': 'O projeto final integra os principais padrões do curso: modelagem com classes, funções '
                             'para tarefas de infraestrutura, persistência em JSON e tratamento de estado. A '
                             'estrutura pode crescer para incluir pesquisa, filtros, relatórios e uma interface.',
               'exercicio': 'Implemente listar, concluir, excluir e carregar do JSON.',
               'desafio': 'Crie um relatório de progresso com percentuais e categorias.',
               'dica': 'Construa primeiro o núcleo funcional e só depois adicione melhorias de interface.',
               'ordem': 125,
               'nivel': 'COMPLETO'}]}

def _curso_aulas(modo):
    return DADOS_CURSO.get(modo, DADOS_CURSO["edu"])

class JanelaBR(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pyrtugues — Python em português")
        self.geometry("1240x860")
        self.minsize(980, 720)
        ctk.set_appearance_mode("Dark")

        self.namespace = {}
        self.executando = False
        self.parar_evento = threading.Event()
        self._input_requests = Queue()
        self._input_atual = None
        self._input_janela = None
        self._timer_traducao = None
        self._thread_execucao = None

        # ===== Estado do aplicativo/curso integrado =====
        self.modo_aplicativo = "edu"
        self.modo_curso = "edu"
        self.indice_aula_curso = 0
        self.aulas_concluidas = {"edu": set(), "completo": set()}
        self._curso_botoes_aulas = {}
        self._curso_modulos_visiveis = []

        self.versao = "1.4.0"

        # ===== Identidade visual do Editor Web =====
        self.c_bg = "#070B12"
        self.c_panel = "#0E1624"
        self.c_card = "#101A2A"
        self.c_editor = "#0B1320"
        self.c_border = "#22324A"
        self.c_text = "#F8FAFC"
        self.c_muted = "#94A3B8"
        self.c_dim = "#5F718A"
        self.c_green = "#10B981"
        self.c_green_hover = "#059669"
        self.c_green_soft = "#6EE7B7"
        self.c_red = "#7F1D1D"

        self.configure(fg_color=self.c_bg)

        # ===== Topbar =====
        topo = ctk.CTkFrame(self, height=82, corner_radius=0, fg_color=self.c_panel)
        topo.pack(fill="x")
        topo.pack_propagate(False)

        marca = ctk.CTkFrame(topo, fg_color="transparent")
        marca.pack(side="left", padx=20)

        ctk.CTkLabel(
            marca,
            text="P",
            width=42,
            height=42,
            corner_radius=12,
            fg_color=self.c_green,
            text_color="#03241B",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left", padx=(0, 12))

        textos = ctk.CTkFrame(marca, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(
            textos,
            text="Pyrtugues",
            font=("Segoe UI", 21, "bold"),
            text_color=self.c_text,
        ).pack(anchor="w")
        ctk.CTkLabel(
            textos,
            text="Programação em português",
            font=("Segoe UI", 10),
            text_color=self.c_muted,
        ).pack(anchor="w")

        nav = ctk.CTkFrame(topo, fg_color="transparent")
        nav.pack(side="left", padx=(28, 0))
        self.nav_buttons = {}

        def nav_button(key, label):
            button = ctk.CTkButton(
                nav,
                text=label,
                command=lambda k=key: self._mostrar_pagina(k),
                fg_color=self.c_green if key == "editor" else "transparent",
                hover_color=self.c_green_hover if key == "editor" else "#182438",
                text_color="#03241B" if key == "editor" else self.c_muted,
                font=("Segoe UI", 11, "bold" if key == "editor" else "normal"),
                height=34,
                width=92,
                corner_radius=8,
                border_width=0 if key == "editor" else 1,
                border_color=self.c_border,
            )
            self.nav_buttons[key] = button
            return button

        nav_button("editor", "Editor").pack(side="left", padx=3)
        nav_button("exemplos", "Exemplos").pack(side="left", padx=3)
        nav_button("curso", "Curso").pack(side="left", padx=3)
        nav_button("sobre", "Sobre").pack(side="left", padx=3)

        status_area = ctk.CTkFrame(topo, fg_color="transparent")
        status_area.pack(side="right", padx=18)
        ctk.CTkLabel(
            status_area,
            text="PYRTUGUES  •  v1.4.0",
            font=("Consolas", 9, "bold"),
            text_color=self.c_green_soft,
        ).pack(side="left", padx=(0, 16))
        self.status_label = ctk.CTkLabel(
            status_area,
            text="●  Pronto",
            font=("Segoe UI", 10, "bold"),
            text_color=self.c_green_soft,
        )
        self.status_label.pack(side="left")

        # ===== Área onde as páginas são alternadas =====
        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True, padx=18, pady=16)

        self.pagina_selecao = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_editor = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_exemplos = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_curso = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_sobre = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent", corner_radius=0
        )

        self._construir_pagina_selecao()
        self._construir_pagina_editor()
        self._construir_pagina_exemplos()
        self._construir_pagina_curso()
        self._construir_pagina_sobre()

        # Primeiro mostramos a escolha EDU/COMPLETO dentro da própria janela.
        self._mostrar_pagina("selecao")
        self.bind("<Control-Return>", lambda e: self.executar_codigo())
        self.after_idle(self._configurar_editor_interno)
        self.carregar_exemplo()
        self.after(180, self._mostrar_seletor_inicial)


    def _construir_pagina_selecao(self):
        """Tela inicial de seleção EDU/COMPLETO, sem depender de sys.stdin."""
        page = self.pagina_selecao
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(
            page,
            fg_color=self.c_panel,
            corner_radius=18,
            border_width=1,
            border_color=self.c_border,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=40, pady=30)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            container,
            text="Bem-vindo ao Pyrtugues",
            font=("Segoe UI", 30, "bold"),
            text_color=self.c_text,
        ).grid(row=0, column=0, pady=(55, 8))

        ctk.CTkLabel(
            container,
            text="Escolha a versão do Pyrtugues que deseja usar",
            font=("Segoe UI", 14),
            text_color=self.c_muted,
        ).grid(row=1, column=0, pady=(0, 30))

        cards = ctk.CTkFrame(container, fg_color="transparent")
        cards.grid(row=2, column=0, padx=40, pady=(0, 30), sticky="ew")
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)

        def card(col, titulo, subtitulo, descricao, modo):
            card_frame = ctk.CTkFrame(
                cards, fg_color=self.c_card, corner_radius=16,
                border_width=1, border_color=self.c_border
            )
            card_frame.grid(row=0, column=col, sticky="nsew", padx=8)

            ctk.CTkLabel(
                card_frame, text=titulo,
                font=("Segoe UI", 24, "bold"), text_color=self.c_text
            ).pack(anchor="w", padx=22, pady=(24, 4))
            ctk.CTkLabel(
                card_frame, text=subtitulo,
                font=("Segoe UI", 12, "bold"), text_color=self.c_green_soft
            ).pack(anchor="w", padx=22)
            ctk.CTkLabel(
                card_frame, text=descricao,
                font=("Segoe UI", 10), text_color=self.c_muted,
                justify="left", wraplength=300, anchor="w"
            ).pack(fill="x", padx=22, pady=(12, 20))
            ctk.CTkButton(
                card_frame, text=f"Entrar no {titulo}", height=42, corner_radius=10,
                fg_color=self.c_green, hover_color=self.c_green_hover,
                text_color="#03241B", font=("Segoe UI", 11, "bold"),
                command=lambda m=modo: self._entrar_modo_inicial(m),
            ).pack(fill="x", padx=22, pady=(0, 22))

        card(
            0, "EDU", "Para começar",
            "Aprenda os fundamentos de programação e Python de forma progressiva,\ncom uma introdução mais simples ao Pyrtugues.",
            "edu"
        )
        card(
            1, "COMPLETO", "Para aprofundar",
            "Use o conjunto completo de traduções e acesse o curso aprofundado\ncom recursos avançados de Python.",
            "completo"
        )

        ctk.CTkLabel(
            container,
            text="Você poderá trocar entre EDU e COMPLETO depois pelo Curso.",
            font=("Segoe UI", 10), text_color=self.c_dim
        ).grid(row=4, column=0, pady=(0, 28))

    def _entrar_modo_inicial(self, modo):
        self._definir_modo_aplicativo(modo)
        self._mostrar_pagina("editor")

    def _construir_pagina_editor(self):
        """Monta o workspace principal: editor + Python lado a lado, terminal abaixo."""
        page = self.pagina_editor
        page.grid_rowconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=0)
        page.grid_rowconfigure(3, weight=1)
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)

        # ===== Workspace superior =====
        editor_card = ctk.CTkFrame(
            page,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        editor_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        editor_card.grid_rowconfigure(1, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)

        editor_header = ctk.CTkFrame(editor_card, fg_color="transparent", height=56)
        editor_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))
        editor_header.grid_columnconfigure(0, weight=1)
        editor_header.grid_columnconfigure(1, weight=0)
        editor_header.grid_propagate(False)

        left_head = ctk.CTkFrame(editor_header, fg_color="transparent")
        left_head.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left_head,
            text="Seu Código (.pyrt)",
            font=("Segoe UI", 14, "bold"),
            text_color=self.c_text,
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            left_head,
            text="Português Nativo",
            font=("Consolas", 9),
            text_color=self.c_green_soft,
        ).pack(anchor="w")
        ctk.CTkLabel(
            editor_header,
            text="Ctrl + Enter para executar",
            font=("Segoe UI", 9),
            text_color=self.c_dim,
        ).grid(row=0, column=1, sticky="e", pady=(14, 0))

        editor_frame = ctk.CTkFrame(
            editor_card,
            fg_color=self.c_editor,
            corner_radius=10,
            border_width=1,
            border_color=self.c_border,
        )
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(1, weight=1)

        self.numeros_linha = ctk.CTkTextbox(
            editor_frame,
            width=52,
            font=("Consolas", 14),
            fg_color="#09111C",
            text_color="#53647B",
            border_width=0,
            corner_radius=0,
            wrap="none",
            padx=12,
            pady=14,
            activate_scrollbars=False,
        )
        self.numeros_linha.grid(row=0, column=0, sticky="ns", padx=(2, 0), pady=2)
        self.numeros_linha.configure(state="disabled", cursor="arrow")
        self.numeros_linha._textbox.configure(
            spacing1=0, spacing2=0, spacing3=0, wrap="none", takefocus=0
        )

        self.caixa_codigo = ctk.CTkTextbox(
            editor_frame,
            font=("Consolas", 14),
            fg_color="#0D1421",
            text_color="#E2E8F0",
            border_width=0,
            corner_radius=10,
            wrap="none",
            padx=16,
            pady=14,
            undo=True,
        )
        self.caixa_codigo.grid(row=0, column=1, sticky="nsew", padx=(0, 2), pady=2)
        self.caixa_codigo._textbox.configure(spacing1=0, spacing2=0, spacing3=0, wrap="none")
        self.caixa_codigo._textbox.tag_configure("linha_atual", background="#101B2B")
        self.numeros_linha._textbox.tag_configure(
            "linha_atual_num", background="#0F1E31", foreground="#86EFAC"
        )
        self.caixa_codigo._textbox.configure(yscrollcommand=self._sincronizar_scroll_editor)

        self.caixa_codigo.bind("<KeyPress>", self._editor_keypress, add="+")
        self.caixa_codigo.bind("<KeyRelease>", self._editor_keyrelease, add="+")
        self.caixa_codigo.bind("<ButtonRelease-1>", self._editor_cursor_changed, add="+")
        self.caixa_codigo.bind("<MouseWheel>", self._editor_cursor_changed, add="+")
        self.caixa_codigo.bind("<Button-4>", self._editor_cursor_changed, add="+")
        self.caixa_codigo.bind("<Button-5>", self._editor_cursor_changed, add="+")
        self.caixa_codigo.bind("<FocusIn>", self._editor_cursor_changed, add="+")
        self.caixa_codigo.bind("<FocusOut>", self._editor_cursor_changed, add="+")

        # ===== Tradução lateral =====
        traducao_card = ctk.CTkFrame(
            page,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        traducao_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        traducao_card.grid_rowconfigure(1, weight=1)
        traducao_card.grid_columnconfigure(0, weight=1)

        traducao_head = ctk.CTkFrame(traducao_card, fg_color="transparent", height=56)
        traducao_head.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))
        traducao_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            traducao_head,
            text="Tradução em Tempo Real",
            font=("Segoe UI", 14, "bold"),
            text_color=self.c_text,
        ).grid(row=0, column=0, sticky="w", pady=(4, 0))
        ctk.CTkLabel(
            traducao_head,
            text="Python",
            font=("Consolas", 9, "bold"),
            text_color=self.c_green_soft,
        ).grid(row=1, column=0, sticky="w")

        preview_body = ctk.CTkFrame(traducao_card, fg_color="transparent")
        preview_body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        preview_body.grid_rowconfigure(0, weight=1)
        preview_body.grid_columnconfigure(0, weight=1)

        self.caixa_python_preview = ctk.CTkTextbox(
            preview_body,
            font=("Consolas", 12),
            fg_color="#09111C",
            text_color="#A7F3D0",
            border_width=1,
            border_color=self.c_border,
            corner_radius=9,
            wrap="none",
            padx=12,
            pady=10,
            activate_scrollbars=True,
        )
        self.caixa_python_preview.grid(row=0, column=0, sticky="nsew")
        self.caixa_python_preview.configure(state="disabled")

        preview_buttons = ctk.CTkFrame(preview_body, fg_color="transparent")
        preview_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        preview_buttons.grid_columnconfigure(0, weight=1)
        preview_buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            preview_buttons,
            text="Copiar",
            command=self.copiar_python,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            preview_buttons,
            text="Baixar .py",
            command=self.baixar_python,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            height=34,
            corner_radius=8,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # ===== Ações =====
        botoes = ctk.CTkFrame(page, fg_color="transparent", height=48)
        botoes.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        botoes.grid_propagate(False)

        self.btn_executar = ctk.CTkButton(
            botoes,
            text="▶  Executar código",
            command=self.executar_codigo,
            fg_color=self.c_green,
            hover_color=self.c_green_hover,
            text_color="#03241B",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=150,
            corner_radius=9,
        )
        self.btn_executar.pack(side="left")
        
        ctk.CTkButton(
            botoes,
            text="🔄  Traduzir",
            command=self._atualizar_preview_python,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            font=("Segoe UI", 11, "bold"),
            height=40,
            width=110,
            corner_radius=9,
        ).pack(side="left", padx=(8, 0))
        
        self.btn_parar = ctk.CTkButton(
            botoes,
            text="⏹  Parar",
            command=self.parar_execucao,
            fg_color=self.c_red,
            hover_color="#991B1B",
            text_color="#FEE2E2",
            font=("Segoe UI", 11, "bold"),
            height=40,
            width=100,
            corner_radius=9,
            state="disabled",
        )
        self.btn_parar.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            botoes,
            text="💡  Exemplos",
            command=self.abrir_exemplos,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            font=("Segoe UI", 11, "bold"),
            height=40,
            width=110,
            corner_radius=9,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            botoes,
            text="📚  Curso",
            command=lambda: self._mostrar_pagina("curso"),
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            font=("Segoe UI", 11, "bold"),
            height=40,
            width=100,
            corner_radius=9,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            botoes,
            text="🗑  Limpar saída",
            command=lambda: self.caixa_saida.delete("1.0", "end"),
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
            font=("Segoe UI", 11),
            height=40,
            width=125,
            corner_radius=9,
        ).pack(side="left", padx=(8, 0))

        # ===== Terminal abaixo dos dois painéis =====
        terminal_card = ctk.CTkFrame(
            page,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
            height=205,
        )
        terminal_card.grid(row=3, column=0, columnspan=2, sticky="nsew")
        terminal_card.grid_propagate(False)
        terminal_card.grid_rowconfigure(1, weight=1)
        terminal_card.grid_columnconfigure(0, weight=1)

        terminal_head = ctk.CTkFrame(terminal_card, fg_color="transparent", height=42)
        terminal_head.grid(row=0, column=0, sticky="ew", padx=14, pady=(6, 0))
        terminal_head.grid_propagate(False)
        ctk.CTkLabel(
            terminal_head,
            text="Saída do Terminal",
            font=("Segoe UI", 13, "bold"),
            text_color=self.c_text,
        ).pack(side="left")
        ctk.CTkLabel(
            terminal_head,
            text="Execução Interativa",
            font=("Consolas", 9),
            text_color=self.c_dim,
        ).pack(side="right")

        self.caixa_saida = ctk.CTkTextbox(
            terminal_card,
            font=("Consolas", 11),
            fg_color="#070B12",
            border_width=1,
            border_color=self.c_border,
            corner_radius=9,
            text_color="#86EFAC",
            wrap="none",
            padx=14,
            pady=10,
        )
        self.caixa_saida.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))


    def _construir_pagina_exemplos(self):
        """Biblioteca de exemplos dentro do mesmo app, sem abrir outra janela."""
        page = self.pagina_exemplos
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        hero = ctk.CTkFrame(
            page, fg_color=self.c_panel, corner_radius=14,
            border_width=1, border_color=self.c_border
        )
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            hero, text="Biblioteca de Exemplos", font=("Segoe UI", 24, "bold"),
            text_color=self.c_text
        ).pack(anchor="w", padx=22, pady=(18, 4))
        ctk.CTkLabel(
            hero,
            text="Escolha um exemplo, carregue no editor e continue editando livremente.",
            font=("Segoe UI", 11), text_color=self.c_muted
        ).pack(anchor="w", padx=22, pady=(0, 18))

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        exemplos = [
            ("👋", "Olá, mundo", "mostrar(\"Olá, mundo!\")", "Primeiro programa"),
            ("📦", "Variáveis", """nome = "Ana"
idade = 12
mostrar(f"Olá, {nome}! Você tem {idade} anos.")""", "Variáveis e f-strings"),
            ("🔀", "Condição", """idade = 15

se idade maior que 10:
    mostrar("Você pode continuar!")
senão:
    mostrar("Ainda é cedo.")""", "if / else em português"),
            ("🔁", "Repetição", """para i em intervalo(1, 6):
    mostrar(i)""", "for e range"),
            ("🧩", "Função", """função saudar(nome):
    mostrar(f"Olá, {nome}!")

saudar("Pyrtugues")""", "funções e parâmetros"),
            ("🧮", "Calculadora", """a = decimal(pergunte("Primeiro número: "))
b = decimal(pergunte("Segundo número: "))
mostrar(a + b)""", "entrada e operações"),
        ]

        for indice, (icone, titulo, codigo, descricao) in enumerate(exemplos):
            linha = indice // 2
            coluna = indice % 2
            card = ctk.CTkFrame(
                scroll, fg_color=self.c_card, corner_radius=14,
                border_width=1, border_color=self.c_border
            )
            card.grid(row=linha, column=coluna, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(
                card, text=f"{icone}  {titulo}",
                font=("Segoe UI", 14, "bold"), text_color=self.c_text, anchor="w"
            ).pack(fill="x", padx=14, pady=(14, 2))
            ctk.CTkLabel(
                card, text=descricao, font=("Segoe UI", 10),
                text_color=self.c_muted, anchor="w"
            ).pack(fill="x", padx=14, pady=(0, 8))
            preview = ctk.CTkTextbox(
                card, height=118, font=("Consolas", 10), fg_color="#09111C",
                text_color="#A7F3D0", border_width=1, border_color=self.c_border,
                corner_radius=8, wrap="none", padx=10, pady=8,
            )
            preview.pack(fill="x", padx=12, pady=(0, 10))
            preview.insert("1.0", codigo)
            preview.configure(state="disabled")
            ctk.CTkButton(
                card, text="Carregar no editor", height=34,
                fg_color=self.c_green, hover_color=self.c_green_hover,
                text_color="#03241B", font=("Segoe UI", 10, "bold"),
                command=lambda c=codigo: self._carregar_codigo(c),
            ).pack(fill="x", padx=12, pady=(0, 12))



    def _construir_pagina_curso(self):
        """Constrói o curso dentro da mesma janela do Pyrtugues."""
        page = self.pagina_curso
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=0)
        page.grid_columnconfigure(1, weight=1)

        # ===== Cabeçalho do curso =====
        hero = ctk.CTkFrame(
            page,
            fg_color=self.c_panel,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        hero.grid_columnconfigure(0, weight=1)

        titulo_area = ctk.CTkFrame(hero, fg_color="transparent")
        titulo_area.grid(row=0, column=0, sticky="w", padx=20, pady=16)

        ctk.CTkLabel(
            titulo_area,
            text="📚  Curso de Python",
            font=("Segoe UI", 24, "bold"),
            text_color=self.c_text,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            titulo_area,
            text="Aprenda Python progressivamente usando o Pyrtugues como ponte.",
            font=("Segoe UI", 10),
            text_color=self.c_muted,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        modos = ctk.CTkFrame(hero, fg_color="transparent")
        modos.grid(row=0, column=1, sticky="e", padx=20, pady=16)

        self.curso_btn_edu = ctk.CTkButton(
            modos,
            text="EDU",
            width=120,
            height=38,
            corner_radius=9,
            command=lambda: self._selecionar_modo_curso("edu"),
            font=("Segoe UI", 11, "bold"),
        )
        self.curso_btn_edu.pack(side="left", padx=4)

        self.curso_btn_completo = ctk.CTkButton(
            modos,
            text="COMPLETO",
            width=140,
            height=38,
            corner_radius=9,
            command=lambda: self._selecionar_modo_curso("completo"),
            font=("Segoe UI", 11, "bold"),
        )
        self.curso_btn_completo.pack(side="left", padx=4)

        # ===== Lista de aulas =====
        lista_card = ctk.CTkFrame(
            page,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
            width=300,
        )
        lista_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        lista_card.grid_propagate(False)
        lista_card.grid_rowconfigure(2, weight=1)
        lista_card.grid_columnconfigure(0, weight=1)

        topo_lista = ctk.CTkFrame(lista_card, fg_color="transparent")
        topo_lista.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        ctk.CTkLabel(
            topo_lista,
            text="Aulas",
            font=("Segoe UI", 15, "bold"),
            text_color=self.c_text,
        ).pack(side="left")

        self.curso_contador_label = ctk.CTkLabel(
            topo_lista,
            text="",
            font=("Consolas", 9, "bold"),
            text_color=self.c_green_soft,
        )
        self.curso_contador_label.pack(side="right")

        self.curso_busca = ctk.CTkEntry(
            lista_card,
            placeholder_text="Pesquisar aula, módulo...",
            height=36,
            corner_radius=9,
            fg_color=self.c_editor,
            border_color=self.c_border,
        )
        self.curso_busca.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.curso_busca.bind("<KeyRelease>", lambda _e: self._atualizar_lista_aulas())

        self.curso_lista_scroll = ctk.CTkScrollableFrame(
            lista_card,
            fg_color="transparent",
            corner_radius=0,
        )
        self.curso_lista_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 8))

        # ===== Conteúdo da aula =====
        self.curso_conteudo_scroll = ctk.CTkScrollableFrame(
            page,
            fg_color="transparent",
            corner_radius=0,
        )
        self.curso_conteudo_scroll.grid(row=1, column=1, sticky="nsew")

        self._atualizar_botoes_modo_curso()
        self._atualizar_lista_aulas()
        self._mostrar_aula_curso()

    def _definir_modo_aplicativo(self, modo):
        """Troca o dicionário ativo e mantém curso e tradutor sincronizados."""
        global DICIONARIO
        if modo not in DICIONARIOS:
            return

        self.modo_aplicativo = modo
        self.modo_curso = modo
        DICIONARIO = DICIONARIOS[modo]

        try:
            self._atualizar_botoes_modo_curso()
            self._atualizar_lista_aulas()
            self._mostrar_aula_curso()
        except Exception:
            pass

        try:
            self._atualizar_preview_python()
        except Exception:
            pass

    def _mostrar_seletor_inicial(self):
        """Mostra uma seleção visual e moderna para escolher EDU ou COMPLETO."""
        if getattr(self, "_seletor_inicial", None) is not None:
            try:
                if self._seletor_inicial.winfo_exists():
                    return
            except Exception:
                pass

        janela = ctk.CTkToplevel(self)
        self._seletor_inicial = janela
        janela.title("Escolha sua versão — Pyrtugues")
        janela.geometry("720x455")
        janela.minsize(680, 425)
        janela.configure(fg_color=self.c_bg)
        janela.transient(self)
        janela.grab_set()
        janela.protocol("WM_DELETE_WINDOW", lambda: confirmar("edu"))

        # Cabeçalho
        cab = ctk.CTkFrame(janela, fg_color=self.c_panel, corner_radius=0, height=96)
        cab.pack(fill="x")
        cab.pack_propagate(False)

        ctk.CTkLabel(
            cab, text="P  Pyrtugues",
            font=("Segoe UI", 24, "bold"),
            text_color=self.c_text,
        ).pack(anchor="w", padx=26, pady=(18, 0))
        ctk.CTkLabel(
            cab, text="Escolha o nível do tradutor e do curso",
            font=("Segoe UI", 11),
            text_color=self.c_muted,
        ).pack(anchor="w", padx=28, pady=(2, 12))

        corpo = ctk.CTkFrame(janela, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=22, pady=20)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        escolhida = {"valor": None}

        def confirmar(modo):
            escolhida["valor"] = modo
            self._definir_modo_aplicativo(modo)
            try:
                janela.grab_release()
            except Exception:
                pass
            try:
                janela.destroy()
            except Exception:
                pass
            self._seletor_inicial = None
            self.after(60, self._atualizar_preview_python)

        def criar_card(coluna, modo, titulo, subtitulo, descricao, aulas, destaque):
            card = ctk.CTkFrame(
                corpo,
                fg_color=self.c_card,
                corner_radius=16,
                border_width=2 if destaque else 1,
                border_color=self.c_green if destaque else self.c_border,
            )
            card.grid(row=0, column=coluna, sticky="nsew", padx=7)

            badge = ctk.CTkFrame(
                card, fg_color=self.c_green if destaque else "#151D2E",
                corner_radius=999, height=30, width=105,
            )
            badge.pack(anchor="w", padx=18, pady=(18, 12))
            badge.pack_propagate(False)
            ctk.CTkLabel(
                badge, text=titulo,
                font=("Segoe UI", 10, "bold"),
                text_color="#03241B" if destaque else self.c_text,
            ).pack(expand=True)

            ctk.CTkLabel(
                card, text=subtitulo,
                font=("Segoe UI", 18, "bold"),
                text_color=self.c_text, anchor="w",
            ).pack(fill="x", padx=18)
            ctk.CTkLabel(
                card, text=descricao,
                font=("Segoe UI", 10),
                text_color=self.c_muted, anchor="w", justify="left",
                wraplength=270,
            ).pack(fill="x", padx=18, pady=(6, 5))
            ctk.CTkLabel(
                card, text=f"📚 {aulas} aulas de curso",
                font=("Consolas", 9, "bold"),
                text_color=self.c_green_soft, anchor="w",
            ).pack(fill="x", padx=18, pady=(0, 14))

            ctk.CTkButton(
                card, text=f"Começar com {titulo}", height=42,
                corner_radius=10,
                fg_color=self.c_green if destaque else "#151D2E",
                hover_color=self.c_green_hover if destaque else "#1E293B",
                text_color="#03241B" if destaque else self.c_text,
                border_width=0 if destaque else 1,
                border_color=self.c_border,
                font=("Segoe UI", 11, "bold"),
                command=lambda: confirmar(modo),
            ).pack(fill="x", padx=18, pady=(0, 18))
            return card

        criar_card(
            0, "edu", "EDU", "Começar pelo básico",
            "Aprenda programação de forma progressiva, com uma base mais enxuta e direta.",
            len(_curso_aulas("edu")), True,
        )
        criar_card(
            1, "completo", "COMPLETO", "Aprender mais fundo",
            "Inclui o caminho completo, conteúdos avançados e uma trilha maior de Python.",
            len(_curso_aulas("completo")), False,
        )

        ctk.CTkLabel(
            janela,
            text="Você pode trocar de modo depois dentro da página Curso.",
            font=("Segoe UI", 9),
            text_color=self.c_dim,
        ).pack(pady=(0, 14))

        janela.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - janela.winfo_width()) // 2
            y = self.winfo_rooty() + (self.winfo_height() - janela.winfo_height()) // 2
            janela.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _selecionar_modo_curso(self, modo):
        if modo not in DADOS_CURSO:
            return
        self._definir_modo_aplicativo(modo)
        total = len(_curso_aulas(modo))
        if self.indice_aula_curso >= total:
            self.indice_aula_curso = max(0, total - 1)
        self._atualizar_botoes_modo_curso()
        self._atualizar_lista_aulas()
        self._mostrar_aula_curso()

    def _atualizar_botoes_modo_curso(self):
        try:
            for modo, botao in (
                ("edu", self.curso_btn_edu),
                ("completo", self.curso_btn_completo),
            ):
                ativo = self.modo_curso == modo
                botao.configure(
                    fg_color=self.c_green if ativo else "#151D2E",
                    hover_color=self.c_green_hover if ativo else "#1E293B",
                    text_color="#03241B" if ativo else self.c_text,
                    border_width=0 if ativo else 1,
                    border_color=self.c_border,
                )
        except Exception:
            pass

    def _aulas_filtradas_curso(self):
        aulas = _curso_aulas(self.modo_curso)
        termo = self.curso_busca.get().strip().casefold() if hasattr(self, "curso_busca") else ""
        if not termo:
            return list(enumerate(aulas))

        filtradas = []
        for indice, aula in enumerate(aulas):
            haystack = " ".join([
                aula.get("modulo", ""),
                aula.get("titulo", ""),
                aula.get("descricao", ""),
            ]).casefold()
            if termo in haystack:
                filtradas.append((indice, aula))
        return filtradas

    def _atualizar_lista_aulas(self):
        """Reconstrói a lista lateral sem abrir outra janela."""
        for widget in self.curso_lista_scroll.winfo_children():
            widget.destroy()

        self._curso_botoes_aulas = {}
        filtradas = self._aulas_filtradas_curso()

        if not filtradas:
            ctk.CTkLabel(
                self.curso_lista_scroll,
                text="Nenhuma aula encontrada.",
                font=("Segoe UI", 10),
                text_color=self.c_muted,
            ).pack(padx=10, pady=20)
            self.curso_contador_label.configure(text="0 resultados")
            return

        self.curso_contador_label.configure(
            text=f"{len(filtradas)}/{len(_curso_aulas(self.modo_curso))}"
        )

        ultimo_modulo = None
        for indice, aula in filtradas:
            modulo = aula["modulo"]
            if modulo != ultimo_modulo:
                ctk.CTkLabel(
                    self.curso_lista_scroll,
                    text=modulo,
                    font=("Segoe UI", 10, "bold"),
                    text_color=self.c_green_soft,
                    anchor="w",
                    justify="left",
                    wraplength=245,
                ).pack(fill="x", padx=8, pady=(12 if ultimo_modulo else 6, 5))
                ultimo_modulo = modulo

            concluida = indice + 1 in self.aulas_concluidas[self.modo_curso]
            prefixo = "✓ " if concluida else ""
            texto = f"{prefixo}{indice + 1:03d}  {aula['titulo']}"
            botao = ctk.CTkButton(
                self.curso_lista_scroll,
                text=texto,
                command=lambda i=indice: self._mostrar_aula_curso(i),
                anchor="w",
                height=34,
                corner_radius=8,
                fg_color=self.c_green if indice == self.indice_aula_curso else "#0D1726",
                hover_color=self.c_green_hover if indice == self.indice_aula_curso else "#172235",
                text_color="#03241B" if indice == self.indice_aula_curso else self.c_text,
                font=("Segoe UI", 9, "bold" if indice == self.indice_aula_curso else "normal"),
                border_width=1,
                border_color=self.c_border,
            )
            botao.pack(fill="x", padx=4, pady=2)
            self._curso_botoes_aulas[indice] = botao

    def _curso_limpar_conteudo(self):
        for widget in self.curso_conteudo_scroll.winfo_children():
            widget.destroy()

    def _curso_label(self, parent, text, *, size=11, bold=False, color=None, pady=(0, 10), wrap=760):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", size, "bold" if bold else "normal"),
            text_color=color or self.c_text,
            justify="left",
            anchor="w",
            wraplength=wrap,
        )

    def _curso_caixa_texto(self, parent, texto, altura=190, cor="#A7F3D0"):
        caixa = ctk.CTkTextbox(
            parent,
            height=altura,
            font=("Consolas", 11),
            fg_color=self.c_editor,
            text_color=cor,
            border_width=1,
            border_color=self.c_border,
            corner_radius=10,
            wrap="none",
            padx=12,
            pady=10,
        )
        caixa.pack(fill="x", padx=2, pady=(0, 12))
        caixa.insert("1.0", texto)
        caixa.configure(state="disabled")
        return caixa

    def _mostrar_aula_curso(self, indice=None):
        aulas = _curso_aulas(self.modo_curso)
        if not aulas:
            return

        if indice is not None:
            indice = max(0, min(indice, len(aulas) - 1))
            self.indice_aula_curso = indice

        aula = aulas[self.indice_aula_curso]
        self._curso_limpar_conteudo()

        numero = self.indice_aula_curso + 1
        total = len(aulas)
        concluida = numero in self.aulas_concluidas[self.modo_curso]
        progresso = len(self.aulas_concluidas[self.modo_curso]) / max(1, total)

        topo = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        topo.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(
            topo,
            text=f"{aula['modulo']}   •   Aula {numero} de {total}",
            font=("Consolas", 10, "bold"),
            text_color=self.c_green_soft,
        ).pack(anchor="w", padx=18, pady=(16, 5))

        ctk.CTkLabel(
            topo,
            text=aula["titulo"],
            font=("Segoe UI", 24, "bold"),
            text_color=self.c_text,
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=18, pady=(0, 5))

        ctk.CTkLabel(
            topo,
            text=aula["descricao"],
            font=("Segoe UI", 11),
            text_color=self.c_muted,
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=18, pady=(0, 14))

        progresso_linha = ctk.CTkFrame(topo, fg_color="transparent")
        progresso_linha.pack(fill="x", padx=18, pady=(0, 16))

        self.curso_progresso_barra = ctk.CTkProgressBar(
            progresso_linha,
            height=8,
            corner_radius=5,
            progress_color=self.c_green,
            fg_color="#1A2536",
        )
        self.curso_progresso_barra.pack(side="left", fill="x", expand=True)
        self.curso_progresso_barra.set(progresso)

        self.curso_progresso_texto = ctk.CTkLabel(
            progresso_linha,
            text=f"{len(self.aulas_concluidas[self.modo_curso])}/{total} concluídas",
            font=("Consolas", 9, "bold"),
            text_color=self.c_green_soft,
        )
        self.curso_progresso_texto.pack(side="right", padx=(10, 0))

        # Conteúdo
        secao_conteudo = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        secao_conteudo.pack(fill="x", padx=4, pady=5)

        self._curso_label(secao_conteudo, "📖 Conteúdo", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(16, 8)
        )
        self._curso_label(secao_conteudo, aula["conteudo"], size=11, color=self.c_muted, wrap=760).pack(
            fill="x", padx=18, pady=(0, 18)
        )

        # Pyrtugues
        secao_pyr = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        secao_pyr.pack(fill="x", padx=4, pady=5)
        self._curso_label(secao_pyr, "🟢 Exemplo em Pyrtugues", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(16, 8)
        )
        self._curso_label(
            secao_pyr,
            "Este exemplo foi escrito para respeitar a sintaxe que o tradutor atual consegue processar. "
            "Quando uma biblioteca ou recurso não possui uma forma contextual traduzida no tradutor atual, "
            "a aula usa a forma Python sem inventar uma tradução.",
            size=10,
            color=self.c_dim,
            wrap=760,
        ).pack(fill="x", padx=18, pady=(0, 8))
        self._curso_caixa_texto(secao_pyr, aula["pyrtugues"], altura=min(300, max(150, 110 + 14 * aula["pyrtugues"].count("\n"))))

        # Python
        secao_py = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        secao_py.pack(fill="x", padx=4, pady=5)
        self._curso_label(secao_py, "🐍 Equivalente em Python", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(16, 8)
        )
        self._curso_caixa_texto(secao_py, aula["python"], altura=min(300, max(150, 110 + 14 * aula["python"].count("\n"))), cor="#E2E8F0")

        # Explicação
        secao_exp = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        secao_exp.pack(fill="x", padx=4, pady=5)
        self._curso_label(secao_exp, "🧠 Explicação", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(16, 8)
        )
        self._curso_label(secao_exp, aula["explicacao"], size=11, color=self.c_muted, wrap=760).pack(
            fill="x", padx=18, pady=(0, 18)
        )

        # Exercício e desafio
        secao_ex = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color=self.c_card,
            corner_radius=14,
            border_width=1,
            border_color=self.c_border,
        )
        secao_ex.pack(fill="x", padx=4, pady=5)

        self._curso_label(secao_ex, "✏️ Exercício", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(16, 6)
        )
        self._curso_label(secao_ex, aula["exercicio"], size=11, color=self.c_text, wrap=760).pack(
            fill="x", padx=18, pady=(0, 12)
        )

        self._curso_label(secao_ex, "🚀 Desafio", size=16, bold=True, wrap=760).pack(
            fill="x", padx=18, pady=(4, 6)
        )
        self._curso_label(secao_ex, aula["desafio"], size=11, color=self.c_text, wrap=760).pack(
            fill="x", padx=18, pady=(0, 12)
        )

        if aula.get("dica"):
            self._curso_label(secao_ex, f"💡 Dica: {aula['dica']}", size=10, color=self.c_green_soft, wrap=760).pack(
                fill="x", padx=18, pady=(0, 16)
            )

        # Navegação
        nav = ctk.CTkFrame(
            self.curso_conteudo_scroll,
            fg_color="transparent",
        )
        nav.pack(fill="x", padx=4, pady=(8, 4))

        anterior = ctk.CTkButton(
            nav,
            text="← Anterior",
            width=120,
            height=40,
            command=self._curso_anterior,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
        )
        anterior.pack(side="left")
        if numero <= 1:
            anterior.configure(state="disabled")

        concluir_texto = "✓ Desmarcar concluída" if concluida else "✓ Marcar como concluída"
        ctk.CTkButton(
            nav,
            text=concluir_texto,
            width=180,
            height=40,
            command=self._alternar_conclusao_curso,
            fg_color=self.c_green if not concluida else "#334155",
            hover_color=self.c_green_hover if not concluida else "#475569",
            text_color="#03241B" if not concluida else self.c_text,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            nav,
            text="📝 Abrir no Editor",
            width=150,
            height=40,
            command=self._abrir_aula_no_editor,
            fg_color=self.c_green,
            hover_color=self.c_green_hover,
            text_color="#03241B",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right")

        proximo_texto = "Curso concluído →" if numero >= total else "Próxima →"
        ctk.CTkButton(
            nav,
            text=proximo_texto,
            width=145,
            height=40,
            command=self._curso_proxima,
            fg_color="#151D2E",
            hover_color="#1E293B",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_text,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            self.curso_conteudo_scroll,
            text="↑ Voltar à lista de aulas",
            width=160,
            height=34,
            command=lambda: self.curso_busca.focus_set(),
            fg_color="transparent",
            hover_color="#182438",
            border_width=1,
            border_color=self.c_border,
            text_color=self.c_muted,
        ).pack(anchor="w", padx=4, pady=(0, 16))

        self._atualizar_lista_aulas()
        try:
            self.curso_conteudo_scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _alternar_conclusao_curso(self):
        numero = self.indice_aula_curso + 1
        concluidas = self.aulas_concluidas[self.modo_curso]
        if numero in concluidas:
            concluidas.remove(numero)
        else:
            concluidas.add(numero)
        self._mostrar_aula_curso()

    def _curso_anterior(self):
        if self.indice_aula_curso <= 0:
            return
        self.indice_aula_curso -= 1
        self._mostrar_aula_curso()

    def _curso_proxima(self):
        aulas = _curso_aulas(self.modo_curso)
        if self.indice_aula_curso < len(aulas) - 1:
            self.indice_aula_curso += 1
            self._mostrar_aula_curso()
        else:
            self._atualizar_status("Curso concluído", self.c_green_soft)

    def _abrir_aula_no_editor(self):
        aulas = _curso_aulas(self.modo_curso)
        if not aulas:
            return
        aula = aulas[self.indice_aula_curso]
        self._carregar_codigo(aula["pyrtugues"])
        self._mostrar_pagina("editor")
        self._atualizar_status(f"Aula {self.indice_aula_curso + 1} carregada", self.c_green_soft)

    def _construir_pagina_sobre(self):
        """Página Sobre integrada ao app, sem Toplevel."""
        page = self.pagina_sobre
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        hero = ctk.CTkFrame(
            page, fg_color=self.c_panel, corner_radius=14,
            border_width=1, border_color=self.c_border
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            hero, text="Sobre o Pyrtugues", font=("Segoe UI", 24, "bold"),
            text_color=self.c_text
        ).pack(anchor="w", padx=22, pady=(18, 4))
        ctk.CTkLabel(
            hero,
            text="Python em português, feito para aprender programação.",
            font=("Segoe UI", 11), text_color=self.c_green_soft
        ).pack(anchor="w", padx=22, pady=(0, 18))

        projeto = ctk.CTkFrame(
            page, fg_color=self.c_card, corner_radius=14,
            border_width=1, border_color=self.c_border
        )
        projeto.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=6)
        ctk.CTkLabel(
            projeto, text="🐍 O projeto", font=("Segoe UI", 16, "bold"),
            text_color=self.c_text, anchor="w"
        ).pack(fill="x", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            projeto,
            text=(
                "O Pyrtugues é um projeto educacional que permite escrever código "
                "usando palavras em português e executar o resultado com Python.\n\n"
                "A proposta é facilitar o primeiro contato com programação sem mudar a "
                "lógica que o aluno vai encontrar no Python tradicional."
            ),
            font=("Segoe UI", 11), text_color=self.c_muted,
            justify="left", anchor="w", wraplength=500
        ).pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(
            projeto,
            text="""se idade maior que 10:
    mostrar("Olá!")

↓

if idade > 10:
    print("Olá!")""",
            font=("Consolas", 11), text_color="#A7F3D0",
            justify="left", anchor="w"
        ).pack(fill="x", padx=18, pady=(0, 18))

        criador = ctk.CTkFrame(
            page, fg_color=self.c_card, corner_radius=14,
            border_width=1, border_color=self.c_border
        )
        criador.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=6)
        ctk.CTkLabel(
            criador, text="👨‍💻 O criador", font=("Segoe UI", 16, "bold"),
            text_color=self.c_text, anchor="w"
        ).pack(fill="x", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            criador,
            text=(
                "Vinicius Caracciolo dos Santos\n\n"
                "O projeto nasceu como uma iniciativa pessoal voltada para programação e educação, "
                "com a ideia de tornar o primeiro contato com código mais acessível para falantes de português."
            ),
            font=("Segoe UI", 11), text_color=self.c_muted,
            justify="left", anchor="w", wraplength=500
        ).pack(fill="x", padx=18, pady=(0, 18))
        destaque = ctk.CTkFrame(criador, fg_color="#0D1726", corner_radius=10)
        destaque.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(
            destaque, text="💡 A proposta", font=("Segoe UI", 12, "bold"),
            text_color=self.c_text, anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            destaque,
            text="Programar em português → entender a lógica → enxergar o Python → aprender Python.",
            font=("Segoe UI", 10), text_color=self.c_green_soft,
            justify="left", anchor="w", wraplength=460
        ).pack(fill="x", padx=14, pady=(0, 12))

        como = ctk.CTkFrame(
            page, fg_color=self.c_card, corner_radius=14,
            border_width=1, border_color=self.c_border
        )
        como.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(
            como, text="📖 Como usar", font=("Segoe UI", 16, "bold"),
            text_color=self.c_text, anchor="w"
        ).pack(fill="x", padx=18, pady=(18, 10))
        passos = [
            ("1", "Escreva", "Digite no editor."),
            ("2", "Execute", "Use o botão ou Ctrl + Enter."),
            ("3", "Veja", "Confira o Python e o terminal."),
            ("4", "Experimente", "Carregue exemplos e altere livremente."),
        ]
        faixa = ctk.CTkFrame(como, fg_color="transparent")
        faixa.pack(fill="x", padx=12, pady=(0, 16))
        for numero, titulo, descricao in passos:
            bloco = ctk.CTkFrame(faixa, fg_color="#0D1726", corner_radius=10)
            bloco.pack(side="left", fill="both", expand=True, padx=4)
            ctk.CTkLabel(
                bloco, text=numero, width=30, height=30, corner_radius=15,
                fg_color=self.c_green, text_color="#03241B", font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", padx=12, pady=(12, 8))
            ctk.CTkLabel(
                bloco, text=titulo, font=("Segoe UI", 11, "bold"),
                text_color=self.c_text, anchor="w"
            ).pack(fill="x", padx=12)
            ctk.CTkLabel(
                bloco, text=descricao, font=("Segoe UI", 9),
                text_color=self.c_muted, anchor="w", justify="left", wraplength=180
            ).pack(fill="x", padx=12, pady=(2, 12))


    def _mostrar_pagina(self, nome):
        """Troca os frames principais sem abrir novas janelas."""
        paginas = {
            "selecao": self.pagina_selecao,
            "editor": self.pagina_editor,
            "exemplos": self.pagina_exemplos,
            "curso": self.pagina_curso,
            "sobre": self.pagina_sobre,
        }
        pagina = paginas.get(nome, self.pagina_editor)
        for frame in paginas.values():
            frame.pack_forget()
        pagina.pack(fill="both", expand=True)

        for chave, button in self.nav_buttons.items():
            ativo = chave == nome
            button.configure(
                fg_color=self.c_green if ativo else "transparent",
                hover_color=self.c_green_hover if ativo else "#182438",
                text_color="#03241B" if ativo else self.c_muted,
                font=("Segoe UI", 11, "bold" if ativo else "normal"),
                border_width=0 if ativo else 1,
            )

        if nome == "selecao":
            for button in self.nav_buttons.values():
                try:
                    button.pack_forget()
                except Exception:
                    pass
        else:
            if not any(button.winfo_manager() for button in self.nav_buttons.values()):
                for button in self.nav_buttons.values():
                    button.pack(side="left", padx=3)

        if nome == "editor":
            self.after_idle(self._ir_para_editor)
        elif nome == "curso":
            self.after_idle(self._mostrar_aula_curso)


    def _ir_para_editor(self):
        try:
            self.caixa_codigo.focus_set()
            self.caixa_codigo.see("insert")
        except Exception:
            pass

    def _atualizar_preview_python(self, event=None):
        """Atualiza a tradução visual sem alterar o código do usuário."""
        try:
            codigo = self.caixa_codigo.get("1.0", "end").rstrip()
            traduzido = traduzir(codigo) if codigo else ""
            self.caixa_python_preview.configure(state="normal")
            self.caixa_python_preview.delete("1.0", "end")
            self.caixa_python_preview.insert("1.0", traduzido)
            self.caixa_python_preview.configure(state="disabled")
        except Exception:
            # Enquanto o usuário digita código incompleto, mantemos a última
            # tradução válida em vez de interromper a edição.
            pass

    def copiar_python(self):
        try:
            codigo = self.caixa_python_preview.get("1.0", "end").rstrip()
            self.clipboard_clear()
            self.clipboard_append(codigo)
            self._atualizar_status("● Python copiado", self.c_green_soft)
        except Exception as exc:
            messagebox.showerror("Copiar Python", f"Não foi possível copiar o código.\n\n{exc}")

    def baixar_python(self):
        codigo = self.caixa_python_preview.get("1.0", "end").rstrip()
        if not codigo:
            messagebox.showwarning("Baixar Python", "Digite algum código primeiro.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Baixar código Python",
            defaultextension=".py",
            filetypes=[("Arquivo Python", "*.py"), ("Todos os arquivos", "*.*")],
            initialfile="programa.py",
        )
        if not caminho:
            return
        try:
            Path(caminho).write_text(codigo + "\n", encoding="utf-8")
            self._atualizar_status("● Python salvo", self.c_green_soft)
        except Exception as exc:
            messagebox.showerror("Baixar Python", f"Não foi possível salvar o arquivo.\n\n{exc}")

    def _carregar_codigo(self, codigo):
        self.caixa_codigo.delete("1.0", "end")
        self.caixa_codigo.insert("1.0", codigo)
        self.atualizar_numeros_linha()
        self._atualizar_preview_python()
        self._ir_para_editor()

    def abrir_exemplos(self):
        """Mostra a biblioteca de exemplos na página interna do app."""
        self._mostrar_pagina("exemplos")

    def _configurar_editor_interno(self):
        """Configura detalhes do Tk Text que o CTkTextbox não expõe no tema."""
        try:
            self.caixa_codigo._textbox.configure(
                insertbackground="#E5F7EF",
                insertwidth=2,
                selectbackground="#14532D",
                selectforeground="#F8FAFC",
            )
            self.numeros_linha._textbox.configure(
                spacing1=0, spacing2=0, spacing3=0,
                insertwidth=0,
            )
            self._atualizar_linha_atual()
            self.atualizar_numeros_linha()
        except Exception:
            pass

    def _sincronizar_scroll_editor(self, first, last):
        """Mantém scrollbar, editor e gutter sincronizados em tempo real."""
        try:
            # Continua alimentando a scrollbar nativa do CTkTextbox.
            if getattr(self.caixa_codigo, "_scrollbar", None) is not None:
                self.caixa_codigo._scrollbar.set(first, last)
            self.numeros_linha.yview_moveto(first)
        except Exception:
            pass

    def atualizar_numeros_linha(self, event=None):
        """Atualiza o gutter com o mesmo espaçamento vertical do editor."""
        try:
            total = int(self.caixa_codigo.index("end-1c").split(".")[0])
        except Exception:
            return

        # A largura aumenta quando passam de 9, 99, 999 linhas etc.
        largura = max(54, 18 + len(str(total)) * 9)
        try:
            self.numeros_linha.configure(width=largura)
        except Exception:
            pass

        numeros = "\n".join(str(i) for i in range(1, total + 1))
        self.numeros_linha.configure(state="normal")
        self.numeros_linha.delete("1.0", "end")
        self.numeros_linha.insert("1.0", numeros)
        self.numeros_linha.configure(state="disabled")
        self.sincronizar_numeros_linha()
        self._atualizar_linha_atual()

    def sincronizar_numeros_linha(self, event=None):
        """Sincroniza o gutter com a posição vertical real do editor."""
        try:
            primeiro = self.caixa_codigo._textbox.yview()[0]
            self.numeros_linha._textbox.yview_moveto(primeiro)
        except Exception:
            try:
                self.numeros_linha.yview_moveto(self.caixa_codigo.yview()[0])
            except Exception:
                pass

    def _atualizar_linha_atual(self, event=None):
        """Destaca suavemente a linha onde o cursor está."""
        try:
            self.caixa_codigo._textbox.tag_remove("linha_atual", "1.0", "end")
            self.numeros_linha._textbox.tag_remove("linha_atual_num", "1.0", "end")
            linha = self.caixa_codigo.index("insert").split(".")[0]
            self.caixa_codigo._textbox.tag_add(
                "linha_atual", f"{linha}.0", f"{linha}.end+1c"
            )
            self.numeros_linha._textbox.tag_add(
                "linha_atual_num", f"{linha}.0", f"{linha}.end+1c"
            )
        except Exception:
            pass

    def _editor_cursor_changed(self, event=None):
        self.after_idle(self._atualizar_linha_atual)
        self.after_idle(self.sincronizar_numeros_linha)
        return None

    def _editor_keyrelease(self, event=None):
        self.after_idle(self.atualizar_numeros_linha)
        self.after_idle(self._atualizar_linha_atual)
        if self._timer_traducao is not None:
            try:
                self.after_cancel(self._timer_traducao)
            except Exception:
                pass
        self._timer_traducao = self.after(50, self._atualizar_preview_python)
        return None


    def _editor_indentacao(self, linha_texto):
        """Retorna a indentação inicial e uma indentação adicional de 4 espaços."""
        base = re.match(r"^\s*", linha_texto).group(0)
        return base, base + "    "

    def _selecionar_linhas(self):
        """Obtém o intervalo de linhas selecionadas, quando houver seleção."""
        try:
            inicio = self.caixa_codigo.index("sel.first")
            fim = self.caixa_codigo.index("sel.last")
        except Exception:
            return None
        return inicio, fim

    def _editor_keypress(self, event):
        """Atalhos de editor: pares, indentação, Enter e navegação."""
        texto = self.caixa_codigo
        char = event.char
        keysym = event.keysym
        selecao = self._selecionar_linhas()

        # Shift+Tab: remove até 4 espaços da linha atual.
        # O bit 0x0001 corresponde à tecla Shift no Tk.
        if keysym == "ISO_Left_Tab" or (keysym == "Tab" and (event.state & 0x0001)):
            linha = texto.index("insert").split(".")[0]
            conteudo = texto.get(f"{linha}.0", f"{linha}.end")
            removidos = len(conteudo) - len(conteudo.lstrip(" "))
            remover = min(4, removidos)
            if remover:
                texto.delete(f"{linha}.0", f"{linha}.{remover}")
            return "break"

        # Tab: quatro espaços.
        if keysym == "Tab":
            if selecao:
                inicio, fim = selecao
                primeira_linha = int(inicio.split(".")[0])
                ultima_linha = int(fim.split(".")[0])
                for numero in range(primeira_linha, ultima_linha + 1):
                    texto.insert(f"{numero}.0", "    ")
            else:
                texto.insert("insert", "    ")
            return "break"

        # Backspace: apaga o par vazio de uma vez.
        if keysym == "BackSpace" and not selecao:
            cursor = texto.index("insert")
            antes = texto.get(f"{cursor}-1c", cursor)
            depois = texto.get(cursor, f"{cursor}+1c")
            if (antes, depois) in {("(", ")"), ("[", "]"), ("{", "}"), ('"', '"'), ("'", "'")}:
                texto.delete(f"{cursor}-1c", f"{cursor}+1c")
                return "break"

        # Enter: indentação automática e bloco entre delimitadores.
        if keysym == "Return":
            cursor = texto.index("insert")
            linha_atual = int(cursor.split(".")[0])
            coluna = int(cursor.split(".")[1])
            linha_texto = texto.get(f"{linha_atual}.0", f"{linha_atual}.end")
            antes = linha_texto[:coluna]
            depois = linha_texto[coluna:]
            base, interna = self._editor_indentacao(linha_texto)

            # Se o cursor estiver entre (), [] ou {}, abre uma linha interna.
            pares = {"(": ")", "[": "]", "{": "}"}
            if antes and depois and antes[-1] in pares and depois[0] == pares[antes[-1]]:
                texto.delete(f"{linha_atual}.0", f"{linha_atual}.end")
                texto.insert(
                    f"{linha_atual}.0",
                    antes + "\n" + interna + "\n" + base + depois
                )
                texto.mark_set("insert", f"{linha_atual + 1}.{len(interna)}")
                return "break"

            # Dois pontos no fim da instrução: entra um nível de indentação.
            if antes.rstrip().endswith(":"):
                texto.insert("insert", "\n" + interna)
                return "break"

            # Caso normal: mantém a indentação da linha atual.
            texto.insert("insert", "\n" + base)
            return "break"

        # Auto-fechamento de (), [], {}, aspas.
        pares_abertura = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        if char in pares_abertura:
            fechamento = pares_abertura[char]
            cursor = texto.index("insert")

            # Com seleção, envolve o trecho selecionado.
            if selecao and char in "([{\"'":
                inicio, fim = selecao
                selecionado = texto.get(inicio, fim)
                texto.delete(inicio, fim)
                texto.insert(inicio, char + selecionado + fechamento)
                texto.mark_set("insert", f"{inicio}+{len(selecionado) + 2}c")
                texto.tag_remove("sel", "1.0", "end")
                return "break"

            # Se o fechamento já estiver à frente, só passa por ele.
            proximo = texto.get(cursor, f"{cursor}+1c")
            if proximo == fechamento and char in '"\'':
                texto.mark_set("insert", f"{cursor}+1c")
                return "break"

            texto.insert(cursor, char + fechamento)
            texto.mark_set("insert", f"{cursor}+1c")
            return "break"

        # Fechamento duplicado: navega sem inserir outro caractere.
        if char in {")", "]", "}", '"', "'"
        } and not selecao:
            cursor = texto.index("insert")
            proximo = texto.get(cursor, f"{cursor}+1c")
            if proximo == char:
                texto.mark_set("insert", f"{cursor}+1c")
                return "break"

        return None

    def ver_python(self):
        """Mostra o código Python gerado pelo tradutor."""
        codigo_br = self.caixa_codigo.get("1.0", "end").rstrip()
        if not codigo_br:
            messagebox.showwarning("Ver Python", "Digite algum código primeiro.")
            return

        try:
            codigo_py = traduzir(codigo_br)
        except Exception as exc:
            messagebox.showerror("Ver Python", f"Não foi possível traduzir o código.\n\n{exc}")
            return

        janela = ctk.CTkToplevel(self)
        janela.title("Pyrtugues → Python")
        janela.geometry("900x640")
        janela.minsize(700, 480)
        janela.configure(fg_color="#070B12")
        janela.transient(self)
        janela.grab_set()

        cab = ctk.CTkFrame(janela, fg_color="#0E1624", corner_radius=0, height=76)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        ctk.CTkLabel(
            cab, text="🐍  Python gerado", font=("Segoe UI", 19, "bold"),
            text_color="#F8FAFC"
        ).pack(side="left", padx=22)
        ctk.CTkLabel(
            cab, text="Código traduzido pelo Pyrtugues 1.4.0",
            font=("Segoe UI", 10), text_color="#6EE7B7"
        ).pack(side="left", padx=10)

        area = ctk.CTkTextbox(
            janela, font=("Consolas", 13), fg_color="#0D1421",
            text_color="#E2E8F0", border_width=1, border_color="#20304A",
            wrap="none", padx=16, pady=14
        )
        area.pack(fill="both", expand=True, padx=18, pady=18)
        area.insert("1.0", codigo_py)
        area.configure(state="disabled")

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(
            botoes, text="Copiar Python", height=38, width=145,
            fg_color="#10B981", hover_color="#059669", text_color="#03241B",
            font=("Segoe UI", 11, "bold"),
            command=lambda: (janela.clipboard_clear(), janela.clipboard_append(codigo_py))
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Fechar", height=38, width=100,
            fg_color="#151D2E", hover_color="#1E293B",
            font=("Segoe UI", 11, "bold"), command=janela.destroy
        ).pack(side="right")

    # ===== Backend original =====

    def input_gui(self, prompt=""):
        """Entrada segura para código executado em background, com modal criado no thread do Tk."""
        if threading.current_thread() is threading.main_thread():
            return self._abrir_input_modal(prompt)

        evento = threading.Event()
        pedido = {"prompt": str(prompt), "resultado": "", "evento": evento}
        self._input_requests.put(pedido)
        self.after(0, self._processar_pedido_input)

        while not evento.wait(0.05):
            if self.parar_evento.is_set():
                return ""
        return pedido["resultado"]

    def _estilizar_modal_entrada(self, janela, prompt, entrada, confirmar, cancelar):
        """Monta uma caixa de entrada visual consistente com o Pyrtugues."""
        janela.configure(fg_color=self.c_bg)
        janela.transient(self)
        janela.grab_set()

        cab = ctk.CTkFrame(janela, fg_color=self.c_panel, corner_radius=0, height=76)
        cab.pack(fill="x")
        cab.pack_propagate(False)

        linha = ctk.CTkFrame(cab, fg_color="transparent")
        linha.pack(fill="both", expand=True, padx=18)
        ctk.CTkLabel(
            linha, text="⌨  Entrada de dados",
            font=("Segoe UI", 16, "bold"),
            text_color=self.c_text,
        ).pack(anchor="w", pady=(12, 0))
        ctk.CTkLabel(
            linha, text="O programa está esperando uma resposta",
            font=("Segoe UI", 9),
            text_color=self.c_green_soft,
        ).pack(anchor="w", pady=(1, 0))

        corpo = ctk.CTkFrame(janela, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=18, pady=14)

        prompt_card = ctk.CTkFrame(
            corpo, fg_color=self.c_card, corner_radius=12,
            border_width=1, border_color=self.c_border,
        )
        prompt_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            prompt_card, text=str(prompt).strip() or "Digite um valor:",
            font=("Segoe UI", 11, "bold"),
            text_color=self.c_text, anchor="w", justify="left",
            wraplength=390,
        ).pack(fill="x", padx=14, pady=12)

        entrada.configure(
            height=44, corner_radius=10,
            fg_color=self.c_editor, border_color=self.c_border,
            border_width=1, text_color=self.c_text,
            placeholder_text="Digite sua resposta...",
        )
        entrada.pack(fill="x", padx=2, pady=(0, 10))

        botoes = ctk.CTkFrame(corpo, fg_color="transparent")
        botoes.pack(fill="x")

        ctk.CTkButton(
            botoes, text="Cancelar", height=38, width=110,
            fg_color="#151D2E", hover_color="#1E293B",
            border_width=1, border_color=self.c_border,
            text_color=self.c_text, font=("Segoe UI", 10, "bold"),
            command=cancelar,
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Confirmar  →", height=38, width=130,
            fg_color=self.c_green, hover_color=self.c_green_hover,
            text_color="#03241B", font=("Segoe UI", 10, "bold"),
            command=confirmar,
        ).pack(side="right")

        entrada.bind("<Return>", confirmar)
        janela.protocol("WM_DELETE_WINDOW", cancelar)
        entrada.focus_set()

    def _abrir_input_modal(self, prompt):
        """Entrada manual bonita para chamadas feitas na thread principal."""
        janela = ctk.CTkToplevel(self)
        janela.title("Pyrtugues — Entrada de dados")
        janela.geometry("460x235")
        janela.minsize(420, 220)
        resultado = [""]

        entrada = ctk.CTkEntry(janela, font=("Segoe UI", 13))

        def confirmar(_event=None):
            resultado[0] = entrada.get()
            try:
                janela.grab_release()
            except Exception:
                pass
            janela.destroy()

        def cancelar():
            resultado[0] = ""
            try:
                janela.grab_release()
            except Exception:
                pass
            janela.destroy()

        self._estilizar_modal_entrada(janela, prompt, entrada, confirmar, cancelar)
        self.wait_window(janela)
        return resultado[0]

    def _processar_pedido_input(self):
        if self._input_atual is not None or self.parar_evento.is_set():
            return
        try:
            self._input_atual = self._input_requests.get_nowait()
        except Empty:
            return

        pedido = self._input_atual
        janela = ctk.CTkToplevel(self)
        self._input_janela = janela
        janela.title("Pyrtugues — Entrada de dados")
        janela.geometry("460x235")
        janela.minsize(420, 220)

        entrada = ctk.CTkEntry(janela, font=("Segoe UI", 13))

        def finalizar(valor=""):
            if self._input_atual is not pedido:
                return
            pedido["resultado"] = str(valor)
            pedido["evento"].set()
            self._input_atual = None
            self._input_janela = None
            try:
                janela.grab_release()
            except Exception:
                pass
            try:
                janela.destroy()
            except Exception:
                pass
            self.after(0, self._processar_pedido_input)

        def confirmar(_event=None):
            finalizar(entrada.get())

        def cancelar():
            finalizar("")

        self._estilizar_modal_entrada(janela, pedido["prompt"], entrada, confirmar, cancelar)

    def _cancelar_pedidos_input(self):
        if self._input_atual is not None:
            self._input_atual["resultado"] = ""
            self._input_atual["evento"].set()
            self._input_atual = None
        while True:
            try:
                pedido = self._input_requests.get_nowait()
            except Empty:
                break
            pedido["resultado"] = ""
            pedido["evento"].set()

    def abrir_sobre(self):
        """Mostra a página Sobre integrada ao app."""
        self._mostrar_pagina("sobre")

    def _trace_execucao(self, frame, evento, arg):
        if self.parar_evento.is_set():
            raise RuntimeError("Execução interrompida pelo usuário.")
        return self._trace_execucao

    def _atualizar_status(self, texto, cor="#6EE7B7"):
        try:
            self.status_label.configure(text=f"●  {texto}", text_color=cor)
        except Exception:
            pass

    def executar_codigo(self):
        if self.executando:
            return

        codigo_br = self.caixa_codigo.get("1.0", "end").strip()
        if not codigo_br:
            messagebox.showwarning("Aviso", "Digite algum código!")
            return

        self.caixa_saida.delete("1.0", "end")
        self.escrever_saida("─" * 50 + "\n📤 Saída:\n" + "─" * 50 + "\n")
        self.executando = True
        self.parar_evento.clear()
        self.btn_parar.configure(state="normal")
        self.btn_executar.configure(state="disabled")
        self._atualizar_status("Executando", "#FDE68A")

        self._thread_execucao = threading.Thread(
            target=self._executar_em_background,
            args=(codigo_br,),
            daemon=True,
        )
        self._thread_execucao.start()

    def _executar_em_background(self, codigo_br):
        linhas_br = codigo_br.splitlines()
        try:
            codigo_py = traduzir(codigo_br)
            namespace = self.namespace.copy()
            namespace["input"] = self.input_gui
            namespace["print"] = self.print_gui

            sys.settrace(self._trace_execucao)
            exec(codigo_py, namespace)
            sys.settrace(None)

            if not self.parar_evento.is_set():
                self.after(0, lambda ns=namespace: self._finalizar_execucao_sucesso(ns))
            else:
                self.after(0, self._finalizar_execucao_parado)
        except Exception as exc:
            try:
                sys.settrace(None)
            except Exception:
                pass
            if self.parar_evento.is_set():
                self.after(0, self._finalizar_execucao_parado)
                return

            linha_erro = None
            tb = exc.__traceback__
            while tb:
                if tb.tb_frame.f_code.co_filename == "<string>":
                    linha_erro = tb.tb_lineno
                tb = tb.tb_next

            self.after(0, lambda e=exc, linha=linha_erro, linhas=linhas_br: self._mostrar_erro_execucao(e, linha, linhas))

    def _finalizar_execucao_sucesso(self, namespace):
        self.namespace.update(namespace)
        self.executando = False
        self.btn_parar.configure(state="disabled")
        self.btn_executar.configure(state="normal")
        self._input_atual = None
        self._atualizar_status("Pronto", "#6EE7B7")
        self.escrever_saida("\n" + "=" * 50 + "\n✅ Código finalizado.\n")

    def _finalizar_execucao_parado(self):
        self.executando = False
        self.parar_evento.set()
        self.btn_parar.configure(state="disabled")
        self.btn_executar.configure(state="normal")
        self._cancelar_pedidos_input()
        self._atualizar_status("Interrompido", "#FBBF24")
        self.escrever_saida("\n⚠️ Execução interrompida.\n" + "=" * 50 + "\n")

    def _mostrar_erro_execucao(self, erro, linha_erro, linhas_br):
        self.executando = False
        self.btn_parar.configure(state="disabled")
        self.btn_executar.configure(state="normal")
        self._atualizar_status("Erro", "#FCA5A5")
        if linha_erro and 1 <= linha_erro <= len(linhas_br):
            self.escrever_saida(f"\n❌ Erro na linha {linha_erro}:\n")
            self.escrever_saida(f"   {linhas_br[linha_erro - 1]}\n")
            self.escrever_saida(f"\n   Detalhes: {erro}\n")
        else:
            self.escrever_saida(f"\n❌ Erro: {erro}\n")
        self.escrever_saida("\n" + "=" * 50 + "\n")

    def parar_execucao(self):
        if not self.executando:
            return
        self.parar_evento.set()
        self._cancelar_pedidos_input()
        if self._input_janela is not None:
            try:
                self._input_janela.grab_release()
            except Exception:
                pass
            try:
                self._input_janela.destroy()
            except Exception:
                pass
            self._input_janela = None
        self.btn_parar.configure(state="disabled")
        self.btn_executar.configure(state="normal")

    def print_gui(self, *args, sep=" ", end="\n", **kwargs):
        """Versão de print compatível com o editor, enviada para a saída do app."""
        if kwargs.get("file") not in (None, sys.stdout, sys.__stdout__):
            # O interpretador não tenta suportar destinos externos no editor.
            raise ValueError("Destino de saída externo não é suportado no editor.")
        texto = sep.join(str(arg) for arg in args) + end
        self.escrever_saida(texto)

    def write(self, texto):
        self.escrever_saida(texto)

    def flush(self):
        pass

    def escrever_saida(self, texto):
        texto = str(texto)
        if threading.current_thread() is threading.main_thread():
            try:
                self.caixa_saida.insert("end", texto)
                self.caixa_saida.see("end")
            except Exception:
                pass
        else:
            try:
                self.after(0, self.escrever_saida, texto)
            except Exception:
                pass

    def carregar_exemplo(self):
        exemplo = '''função calcular_media(nota1, nota2):
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

mostrar(f"\\nAluno: {nome}")
mostrar(f"Média: {media}")
mostrar(f"Situação: {situacao}")
'''
        self.caixa_codigo.delete("1.0", "end")
        self.caixa_codigo.insert("1.0", exemplo)
        self.atualizar_numeros_linha()
        self._atualizar_preview_python()
        self._atualizar_linha_atual()


if __name__ == "__main__":
    app = JanelaBR()
    app.mainloop()
