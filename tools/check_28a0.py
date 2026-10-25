#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Read actual RTX 4060 Laptop rates; a loaded module alone is not success."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from print_boot_option import ad107_board_matches
import read_sm_rates

TENSOR_FIELDS = ("fmla32", "imla2", "imla4")


def status() -> dict:
    identities = read_sm_rates.gpu_identity()
    if len(identities) != 1:
        raise RuntimeError("this checker requires exactly one NVIDIA GPU")
    fields = [value.strip() for value in identities[0].split(",")]
    if len(fields) < 4:
        raise RuntimeError("incomplete NVIDIA GPU identity")
    domain, bus, slot = fields[2].lower().split(":")
    address = f"{int(domain, 16):04x}:{bus}:{slot}"
    if not ad107_board_matches(address):
        raise RuntimeError("GPU must be 10de:28a0 subsystem 1d05:1274 revision a1")
    result = read_sm_rates.read_rates(fields[0])
    rates = result["rates"]
    return {
        "gpu": fields[1], "pci_address": address, "driver": fields[3],
        "kernel": os.uname().release,
        "boot_options": [option for option in Path("/proc/cmdline").read_text().split()
                         if option.startswith(("gpu_unlock.", "nvidia.NVreg_DynamicPowerManagement="))],
        "rates": rates,
        "tensor_fp32_full_rate": all(rates[name] == 0 for name in TENSOR_FIELDS),
        "meaning": "0=full rate; 1=half rate; this is a driver readback, not a performance benchmark",
        "hardware_changes": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect", choices=("full", "stock", "any"), default="full")
    args = parser.parse_args()
    try:
        result = status()
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"rate check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    expected = {"full": 0, "stock": 1}.get(args.expect)
    if expected is not None and any(result["rates"][name] != expected for name in TENSOR_FIELDS):
        print(f"GPU rates do not match --expect {args.expect}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
