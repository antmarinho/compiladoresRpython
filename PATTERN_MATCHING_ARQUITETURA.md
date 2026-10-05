# Pattern matching no RPython legado

## Resumo da arquitetura

A implementação feita não adiciona um nó `Match` ao AST do Python 2.7. Ela usa um **pré-processador de código-fonte** que reconhece um subconjunto de `match`/`case` e o transforma em código Python comum com `if`, `elif` e `else`.

```text
arquivo RPython com match/case
              |
              v
rpython/tool/patternmatching.py
              |
              |  lê match, case e padrões
              |  números, strings, _ e capturas
              v
código Python/RPython sem match
              |
              v
Python 2.7 ou PyPy 2.7
              |
              v
code object / bytecode
              |
              v
rpython.flowspace.objspace.build_flow()
              |
              v
grafo de fluxo RPython
              |
              v
Annotator -> RTyper -> backend C
```

O launcher `rpython/bin/rpython-match` automatiza as duas primeiras etapas:

```text
Python 3: transforma o arquivo
Python 2.7: executa rpython/bin/rpython no arquivo transformado
```

## Arquivos envolvidos

```text
rpython/tool/patternmatching.py
rpython/tool/test/test_patternmatching.py
rpython/flowspace/objspace.py
rpython/bin/rpython-match
```

## Parser implementado

O parser atual é deliberadamente simples e baseado em linhas e indentação. Ele reconhece estas formas:

```python
match expressão:
    case literal:
        bloco

    case nome:
        bloco

    case _:
        bloco
```

Os padrões aceitos são:

```python
case 0:             # número inteiro
case 2.5:           # número decimal
case "1":           # string
case 'ok':          # string
case nome:          # captura do valor
case _:             # wildcard
```

Os padrões abaixo ainda são rejeitados:

```python
case x if x > 0:    # guardas
case [a, b]:        # sequências
case {"x": x}:      # mappings
case Point(x, y):   # classes
case 1 | 2:         # OR-patterns
```

## Representação interna do parser

O parser não cria classes AST próprias. Para cada caso, ele produz internamente informações equivalentes a:

```text
Case(
    kind = LITERAL | CAPTURE | WILDCARD,
    value = texto do literal ou nome da variável,
    body = linhas do bloco
)
```

Exemplo de entrada:

```python
match valor:
    case "1":
        return "número um"
    case "2":
        return "número dois"
    case outro:
        return "valor desconhecido"
```

Representação lógica produzida:

```text
Match(
    subject = Name("valor"),
    cases = [
        Case(
            kind = LITERAL,
            value = "'1'",
            body = Return("número um")
        ),
        Case(
            kind = LITERAL,
            value = "'2'",
            body = Return("número dois")
        ),
        Case(
            kind = CAPTURE,
            value = "outro",
            body = Return("valor desconhecido")
        )
    ]
)
```

Essa representação é conceitual. No código atual, os casos são armazenados como tuplas com o resultado da expressão regular, o número da linha e as linhas do corpo.

## Lowering para Python comum

Entrada:

```python
def nome(valor):
    match valor:
        case "1":
            return "número um"
        case "2":
            return "número dois"
        case outro:
            return "valor desconhecido"
```

Saída do `transform_source()`:

```python
def nome(valor):
    __rpython_match_subject_0 = valor
    if __rpython_match_subject_0 == '1':
        return "número um"
    elif __rpython_match_subject_0 == '2':
        return "número dois"
    else:
        outro = __rpython_match_subject_0
        return "valor desconhecido"
```

A atribuição temporária garante que a expressão do `match` seja avaliada somente uma vez.

## AST depois do lowering

Depois da conversão, o Python 2.7 não recebe mais um `Match` AST. Ele recebe uma estrutura equivalente a:

```text
FunctionDef(nome)
└── arguments(valor)
    └── Assign
        ├── Name(__rpython_match_subject_0)
        └── Name(valor)
    └── If
        ├── Compare
        │   ├── Name(__rpython_match_subject_0)
        │   ├── Eq
        │   └── Str('1')
        ├── Return(Str('número um'))
        └── orelse: If
            ├── Compare
            │   ├── Name(__rpython_match_subject_0)
            │   ├── Eq
            │   └── Str('2')
            ├── Return(Str('número dois'))
            └── orelse: Assign + Return
```

No caso da captura, o último ramo é equivalente a:

```text
Else
├── Assign
│   ├── Name(outro)
│   └── Name(__rpython_match_subject_0)
└── Return(Str('valor desconhecido'))
```

## Integração automática

O ponto de integração no FlowSpace é:

```python
# rpython/flowspace/objspace.py

def build_flow(func):
    func = lower_function(func)
    _assert_rpythonic(func)
    ...
```

A função `lower_function()` obtém o código-fonte, chama `transform_source()`, recompila a função sem `match` e entrega a nova função ao fluxo normal do RPython.

Entretanto, com Python 2.7 essa integração interna não pode ser usada para ler o arquivo original, pois Python 2.7 falha antes, durante o parsing de `match`. Por isso o caminho correto é o launcher externo:

```bash
./rpython/bin/rpython-match \
    --python2 /caminho/para/python2.7 \
    target_nome.py
```

O launcher transforma o arquivo com Python 3 e só depois chama o tradutor RPython com Python 2.7.

## Teste mínimo

```python
def nome(valor):
    match valor:
        case "1":
            return "número um"
        case "2":
            return "número dois"
        case outro:
            return "valor desconhecido"
```

Equivalente para o tradutor RPython:

```python
def nome(valor):
    __rpython_match_subject_0 = valor
    if __rpython_match_subject_0 == '1':
        return "número um"
    elif __rpython_match_subject_0 == '2':
        return "número dois"
    else:
        outro = __rpython_match_subject_0
        return "valor desconhecido"
```
