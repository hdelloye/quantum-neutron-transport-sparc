"""PLAT-04 / PLAT-01 compliance gates. Each check has a negative test proving it can fail."""
from pathlib import Path

import pytest

import compliance_checks as cc

ROOT = Path(__file__).resolve().parents[1]


def test_nothing_reachable_from_main_imports_aer_or_algorithms():
    assert cc.forbidden_imports(ROOT) == set()


def test_no_committed_file_over_2mb():
    assert cc.oversized_files(ROOT) == []


def test_no_backend_constructed_outside_local_runners():
    assert cc.backend_constructions(ROOT) == []
    assert cc.backend_assigned_in_main(ROOT) == []
    assert cc.package_uses_global_backend(ROOT) == []


def test_main_signature_is_qollab_form_compatible():
    assert cc.main_signature_problems(ROOT) == []


def test_no_whitespace_in_repo_paths():
    assert cc.whitespace_paths(ROOT) == []


def test_every_data_file_is_referenced_by_literal_path():
    files, _ = cc.reachable_modules(ROOT)
    text = "\n".join(p.read_text(encoding="utf-8") for p in files)
    data = [p for p in (ROOT / "data").rglob("*") if p.is_file()] if (ROOT / "data").is_dir() else []
    missing = [str(p.relative_to(ROOT)) for p in data if f'"{p.relative_to(ROOT).as_posix()}"' not in text]
    assert missing == []


def test_qollab_upload_stays_under_100_files_and_ships_entry_point():
    files = cc.qollab_upload_files(ROOT)
    assert len(files) <= cc.MAX_QOLLAB_FILES
    # LICENSE and README.md are asserted by plan 01-02's docs tests (they do not exist yet).
    assert {"main.py", "requirements.txt"} <= set(files)
    assert not any(f.startswith(("tests/", "scripts/", ".planning/")) for f in files)


# ---- negative tests: prove each gate fires -------------------------------------------
@pytest.fixture
def fake_project(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "main.py").write_text("from pkg import core\n\ndef main(shots: int = 10):\n    core.go(backend, shots)\n")
    return tmp_path


@pytest.mark.parametrize("stmt", [
    "import qiskit_aer\n",
    "from qiskit_aer import AerSimulator\n",
    "def f():\n    from qiskit_algorithms import IterativeAmplitudeEstimation\n",
    "try:\n    import qiskit_aer\nexcept ImportError:\n    pass\n",
    "import importlib\nimportlib.import_module('qiskit_algorithms')\n",
])
def test_forbidden_import_is_detected_through_package(fake_project, stmt):
    (fake_project / "pkg" / "core.py").write_text(stmt + "\ndef go(backend, shots):\n    pass\n")
    assert cc.forbidden_imports(fake_project)


def test_oversized_file_is_detected(fake_project):
    (fake_project / "big.json").write_bytes(b"0" * (cc.MAX_FILE_BYTES + 1))
    (fake_project / "pkg" / "core.py").write_text("def go(backend, shots):\n    pass\n")
    assert cc.oversized_files(fake_project)


@pytest.mark.parametrize("code", [
    "from qiskit_aer import AerSimulator\ndef go(backend, shots):\n    b = AerSimulator()\n",
    "def go(backend, shots):\n    from qiskit.providers.basic_provider import BasicSimulator\n    return BasicSimulator()\n",
    "def go(backend, shots):\n    return provider.get_backend('simulator')\n",
])
def test_backend_construction_is_detected(fake_project, code):
    (fake_project / "pkg" / "core.py").write_text(code)
    assert cc.backend_constructions(fake_project)


@pytest.mark.parametrize("relpath", [
    "bad name.py",
    "my dir/x.txt",
    "bad\u00a0name.py",
])
def test_whitespace_path_is_detected(fake_project, relpath):
    target = fake_project / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x\n")
    assert cc.whitespace_paths(fake_project)


def test_global_backend_read_in_package_is_detected(fake_project):
    (fake_project / "pkg" / "core.py").write_text("def go(shots):\n    return backend.run\n")
    assert cc.package_uses_global_backend(fake_project, package="pkg")


@pytest.mark.parametrize("src", [
    "def main(shots=10):\n    pass\n",
    "def main(shots: int = -1):\n    pass\n",
    "def main(\n    shots: int = 10,\n):\n    pass\n",
    "def main(shots: int = 10):\n    pass\n\nif __name__ == '__main__':\n    main()\n",
])
def test_bad_main_signature_is_detected(tmp_path, src):
    (tmp_path / "main.py").write_text(src)
    assert cc.main_signature_problems(tmp_path)
