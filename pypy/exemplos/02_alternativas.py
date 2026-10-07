# -*- coding: utf-8 -*-


def classificar_comando(valor):
    match valor:
        case "s" | "sim" | "yes":
            return "resposta positiva"
        case "n" | "nao" | "no":
            return "resposta negativa"
        case "1" | "2" | "3":
            return "numero de um a tres"
        case outro:
            return "comando desconhecido: " + outro


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: 02_alternativas [s|sim|n|nao|1|2|3|outro]"
        return 1
    print classificar_comando(argv[1])
    return 0


def target(*args):
    return entry_point
