# -*- coding: utf-8 -*-


def classificar(grupo, valor):
    match grupo:
        case "numero":
            match valor:
                case "1":
                    return "numero um"
                case "2":
                    return "numero dois"
                case outro:
                    return "numero desconhecido: " + outro
        case "texto":
            match valor:
                case "a" | "A":
                    return "letra A"
                case "b" | "B":
                    return "letra B"
                case outro:
                    return "texto desconhecido: " + outro
        case outro:
            return "grupo desconhecido: " + outro


def entry_point(argv):
    if len(argv) < 3:
        print "Uso: 05_aninhado [numero|texto] [valor]"
        return 1
    print classificar(argv[1], argv[2])
    return 0


def target(*args):
    return entry_point
