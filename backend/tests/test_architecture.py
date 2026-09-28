"""The boundaries of the modular monolith, checked on every test run (see docs/ARCHITECTURE.md).

- `allegro.core` is the shared kernel and knows nothing about the modules;
- a module uses another module only through its public surface: service, schemas, deps, roles —
  never its models, repository or HTTP layer;
- modules depend on each other in one direction only (the order below), so there are no cycles;
- only the composition root (`allegro.main`, `allegro.models`) sees everything.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "allegro"

# A module may depend only on modules listed before it
ORDER = ["accounts", "discussion", "catalog", "publications", "media", "site", "feed", "search"]
PUBLIC = {"service", "schemas", "deps", "roles"}
COMPOSITION_ROOT = {"main.py", "models.py", "__init__.py"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
            names += [f"{node.module}.{alias.name}" for alias in node.names]
    return [n for n in names if n.startswith("allegro")]


def _files(sub: str):
    return sorted((ROOT / sub).rglob("*.py"))


def test_every_module_is_known():
    found = {p.name for p in (ROOT / "modules").iterdir() if p.is_dir() and not p.name.startswith("__")}
    assert found == set(ORDER), "add the new module to ORDER (and to docs/ARCHITECTURE.md)"


def test_core_does_not_know_the_modules():
    offenders = [f"{p.relative_to(ROOT)} → {name}" for p in _files("core") for name in _imports(p)
                 if name.startswith("allegro.modules")]
    assert not offenders, offenders


def test_modules_use_each_other_only_through_public_surface_and_in_one_direction():
    offenders = []
    for module in ORDER:
        allowed = set(ORDER[:ORDER.index(module)])
        for path in _files(f"modules/{module}"):
            for name in _imports(path):
                parts = name.split(".")
                if parts[:2] != ["allegro", "modules"] or len(parts) < 3 or parts[2] == module:
                    continue
                other, part = parts[2], parts[3] if len(parts) > 3 else None
                where = f"{path.relative_to(ROOT)} → {name}"
                if other not in allowed:
                    offenders.append(f"{where}: {module} may not depend on {other}")
                elif part is not None and part not in PUBLIC:
                    offenders.append(f"{where}: only {sorted(PUBLIC)} of another module are public")
    assert not offenders, "\n".join(offenders)


def test_only_the_composition_root_lives_at_the_top():
    top = {p.name for p in ROOT.glob("*.py")}
    assert top <= COMPOSITION_ROOT, top - COMPOSITION_ROOT
