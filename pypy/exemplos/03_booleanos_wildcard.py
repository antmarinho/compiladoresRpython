# -*- coding: utf-8 -*-


def interpretar(valor):
    match valor:
        case "true":
            return "verdadeiro"
        case "false":
            return "falso"
        case _:
            return "valor sem classificacao"


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: 03_booleanos_wildcard [true|false|outro]"
        return 1
    print interpretar(argv[1])
    return 0


def target(*args):
    return entry_point
