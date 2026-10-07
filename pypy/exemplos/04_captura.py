# -*- coding: utf-8 -*-


def mostrar(valor):
    match valor:
        case "admin":
            return "usuario administrador"
        case "convidado":
            return "usuario convidado"
        case nome:
            return "usuario recebido: " + nome


def entry_point(argv):
    if len(argv) < 2:
        print "Uso: 04_captura [admin|convidado|nome]"
        return 1
    print mostrar(argv[1])
    return 0


def target(*args):
    return entry_point
