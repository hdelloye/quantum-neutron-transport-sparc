"""Static compliance checks (stdlib only). Mirrors Qollab's own import Walker:
ast-walk main.py, follow every import whose top-level name is a local file/folder,
scan EVERY node (function bodies and try/except included), collect external names."""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

FORBIDDEN_REACHABLE = {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq", "qiskit_ibm_runtime"}
MAX_FILE_BYTES = 2_000_000          # Qollab says "2 MB"; use the stricter decimal reading
MAX_QOLLAB_FILES = 100
BACKEND_CONSTRUCTORS = {"AerSimulator", "BasicSimulator", "IonQProvider", "QiskitRuntimeService",
                        "BraketLocalBackend", "BraketProvider", "GenericBackendV2", "StatevectorSimulator"}
BACKEND_FACTORY_ATTRS = {"get_backend", "backends"}
ALLOWLIST_DIRS = ("tests", "scripts")   # local-dev runners may construct backends


def _module_file(root: Path, dotted: str) -> Path | None:
    base = root.joinpath(*dotted.split("."))
    for cand in (base / "__init__.py", base.with_suffix(".py")):
        if cand.is_file():
            return cand
    return None


def _is_local(root: Path, top: str) -> bool:
    return (root / f"{top}.py").is_file() or (root / top).is_dir()


def _package_of(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        return ".".join(parts[:-1])
    return ".".join(parts[:-1])


def _imported_names(node: ast.AST, package: str):
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
    elif isinstance(node, ast.ImportFrom):
        if node.level:
            parts = package.split(".") if package else []
            parts = parts[: len(parts) - (node.level - 1)]
            if node.module:
                parts.append(node.module)
            base = ".".join(parts)
        else:
            base = node.module or ""
        if base:
            yield base
        for alias in node.names:
            if alias.name != "*":
                yield f"{base}.{alias.name}" if base else alias.name


def reachable_modules(root: Path, entry: str = "main.py") -> tuple[list[Path], set[str]]:
    """Return (local .py files reachable from entry, external top-level names imported)."""
    root = root.resolve()
    start = root / entry
    seen, pending, externals = {start}, [start], set()
    while pending:
        path = pending.pop()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package = _package_of(root, path)
        for node in ast.walk(tree):
            # importlib.import_module("x") / __import__("x") with a literal string
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if fname in {"import_module", "__import__"}:
                    externals.add(node.args[0].value.split(".")[0])
            for name in _imported_names(node, package):
                parts = name.split(".")
                for i in range(1, len(parts) + 1):
                    dotted = ".".join(parts[:i])
                    top = parts[0]
                    if not _is_local(root, top):
                        externals.add(top)
                        break
                    f = _module_file(root, dotted)
                    if f and f not in seen:
                        seen.add(f)
                        pending.append(f)
    return sorted(seen), externals


def forbidden_imports(root: Path) -> set[str]:
    _, externals = reachable_modules(root)
    return externals & FORBIDDEN_REACHABLE


def repo_files(root: Path) -> list[Path]:
    """Files git tracks plus untracked files that are not ignored (i.e. everything that is
    committed or about to be committed); falls back to a directory walk outside a git checkout."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=root, check=True, capture_output=True).stdout
        return [root / p for p in out.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip and not d.endswith(".egg-info")]
            found.extend(Path(dirpath) / f for f in filenames)
        return found


def oversized_files(root: Path, limit: int = MAX_FILE_BYTES) -> list[tuple[str, int]]:
    return [(str(p.relative_to(root)), p.stat().st_size) for p in repo_files(root)
            if p.is_file() and p.stat().st_size > limit]


def whitespace_paths(root: Path) -> list[str]:
    """Repo-relative POSIX paths (directories included) containing any character for which
    str.isspace() is true: space, tab, U+00A0 and the rest."""
    rels = {p.relative_to(root).as_posix() for p in repo_files(root)}
    return sorted(r for r in rels if any(ch.isspace() for ch in r))


def backend_constructions(root: Path) -> list[str]:
    """Calls that build a backend, in any .py file outside ALLOWLIST_DIRS."""
    hits = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel.parts[0] in ALLOWLIST_DIRS or any(p.startswith(".") or p in {"venv", "build"} for p in rel.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
                if name in BACKEND_CONSTRUCTORS or name in BACKEND_FACTORY_ATTRS or name.startswith("Fake"):
                    hits.append(f"{rel}:{node.lineno}: {name}(...)")
    return hits


def backend_assigned_in_main(root: Path) -> list[str]:
    """main.py must use the injected global `backend`, never assign it."""
    tree = ast.parse((root / "main.py").read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] \
            if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else []
        for t in targets:
            if isinstance(t, ast.Name) and t.id == "backend":
                hits.append(f"main.py:{node.lineno}")
        if isinstance(node, ast.Global) and "backend" in node.names:
            hits.append(f"main.py:{node.lineno}: global backend")
    return hits


def package_uses_global_backend(root: Path, package: str = "neutron_qae") -> list[str]:
    """Inside the package, `backend` must always be a function parameter, never a free global."""
    hits = []
    for path in sorted((root / package).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
            uses = any(isinstance(n, ast.Name) and n.id == "backend" and isinstance(n.ctx, ast.Load)
                       for n in ast.walk(fn))
            if uses and "backend" not in params:
                hits.append(f"{path.relative_to(root)}:{fn.lineno}: {fn.name}() reads global backend")
    return hits


def main_signature_problems(root: Path) -> list[str]:
    """Qollab builds the Run-settings form only if `def main(` is on one line at column 0,
    every parameter is annotated int/float/str/bool, and defaults are plain literals."""
    src = (root / "main.py").read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if ln.startswith("def main(")]
    if len(lines) != 1:
        return [f"expected exactly one 'def main(' line at column 0, found {len(lines)}"]
    if not lines[0].rstrip().endswith(":"):
        return ["def main(...) signature must fit on one line"]
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    probs = []
    for a in fn.args.args:
        ann = a.annotation
        if not (isinstance(ann, ast.Name) and ann.id in {"int", "float", "str", "bool"}):
            probs.append(f"parameter {a.arg!r} must be annotated int/float/str/bool")
    for d in fn.args.defaults:
        if not isinstance(d, ast.Constant):
            probs.append(f"default at line {d.lineno} must be a plain literal (no -x, no expressions)")
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        probs.append("no *args/**kwargs/keyword-only params (Qollab passes form values positionally)")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            probs.append(f"line {node.lineno}: remove `if __name__ == ...` (Qollab calls main() itself)")
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and \
                getattr(node.value.func, "id", "") == "main":
            probs.append(f"line {node.lineno}: do not call main() at module level")
    return probs


def qollab_upload_files(root: Path) -> list[str]:
    """Tracked files that `git archive` would ship (export-ignore entries in .gitattributes removed)."""
    ignored = []
    attrs = root / ".gitattributes"
    if attrs.is_file():
        for line in attrs.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("#") and "export-ignore" in parts[1:]:
                ignored.append(parts[0].rstrip("/"))
    files = [p.relative_to(root).as_posix() for p in repo_files(root)]
    return [f for f in files if not any(f == i or f.startswith(i + "/") for i in ignored)]
