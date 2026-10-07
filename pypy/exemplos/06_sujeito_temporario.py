# -*- coding: utf-8 -*-


def obter_valor(argv):
    return argv[1]


def analisar(argv):
    match obter_valor(argv):
        case "ok":
            return "valor aprovado"
        case "erro":
            return "valor rejeitado"
        case outro:
            return "valor recebido: " + outro


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: 06_sujeito_temporario [ok|erro|outro]"
        return 1
    print analisar(argv)
    return 0


def target(*args):
    return entry_point
