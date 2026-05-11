#!/usr/bin/env python3

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = SCRIPT_DIR / "Odoo_sync_splited_script"
DEFAULT_TARGET = SCRIPT_DIR / "Odoo_sync_compile_left_script"
MIXIN_MODELS = {
    "mail.thread",
    "mail.activity.mixin",
    "portal.mixin",
    "pos.bus.mixin",
    "pos.load.mixin",
}
RELATIVE_IMPORT_RE = re.compile(
    r"(?m)^(?P<indent>\s*)from (?P<dots>\.{2,})(?P<module>[A-Za-z_][\w\.]*)? import (?P<rest>.+)$"
)
HELPER_COPIES = (
    (
        "os_delivery/delivery_apps/delivery_canada_post/models/canpost_request.py",
        "os_delivery/delivery_apps/delivery_canada_post/models/table_models/canpost_request.py",
    ),
    (
        "os_payment/payment_apps/odoo_clover_cloud/models/clover_request.py",
        "os_payment/payment_apps/odoo_clover_cloud/models/table_models/clover_request.py",
    ),
    (
        "os_payment/payment_apps/odoo_bambora_checkout/models/utils.py",
        "os_payment/payment_apps/odoo_bambora_checkout/models/table_models/utils.py",
    ),
)
HELPER_COPY_TARGETS = {Path(dest_rel) for _, dest_rel in HELPER_COPIES}
RUNTIME_IMPORT_REWRITES = {
    "from .canpost_request import CanadaPostRequest": (
        "from odoo.addons.os_delivery.delivery_apps.delivery_canada_post.models.table_models.canpost_request "
        "import CanadaPostRequest"
    ),
    "from ..models.clover_request import CloverRequest": (
        "from odoo.addons.os_payment.payment_apps.odoo_clover_cloud.models.table_models.clover_request "
        "import CloverRequest"
    ),
    "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.utils import (": (
        "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.table_models.utils import ("
    ),
}
TABLE_IMPORT_REWRITES = {
    "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.utils import (": (
        "from .utils import ("
    ),
    "from ..canpost_request import CanadaPostRequest": (
        "from .canpost_request import CanadaPostRequest"
    ),
}
BAMBORA_UTILS_PATH = Path("os_payment/payment_apps/odoo_bambora_checkout/models/utils.py")
BAMBORA_UTILS_IMPORT_PATTERNS = (
    "from .utils import *",
    "from ..utils import *",
    "from ...utils import *",
    "from .utils import (",
    "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.utils import (",
    "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.table_models.utils import (",
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

    def text_for_stmt(self, node: ast.AST) -> str:
        start = self.line_start(node.lineno)
        end = self.index(node.end_lineno, node.end_col_offset)
        return self.text[start:end]

    def indent_for(self, lineno: int) -> str:
        line = self.text[self.line_start(lineno):].splitlines()[0]
        return line[: len(line) - len(line.lstrip(" \t"))]


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TARGET

    if not source.is_dir():
        print(f"Source add-ons root not found: {source}", file=sys.stderr)
        return 1

    if shutil.which("rsync") is None:
        print("Required command not found: rsync", file=sys.stderr)
        return 1

    copy_tree(source, target)

    helper_copies_added = copy_helper_files(target)

    init_files = find_model_init_files(target)
    loader_updates = 0
    for init_path in init_files:
        modules = parse_model_modules(init_path.read_text())
        init_path.write_text(render_loader(modules))
        loader_updates += 1

    import_rewrites = rewrite_imports(target)
    bambora_import_rewrites = normalize_bambora_utils_imports(target)
    runtime_inherit_fixes = normalize_runtime_inherit(target)

    remove_cache_artifacts(target)
    verify_tree(source, target, helper_copies_added, init_files)

    print("Summary")
    print(f"- Source: {source}")
    print(f"- Target: {target}")
    print(f"- Loader files updated: {loader_updates}")
    print(f"- Runtime _inherit fixes: {runtime_inherit_fixes}")
    print(f"- Import rewrites: {import_rewrites + bambora_import_rewrites}")
    print("Helper copies added")
    for rel_path in helper_copies_added:
        print(f"- {rel_path}")
    print("Verification results")
    print("- Source tree left untouched")
    print("- No unrelated addons introduced")
    print("- No .pyc or __pycache__ in target")
    print("- All Python files parse successfully")
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
    modules: list[str] = []
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


def render_loader(modules: list[str]) -> str:
    pyc_entries = "\n".join(f"    {module!r}," for module in modules)
    if pyc_entries:
        pyc_block = f"pyc_files = [\n{pyc_entries}\n]"
    else:
        pyc_block = "pyc_files = [\n]"

    return (
        "from . import table_models\n\n"
        "import importlib\n"
        "import importlib.util\n"
        "import os\n"
        "import sys\n\n"
        "base_path = os.path.dirname(__file__)\n\n"
        'py_version = f"{sys.version_info.major}_{sys.version_info.minor}"\n'
        "version_folder = py_version\n\n"
        f"{pyc_block}\n\n"
        "def load_pyc_module(module_name, file_path):\n"
        "    spec = importlib.util.spec_from_file_location(module_name, file_path)\n"
        "    module = importlib.util.module_from_spec(spec)\n"
        "    sys.modules[module_name] = module\n"
        "    spec.loader.exec_module(module)\n\n"
        "for file_name in pyc_files:\n"
        '    module_name = f"{__name__}.{file_name}"\n'
        "    strip_python = py_version.replace('_', '')\n"
        "    file_path = os.path.join(base_path, '__pycache__', f\"{file_name}.cpython-{strip_python}.pyc\")\n"
        "    if os.path.exists(file_path):\n"
        "        load_pyc_module(module_name, file_path)\n"
        "    else:\n"
        "        importlib.import_module(module_name)\n"
    )


def copy_helper_files(root: Path) -> list[str]:
    added = []
    for src_rel, dest_rel in HELPER_COPIES:
        src = root / src_rel
        dest = root / dest_rel
        if not src.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        added.append(dest_rel)
    return added


def rewrite_imports(root: Path) -> int:
    rewrites = 0
    for path in sorted(root.rglob("*.py")):
        if "static" in path.parts:
            continue
        original = path.read_text()
        updated = original
        rel_path = path.relative_to(root)

        if "table_models" in path.parts:
            for old, new in TABLE_IMPORT_REWRITES.items():
                updated = updated.replace(old, new)
            if rel_path in HELPER_COPY_TARGETS:
                updated = deepen_table_model_imports(updated)
        else:
            for old, new in RUNTIME_IMPORT_REWRITES.items():
                updated = updated.replace(old, new)

        if updated != original:
            path.write_text(updated)
            rewrites += 1
    return rewrites


def normalize_bambora_utils_imports(root: Path) -> int:
    helper_path = root / BAMBORA_UTILS_PATH
    if not helper_path.exists():
        return 0

    helper_public_names = get_helper_public_names(helper_path)
    rewrites = 0
    for path in sorted((root / "os_payment/payment_apps/odoo_bambora_checkout/models").rglob("*.py")):
        if "static" in path.parts:
            continue
        original = path.read_text()
        updated = rewrite_bambora_utils_file(path, original, helper_public_names)
        if updated != original:
            path.write_text(updated)
            rewrites += 1
    return rewrites


def get_helper_public_names(helper_path: Path) -> list[str]:
    tree = ast.parse(helper_path.read_text())
    public_names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            public_names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    public_names.append(target.id)
    return public_names


def rewrite_bambora_utils_file(path: Path, source: str, helper_public_names: list[str]) -> str:
    import_lines = source.splitlines(keepends=True)
    filtered_lines = [
        line
        for line in import_lines
        if not any(pattern in line for pattern in BAMBORA_UTILS_IMPORT_PATTERNS)
    ]
    filtered_source = "".join(filtered_lines)

    if path.name == "utils.py":
        return filtered_source

    if "table_models" in path.parts:
        import_stmt = render_import_block(".utils", used_helper_names(filtered_source, helper_public_names))
    else:
        import_stmt = render_import_block(
            "odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.table_models.utils",
            used_helper_names(filtered_source, helper_public_names),
        )

    if not import_stmt:
        return filtered_source

    insert_at = find_import_insert_offset(filtered_source)
    return filtered_source[:insert_at] + import_stmt + filtered_source[insert_at:]


def used_helper_names(source: str, helper_public_names: list[str]) -> list[str]:
    tree = ast.parse(source)
    seen = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in helper_public_names
    }
    return [name for name in helper_public_names if name in seen]


def render_import_block(module_path: str, names: list[str]) -> str:
    if not names:
        return ""
    body = "".join(f"    {name},\n" for name in names)
    return f"from {module_path} import (\n{body})\n"


def find_import_insert_offset(source: str) -> int:
    tree = ast.parse(source)
    buffer = SourceBuffer(source)
    last_import_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_end = buffer.index(node.end_lineno, node.end_col_offset)
        else:
            break
    if last_import_end and not source[last_import_end:last_import_end + 1] == "\n":
        return last_import_end
    if last_import_end:
        return last_import_end + 1
    return 0


def deepen_table_model_imports(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        indent = match.group("indent")
        dots = match.group("dots")
        module = match.group("module") or ""
        rest = match.group("rest")
        return f"{indent}from {'.' * (len(dots) + 1)}{module} import {rest}"

    return RELATIVE_IMPORT_RE.sub(replace, text)


def normalize_runtime_inherit(root: Path) -> int:
    fixes = 0
    for path in sorted(root.rglob("*.py")):
        if "static" in path.parts or "table_models" in path.parts:
            continue
        original = path.read_text()
        updated = rewrite_runtime_inherit_file(original)
        if updated != original:
            path.write_text(updated)
            fixes += 1
    return fixes


def rewrite_runtime_inherit_file(source: str) -> str:
    tree = ast.parse(source)
    buffer = SourceBuffer(source)
    replacements: list[tuple[int, int, str]] = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if assignment_name(stmt) != "_inherit":
                continue
            value = stmt_value(stmt)
            literal = literal_value(value)
            if not (isinstance(literal, (list, tuple)) and all(isinstance(item, str) for item in literal)):
                continue

            non_mixins = [item for item in literal if item not in MIXIN_MODELS]
            if len(non_mixins) != 1 or len(non_mixins) == len(literal):
                continue

            start = buffer.line_start(stmt.lineno)
            end = buffer.index(stmt.end_lineno, stmt.end_col_offset)
            indent = buffer.indent_for(stmt.lineno)
            replacements.append((start, end, f"{indent}_inherit = {non_mixins[0]!r}"))

    if not replacements:
        return source

    parts = []
    cursor = 0
    for start, end, replacement in replacements:
        parts.append(source[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(source[cursor:])
    return "".join(parts)


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


def literal_value(node: ast.expr | None):
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def remove_cache_artifacts(root: Path) -> None:
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in root.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)


def verify_tree(source: Path, target: Path, helper_copies_added: list[str], init_files: list[Path]) -> None:
    if top_level_entries(source) != top_level_entries(target):
        raise RuntimeError("Top-level addon entries differ between source and target")

    for rel_path in helper_copies_added:
        if not (target / rel_path).exists():
            raise RuntimeError(f"Expected helper copy missing: {rel_path}")

    if list(target.rglob("__pycache__")):
        raise RuntimeError("Target contains __pycache__ directories")
    if list(target.rglob("*.pyc")):
        raise RuntimeError("Target contains .pyc files")

    for init_path in init_files:
        target_init = target / init_path.relative_to(target)
        text = target_init.read_text()
        if not text.startswith("from . import table_models\n"):
            raise RuntimeError(f"Loader missing table_models import: {target_init}")
        if "module_name = f\"{__name__}.{file_name}\"" not in text:
            raise RuntimeError(f"Loader missing module_name pattern: {target_init}")

    assert_absent(
        target,
        [
            "from ..models.clover_request import CloverRequest",
            "from odoo.addons.os_payment.payment_apps.odoo_bambora_checkout.models.utils import (",
            "from ....utils.delivery_data import DataUtils",
            "from ....shopify.utils import *",
            "from ....lib import mpgClasses",
            "from ....exceptions.MonerisGo import",
            "from ....exceptions.ExpireAPIKey import",
            "from ...canpost_request import CanadaPostRequest",
        ],
    )

    runtime_canpost = (
        target / "os_delivery/delivery_apps/delivery_canada_post/models/delivery_canada_post.py"
    ).read_text()
    if (
        "from odoo.addons.os_delivery.delivery_apps.delivery_canada_post.models.table_models.canpost_request "
        "import CanadaPostRequest"
    ) not in runtime_canpost:
        raise RuntimeError("Canada Post runtime import was not rewritten")

    for path in sorted(target.rglob("*.py")):
        ast.parse(path.read_text())

    bad_runtime_inherit = find_bad_runtime_inherit(target)
    if bad_runtime_inherit:
        raise RuntimeError("Runtime _inherit mixin patterns remain:\n" + "\n".join(bad_runtime_inherit))


def top_level_entries(root: Path) -> set[str]:
    return {path.name for path in root.iterdir()}


def assert_absent(root: Path, patterns: list[str]) -> None:
    for path in sorted(root.rglob("*.py")):
        text = path.read_text()
        for pattern in patterns:
            if pattern in text:
                raise RuntimeError(f"Unexpected pattern in {path}: {pattern}")


def find_bad_runtime_inherit(root: Path) -> list[str]:
    bad = []
    for path in sorted(root.rglob("*.py")):
        if "table_models" in path.parts or "static" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if assignment_name(stmt) != "_inherit":
                    continue
                literal = literal_value(stmt_value(stmt))
                if not (isinstance(literal, (list, tuple)) and all(isinstance(item, str) for item in literal)):
                    continue
                non_mixins = [item for item in literal if item not in MIXIN_MODELS]
                if len(non_mixins) == 1 and len(non_mixins) != len(literal):
                    bad.append(f"{path}:{node.name}")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
