# CLAUDE.md — Centro de Control

## Qué es
Integración HACS pública (`custom_components/centro_control`) con panel propio en JS (`frontend/centro-control-panel.js`) y script de Windows (`tools/centro-control.ps1`) para configurar una casa con token.

## Por dónde empezar
1. `CHANGELOG.md` (versión actual arriba) y `docs/STATUS.md` si existe.
2. Solo el módulo afectado: `energy.py`, `tariff.py`, `problems.py`, `panel.py`… El JS del panel tiene ~1.300 líneas: busca la función, no lo leas entero.
No abras `docs/capturas/` ni `brand/`.

## Reglas
- Público y **anónimo**: nada de entidades, IPs ni datos de la casa de Manu. Autor visible: manu8613 (NOTICE, notas de versión).
- Versión en `manifest.json` + `## [X.Y.Z]` en CHANGELOG → `release.yml` publica la versión y el ZIP solo.
- Pruebas: `pip install -r requirements_test.txt && pytest -q`. CI ejecuta además hassfest y la validación HACS.
- Detecta Gas TUR (`manu8613/gas-tur`) si está instalado: no romper esa interfaz.
- Cambios en rama y por PR. Nada de merge sin autorización.
- Al terminar: bloque CIERRE.
