"""Columna de texto guardada comprimida (zlib) en SQLite.

Lectura tolerante: valores str (filas viejas sin comprimir) pasan tal cual.
SQL crudo debe usar `unpack()`; json_extract/LIKE no funcionan sobre estas columnas.
"""
import zlib

from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator


def pack(value: str | None) -> bytes | None:
    return None if value is None else zlib.compress(value.encode("utf-8"), 6)


def unpack(value: bytes | str | None) -> str | None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return zlib.decompress(bytes(value)).decode("utf-8")
    return value


class CompressedText(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        return pack(value)

    def process_result_value(self, value, dialect):
        return unpack(value)
