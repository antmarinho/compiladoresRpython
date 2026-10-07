# -*- coding: utf-8 -*-


def classificar(valor):
    match valor:
        case "0":
            return "zero"
        case "1":
            return "um"
        case "2":
            return "dois"
        case "10":
            return "dez"
        case outro:
            return "valor desconhecido: " + outro


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: 01_numeros_strings [0|1|2|10|texto]"
        return 1
    print classificar(argv[1])
    return 0


def target(*args):
    return entry_point
