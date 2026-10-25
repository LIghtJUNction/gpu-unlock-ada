# SPDX-License-Identifier: GPL-2.0-only
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_28a0


class Check28a0Tests(unittest.TestCase):
    def invoke(self, expected, rates):
        with mock.patch("sys.argv", ["check_28a0.py", "--expect", expected]), \
                mock.patch.object(check_28a0, "status", return_value={"rates": rates}), \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return check_28a0.main()

    def test_full_requires_each_target_rate_to_be_full(self):
        rates = dict.fromkeys(check_28a0.TENSOR_FIELDS, 0)
        self.assertEqual(self.invoke("full", rates), 0)
        for name in check_28a0.TENSOR_FIELDS:
            with self.subTest(name=name):
                changed = dict(rates, **{name: 1})
                self.assertEqual(self.invoke("full", changed), 2)

    def test_stock_requires_half_rate_not_just_a_failed_full_check(self):
        rates = dict.fromkeys(check_28a0.TENSOR_FIELDS, 1)
        self.assertEqual(self.invoke("stock", rates), 0)
        self.assertEqual(self.invoke("stock", dict(rates, fmla32=2)), 2)
        self.assertEqual(self.invoke("any", dict(rates, fmla32=0)), 0)

    def test_wrong_board_or_multiple_gpus_prevent_the_getter(self):
        identity = "GPU-private, RTX 4060 Laptop, 00000000:01:00.0, 615.78.08"
        for identities in ([identity], [identity, identity]):
            with self.subTest(count=len(identities)), \
                    mock.patch.object(check_28a0.read_sm_rates, "gpu_identity", return_value=identities), \
                    mock.patch.object(check_28a0, "ad107_board_matches", return_value=False), \
                    mock.patch.object(check_28a0.read_sm_rates, "read_rates") as getter:
                with self.assertRaises(RuntimeError):
                    check_28a0.status()
                getter.assert_not_called()

    def test_report_uses_exact_identity_without_publishing_uuid(self):
        identity = "GPU-private, RTX 4060 Laptop, 00000000:01:00.0, 615.78.08"
        rates = dict.fromkeys(check_28a0.TENSOR_FIELDS, 0)
        with mock.patch.object(check_28a0.read_sm_rates, "gpu_identity", return_value=[identity]), \
                mock.patch.object(check_28a0, "ad107_board_matches", return_value=True) as board, \
                mock.patch.object(check_28a0.read_sm_rates, "read_rates", return_value={"rates": rates}) as getter, \
                mock.patch.object(check_28a0.Path, "read_text", return_value="root=PRIVATE gpu_unlock.ad107_experimental=1"):
            result = check_28a0.status()
        board.assert_called_once_with("0000:01:00.0")
        getter.assert_called_once_with("GPU-private")
        self.assertTrue(result["tensor_fp32_full_rate"])
        self.assertEqual(result["boot_options"], ["gpu_unlock.ad107_experimental=1"])
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("GPU-private", json.dumps(result))

    def test_getter_failure_is_an_error_not_full_speed(self):
        with mock.patch("sys.argv", ["check_28a0.py"]), \
                mock.patch.object(check_28a0, "status", side_effect=RuntimeError("RM failed")), \
                contextlib.redirect_stdout(io.StringIO()) as output, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(check_28a0.main(), 1)
        self.assertEqual(output.getvalue(), "")
