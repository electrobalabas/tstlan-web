from tstlan.devices.unidriver import InMemoryUnidriverIO


def test_write_then_read_bytes() -> None:
    io = InMemoryUnidriverIO()
    io.write_bytes(1, 4, b"\x01\x02\x03")
    assert io.read_bytes(1, 4, 3) == b"\x01\x02\x03"


def test_read_past_end_is_zero_padded() -> None:
    io = InMemoryUnidriverIO()
    assert io.read_bytes(1, 0, 4) == b"\x00\x00\x00\x00"


def test_bit_set_and_clear() -> None:
    io = InMemoryUnidriverIO()
    io.write_bit(1, 0, 3, True)
    assert io.read_bit(1, 0, 3) is True
    assert io.read_bit(1, 0, 2) is False
    io.write_bit(1, 0, 3, False)
    assert io.read_bit(1, 0, 3) is False


def test_bits_share_a_byte() -> None:
    io = InMemoryUnidriverIO()
    io.write_bit(2, 5, 0, True)
    io.write_bit(2, 5, 7, True)
    assert io.read_bytes(2, 5, 1) == bytes([0b1000_0001])


def test_handles_are_isolated() -> None:
    io = InMemoryUnidriverIO()
    io.write_bytes(1, 0, b"\xaa")
    assert io.read_bytes(2, 0, 1) == b"\x00"


def test_is_connected_after_io() -> None:
    io = InMemoryUnidriverIO()
    assert io.is_connected(1) is False
    io.write_bytes(1, 0, b"\x00")
    assert io.is_connected(1) is True


def test_tick_is_a_noop() -> None:
    assert InMemoryUnidriverIO().tick() is None
