<div align="center">

<img src="./assets/logo-pyrtugues.png" alt="Logo do Pyrtugues — programação em português baseada em Python" width="160">

# Pyrtugues

### Python em português, feito para aprender programação.

**Programação em português • lógica de Python • aprendizado progressivo**

Uma linguagem educacional baseada na lógica do Python, criada para facilitar o aprendizado de programação usando comandos e estruturas em português.

**Versão 1.5.0**

</div>

---

## 📚 O que é o Pyrtugues?

**Pyrtugues** é uma linguagem de programação educacional baseada na sintaxe e na lógica do Python.

A proposta é permitir que iniciantes aprendam programação utilizando palavras em português, sem abandonar os conceitos fundamentais presentes no Python.

O Pyrtugues funciona como uma ponte:

```text
Pyrtugues
    ↓
Motor de tradução
    ↓
Python
    ↓
Execução
```

Isso significa que o estudante pode aprender conceitos como:

* variáveis;
* tipos de dados;
* condições;
* repetições;
* funções;
* classes;
* exceções;
* módulos;
* arquivos;
* estruturas de dados;
* testes;
* programação gráfica;
* Pygame;

usando uma sintaxe em português e, ao mesmo tempo, entendendo como esses conceitos aparecem no Python.

> **Programar em português → entender a lógica → enxergar o Python → aprender Python.**

---

# 🚀 Começando

O Pyrtugues possui diferentes formas de utilização:

* 🖥️ aplicação Desktop;
* 🪟 Windows;
* 🐧 Linux;
* 🌐 Editor Web;
* 🎮 suporte a Pygame;
* 📚 exemplos educacionais;
* 🧪 materiais e exercícios de programação.

O código principal da aplicação Desktop está em:

```text
Pyrtugues_code.py
```

---

# 💡 Primeiro programa

No Pyrtugues:

```pyrtugues
mostrar("Olá, mundo!")
```

O equivalente em Python é:

```python
print("Olá, mundo!")
```

A ideia não é criar uma linguagem completamente diferente do Python, mas aproximar a linguagem de quem está começando a programar em português.

---

# 🔤 Pyrtugues → Python

Algumas das principais correspondências da linguagem:

| Pyrtugues      | Python        |
| -------------- | ------------- |
| `se`           | `if`          |
| `senão`        | `else`        |
| `senão_se`     | `elif`        |
| `para`         | `for`         |
| `enquanto`     | `while`       |
| `quebrar`      | `break`       |
| `continuar`    | `continue`    |
| `passar`       | `pass`        |
| `função`       | `def`         |
| `classe`       | `class`       |
| `retornar`     | `return`      |
| `produzir`     | `yield`       |
| `assíncrono`   | `async`       |
| `aguardar`     | `await`       |
| `importar`     | `import`      |
| `de`           | `from`        |
| `como`         | `as`          |
| `tentar`       | `try`         |
| `exceto`       | `except`      |
| `finalmente`   | `finally`     |
| `levantar`     | `raise`       |
| `afirmar`      | `assert`      |
| `e`            | `and`         |
| `ou`           | `or`          |
| `não`          | `not`         |
| `é`            | `is`          |
| `em`           | `in`          |
| `verdadeiro`   | `True`        |
| `falso`        | `False`       |
| `nulo`         | `None`        |
| `mostrar()`    | `print()`     |
| `entrada()`    | `input()`     |
| `inteiro()`    | `int()`       |
| `decimal()`    | `float()`     |
| `texto()`      | `str()`       |
| `lista()`      | `list()`      |
| `tupla()`      | `tuple()`     |
| `conjunto()`   | `set()`       |
| `dicionário()` | `dict()`      |
| `intervalo()`  | `range()`     |
| `tamanho()`    | `len()`       |
| `ordenar()`    | `sorted()`    |
| `inverter()`   | `reversed()`  |
| `filtrar()`    | `filter()`    |
| `mapear()`     | `map()`       |
| `enumerar()`   | `enumerate()` |
| `todos()`      | `all()`       |
| `algum()`      | `any()`       |
| `absoluto()`   | `abs()`       |
| `arredondar()` | `round()`     |
| `somar()`      | `sum()`       |
| `máximo()`     | `max()`       |
| `mínimo()`     | `min()`       |
| `potência()`   | `pow()`       |

O vocabulário da linguagem continua evoluindo conforme o desenvolvimento do projeto.

---

# 🧱 Fundamentos

## Variáveis

```pyrtugues
nome = "Ana"
idade = 15
altura = 1.65

mostrar(nome)
mostrar(idade)
mostrar(altura)
```

O Pyrtugues mantém a mesma ideia de atribuição utilizada pelo Python.

---

## Comentários

Comentários continuam utilizando `#`:

```pyrtugues
# Esta linha não será executada
mostrar("Código executável")
```

---

## Condições

```pyrtugues
idade = 15

se idade maior que 10:
    mostrar("Pode continuar")
senão:
    mostrar("Precisa estudar mais")
```

Também é possível utilizar múltiplos caminhos:

```pyrtugues
nota = 8

se nota maior ou igual a 9:
    mostrar("Excelente")
senão_se nota maior ou igual a 7:
    mostrar("Bom")
senão_se nota maior ou igual a 5:
    mostrar("Recuperação")
senão:
    mostrar("Reprovado")
```

---

# 🔁 Repetições

## `para`

```pyrtugues
para numero em intervalo(1, 6):
    mostrar(numero)
```

Equivalente:

```python
for numero in range(1, 6):
    print(numero)
```

---

## `enquanto`

```pyrtugues
contador = 0

enquanto contador menor que 5:
    mostrar(contador)
    contador += 1
```

---

## Controle de loops

### `quebrar`

```pyrtugues
para numero em intervalo(1, 10):
    se numero igual a 5:
        quebrar

    mostrar(numero)
```

### `continuar`

```pyrtugues
para numero em intervalo(1, 8):
    se numero igual a 4:
        continuar

    mostrar(numero)
```

### `passar`

```pyrtugues
função futura():
    passar
```

---

# 🧩 Funções

Funções podem ser declaradas utilizando `função`:

```pyrtugues
função saudacao(nome):
    retornar f"Olá, {nome}!"

mensagem = saudacao("Pyrtugues")
mostrar(mensagem)
```

Outro exemplo:

```pyrtugues
função calcular_media(nota1, nota2):
    retornar (nota1 + nota2) / 2

media = calcular_media(8, 10)

mostrar(media)
```

---

# 📥 Entrada de dados

Programas interativos podem solicitar dados:

```pyrtugues
nome = pergunte("Qual é o seu nome? ")

mostrar(f"Olá, {nome}!")
```

Conversões podem ser feitas utilizando os tipos traduzidos:

```pyrtugues
idade = inteiro(pergunte("Idade: "))
altura = decimal(pergunte("Altura: "))

mostrar(idade)
mostrar(altura)
```

---

# 🧮 Operações

O Pyrtugues mantém os operadores matemáticos tradicionais do Python:

```pyrtugues
a = 10
b = 3

mostrar(a + b)
mostrar(a - b)
mostrar(a * b)
mostrar(a / b)
mostrar(a // b)
mostrar(a % b)
mostrar(a ** b)
```

Também existem formas traduzidas para operadores compostos:

```pyrtugues
contador = 0

contador += 1
contador -= 1
contador *= 2
contador /= 2
```

---

# 📦 Listas

```pyrtugues
nomes = ["Ana", "Bia", "Carlos"]

mostrar(nomes)
mostrar(nomes[0])
```

Percorrendo uma lista:

```pyrtugues
nomes = ["Ana", "Bia", "Carlos"]

para nome em nomes:
    mostrar(nome)
```

---

# 🔷 Tuplas

```pyrtugues
coordenadas = (10, 20)

mostrar(coordenadas)
mostrar(coordenadas[0])
```

Tuplas são úteis quando os valores representam uma coleção que não deve ser modificada.

---

# 🔹 Conjuntos

```pyrtugues
numeros = {1, 2, 3, 3, 4}

mostrar(numeros)
```

Conjuntos eliminam valores duplicados.

---

# 📖 Dicionários

```pyrtugues
aluno = {
    "nome": "Ana",
    "idade": 15,
    "nota": 9
}

mostrar(aluno["nome"])
mostrar(aluno["nota"])
```

Dicionários permitem representar informações estruturadas por chave e valor.

---

# 🧵 Textos

Strings podem ser utilizadas normalmente:

```pyrtugues
texto = "PYRTUGUES"

mostrar(texto[0])
mostrar(texto[-1])
```

Também podem ser usadas f-strings:

```pyrtugues
nome = "Ana"
idade = 15

mostrar(f"Nome: {nome}")
mostrar(f"Idade: {idade}")
```

---

# ⚠️ Exceções

O Pyrtugues possui estruturas para tratamento de erros.

```pyrtugues
tentar:
    numero = inteiro(pergunte("Número: "))
    mostrar(numero * 2)

exceto ValueError:
    mostrar("Valor inválido")

finalmente:
    mostrar("Fim da tentativa")
```

Também é possível gerar exceções:

```pyrtugues
função dividir(a, b):
    se b == 0:
        levantar ValueError("Divisor não pode ser zero")

    retornar a / b
```

E realizar verificações:

```pyrtugues
função quadrado(numero):
    retornar numero * numero

afirmar quadrado(4) == 16
afirmar quadrado(-2) == 4
```

---

# 📚 Módulos

O Pyrtugues pode utilizar módulos da biblioteca padrão do Python.

```pyrtugues
importar matemática

mostrar(matématica.sqrt(81))
```

Também é possível utilizar `de` e `como`:

```pyrtugues
de matemática importar sqrt como raiz

mostrar(raiz(81))
```

> Os nomes exatos disponíveis dependem do dicionário e da versão do tradutor.

---

# 🎲 Biblioteca padrão

Exemplos de módulos utilizados nos materiais do projeto:

* `math`;
* `random`;
* `datetime`;
* `time`;
* `os`;
* `sys`;
* `re`;
* `json`;
* `csv`;
* `collections`;
* `calendar`;
* `unittest`;
* entre outros recursos da biblioteca padrão compatíveis com o tradutor.

Exemplo:

```pyrtugues
importar aleatório
importar datetime

numero = aleatório.randint(1, 10)
agora = datetime.datetime.now()

mostrar(numero)
mostrar(agora)
```

---

# 💾 JSON

O Pyrtugues pode trabalhar com dados JSON utilizando o módulo `json`.

Exemplo:

```pyrtugues
importar json

dados = {
    "nome": "Ana",
    "nota": 9
}

com abrir("aluno.json", "w", encoding="utf-8") como arquivo:
    json.dump(dados, arquivo, ensure_ascii=False, indent=2)
```

Leitura:

```pyrtugues
com abrir("aluno.json", "r", encoding="utf-8") como arquivo:
    recuperado = json.load(arquivo)

mostrar(recuperado)
```

---

# 📊 CSV

Também é possível trabalhar com arquivos CSV:

```pyrtugues
importar csv

com abrir("alunos.csv", "w", newline="", encoding="utf-8") como arquivo:
    gravador = csv.writer(arquivo)

    gravador.writerow(["nome", "nota"])
    gravador.writerow(["Ana", 9])
```

---

# 🧪 Testes

O Pyrtugues possui suporte a conceitos de testes automatizados.

Exemplo:

```pyrtugues
função somar(a, b):
    retornar a + b

afirmar somar(2, 2) == 4
afirmar somar(10, 5) == 15
```

Também podem ser utilizados recursos do `unittest` quando compatíveis com o ambiente:

```pyrtugues
importar testes_unitários

classe TesteSoma(testes_unitários.TestCase):

    função teste_soma(self):
        self.assertEqual(2 + 2, 4)
```

---

# 🎮 Pygame

O Pyrtugues possui integração com **Pygame**, permitindo utilizar conceitos de programação gráfica e desenvolvimento de jogos.

A arquitetura pode ser entendida como:

```text
Pyrtugues
    ↓
Tradutor
    ↓
Python
    ↓
Pygame
    ↓
Jogo / Aplicação
```

Entre os conceitos que podem ser explorados estão:

* janelas;
* eventos;
* teclado;
* mouse;
* imagens;
* textos;
* formas;
* cores;
* sprites;
* colisões;
* sons;
* músicas;
* animações;
* controle de tempo.

Um exemplo conceitual:

```pyrtugues
importar pygame

pygame.init()

janela = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Meu primeiro projeto")

executando = verdadeiro

enquanto executando:

    para evento em pygame.event.get():

        se evento.type == pygame.QUIT:
            executando = falso

    janela.fill((30, 30, 30))

    pygame.display.flip()

pygame.quit()
```

> A disponibilidade de determinados recursos do Pygame depende da versão do tradutor e do ambiente em que o Pyrtugues está sendo executado.

---

# 🖥️ Desktop

A versão Desktop utiliza:

* Python;
* CustomTkinter;
* Tkinter;
* Pygame.

O aplicativo reúne recursos como:

* editor de código;
* execução do programa;
* terminal de saída;
* entrada interativa;
* visualização do Python gerado;
* exemplos;
* navegação;
* destaque da linha atual;
* interrupção da execução;
* carregamento de exemplos;
* interface gráfica.

O arquivo principal é:

```text
Pyrtugues_code.py
```

---

# 🧠 Execução do código

No Desktop, o fluxo principal é:

```text
Código Pyrtugues
       ↓
    tradução
       ↓
Código Python
       ↓
exec(...)
       ↓
resultado
```

O aplicativo também possui mecanismos para executar o código em uma thread separada, permitindo manter a interface responsiva durante a execução.

A entrada e a saída são integradas à interface gráfica do aplicativo.

---

# 🌐 Editor Web

O projeto também possui uma experiência Web para experimentar Pyrtugues diretamente no navegador.

A versão Web possui recursos como:

* editor;
* tradução Pyrtugues → Python;
* execução;
* entrada interativa;
* terminal;
* exemplos;
* visualização do Python gerado;
* cópia do código Python;
* download do código Python;
* execução do motor em Web Worker.

A arquitetura Web utiliza:

```text
Pyrtugues
    ↓
Tradutor
    ↓
Python
    ↓
Pyodide
    ↓
Navegador
```

---

# 📂 Estrutura do projeto

A estrutura principal do repositório inclui:

```text
Pyrtugues/
├── assets/
│   └── logo-pyrtugues.png
├── Pyrtugues_Documentacao/
├── site-principal/
├── LICENSE
├── README.md
└── Pyrtugues_code.py
```

| Arquivo / pasta           | Função                        |
| ------------------------- | ----------------------------- |
| `assets/`                 | Recursos visuais              |
| `Pyrtugues_Documentacao/` | Documentação do projeto       |
| `site-principal/`         | Arquivos relacionados ao site |
| `Pyrtugues_code.py`       | Aplicação Desktop             |
| `README.md`               | Documentação principal        |
| `LICENSE`                 | Licença do projeto            |

---

# 🛠️ Tecnologias

## Desktop

* Python
* CustomTkinter
* Tkinter
* Pygame

## Web

* HTML
* CSS
* JavaScript
* Tailwind CSS
* Pyodide
* Web Worker

---

# 🚀 Executando pelo código-fonte

Clone o projeto:

```bash
git clone https://github.com/pyrtugues/Pyrtugues.git
```

Entre no diretório:

```bash
cd Pyrtugues
```

A aplicação Desktop está em:

```text
Pyrtugues_code.py
```

As dependências devem ser instaladas de acordo com o ambiente utilizado.

Exemplo:

```bash
pip install customtkinter pygame
```

Depois:

```bash
python Pyrtugues_code.py
```

> O conjunto exato de dependências pode mudar conforme a versão do projeto e o sistema operacional.

---

# 📖 Exemplos de projetos

## Calculadora

```pyrtugues
função calcular(a, b, operador):

    se operador == "+":
        retornar a + b

    senão se operador == "-":
        retornar a - b

    senão se operador == "*":
        retornar a * b

    senão se operador == "/":
        retornar a / b

    senão:
        levantar ValueError("Operador inválido")


a = decimal(pergunte("Primeiro: "))
b = decimal(pergunte("Segundo: "))
operador = pergunte("Operação (+, -, *, /): ")

mostrar(calcular(a, b, operador))
```

---

## Conversor

```pyrtugues
função c_para_f(celsius):
    retornar celsius * 9 / 5 + 32

c = decimal(pergunte("Temperatura em C: "))

mostrar(f"{c} C = {c_para_f(c)} F")
```

---

## Quiz

```pyrtugues
perguntas = [
    ("Qual linguagem está na base do Pyrtugues?", "python"),
    ("Quanto é 2 + 2?", "4")
]

pontuacao = 0

para pergunta, resposta_correta em perguntas:

    resposta = pergunte(pergunta + " ")

    se resposta.lower() == resposta_correta:
        mostrar("Correto!")
        pontuacao += 1

    senão:
        mostrar("Resposta incorreta.")

mostrar(f"Pontuação: {pontuacao}/{tamanho(perguntas)}")
```

---

## Lista de tarefas

```pyrtugues
tarefas = []

enquanto verdadeiro:

    mostrar("1 - adicionar")
    mostrar("2 - listar")
    mostrar("3 - sair")

    opcao = pergunte("Opção: ")

    se opcao == "1":

        tarefa = pergunte("Tarefa: ")
        tarefas.adicionar(tarefa)

    senão se opcao == "2":

        para tarefa em tarefas:
            mostrar(tarefa)

    senão:

        quebrar

mostrar("Fim")
```

---

# 🎓 Pyrtugues como ferramenta educacional

O projeto foi pensado para ensinar programação de maneira progressiva.

O estudante pode começar com:

```pyrtugues
mostrar("Olá!")
```

e avançar para:

```text
variáveis
   ↓
condições
   ↓
repetições
   ↓
funções
   ↓
estruturas de dados
   ↓
exceções
   ↓
módulos
   ↓
arquivos
   ↓
testes
   ↓
Pygame
   ↓
projetos
```

A intenção é que os conhecimentos adquiridos sejam transferíveis para Python.

---

# 🔎 Filosofia do projeto

O Pyrtugues não pretende substituir o Python.

A proposta é diminuir a barreira inicial causada pela sintaxe em inglês e permitir que o estudante concentre sua atenção primeiro na lógica.

Depois, ao visualizar o Python equivalente, o estudante consegue perceber a relação:

```text
mostrar()       → print()
se              → if
senão           → else
para            → for
enquanto        → while
função          → def
retornar        → return
```

Dessa forma, o Pyrtugues pode funcionar como uma ponte entre o primeiro contato com programação e o Python.

---

# 📦 Versão

## Pyrtugues 1.5.0

Esta documentação corresponde à versão **1.5.0** do projeto.

O Pyrtugues continua em desenvolvimento e a compatibilidade de determinados recursos pode mudar entre versões.

Para saber exatamente quais comandos estão disponíveis no ambiente utilizado, consulte o código do tradutor e os exemplos correspondentes à versão.

---

# 🤝 Contribuições

Contribuições podem ajudar o projeto a evoluir.

Algumas formas de contribuir:

* 🐛 reportar bugs;
* 🧪 testar recursos;
* 💡 sugerir novos comandos;
* 📖 melhorar a documentação;
* 🧩 criar exemplos;
* 🎮 criar projetos com Pygame;
* 🐧 testar no Linux;
* 🪟 testar no Windows;
* 💻 contribuir com código.

Ao alterar o tradutor, é importante testar especialmente:

* variáveis;
* strings;
* comentários;
* f-strings;
* expressões;
* nomes que coincidem com palavras reservadas;
* imports;
* estruturas condicionais;
* loops;
* funções;
* exceções;
* código Python já existente.

---

# 📜 Licença

O Pyrtugues possui uma licença própria.

A licença atual estabelece regras específicas para:

* uso pessoal;
* uso educacional individual;
* uso institucional;
* uso comercial;
* modificações;
* redistribuição;
* atribuição;
* marca e identidade do projeto.

Consulte o arquivo:

```text
LICENSE
```

antes de utilizar, modificar ou redistribuir o projeto.

---

# 👨‍💻 Criador

**Vinicius Caracciolo**

O Pyrtugues nasceu como um projeto pessoal voltado para programação e educação.

O projeto evoluiu para incluir:

* linguagem de programação em português;
* tradutor para Python;
* aplicação Desktop;
* suporte ao Linux;
* suporte ao Windows;
* Pygame;
* Editor Web;
* materiais educacionais;
* documentação;
* exemplos e projetos.

---

# 🌱 Estado do projeto

**Versão atual: 1.5.0**

O Pyrtugues continua em desenvolvimento.

Entre as áreas que podem evoluir estão:

* novos comandos;
* melhorias no tradutor;
* maior compatibilidade com Python;
* melhorias no Pygame;
* tratamento de erros;
* novos exemplos;
* documentação;
* Desktop;
* Linux;
* Windows;
* Editor Web;
* materiais educacionais;
* novas plataformas.

---

<div align="center">

## 💚 Pyrtugues

**Programação em português.**

**Lógica de Python.**

**Uma ponte para aprender.**

### Pyrtugues — Python em português, feito para aprender programação.

</div>
