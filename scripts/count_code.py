"""Conservative original-backend Python count, excluding vendored code and tests."""
import ast
import io
import json
import tokenize
from pathlib import Path


def inventory(project):
    rows = []
    for path in sorted((project/'backend/brain_eval').rglob('*.py')):
        if 'vendor' in path.parts:
            continue
        source = path.read_text()
        tree = ast.parse(source)
        docstrings = set()
        functions = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
                head = node.body[0]
                if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant) and isinstance(head.value.value, str):
                    docstrings.update(range(head.lineno, head.end_lineno+1))
        lines = set()
        skipped = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                   tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING}
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type not in skipped:
                lines.update(range(token.start[0], token.end[0]+1))
        rows.append(dict(file=str(path.relative_to(project)), code_lines=len(lines-docstrings), functions=functions))
    return dict(scope='Original backend Python only; excludes vendor, tests, scripts, TS, shell and docs',
                counting_rule='Physical lines containing non-comment tokens, excluding AST docstring lines',
                total_lines=sum(r['code_lines'] for r in rows),
                functions=sum(r['functions'] for r in rows),
                nonempty_modules=sum(r['code_lines'] > 0 for r in rows), files=rows)


if __name__ == '__main__':
    print(json.dumps(inventory(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
