"""Parse and lower a small RPython-friendly subset of match/case.

The parser builds an intermediate AST from ``patternmatching_ast`` and only
then emits ordinary if/elif/else source accepted by the legacy RPython
translator.
"""
from __future__ import absolute_import

import ast
import inspect
import re
import textwrap

from rpython.tool.patternmatching_ast import (CaseNode, CapturePattern,
    BooleanPattern, LiteralPattern, MatchNode, OrPattern, SourceNode,
    WildcardPattern, pattern_name)

_MATCH_RE = re.compile(r'^(?P<indent>[ \t]*)match[ \t]+(?P<subject>.+):[ \t]*(?:#.*)?$')
_CASE_RE = re.compile(r'^(?P<indent>[ \t]*)case[ \t]+(?P<pattern>.+):[ \t]*(?:#.*)?$')
_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z_0-9]*$')


class PatternSyntaxError(ValueError):
    """Raised when the supported match subset is used incorrectly."""


def _indent_width(text):
    return len(text.expandtabs(8))


def _line_indent(line):
    return line[:len(line) - len(line.lstrip(' \t'))]


def _is_child(line, parent_indent):
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        return False
    return _indent_width(_line_indent(line)) > parent_indent


def _find_suite_end(lines, start, parent_indent):
    i = start
    while i < len(lines):
        if _is_child(lines[i], parent_indent):
            i += 1
        elif lines[i].strip() == '' or lines[i].lstrip().startswith('#'):
            i += 1
        else:
            break
    if i == start:
        raise PatternSyntaxError('line %d: expected an indented suite' % (start + 1))
    return i


def _dedent_lines(lines, amount):
    result = []
    for line in lines:
        if line.strip() == '':
            result.append(line)
        else:
            prefix = _line_indent(line)
            if _indent_width(prefix) < amount:
                raise PatternSyntaxError('case body has invalid indentation')
            result.append(line[amount:])
    return result


def _split_or_pattern(pattern):
    """Split top-level ``|`` characters, ignoring quoted string contents."""
    parts = []
    start = 0
    quote = None
    escaped = False
    depth = 0
    for index, char in enumerate(pattern):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == '|' and depth == 0:
            parts.append(pattern[start:index].strip())
            start = index + 1
    if parts:
        parts.append(pattern[start:].strip())
    return parts


def _parse_pattern(pattern, lineno):
    pattern = pattern.strip()
    alternatives = _split_or_pattern(pattern)
    if alternatives:
        if any(not item for item in alternatives):
            raise PatternSyntaxError('line %d: empty pattern around |' % lineno)
        parsed = [_parse_pattern(item, lineno) for item in alternatives]
        for item in parsed:
            if pattern_name(item) in ('capture', 'wildcard', 'or'):
                raise PatternSyntaxError(
                    'line %d: | supports only number, string, and boolean patterns'
                    % lineno)
        return OrPattern(parsed)
    if pattern == '_':
        return WildcardPattern()
    if pattern == 'True':
        return BooleanPattern(True)
    if pattern == 'False':
        return BooleanPattern(False)
    if _NAME_RE.match(pattern):
        return CapturePattern(pattern)
    if ' if ' in pattern or pattern.startswith(('(', '[', '{')):
        raise PatternSyntaxError(
            'line %d: only number, string, and _ patterns are supported' % lineno)
    try:
        value = ast.literal_eval(pattern)
    except (ValueError, SyntaxError):
        raise PatternSyntaxError(
            'line %d: pattern must be a number, string, or _' % lineno)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise PatternSyntaxError(
            'line %d: pattern must be a number, string, or _' % lineno)
    return LiteralPattern(value)


def _parse_range(lines, start, end, counter):
    nodes = []
    i = start
    while i < end:
        line = lines[i]
        match = _MATCH_RE.match(line.rstrip('\n'))
        if not match:
            nodes.append(line)
            i += 1
            continue
        indent = match.group('indent')
        subject = match.group('subject').strip()
        if not subject:
            raise PatternSyntaxError('line %d: match requires an expression' % (i + 1))
        indent_width = _indent_width(indent)
        temp_name = '__rpython_match_subject_%d' % counter[0]
        counter[0] += 1
        suite_start = i + 1
        suite_end = _find_suite_end(lines, suite_start, indent_width)
        cases = []
        j = suite_start
        while j < suite_end:
            if lines[j].strip() == '' or lines[j].lstrip().startswith('#'):
                j += 1
                continue
            case_match = _CASE_RE.match(lines[j].rstrip('\n'))
            if (not case_match or
                    _indent_width(case_match.group('indent')) != indent_width + 4):
                raise PatternSyntaxError(
                    'line %d: expected case indented four spaces inside match' % (j + 1))
            case_start = j + 1
            case_end = _find_suite_end(lines, case_start, indent_width + 4)
            body, counter = _parse_range(lines, case_start, case_end, counter)
            body = SourceNode(body)
            pattern = _parse_pattern(case_match.group('pattern'), j + 1)
            cases.append(CaseNode(pattern, body, j + 1))
            j = case_end
        if not cases:
            raise PatternSyntaxError('line %d: match must contain at least one case' % (i + 1))
        nodes.append(MatchNode(subject, cases, indent, temp_name))
        i = suite_end
    return nodes, counter


def parse_source(source):
    """Parse source into a ``SourceNode`` intermediate AST."""
    if not isinstance(source, str):
        raise TypeError('source must be a string')
    lines, unused = _parse_range(source.splitlines(True), 0,
                                 len(source.splitlines(True)), [0])
    return SourceNode(lines)


def _emit_node(node):
    if isinstance(node, str):
        return [node]
    if isinstance(node, SourceNode):
        result = []
        for child in node.lines:
            result.extend(_emit_node(child))
        return result
    if not isinstance(node, MatchNode):
        raise TypeError('unknown AST node: %r' % (node,))
    result = [node.indent + node.temp_name + ' = ' + node.subject + '\n']
    emitted = False
    catch_all = False
    for index, case in enumerate(node.cases):
        kind = pattern_name(case.pattern)
        if kind in ('wildcard', 'capture'):
            if catch_all:
                raise PatternSyntaxError('line %d: duplicate catch-all case' % case.lineno)
            catch_all = True
            if index != len(node.cases) - 1:
                raise PatternSyntaxError(
                    'line %d: wildcard/capture case must be last' % case.lineno)
            if emitted:
                result.append(node.indent + 'else:\n')
            else:
                result.append(node.indent + 'if True:\n')
            body = _emit_node(case.body)
            body = _dedent_lines(body, 4)
            if kind == 'capture':
                body.insert(0, node.indent + '    ' + case.pattern.name +
                            ' = ' + node.temp_name + '\n')
        elif kind == 'boolean':
            keyword = 'if' if not emitted else 'elif'
            value = 'True' if case.pattern.value else 'False'
            result.append(node.indent + keyword + ' ' + node.temp_name +
                          ' is ' + value + ':\n')
            body = _dedent_lines(_emit_node(case.body), 4)
        elif kind == 'or':
            conditions = []
            for alternative in case.pattern.patterns:
                alternative_kind = pattern_name(alternative)
                if alternative_kind == 'boolean':
                    value = 'True' if alternative.value else 'False'
                    conditions.append(node.temp_name + ' is ' + value)
                else:
                    conditions.append(node.temp_name + ' == ' +
                                      repr(alternative.value))
            keyword = 'if' if not emitted else 'elif'
            result.append(node.indent + keyword + ' ' + ' or '.join(conditions) +
                          ':\n')
            body = _dedent_lines(_emit_node(case.body), 4)
        else:
            keyword = 'if' if not emitted else 'elif'
            value = repr(case.pattern.value)
            result.append(node.indent + keyword + ' ' + node.temp_name +
                          ' == ' + value + ':\n')
            body = _dedent_lines(_emit_node(case.body), 4)
        result.extend(body)
        emitted = True
    return result


def emit_source(tree):
    """Emit Python 2.7-compatible source from the intermediate AST."""
    if not isinstance(tree, SourceNode):
        raise TypeError('tree must be a SourceNode')
    return ''.join(_emit_node(tree))


def transform_source(source):
    """Parse and lower supported match statements to if/elif/else."""
    return emit_source(parse_source(source))


def lower_function(func):
    """Return *func*, or a source-lowered replacement when it contains match."""
    try:
        source = inspect.getsource(func)
    except (IOError, OSError, TypeError):
        return func
    if not re.search(r'^[ \t]*match[ \t]+', source, re.MULTILINE):
        return func
    lowered = transform_source(textwrap.dedent(source))
    namespace = dict(func.__globals__)
    filename = getattr(func.__code__, 'co_filename', '<rpython-match>')
    code = compile(lowered, filename, 'exec')
    exec(code, namespace)
    replacement = namespace.get(func.__name__)
    if replacement is None or not hasattr(replacement, '__code__'):
        raise PatternSyntaxError(
            'could not rebuild function %s after lowering match' % func.__name__)
    replacement.__defaults__ = func.__defaults__
    if hasattr(func, '__kwdefaults__'):
        replacement.__kwdefaults__ = func.__kwdefaults__
    replacement.__module__ = func.__module__
    replacement.__doc__ = func.__doc__
    replacement._rpython_match_lowered_ = True
    return replacement


parse_and_lower = transform_source


if __name__ == '__main__':
    import sys
    sys.stdout.write(transform_source(sys.stdin.read()))
