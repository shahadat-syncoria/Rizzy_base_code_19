#!/usr/bin/env python3

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET = SCRIPT_DIR / "Odoo_sync_splited_script"
MODEL_BASES = {"Model", "TransientModel", "AbstractModel"}
FIELD_CALLBACK_KEYWORDS = {
    "compute",
    "default",
    "domain",
    "group_expand",
    "inverse",
    "search",
    "selection",
}
RELATIVE_IMPORT_RE = re.compile(
    r"(?m)^(?P<indent>\s*)from (?P<dots>\.+)(?P<module>[A-Za-z_][\w\.]*)? import (?P<rest>.+)$"
)


class SourceBuffer:
    def __init__(self, text: str) -> None:
        self.text = text
        self._line_offsets = []
        offset = 0
        for line in text.splitlines(keepends=True):
            self._line_offsets.append(offset)
            offset += len(line)
        if not self._line_offsets:
            self._line_offsets.append(0)

    def line_start(self, lineno: int) -> int:
        return self._line_offsets[lineno - 1]

    def index(self, lineno: int, col: int) -> int:
        return self._line_offsets[lineno - 1] + col

    def start_lineno(self, node: ast.AST) -> int:
        decorators = getattr(node, "decorator_list", None)
        if decorators:
            return decorators[0].lineno
        return node.lineno

    def text_for_node(self, node: ast.AST, include_indent: bool = False) -> str:
        start_lineno = self.start_lineno(node)
        start_col = 0 if include_indent else getattr(node, "col_offset", 0)
        start = self.line_start(start_lineno) if include_indent else self.index(start_lineno, start_col)
        end = self.index(node.end_lineno, node.end_col_offset)
        return self.text[start:end]

    def leading_indent(self, lineno: int) -> str:
        line = self.text[self.line_start(lineno) :].splitlines()[0]
        return line[: len(line) - len(line.lstrip(" \t"))]


def main() -> int:
    if len(sys.argv) > 1:
        source = Path(sys.argv[1]).expanduser()
    else:
        source_input = input("Enter source add-ons root: ").strip()
        if not source_input:
            print("Source add-ons root is required.", file=sys.stderr)
            return 1
        source = Path(source_input).expanduser()

    target = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else DEFAULT_TARGET

    if not source.is_dir():
        print(f"Source add-ons root not found: {source}", file=sys.stderr)
        return 1

    if shutil.which("rsync") is None:
        print("Required command not found: rsync", file=sys.stderr)
        return 1

    copy_tree(source, target)
    init_files = find_model_init_files(target)
    if not init_files:
        print(f"No models/__init__.py files found under: {target}", file=sys.stderr)
        return 1

    transformed_modules = 0
    for init_path in init_files:
        modules = parse_model_modules(init_path.read_text())
        table_dir = init_path.parent / "table_models"
        table_dir.mkdir(parents=True, exist_ok=True)
        write_table_init(table_dir / "__init__.py", modules)
        ensure_table_models_import(init_path)

        for module_name in modules:
            module_path = init_path.parent / f"{module_name}.py"
            if not module_path.exists():
                print(f"Skipping missing model module: {module_path}", file=sys.stderr)
                continue
            transform_model_file(module_path, table_dir / f"{module_name}.py", set(modules))
            transformed_modules += 1

    remove_cache_artifacts(target)
    validate_python_tree(target)

    print(f"Processed {len(init_files)} model packages")
    print(f"Transformed {transformed_modules} model modules")
    print(f"Split tree is available in: {target}")
    return 0


def copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            ".git",
            "--exclude",
            "__pycache__",
            "--exclude",
            "*.pyc",
            f"{source}/",
            f"{target}/",
        ],
        check=True,
    )


def find_model_init_files(root: Path) -> list[Path]:
    init_files = []
    for path in root.rglob("__init__.py"):
        if path.parent.name != "models":
            continue
        if "static" in path.parts:
            continue
        init_files.append(path)
    return sorted(init_files)


def parse_model_modules(text: str) -> list[str]:
    modules = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"from\s+\.\s+import\s+(.+)$", line)
        if not match:
            continue
        imported = match.group(1).split("#", 1)[0]
        for name in [item.strip() for item in imported.split(",")]:
            if name and name != "table_models":
                modules.append(name)
    return modules


def write_table_init(init_path: Path, modules: list[str]) -> None:
    lines = [f"from . import {module}" for module in modules]
    init_path.write_text("\n".join(lines) + ("\n" if lines else ""))


def ensure_table_models_import(init_path: Path) -> None:
    text = init_path.read_text()
    if "from . import table_models" in text:
        return
    lines = text.splitlines(keepends=True)
    insert_at = None
    for index, line in enumerate(lines):
        if re.match(r"\s*from\s+\.\s+import\s+", line):
            insert_at = index
            break
    if insert_at is None:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "from . import table_models\n"
    else:
        lines.insert(insert_at, "from . import table_models\n")
        text = "".join(lines)
    init_path.write_text(text)


def transform_model_file(runtime_path: Path, table_path: Path, moved_modules: set[str]) -> None:
    source = runtime_path.read_text()
    buffer = SourceBuffer(source)
    tree = ast.parse(source)

    rebuilt_runtime = rebuild_module(buffer, tree, mode="runtime", moved_modules=moved_modules)
    rebuilt_table = rebuild_module(buffer, tree, mode="table", moved_modules=moved_modules)
    rebuilt_table = rewrite_table_relative_imports(rebuilt_table, moved_modules)

    runtime_path.write_text(rebuilt_runtime.rstrip() + "\n")
    table_path.write_text(rebuilt_table.rstrip() + "\n")


def rebuild_module(buffer: SourceBuffer, tree: ast.Module, mode: str, moved_modules: set[str]) -> str:
    parts = []
    cursor = 0
    for node in tree.body:
        start = buffer.line_start(buffer.start_lineno(node))
        end = buffer.index(node.end_lineno, node.end_col_offset)
        parts.append(buffer.text[cursor:start])
        if isinstance(node, ast.ClassDef) and is_model_class(node):
            parts.append(rebuild_class(node, buffer, mode, moved_modules))
        else:
            parts.append(buffer.text[start:end])
        cursor = end
    parts.append(buffer.text[cursor:])
    return "".join(parts)


def is_model_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            if base.value.id == "models" and base.attr in MODEL_BASES:
                return True
        if isinstance(base, ast.Name) and base.id in MODEL_BASES:
            return True
    return False


def rebuild_class(node: ast.ClassDef, buffer: SourceBuffer, mode: str, moved_modules: set[str]) -> str:
    if not node.body:
        return buffer.text_for_node(node, include_indent=True)

    class_start = buffer.line_start(buffer.start_lineno(node))
    body_start = buffer.line_start(node.body[0].lineno)
    header = buffer.text[class_start:body_start]
    if not header.endswith("\n"):
        header += "\n"
    indent = buffer.leading_indent(node.body[0].lineno) or "    "

    docstring_stmt = get_docstring_stmt(node)
    schema_method_names = collect_schema_method_names(node)
    table_segments = []
    runtime_segments = []

    if docstring_stmt is not None:
        docstring_text = buffer.text_for_node(docstring_stmt, include_indent=True)
        table_segments.append(docstring_text)
        runtime_segments.append(docstring_text)

    original_name = None
    original_inherit_expr = None
    original_inherit_value = None

    for stmt in node.body:
        if stmt is docstring_stmt:
            continue

        stmt_kind = classify_class_stmt(stmt, schema_method_names)
        stmt_text = buffer.text_for_node(stmt, include_indent=True)

        if stmt_kind == "schema":
            table_segments.append(stmt_text)
            name = assignment_name(stmt)
            if name == "_name":
                original_name = string_literal(stmt_value(stmt))
            if name == "_inherit":
                value = stmt_value(stmt)
                original_inherit_expr = buffer.text_for_node(value)
                original_inherit_value = literal_value(value)
            continue

        if stmt_kind == "runtime":
            runtime_segments.append(stmt_text)
            continue

        table_segments.append(stmt_text)
        runtime_segments.append(stmt_text)

    runtime_inherit = synthesize_runtime_inherit(original_name, original_inherit_expr, original_inherit_value)
    if runtime_inherit is not None:
        inherit_stmt = f"{indent}_inherit = {runtime_inherit}"
        if runtime_segments and docstring_stmt is not None:
            runtime_segments.insert(1, inherit_stmt)
        else:
            runtime_segments.insert(0, inherit_stmt)

    if not table_segments:
        table_segments = [f"{indent}pass"]
    if not runtime_segments:
        runtime_segments = [f"{indent}pass"]

    segments = table_segments if mode == "table" else runtime_segments
    return header + "\n\n".join(segment.rstrip() for segment in segments)


def get_docstring_stmt(node: ast.ClassDef) -> ast.Expr | None:
    if not node.body:
        return None
    stmt = node.body[0]
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return stmt
    return None


def collect_schema_method_names(node: ast.ClassDef) -> set[str]:
    method_names = {
        stmt.name
        for stmt in node.body
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    referenced = set()
    for stmt in node.body:
        if is_metadata_assignment(stmt) or is_field_assignment(stmt):
            referenced.update(schema_referenced_method_names(stmt, method_names))
    return referenced


def schema_referenced_method_names(stmt: ast.stmt, method_names: set[str]) -> set[str]:
    value = stmt_value(stmt)
    if value is None:
        return set()

    referenced = {
        node.id
        for node in ast.walk(value)
        if isinstance(node, ast.Name) and node.id in method_names
    }

    if isinstance(value, ast.Call) and is_fields_call(value.func):
        for keyword in value.keywords:
            if keyword.arg in FIELD_CALLBACK_KEYWORDS:
                referenced.update(extract_method_name_literals(keyword.value, method_names))

    return referenced


def extract_method_name_literals(node: ast.AST, method_names: set[str]) -> set[str]:
    referenced = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value in method_names:
            referenced.add(child.value)
    return referenced


def classify_class_stmt(stmt: ast.stmt, schema_method_names: set[str]) -> str:
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "schema" if stmt.name in schema_method_names else "runtime"
    if is_metadata_assignment(stmt) or is_field_assignment(stmt):
        return "schema"
    return "both"


def is_metadata_assignment(stmt: ast.stmt) -> bool:
    name = assignment_name(stmt)
    return bool(name and name.startswith("_"))


def is_field_assignment(stmt: ast.stmt) -> bool:
    value = stmt_value(stmt)
    return isinstance(value, ast.Call) and is_fields_call(value.func)


def is_fields_call(func: ast.expr) -> bool:
    return isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "fields"


def assignment_name(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    return None


def stmt_value(stmt: ast.stmt) -> ast.expr | None:
    if isinstance(stmt, ast.Assign):
        return stmt.value
    if isinstance(stmt, ast.AnnAssign):
        return stmt.value
    return None


def string_literal(node: ast.expr | None) -> str | None:
    value = literal_value(node)
    return value if isinstance(value, str) else None


def literal_value(node: ast.expr | None):
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def synthesize_runtime_inherit(
    model_name: str | None,
    inherit_expr: str | None,
    inherit_value,
) -> str | None:
    if model_name is None:
        return inherit_expr

    return repr(model_name)


def rewrite_table_relative_imports(text: str, moved_modules: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        indent = match.group("indent")
        dots = match.group("dots")
        module = match.group("module") or ""
        rest = match.group("rest")
        depth = len(dots)

        if depth == 1:
            first_segment = module.split(".", 1)[0] if module else ""
            new_depth = 1 if first_segment in moved_modules else 2
        else:
            new_depth = depth + 1

        return f"{indent}from {'.' * new_depth}{module} import {rest}"

    return RELATIVE_IMPORT_RE.sub(replace, text)


def remove_cache_artifacts(root: Path) -> None:
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in root.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)


def validate_python_tree(root: Path) -> None:
    errors = []
    for path in sorted(root.rglob("*.py")):
        try:
            ast.parse(path.read_text())
        except SyntaxError as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        raise RuntimeError("Python parse validation failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    raise SystemExit(main())
