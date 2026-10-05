# -*- coding: utf-8 -*-


def classificar(valor):
    match valor:
        case "sim" | "s":
            return "resposta afirmativa"
        case "1" | "2" | "3":
            return "numero pequeno"
        case "true" | "false":
            return "booleano como texto"
        case outro:
            return "outro valor: " + outro


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: target_exemplo [sim|s|1|2|3|true|false|texto]"
        return 1

    valor = argv[1]
    print classificar(valor)
    return 0


def target(*args):
    return entry_point
