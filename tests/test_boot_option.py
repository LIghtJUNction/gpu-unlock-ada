# SPDX-License-Identifier: GPL-2.0-only
"""The read-only helper never suggests AD107M without explicit inclusion."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "boot_option", Path(__file__).resolve().parents[1] / "tools/print_boot_option.py")
boot_option = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot_option)

PCI = """0000:0A:00.0 VGA compatible controller: NVIDIA [10de:28a0]
0000:0b:00.0 VGA compatible controller: NVIDIA [10de:28a1]
0000:02:00.0 VGA compatible controller: NVIDIA [10de:2684]
"""


class BootOptionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.board = self.root / "0000:0a:00.0"
        self.board.mkdir()
        for name, value in {"vendor": "0x10de", "device": "0x28a0",
                            "subsystem_vendor": "0x1d05", "subsystem_device": "0x1274",
                            "revision": "0xa1"}.items():
            (self.board / name).write_text(value)
        patch = mock.patch.object(boot_option, "SYSFS_ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def test_exact28a0_is_optional_and_not_a_family_match(self):
        self.assertEqual(boot_option.candidates(PCI), [("0000:02:00.0", "2684")])
        self.assertEqual(boot_option.candidates(PCI, True),
                         [("0000:0a:00.0", "28a0"), ("0000:02:00.0", "2684")])

    def test_exact28a0_prints_separate_guarded_option(self):
        with mock.patch("sys.argv", ["print_boot_option.py", "--exact28a0"]), \
                mock.patch.object(boot_option.subprocess, "run") as run, \
                mock.patch("builtins.print") as output:
            run.return_value.stdout = PCI
            self.assertEqual(boot_option.main(), 0)
            run.assert_called_once_with(["lspci", "-Dnn"], check=True,
                                        capture_output=True, text=True, timeout=10)
            output.assert_any_call("gpu_unlock.targets=0000:0a:00.0 "
                                   "gpu_unlock.ad107_experimental=1")

    def test_other_boards_and_revisions_are_not_suggested(self):
        for name, value in (("subsystem_vendor", "0x1043"),
                            ("subsystem_device", "0x1275"), ("revision", "0xa2")):
            with self.subTest(name=name):
                path = self.board / name
                original = path.read_text()
                path.write_text(value)
                self.assertEqual(boot_option.candidates(PCI, True), [("0000:02:00.0", "2684")])
                path.write_text(original)

    def test_missing_or_invalid_identity_does_not_suggest_an_unlock(self):
        path = self.board / "revision"
        path.write_text("invalid")
        self.assertFalse(boot_option.ad107_board_matches("0000:0a:00.0"))
        path.unlink()
        self.assertEqual(boot_option.candidates(PCI, True), [("0000:02:00.0", "2684")])
