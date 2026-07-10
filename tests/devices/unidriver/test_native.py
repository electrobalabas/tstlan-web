import shutil
import subprocess
from pathlib import Path

import pytest

from tstlan.devices.unidriver import NativeUnidriverIO

FIXTURE = Path(__file__).parents[2] / "fixtures" / "native_unidriver.c"


@pytest.fixture
def native_library(tmp_path: Path) -> Path:
    gcc = shutil.which("gcc")
    if gcc is None:
        pytest.skip("gcc is required to build the native unidriver fixture")
    library = tmp_path / "libunidriver.so"
    subprocess.run(
        [gcc, "-shared", "-fPIC", str(FIXTURE), "-o", str(library)],
        check=True,
    )
    return library


def test_native_io_reads_and_writes_bytes(native_library: Path) -> None:
    io = NativeUnidriverIO(native_library)

    io.write_bytes(1, 2, b"\x01\x02\x03")

    assert io.read_bytes(1, 2, 3) == b"\x01\x02\x03"
    assert io.is_connected(1) is True


def test_native_io_reads_and_writes_bits(native_library: Path) -> None:
    io = NativeUnidriverIO(native_library)

    io.write_bit(1, 0, 3, True)

    assert io.read_bit(1, 0, 3) is True
    assert io.read_bytes(1, 0, 1) == bytes([0b0000_1000])


def test_native_io_reports_library_errors(native_library: Path) -> None:
    io = NativeUnidriverIO(native_library)

    with pytest.raises(OSError):
        io.read_bytes(99, 0, 1)
