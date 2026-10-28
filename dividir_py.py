#!/usr/bin/env python3
"""Divide un archivo .py en partes de N lineas y genera archivos .txt.

Uso:
    python dividir_py.py mi_script.py 300
    python dividir_py.py mi_script.py 300 -o salida
"""
import argparse
import math
from pathlib import Path


def dividir_archivo(ruta_entrada, lineas_por_parte, carpeta_salida=None, encabezado=True):
    ruta = Path(ruta_entrada)
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")
    if ruta.suffix.lower() != ".py":
        raise ValueError("El archivo de entrada debe ser .py")
    if lineas_por_parte <= 0:
        raise ValueError("lineas_por_parte debe ser mayor que 0")

    destino = Path(carpeta_salida) if carpeta_salida else ruta.parent / f"{ruta.stem}_partes"
    destino.mkdir(parents=True, exist_ok=True)

    with ruta.open("r", encoding="utf-8", errors="replace") as f:
        lineas = f.readlines()

    total = len(lineas)
    n_partes = max(1, math.ceil(total / lineas_por_parte))
    ancho = max(2, len(str(n_partes)))
    generados = []

    for i in range(n_partes):
        ini = i * lineas_por_parte
        fin = min(ini + lineas_por_parte, total)
        nombre = destino / f"{ruta.stem}_parte_{i + 1:0{ancho}d}.txt"
        with nombre.open("w", encoding="utf-8") as out:
            if encabezado:
                out.write(f"# {ruta.name} | parte {i + 1}/{n_partes} | lineas {ini + 1}-{fin} de {total}\n")
            out.writelines(lineas[ini:fin])
        generados.append(nombre)

    return generados


def main():
    p = argparse.ArgumentParser(description="Divide un .py en archivos .txt por cantidad de lineas.")
    p.add_argument("archivo", help="Ruta del archivo .py")
    p.add_argument("lineas", type=int, help="Lineas por parte")
    p.add_argument("-o", "--salida", help="Carpeta de salida (opcional)")
    p.add_argument("--sin-encabezado", action="store_true", help="No agregar linea de encabezado")
    a = p.parse_args()

    archivos = dividir_archivo(a.archivo, a.lineas, a.salida, not a.sin_encabezado)
    print(f"Se generaron {len(archivos)} archivos:")
    for f in archivos:
        print(" -", f)


if __name__ == "__main__":
    main()
