from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _pack(fmt: str, *values) -> bytes:
    return struct.pack("<" + fmt, *values)


def _string16(value: str = "") -> bytes:
    raw = value.encode("cp1252")
    return _pack("H", len(raw)) + raw


def build_legacy_fixture(path: Path, code: int, *, invalid_unit_count: bool = False) -> Path:
    messages = 5 if code <= 121 else 6
    max_buildings = 30 if code == 126 else 20
    has_ai_type = code >= 122
    has_teams = code >= 123
    has_player_numbers = code >= 124
    has_map_unknowns = code >= 124
    has_population = code >= 122
    body = bytearray()
    body += _pack("If", 100, code / 100)
    for index in range(16):
        name = f"Player {index + 1}".encode("cp1252")
        body += name + b"\0" * (256 - len(name))
    body += _pack("16i", *([-1] * 16))
    for index in range(16):
        body += _pack("4i", int(index < 8), int(index == 0), 1 if index < 8 else 0, 4)
    body += _pack("ibf", 0, 0, -1.0)
    body += _string16("fixture.scx")
    body += _pack(f"{messages}i", *([-1] * messages))
    for index in range(messages):
        body += _string16(f"Message {index}")
    for _ in range(4):
        body += _string16()
    body += _pack("i2ih", 0, 0, 0, 1)
    for _kind in range(3):
        for _player in range(16):
            body += _string16()
    for _player in range(16):
        body += _pack("3I", 0, 0, 0)
    body += bytes([1] * 16)
    body += _pack("i", -99)
    for index in range(16):
        body += _pack("6I", 0, 0, 0, 0, 0, 0)
        if has_player_numbers:
            body += _pack("i", index)
    body += _pack("i10i", -99, 1, 0, 0, 0, 0, 0, 0, 0, 900, 9000)
    for player in range(16):
        diplomacy = [3] * 16
        if player < 8:
            diplomacy[player] = 0
        body += _pack("16i", *diplomacy)
    body += b"\0" * 0x2D00
    body += _pack("i", -99)
    body += b"\0" * 64
    if has_teams:
        body += _pack("4B", 0, 0, 0, 4)
    for kind, maximum in (("tech", 30), ("unit", 30), ("building", max_buildings)):
        counts = [0] * 16
        if kind == "unit" and invalid_unit_count:
            counts[0] = -1
        body += _pack("16i", *counts)
        body += _pack(f"{16 * maximum}i", *([-1] * 16 * maximum))
    body += _pack("3i", 0, 0, 0)
    body += _pack("16i", *([0] * 16))
    body += _pack("i2i", -99, 0, 0)
    if has_ai_type:
        body += _pack("i", 0)
    if has_map_unknowns:
        body += _pack("4I", 0, 0, 0, 0)
    body += _pack("2I", 2, 2)
    for terrain_id in (0, 1, 2, 41):
        body += _pack("3B", terrain_id, 0, 0)
    body += _pack("i", 9)
    for _player in range(8):
        body += _pack("6f", 0, 0, 0, 0, 0, 0)
        if has_population:
            body += _pack("f", 200)
    body += _pack("9I", *([0] * 9))
    body += _pack("i", 9)
    for player in range(8):
        body += _pack("h", 0)
        body += _pack("2f2hBh", 0, 0, 0, 0, 0, 9)
        body += bytes([3] * 9)
        body += _pack("9i", *([4] * 9))
        body += _pack("ifh", player, 2.0 if has_population else 1.0, 0)
        if has_population:
            body += b"\0" * 8
        body += b"\0" * 7
        body += _pack("i", -1)
    body += _pack("dBI", 1.6, 0, 0)
    body += _pack("2i", 0, 0)

    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(bytes(body)) + compressor.flush()
    instructions = b"fixture"
    outer = b"1.21" + _pack("4I", 0, 0, 0, len(instructions)) + instructions + b"\0" * 8
    path.write_bytes(outer + compressed)
    return path
