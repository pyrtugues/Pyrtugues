import re
import threading
from queue import Queue, Empty
import customtkinter as ctk
from tkinter import messagebox, filedialog
import sys
from pathlib import Path
TRADUCAO = {
    "portugues": {
        # ═══════════════ PYTHON BÁSICO ═══════════════
        "senão se": "elif",
        "senãose": "elif",
        "senão": "else",
        "enquanto verdadeiro": "while True",
        "enquanto": "while",
        "para cada": "for",
        "para": "for",
        "se": "if",
        "em": "in",
        "quebrar": "break",
        "continuar": "continue",
        "passar": "pass",
        "com": "with",
        "como": "as",
        "finalmente": "finally",

        "função": "def",
        "classe": "class",
        "retornar verdadeiro": "return True",
        "retornar falso": "return False",
        "retornar nulo": "return None",
        "retornar": "return",
        "produzir": "yield",
        "assíncrono": "async",
        "aguardar": "await",

        "importar": "import",
        "de": "from",

        "tentar": "try",
        "excepto": "except",
        "levantar": "raise",
        "afirmar": "assert",
        "verificar": "assert",
        "lançar": "raise",

        "global": "global",
        "nãolocal": "nonlocal",

        "verdadeiro": "True",
        "falso": "False",
        "nulo": "None",
        "vazio": "pass",
        "nada": "None",

        "e também": "and",
        "ou então": "or",
        "não é": "is not",
        "é": "is",
        "não": "not",
        "e": "and",
        "ou": "or",

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

        "mais": "+",
        "menos": "-",
        "vezes": "*",
        "dividido por": "/",
        "resto": "%",
        "potência": "**",
        "elevado a": "**",

        "inteiro": "int",
        "decimal": "float",
        "texto": "str",
        "booleano": "bool",
        "lista": "list",
        "dicionário": "dict",
        "tupla": "tuple",
        "conjunto": "set",

        "mostrar": "print",
        "imprimir": "print",
        "pergunte": "input",
        "pergunta": "input",
        "intervalo": "range",
        "tamanho": "len",
        "comprimento": "len",
        "tipo": "type",
        "é instância": "isinstance",
        "é subclasse": "issubclass",

        "somar": "sum",
        "máximo": "max",
        "mínimo": "min",
        "ordenar": "sorted",
        "inverter": "reversed",
        "filtrar": "filter",
        "mapear": "map",
        "zipar": "zip",
        "enumerar": "enumerate",
        "todos": "all",
        "algum": "any",

        "absoluto": "abs",
        "arredondar": "round",
        "elevar": "pow",
        "hexadecimal": "hex",
        "octal": "oct",
        "binário": "bin",
        "ordinal": "ord",
        "caractere": "chr",

        "ajuda": "help",
        "atributos": "vars",
        "abrir": "open",
        "formatar": "format",
        "representar": "repr",

        "maiúsculas": "upper",
        "minúsculas": "lower",
        "capitalizar": "capitalize",
        "título": "title",
        "trocar": "replace",
        "dividir": "split",
        "juntar": "join",
        "tirar espaços": "strip",
        "começa com": "startswith",
        "termina com": "endswith",
        "encontrar": "find",
        "contar": "count",
        "é dígito": "isdigit",
        "é letra": "isalpha",
        "é espaço": "isspace",

        "adicionar": "append",
        "estender": "extend",
        "inserir": "insert",
        "remover": "remove",
        "tirar": "pop",
        "limpar": "clear",
        "copiar": "copy",
        "índice": "index",
        "ordenar em ordem": "sort",
        "inverter ordem": "reverse",

        "chaves": "keys",
        "valores": "values",
        "itens": "items",
        "pegar": "get",
        "atualizar": "update",

        "matemática": "math",
        "aleatório": "random",
        "data e hora": "datetime",
        "tempo": "time",
        "sistema": "os",
        "caminho": "path",
        "arquivo": "file",
        "requisição": "request",
        "resposta": "response",
        "expressão regular": "re",

        "mais igual": "+=",
        "menos igual": "-=",
        "vezes igual": "*=",
        "dividido igual": "/=",
        "resto igual": "%=",
        "potência igual": "**=",

        "parar": "stop",
        "iniciar": "start",
        "saida": "exit",

        # ═══════════════ PYGAME ═══════════════

        # Módulos
        "janela": "display",
        "evento": "event",
        "desenho": "draw",
        "imagem": "image",
        "fonte": "font",
        "som": "mixer",
        "musica": "music",
        "tempo_jogo": "time",
        "transformar": "transform",
        "tecla": "key",
        "mouse": "mouse",
        "joystick": "joystick",
        "sprite": "sprite",
        "superficie": "surface",
        "retangulo": "rect",
        "cor": "color",
        "array_som": "sndarray",

        # Classes
        "Superficie": "Surface",
        "Retangulo": "Rect",
        "Sprite": "Sprite",
        "Grupo": "Group",
        "Fonte": "Font",
        "Som": "Sound",
        "Relogio": "Clock",
        "Evento": "Event",
        "Cor": "Color",
        "Vetor2": "Vector2",

        # Funções e métodos
        "iniciar_jogo": "init",
        "sair_jogo": "quit",
        "definir_modo": "set_mode",
        "definir_titulo": "set_caption",
        "atualizar_tela": "flip",
        "atualizar": "update",
        "preencher": "fill",
        "colar": "blit",
        "desenhar": "draw",
        "carregar": "load",
        "tocar": "play",
        "parar_som": "stop",
        "pausar": "pause",
        "despausar": "unpause",
        "pegar_retangulo": "get_rect",
        "pegar_teclas": "get_pressed",
        "pegar_posicao": "get_pos",
        "pegar": "get",
        "definir_temporizador": "set_timer",
        "pegar_ticks": "get_ticks",
        "esperar": "wait",
        "atrasar": "delay",
        "marcar": "tick",
        "circulo": "circle",
        "linha": "line",
        "elipse": "ellipse",
        "poligono": "polygon",
        "arco": "arc",
        "renderizar": "render",
        "adicionar": "add",
        "remover": "remove",
        "colidir_ponto": "collidepoint",
        "colidir_retangulo": "colliderect",
        "colidir_circulo": "collidecircle",
        "mover": "move",
        "rotacionar": "rotate",
        "escalar": "scale",
        "espelhar": "flip",

        # Eventos
        "SAIR": "QUIT",
        "TECLA_PRESSIONADA": "KEYDOWN",
        "TECLA_SOLTA": "KEYUP",
        "BOTAO_MOUSE_PRESSIONADO": "MOUSEBUTTONDOWN",
        "BOTAO_MOUSE_SOLTO": "MOUSEBUTTONUP",
        "MOVIMENTO_MOUSE": "MOUSEMOTION",
        "REDIMENSIONAR_VIDEO": "VIDEORESIZE",
        "EXPOR_VIDEO": "VIDEOEXPOSE",
        "EVENTO_ATIVO": "ACTIVEEVENT",
        "MOVIMENTO_EIXO_JOYSTICK": "JOYAXISMOTION",
        "MOVIMENTO_BOLA_JOYSTICK": "JOYBALLMOTION",
        "MOVIMENTO_HAT_JOYSTICK": "JOYHATMOTION",
        "BOTAO_JOYSTICK_PRESSIONADO": "JOYBUTTONDOWN",
        "BOTAO_JOYSTICK_SOLTO": "JOYBUTTONUP",
        "EVENTO_USUARIO": "USEREVENT",

        # Teclas
        "K_ESQUERDA": "K_LEFT",
        "K_DIREITA": "K_RIGHT",
        "K_CIMA": "K_UP",
        "K_BAIXO": "K_DOWN",
        "K_ESPACO": "K_SPACE",
        "K_ESCAPE": "K_ESCAPE",
        "K_ENTER": "K_RETURN",
        "K_APAGAR": "K_BACKSPACE",
        "K_TAB": "K_TAB",
        "K_SHIFT_ESQ": "K_LSHIFT",
        "K_SHIFT_DIR": "K_RSHIFT",
        "K_CTRL_ESQ": "K_LCTRL",
        "K_CTRL_DIR": "K_RCTRL",

        # Cores
        "VERMELHO": "RED",
        "VERDE": "GREEN",
        "AZUL": "BLUE",
        "AMARELO": "YELLOW",
        "BRANCO": "WHITE",
        "PRETO": "BLACK",
        "CIANO": "CYAN",
        "MAGENTA": "MAGENTA",
        "CINZA": "GRAY",
        "LARANJA": "ORANGE",
        "ROXO": "PURPLE",
        "ROSA": "PINK",

        # Retângulo
        "largura": "width",
        "altura": "height",
        "esquerda": "left",
        "direita": "right",
        "topo": "top",
        "base": "bottom",
        "centro": "center",
        "centro_x": "centerx",
        "centro_y": "centery",
        "topo_esquerda": "topleft",
        "topo_direita": "topright",
        "base_esquerda": "bottomleft",
        "base_direita": "bottomright",
        "meio_topo": "midtop",
        "meio_base": "midbottom",
        "meio_esquerda": "midleft",
        "meio_direita": "midright",
        "x": "x",
        "y": "y",
        "w": "w",
        "h": "h",

        # Áudio
        "definir_volume": "set_volume",
        "pegar_volume": "get_volume",
        "pegar_duracao": "get_length",
        "pegar_ocupado": "get_busy",
        "desvanecer": "fadeout",
        "enfileirar": "queue",
        "definir_evento_final": "set_endevent",

        # Display
        "pegar_superficie": "get_surface",
        "definir_icone": "set_icon",
        "pegar_titulo": "get_caption",
        "minimizar": "iconify",
        "pegar_inicializado": "get_init",

        # Termos úteis
        "tela": "screen",
        "tamanho": "size",
        "posicao": "position",
        "velocidade": "speed",
        "angulo": "angle",
        "raio": "radius",
        "espessura": "thickness",
        "borda": "border",
        "quadro": "frame",
        "fps": "fps",
        "laco": "loop",
        "laco_jogo": "game_loop",
        "laco_eventos": "event_loop",
        "colisao": "collision",
        "gravidade": "gravity",
        "pulo": "jump",
        "andar": "walk",
        "correr": "run",
        "pontuacao": "score",
        "nivel": "level",
        "vidas": "lives",
        "inimigo": "enemy",
        "jogador": "player",
        "bala": "bullet",
        "powerup": "powerup",
        "fundo": "background",
        "frente": "foreground",
        "animacao": "animation",
        "textura": "texture",
        "ladrilho": "tile",
        "mapa": "map",
        "jogo": "pygame"
    }
}

DICIONARIO = TRADUCAO["portugues"]


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

    chaves = sorted(
        DICIONARIO.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for br, py in chaves:
        # "se" exige contexto: no início de uma condição vira "if",
        # mas um identificador como "se = 19" continua sendo variável.
        if br == "se":
            resultado = re.sub(
                r'(?m)^(\s*)se(?=\s+.+:)',
                r'\1if',
                resultado,
                flags=re.IGNORECASE
            )
            continue

        if br in _SKIP_DIRETO:
            continue

        resultado = _substituir_palavra(resultado, br, py)

    # "em" é traduzido apenas na construção de repetição.
    # Assim, uma variável chamada "em" não é alterada.
    resultado = re.sub(
        r'\bfor\s+([A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*)\s+em\b',
        r'for \1 in',
        resultado,
        flags=re.IGNORECASE
    )

    # Módulos somente em import/from ou como objeto qualificado.
    for br, py in sorted(
        _MODULOS.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
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

    # Métodos somente após ponto.
    for br, py in sorted(
        _METODOS.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        resultado = re.sub(
            rf'(?<=\.)\s*{_escape_regex(br)}(?=\s*\()',
            py,
            resultado,
            flags=re.IGNORECASE
        )

    # Operadores contextuais.
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

    for palavra, destino in {
        "mais": "+",
        "menos": "-",
        "vezes": "*",
        "resto": "%",
        "potência": "**"
    }.items():
        operador_contextual(palavra, destino)

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


def traduzir(codigo_br):
    protegido, blocos = _proteger_strings_e_comentarios(codigo_br)
    resultado = _aplicar_traducoes_base(protegido)
    # Na versão desktop, pergunte() é input() síncrono dentro da thread de execução.
    resultado = re.sub(
        r'(?<![A-Za-zÀ-ÿ0-9_.])(pergunte|pergunta)\s*\(',
        'input(',
        resultado,
        flags=re.IGNORECASE,
    )
    return restaurar_strings(resultado, blocos)


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
        self._thread_execucao = None
        self.versao = "1.3.0"

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
        nav_button("sobre", "Sobre").pack(side="left", padx=3)

        status_area = ctk.CTkFrame(topo, fg_color="transparent")
        status_area.pack(side="right", padx=18)
        ctk.CTkLabel(
            status_area,
            text="PYRTUGUES  •  v1.3.0",
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

        self.pagina_editor = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_exemplos = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self.pagina_sobre = ctk.CTkScrollableFrame(
            self.page_container, fg_color="transparent", corner_radius=0
        )

        self._construir_pagina_editor()
        self._construir_pagina_exemplos()
        self._construir_pagina_sobre()

        self._mostrar_pagina("editor")
        self.bind("<Control-Return>", lambda e: self.executar_codigo())
        self.after_idle(self._configurar_editor_interno)
        self.carregar_exemplo()


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
            "editor": self.pagina_editor,
            "exemplos": self.pagina_exemplos,
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

        if nome == "editor":
            self.after_idle(self._ir_para_editor)


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
        self.after_idle(self._atualizar_preview_python)
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
            cab, text="Código traduzido pelo Pyrtugues 1.3.0",
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

    def _abrir_input_modal(self, prompt):
        janela = ctk.CTkToplevel(self)
        janela.title("Entrada")
        janela.geometry("400x160")
        janela.transient(self)
        janela.grab_set()
        resultado = [""]

        ctk.CTkLabel(janela, text=prompt, font=("Segoe UI", 13)).pack(pady=15, padx=20)
        entrada = ctk.CTkEntry(janela, width=320, font=("Consolas", 13))
        entrada.pack(pady=5, padx=20)
        entrada.focus_set()

        def confirmar(_event=None):
            resultado[0] = entrada.get()
            janela.destroy()

        entrada.bind("<Return>", confirmar)
        ctk.CTkButton(
            janela, text="OK", command=confirmar,
            fg_color="#10B981", font=("Segoe UI", 12, "bold")
        ).pack(pady=10)
        janela.protocol("WM_DELETE_WINDOW", confirmar)
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
        janela.title("Entrada")
        janela.geometry("400x160")
        janela.transient(self)
        janela.grab_set()

        ctk.CTkLabel(janela, text=pedido["prompt"], font=("Segoe UI", 13)).pack(pady=15, padx=20)
        entrada = ctk.CTkEntry(janela, width=320, font=("Consolas", 13))
        entrada.pack(pady=5, padx=20)
        entrada.focus_set()

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
            janela.destroy()
            self.after(0, self._processar_pedido_input)

        def confirmar(_event=None):
            finalizar(entrada.get())

        entrada.bind("<Return>", confirmar)
        ctk.CTkButton(
            janela, text="OK", command=confirmar,
            fg_color="#10B981", font=("Segoe UI", 12, "bold")
        ).pack(pady=10)
        janela.protocol("WM_DELETE_WINDOW", confirmar)

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
