#!/usr/bin/env python3
"""Host-only unit tests for the ZIP-overlay legacy cleanup migration."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("cleanup_retired_emulator_assets.py")
SPEC = spec_from_file_location("mithaq_legacy_cleanup", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load cleanup script: {SCRIPT}")
CLEANUP = module_from_spec(SPEC)
SPEC.loader.exec_module(CLEANUP)


class RetiredAssetCleanupTests(unittest.TestCase):
    def test_allowlist_is_exact_and_contains_only_the_retired_paths(self) -> None:
        self.assertEqual(
            {
                "app/src/androidTest",
                "unauthorized-probe",
                "scripts/run_emulator_boundary_tests.sh",
                "scripts/test_emulator_boundary_runner.py",
            },
            {path.as_posix() for path in CLEANUP.RETIRED_PATHS},
        )

    def test_removes_only_the_four_allowlisted_legacy_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in CLEANUP.RETIRED_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if relative.suffix:
                    target.write_text("legacy sentinel", encoding="utf-8")
                else:
                    target.mkdir(parents=True, exist_ok=True)
                    (target / "legacy.txt").write_text("legacy sentinel", encoding="utf-8")
            unrelated = root / "app/src/main/keep.txt"
            unrelated.parent.mkdir(parents=True, exist_ok=True)
            unrelated.write_text("keep", encoding="utf-8")

            removed = CLEANUP.cleanup_retired_assets(root)

            self.assertEqual(
                {path.as_posix() for path in CLEANUP.RETIRED_PATHS},
                set(removed),
            )
            self.assertTrue(unrelated.is_file())
            for relative in CLEANUP.RETIRED_PATHS:
                self.assertFalse((root / relative).exists())

    def test_refuses_to_follow_a_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            outside = base / "outside"
            root.mkdir()
            (outside / "androidTest").mkdir(parents=True)
            sentinel = outside / "androidTest/keep.txt"
            sentinel.write_text("must survive", encoding="utf-8")
            (root / "app").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError):
                CLEANUP.cleanup_retired_assets(root)

            self.assertTrue(sentinel.is_file())

    def test_unlinks_a_final_component_symlink_without_deleting_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            sentinel = outside / "keep.txt"
            sentinel.write_text("must survive", encoding="utf-8")
            (root / "app/src").mkdir(parents=True)
            (root / "app/src/androidTest").symlink_to(outside, target_is_directory=True)

            removed = CLEANUP.cleanup_retired_assets(root)

            self.assertIn("app/src/androidTest", removed)
            self.assertFalse((root / "app/src/androidTest").is_symlink())
            self.assertTrue(sentinel.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
