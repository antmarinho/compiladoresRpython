# Pattern Matching para RPython

Este projeto adiciona suporte experimental a uma sintaxe de pattern matching para o RPython legado.

Exemplo:

```python
def classificar(valor):
    match valor:
        case "sim" | "s":
            return "resposta afirmativa"
        case "1" | "2" | "3":
            return "numero pequeno"
        case True | False:
            return "booleano"
        case outro:
            return "outro"
```

O projeto transforma essa sintaxe em código mais simples, entendido pelo tradutor RPython:

```python
if valor == "sim" or valor == "s":
    return "resposta afirmativa"
elif valor == "1" or valor == "2" or valor == "3":
    return "numero pequeno"
elif valor is True or valor is False:
    return "booleano"
else:
    outro = valor
    return "outro"
```

## Importante: como o projeto funciona

O RPython utilizado neste projeto é legado e depende de uma infraestrutura compatível com Python 2.7. Python 2.7 não entende diretamente as palavras `match` e `case`.

Por isso são usadas duas etapas:

```text
Python 3
  └── lê match/case, cria a AST e gera código if/elif/else

PyPy 2.7 ou Python 2.7
  └── executa o tradutor RPython no código já convertido

Compilador C do Windows
  └── transforma o C gerado em um arquivo .exe
```

O Python 3 executa o parser. O PyPy 2.7 executa o tradutor legado. Eles têm funções diferentes.

## Conteúdo do projeto

```text
pypy-rpython/
│
├── README.md
├── target_exemplo.py
├── PATTERN_MATCHING_ARQUITETURA.md
│
└── rpython/
    ├── bin/
    │   └── rpython-match
    │
    ├── flowspace/
    │   └── objspace.py
    │
    └── tool/
        ├── patternmatching.py
        ├── patternmatching_ast.py
        │
        └── test/
            └── test_patternmatching.py
```

### `rpython/tool/patternmatching_ast.py`

Define a AST intermediária do pattern matching.

Classes principais:

```text
Node
Pattern
LiteralPattern
BooleanPattern
CapturePattern
WildcardPattern
OrPattern
CaseNode
MatchNode
SourceNode
```

Exemplos:

```python
case 10
```

vira conceitualmente:

```text
LiteralPattern(10)
```

```python
case True
```

vira:

```text
BooleanPattern(True)
```

```python
case valor
```

vira:

```text
CapturePattern("valor")
```

```python
case 1 | 2 | 3
```

vira:

```text
OrPattern([
    LiteralPattern(1),
    LiteralPattern(2),
    LiteralPattern(3)
])
```

### `rpython/tool/patternmatching.py`

É o parser e o conversor principal. Ele contém:

- leitura de `match` e `case`;
- análise da indentação;
- reconhecimento de números;
- reconhecimento de strings;
- reconhecimento de `True` e `False`;
- reconhecimento de variáveis de captura;
- reconhecimento do wildcard `_`;
- reconhecimento do operador `|`;
- suporte a `match` aninhado;
- criação da AST;
- lowering para `if`/`elif`/`else`;
- reconstrução de funções para integração com o FlowSpace.

As funções mais importantes são:

```python
parse_source(source)
```

Cria a AST intermediária.

```python
emit_source(tree)
```

Gera código Python sem `match`/`case` a partir da AST.

```python
transform_source(source)
```

Executa parsing e lowering:

```text
source -> AST -> código if/elif/else
```

```python
lower_function(func)
```

Obtém o código-fonte de uma função, converte o `match` e recria a função sem essa sintaxe.

### `rpython/flowspace/objspace.py`

É o ponto de integração com o FlowSpace quando a função já foi carregada como objeto Python:

```python
func = lower_function(func)
```

Atenção: esse ponto não consegue fazer o Python 2.7 aceitar a sintaxe `match` diretamente. Para arquivos completos, use o launcher `rpython-match`.

### `rpython/bin/rpython-match`

É o launcher do projeto.

Ele faz:

```text
1. recebe o arquivo com match/case;
2. executa o parser com Python 3;
3. cria um arquivo temporário sem match/case;
4. chama o tradutor RPython com PyPy 2.7/Python 2.7;
5. remove o arquivo temporário.
```

Uso:

```powershell
python rpython\bin\rpython-match `
    --python2 C:\pypy2.7\pypy.exe `
    target_exemplo.py
```

### `rpython/tool/test/test_patternmatching.py`

Contém os testes automatizados para:

- números;
- strings;
- booleanos;
- variáveis;
- wildcard;
- alternativas com `|`;
- matches aninhados;
- avaliação única do sujeito;
- validação de erros;
- criação da AST;
- execução do código convertido.

### `target_exemplo.py`

É um programa de exemplo que demonstra a implementação:

```python
match valor:
    case "sim" | "s":
        return "resposta afirmativa"
    case "1" | "2" | "3":
        return "numero pequeno"
    case "true" | "false":
        return "booleano como texto"
    case outro:
        return "outro valor: " + outro
```

### Documentação técnica

`PATTERN_MATCHING_ARQUITETURA.md` contém um resumo da arquitetura e da AST.

## Padrões suportados

### Strings

```python
match valor:
    case "sim":
        return "sim"
```

### Números

```python
match valor:
    case 1:
        return "um"
    case 2.5:
        return "dois e meio"
```

### Booleanos

```python
match valor:
    case True:
        return "verdadeiro"
    case False:
        return "falso"
```

Booleanos são emitidos com `is` para evitar confusão com números:

```python
valor is True
valor is False
```

### Captura de variável

```python
match valor:
    case numero:
        return numero
```

Uma captura aceita qualquer valor e deve ser o último `case`.

### Wildcard

```python
match valor:
    case _:
        return "qualquer valor"
```

### Alternativas com `|`

```python
match valor:
    case "sim" | "s":
        return "sim"
    case 1 | 2 | 3:
        return "numero"
    case True | False:
        return "booleano"
```

As alternativas geram comparações com `or`.

Não é permitido misturar captura ou wildcard dentro de uma alternativa:

```python
case 1 | outro:
case _ | 1:
```

## Limitações atuais

Ainda não são suportados:

- guardas:

```python
case numero if numero > 0:
```

- padrões de lista;
- padrões de tupla;
- padrões de dicionário;
- padrões de classe;
- `as-patterns`;
- alternativas com captura;
- type check estático completo.

O projeto possui validação dos padrões, mas não possui um analisador completo que infira o tipo de cada variável do programa.

## Instalação no Windows

### 1. Instale o Python 3

Baixe pelo site oficial:

<https://www.python.org/downloads/windows/>

Durante a instalação, marque:

```text
Add Python to PATH
```

Abra um novo PowerShell e teste:

```powershell
python --version
```

Use Python 3.10 ou mais recente.

### 2. Instale o Git

Baixe:

<https://git-scm.com/download/win>

Teste:

```powershell
git --version
```

### 3. Instale o PyPy 2.7

Baixe uma versão Windows do PyPy 2.7:

<https://www.pypy.org/download_advanced.html>

Extraia, por exemplo, em:

```text
C:\pypy2.7
```

Confirme que existe:

```text
C:\pypy2.7\pypy.exe
```

No PowerShell, um programa da pasta atual precisa de `.` e barra invertida:

```powershell
cd C:\pypy2.7
.\pypy.exe --version
```

Ou use o caminho completo:

```powershell
C:\pypy2.7\pypy.exe --version
```

### 4. Baixe o projeto

Clone o repositório original:

```powershell
cd C:\
git clone https://github.com/pypy/pypy.git pypy-rpython
cd C:\pypy-rpython
```

Depois extraia o ZIP deste projeto dentro de `C:\pypy-rpython`, preservando as pastas.

## Abrir no Visual Studio Code

Instale o VS Code:

<https://code.visualstudio.com/>

Abra o PowerShell e execute:

```powershell
cd C:\pypy-rpython
code .
```

Ou abra o VS Code manualmente e selecione:

```text
File -> Open Folder -> C:\pypy-rpython
```

No VS Code, abra o terminal integrado:

```text
Terminal -> New Terminal
```

Atalho:

```text
Ctrl + `
```

Confirme o diretório:

```powershell
Get-Location
```

O resultado deve indicar:

```text
C:\pypy-rpython
```

Se necessário:

```powershell
cd C:\pypy-rpython
```

## Testar apenas o parser

Esta etapa não precisa compilar C. Ela verifica o parser, a AST e o lowering.

No terminal do VS Code:

```powershell
cd C:\pypy-rpython
$env:PYTHONPATH = "C:\pypy-rpython"
python -m unittest rpython.tool.test.test_patternmatching
```

Resultado esperado:

```text
Ran 11 tests
OK
```

Para visualizar o código convertido:

```powershell
python -c "from rpython.tool.patternmatching import transform_source; print(transform_source(open('exemplos\exemplo.py').read()))"
```

O resultado deve mostrar `if`, `elif`, `else`, `or` e `is` no lugar de `match` e `case`.

## Compilar o programa RPython

Para gerar um `.exe`, além do VS Code, Python 3 e PyPy 2.7, é necessário um compilador C compatível com o backend Windows do RPython.

O VS Code é um editor e terminal; ele não contém um compilador C. O tradutor pode falhar com:

```text
Could not find a Microsoft Compiler
```

Se essa mensagem aparecer, o parser funcionou, mas falta o compilador C no ambiente.

Com um compilador Windows compatível instalado e disponível no `PATH`, execute no terminal do VS Code:

```powershell
python rpython\bin\rpython-match --python2 C:\pypy2.7\pypy.exe exemplos\target_exemplo.py

```

Se o caminho do PyPy for diferente, substitua:

```text
C:\pypy2.7\pypy.exe
```

pelo caminho correto.

Depois procure o executável:

```powershell
Get-ChildItem *.exe
```

O nome esperado é parecido com:

```text
exemplo-c.exe
```

Execute:

```powershell
.\target_exemplo-c.exe sim
.\target_exemplo-c.exe s
.\target_exemplo-c.exe 2
.\target_exemplo-c.exe qualquer
```

Saídas esperadas:

```text
resposta afirmativa
resposta afirmativa
numero pequeno
outro valor: qualquer
```

## Se você não tiver compilador C

Ainda é possível executar e testar tudo até o lowering:

```powershell
python -m unittest rpython.tool.test.test_patternmatching
```

Também é possível visualizar o código convertido:

```powershell
python -c "from rpython.tool.patternmatching import transform_source; print(transform_source(open('exemplos/exemplo.py').read()))"
```

O que não será possível é gerar o executável final `.exe`, porque essa etapa exige um compilador C.

Não existe comando do VS Code que substitua o compilador. O VS Code pode executar o compilador quando ele está instalado, mas não compila C sozinho.

## Repositório original

O RPython faz parte do repositório do PyPy:

<https://github.com/pypy/pypy>

As alterações de pattern matching deste projeto são arquivos locais adicionados ao clone. Elas não foram publicadas automaticamente no repositório oficial.
