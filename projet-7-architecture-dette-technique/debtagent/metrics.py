"""Static metrics of one Python file, from its syntax tree and its comments.

Cyclomatic complexity follows McCabe (1976): one plus the number of decision
points. As in common tools such as radon, each if, elif, for, while, except,
conditional expression, match case, and comprehension condition counts one,
and each boolean operator counts one per extra operand. Nested functions and
classes are measured separately.
"""
import ast
import io
import re
import tokenize

_MARKER = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b[:\s-]*(.*)")
_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def complexity(node):
    count = 1
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, _NESTED):
            continue
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.match_case)):
            count += 1
        elif isinstance(n, ast.BoolOp):
            count += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            count += 1 + len(n.ifs)
        stack.extend(ast.iter_child_nodes(n))
    return count


def functions(tree):
    """Yield (qualified name, node) for every function, methods included."""
    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + child.name
                yield name, child
                yield from walk(child, name + ".")
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, prefix + child.name + ".")
    yield from walk(tree, "")


def imports(tree, module, is_package):
    """Yield (names, line): for each import statement, the modules it may name.

    For "import a.b.c" the name is a.b.c; for "from a.b import c, d" the names
    are a.b.c, a.b.d and the package a.b itself. Relative imports are resolved
    against the package of the module.
    """
    package = module if is_package else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield [alias.name], node.lineno
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                if node.level > 1:
                    parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join(p for p in parts + ([node.module] if node.module else []) if p)
            yield [f"{base}.{a.name}" if base else a.name for a in node.names] + ([base] if base else []), node.lineno


def code_lines(source):
    """Line numbers that hold code: not blank, not only a comment."""
    lines = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                                tokenize.DEDENT, tokenize.ENDMARKER):
                lines.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        lines = {i for i, l in enumerate(source.splitlines(), 1) if l.strip() and not l.strip().startswith("#")}
    return lines


def markers(source):
    """Self-admitted technical debt: TODO, FIXME, HACK and XXX comments."""
    found = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                m = _MARKER.match(tok.string)
                if m:
                    found.append((tok.start[0], m.group(1), m.group(2).strip()[:300]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return found
