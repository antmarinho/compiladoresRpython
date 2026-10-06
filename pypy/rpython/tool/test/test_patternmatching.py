from __future__ import absolute_import

import unittest

from rpython.tool.patternmatching import (PatternSyntaxError, lower_function,
                                          parse_source, transform_source)
from rpython.tool.patternmatching_ast import (CapturePattern, LiteralPattern,
                                              BooleanPattern, MatchNode,
                                              OrPattern, SourceNode)


def function_with_match(value):
    match value:
        case "1":
            return "número um"
        case text:
            return text


class TestPatternMatchingLowering(unittest.TestCase):
    def test_number_and_string(self):
        source = '''def classify(value):
    match value:
        case 1:
            return "one"
        case "ok":
            return "okay"
        case _:
            return "other"
'''
        expected = '''def classify(value):
    __rpython_match_subject_0 = value
    if __rpython_match_subject_0 == 1:
        return "one"
    elif __rpython_match_subject_0 == 'ok':
        return "okay"
    else:
        return "other"
'''
        self.assertEqual(transform_source(source), expected)

    def test_subject_is_evaluated_once(self):
        source = '''match next_value():
    case -1:
        return 1
    case 2.5:
        return 2
'''
        result = transform_source(source)
        self.assertIn('__rpython_match_subject_0 = next_value()\n', result)
        self.assertEqual(result.count('next_value()'), 1)
        self.assertIn("elif __rpython_match_subject_0 == 2.5:", result)

    def test_capture_number_and_string(self):
        source = '''def identity(value):
    match value:
        case number:
            return number

def text_identity(value):
    match value:
        case text:
            return text
'''
        result = transform_source(source)
        self.assertIn('if True:\n        number = __rpython_match_subject_0', result)
        self.assertIn('return number', result)
        self.assertIn('if True:\n        text = __rpython_match_subject_1', result)
        self.assertIn('return text', result)

    def test_capture_must_be_last(self):
        with self.assertRaises(PatternSyntaxError):
            transform_source('''match x:\n    case value:\n        return value\n    case 1:\n        return 1\n''')

    def test_lower_function(self):
        lowered = lower_function(function_with_match)
        self.assertEqual(lowered("1"), "número um")
        self.assertEqual(lowered("abc"), "abc")
        self.assertTrue(getattr(lowered, '_rpython_match_lowered_', False))

    def test_intermediate_ast(self):
        tree = parse_source('''match value:\n    case "ok":\n        return 1\n    case other:\n        return other\n''')
        self.assertIsInstance(tree, SourceNode)
        self.assertIsInstance(tree.lines[0], MatchNode)
        self.assertIsInstance(tree.lines[0].cases[0].pattern, LiteralPattern)
        self.assertIsInstance(tree.lines[0].cases[1].pattern, CapturePattern)

    def test_boolean_patterns(self):
        source = '''def describe(value):
    match value:
        case True:
            return "yes"
        case False:
            return "no"
        case other:
            return "other"
'''
        tree = parse_source(source)
        match = tree.lines[1]
        self.assertIsInstance(match.cases[0].pattern, BooleanPattern)
        self.assertIsInstance(match.cases[1].pattern, BooleanPattern)
        result = transform_source(source)
        self.assertIn('if __rpython_match_subject_0 is True:', result)
        self.assertIn('elif __rpython_match_subject_0 is False:', result)
        namespace = {}
        exec(compile(result, '<lowered>', 'exec'), namespace)
        self.assertEqual(namespace['describe'](True), 'yes')
        self.assertEqual(namespace['describe'](False), 'no')

    def test_or_patterns_for_all_literal_types(self):
        source = '''def classify(value):
    match value:
        case "yes" | "y":
            return "string"
        case 1 | 2 | 3:
            return "number"
        case True | False:
            return "boolean"
        case other:
            return "other"
'''
        tree = parse_source(source)
        self.assertIsInstance(tree.lines[1].cases[0].pattern, OrPattern)
        result = transform_source(source)
        self.assertIn("if __rpython_match_subject_0 == 'yes' or "
                      "__rpython_match_subject_0 == 'y':", result)
        self.assertIn('elif __rpython_match_subject_0 == 1 or '
                      '__rpython_match_subject_0 == 2 or '
                      '__rpython_match_subject_0 == 3:', result)
        self.assertIn('elif __rpython_match_subject_0 is True or '
                      '__rpython_match_subject_0 is False:', result)
        namespace = {}
        exec(compile(result, '<lowered>', 'exec'), namespace)
        self.assertEqual(namespace['classify']('y'), 'string')
        self.assertEqual(namespace['classify'](2), 'number')
        self.assertEqual(namespace['classify'](False), 'boolean')
        self.assertEqual(namespace['classify']('no'), 'other')

    def test_or_capture_is_rejected(self):
        with self.assertRaises(PatternSyntaxError):
            transform_source('''match value:\n    case 1 | other:\n        return value\n''')

    def test_nested_match(self):
        source = '''def classify(value):
    match value:
        case 1:
            match value:
                case "x":
                    return 10
                case _:
                    return 11
        case _:
            return 20
'''
        result = transform_source(source)
        self.assertIn('__rpython_match_subject_1 = value', result)
        self.assertIn("if __rpython_match_subject_1 == 'x':", result)

    def test_rejects_guard_and_structural_pattern(self):
        with self.assertRaises(PatternSyntaxError):
            transform_source('''match x:\n    case 1 if x > 0:\n        return 1\n''')
        with self.assertRaises(PatternSyntaxError):
            transform_source('''match x:\n    case [a, b]:\n        return 1\n''')


if __name__ == '__main__':
    unittest.main()
