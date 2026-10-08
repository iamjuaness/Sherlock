# Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16)

Documento de referencia para la ejecución del nuevo pipeline arquitectónico de Sherlock con **Taxonomía Canónica**, **Calibración Jerárquica de 9 Niveles**, **Gobernanza de Segmentos (Drift/Status)** y **Validación OOF A/B/C**.

---

## 1. ¿Qué cambió respecto al flujo antiguo?

### Flujo Antiguo:
```
Picks históricos -> train_calibration (Global) -> calibration_v1.json -> Predicciones
```
- **Falta de granularidad**: La calibración era única global o por familia simple.
- **Inestabilidad por muestra**: Segmentos con pocos picks podían sobreajustarse o distorsionar la probabilidad.
- **Sin gobernanza de segmentos**: Un segmento con ECE alto o Drift continuaba publicando picks con stake completo.

---

### Nuevo Flujo (Fase 1-16):
```
1. Taxonomía Canónica (Liga + Familia + Lado + Bucket)
        │
2. Entrenamiento Calibración Jerárquica 9 Niveles (walk-forward OOF)
        │
3. Gobernanza de Segmentos (Evaluar ECE/CLV/Recencia -> status BLOCKED / REDUCED / WATCH / EXPERIMENTAL)
        │
4. Evaluación OOF Comparativa A/B/C (Validar ROI, Brier, ECE antes de desplegar)
        │
5. Motor de Selección y Riesgo (Pick Snapshot -> Eligibility -> Kelly + Reliability + Stake Engine -> Traceability)
```

---

## 2. Paso a Paso del Nuevo Pipeline

### Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal
Entrena la jerarquía de 9 niveles (`global` -> `family` -> `family+side` -> `family+side+bucket` -> `league` -> `league+family` -> `league+family+side` -> `league+family+side+bucket`).

```bash
# Ejemplo: Entrenar con datos hasta final de mes (Walk-Forward OOF)
python -m src.core.train_calibration \
    --folds 5 \
    --prior-strength 35 \
    --min-samples 60 \
    --include-excluded \
    --until-date 2026-09-30
```

> **Nota:** La validación OOF integrada automáticamente rechaza la promoción si la curva jerárquica no mejora las métricas Brier y LogLoss sobre la muestra retenida.

---

### Paso 2: Listar y Auditar el Estado de Gobernanza de Segmentos
Inspecciona qué segmentos han sido bloqueados o reducidos debido a baja muestra, descalibración (ECE alto) o caída en CLV reciente.

```bash
# Ver todos los segmentos configurados por estado de gobernanza
python scripts/list_governance.py

# Ver solo los segmentos bloqueados
python scripts/list_governance.py --status BLOCKED

# Ver segmentos bajo reducción de stake
python scripts/list_governance.py --status REDUCED
```

*`data/segment_governance.json` se genera automaticamente con `update_governance.py`.*
*Los overrides manuales (segmentos forzados a BLOCKED/WATCH) se preservan entre ejecuciones (marcados con `"auto": false`).*

---

### Paso 3: Evaluación OOF Comparativa (A/B/C)
Evalúa el desempeño antes de autorizar la actualización en producción comparando 3 sistemas sobre el histórico retenido:
- **Sistema A**: Calibrador global legacy.
- **Sistema B**: Calibración jerárquica nueva sin reglas de bloqueo.
- **Sistema C**: Sistema completo con Calibración Jerárquica + Probabilidad de Mercado (No-Vig/CLV) + Gobernanza + Motor de Riesgo Kelly Ajustado por Fiabilidad.

```bash
# Ejecutar evaluacion comparativa OOF (lee de la DB automaticamente)
python scripts/evaluate_oof_comparison.py \
    --output reports/oof_comparison.json \
    --n-folds 5
```

---

### Paso 4: Verificación de Invariantes y Reglas de Elegibilidad
Ejecuta la suite de verificación de regresiones e inalterabilidad para garantizar que ningún bloqueo duro previo haya sido anulado.

```bash
pytest tests/unit/test_invariants_and_eligibility.py tests/unit/test_stake_and_traceability.py -v
```

---

## 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual)

```bash
# 1. Re-entrenar calibracion jerarquica hasta la fecha deseada
python -m src.core.train_calibration --folds 5 --prior-strength 35 --min-samples 60 --include-excluded --until-date 2026-09-30

# 2. Generar governance automaticamente desde el artefacto calibrado
python scripts/update_governance.py
#    Solo ver el resumen sin escribir:  python scripts/update_governance.py --dry-run --verbose
#    Resetear overrides manuales:       python scripts/update_governance.py --reset

# 3. Verificar estado de la gobernanza
python scripts/list_governance.py

# 4. Correr informe comparativo OOF (lee de la DB directamente, sin CSV)
python scripts/evaluate_oof_comparison.py --output reports/oof_comparison_2026_09.json --n-folds 5

# 5. Validar inalterabilidad de bloqueos y politicas
python -m pytest tests/unit/ -v
```

---

## 4. Overrides Manuales de Governance

Si quieres bloquear un segmento manualmente (sin depender de las metricas):

1. Ejecuta `python scripts/update_governance.py` para generar el JSON base.
2. Abre `data/segment_governance.json`.
3. En `segments`, cambia el valor del segmento: `"blocked"`, `"reduced"`, `"watch"`, etc.
4. En `segment_meta`, para ese mismo segmento, cambia `"auto": true` -> `"auto": false`.
5. La proxima vez que corras `update_governance.py`, ese segmento NO sera sobreescrito.

```json
{
  "segments": {
    "league:premier league|family:shots": "blocked"
  },
  "segment_meta": {
    "league:premier league|family:shots": {
      "n_samples": 235,
      "calibration_gap": 0.149,
      "auto": false
    }
  }
}
```
