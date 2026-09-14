"""Backup y restauración segura de data/sherlock.db (modo WAL).

Cambios sobre la versión anterior:
  - Rutas ancladas a PROJECT_ROOT (ubicación de este archivo), no al cwd
    desde el que se invoque el script, para que "backup" y "data" siempre
    apunten a las carpetas reales del proyecto sin importar desde dónde
    se ejecute.
  - Búsqueda de backups con os.listdir() + startswith/endswith en vez de
    glob, porque glob trata "[", "]", "?" como caracteres especiales de
    patrón: un nombre de archivo con esos caracteres literales (por
    ejemplo, generado a mano o por otra herramienta) no matchea con
    glob("sherlock_*.db") aunque sí empiece y termine como se espera.
  - backup_db() usa VACUUM INTO (copia consistente aunque haya WAL activo)
    en vez de copiar el archivo directamente.
  - restore_backup() borra -wal/-shm/-journal residuales antes de copiar
    y selecciona el backup más reciente por fecha de modificación.
"""

import sqlite3
import shutil
import os
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "sherlock.db"
BACKUP_DIR = PROJECT_ROOT / "backup"


def _list_backup_files() -> list[str]:
    """Lista los nombres de backup válidos en BACKUP_DIR.

    Usa startswith/endswith sobre os.listdir() en vez de glob, para no
    depender de que el nombre de archivo no contenga caracteres especiales
    de patrón glob ("[", "]", "?", etc.).
    """
    if not BACKUP_DIR.exists():
        return []
    return [
        filename
        for filename in os.listdir(BACKUP_DIR)
        if filename.startswith("sherlock_") and filename.endswith(".db")
    ]


def backup_db() -> None:
    """Genera un backup consistente de data/sherlock.db en backup/."""
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        if not DB_PATH.exists():
            print(f"Error al generar backup: no existe {DB_PATH}")
            return

        # Eliminar backups anteriores
        for filename in _list_backup_files():
            os.remove(BACKUP_DIR / filename)

        fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"sherlock_{fecha_actual}.db"

        # VACUUM INTO toma un snapshot consistente aunque haya un -wal
        # activo, a diferencia de copiar el archivo .db directamente.
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        try:
            conn.execute(f"VACUUM INTO '{backup_path.as_posix()}'")
        finally:
            conn.close()

        check_conn = sqlite3.connect(str(backup_path))
        try:
            result = check_conn.execute("PRAGMA integrity_check;").fetchone()
        finally:
            check_conn.close()

        if result and result[0] == "ok":
            print(f"Backup generado exitosamente: {backup_path}")
        else:
            print(f"Backup generado pero integrity_check devolvió: {result}")

    except Exception as e:
        print(f"Error al generar backup: {e}")


def restore_backup() -> None:
    """Restaura el backup más reciente sobre data/sherlock.db."""
    try:
        nombres = _list_backup_files()
        if not nombres:
            contenido = os.listdir(BACKUP_DIR) if BACKUP_DIR.exists() else None
            print(
                "Error al restaurar backup: no se encontraron archivos "
                f"'sherlock_*.db' en {BACKUP_DIR.resolve()}\n"
                f"Contenido actual de esa carpeta: {contenido if contenido is not None else 'la carpeta no existe'}"
            )
            return

        # Ordenar por fecha de modificación real, más reciente primero.
        nombres.sort(key=lambda n: (BACKUP_DIR / n).stat().st_mtime, reverse=True)
        backup_path = BACKUP_DIR / nombres[0]

        # Eliminar la base actual y CUALQUIER -wal/-shm residual.
        for suffix in ("", "-wal", "-shm", "-journal"):
            target = Path(f"{DB_PATH}{suffix}")
            if target.exists():
                os.remove(target)

        shutil.copy2(backup_path, DB_PATH)

        conn = sqlite3.connect(str(DB_PATH))
        try:
            result = conn.execute("PRAGMA integrity_check;").fetchone()
        finally:
            conn.close()

        if result and result[0] == "ok":
            print(f"Backup restaurado exitosamente desde {backup_path}")
        else:
            print(f"Backup restaurado pero integrity_check devolvió: {result}")

    except Exception as e:
        print(f"Error al restaurar backup: {e}")


if __name__ == "__main__":
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"DB_PATH:      {DB_PATH}  (existe: {DB_PATH.exists()})")
    print(f"BACKUP_DIR:   {BACKUP_DIR}  (existe: {BACKUP_DIR.exists()})")
    print(f"Backups detectados: {_list_backup_files()}")
    backup_db()
    # restore_backup()