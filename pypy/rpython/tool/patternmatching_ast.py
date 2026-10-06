"""Small, Python-2-compatible AST for the supported match subset."""
from __future__ import absolute_import


class Node(object):
    pass


class Pattern(Node):
    pass


class LiteralPattern(Pattern):
    def __init__(self, value):
        self.value = value


class BooleanPattern(Pattern):
    def __init__(self, value):
        self.value = value


class OrPattern(Pattern):
    def __init__(self, patterns):
        self.patterns = patterns


class CapturePattern(Pattern):
    def __init__(self, name):
        self.name = name


class WildcardPattern(Pattern):
    pass


class CaseNode(Node):
    def __init__(self, pattern, body, lineno):
        self.pattern = pattern
        self.body = body
        self.lineno = lineno


class MatchNode(Node):
    def __init__(self, subject, cases, indent, temp_name):
        self.subject = subject
        self.cases = cases
        self.indent = indent
        self.temp_name = temp_name


class SourceNode(Node):
    def __init__(self, lines):
        self.lines = lines


def pattern_name(pattern):
    if isinstance(pattern, OrPattern):
        return 'or'
    if isinstance(pattern, BooleanPattern):
        return 'boolean'
    if isinstance(pattern, LiteralPattern):
        return 'literal'
    if isinstance(pattern, CapturePattern):
        return 'capture'
    if isinstance(pattern, WildcardPattern):
        return 'wildcard'
    raise TypeError('unknown pattern node: %r' % (pattern,))
