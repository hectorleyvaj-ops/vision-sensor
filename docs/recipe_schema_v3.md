# Esquema universal de recetas v3

La raiz del catalogo es:

```json
{
  "schema_version": 3,
  "recipes": []
}
```

## ROI canonica

Toda ROI de enfoque o herramienta se guarda como:

```json
[x1, y1, x2, y2]
```

Las coordenadas son pixeles del frame original. `x1/y1` pertenecen a la region
y `x2/y2` son limites exclusivos, igual que un slice de NumPy. Debe cumplirse:

```text
0 <= x1 < x2
0 <= y1 < y2
```

Al migrar v1/v2, las ROI DataMatrix y de enfoque se conservan como `xyxy`. Las
ROI de `img_hist`, que antes eran `[x, y, ancho, alto]`, se convierten a
`[x, y, x + ancho, y + alto]`. El respaldo `.bak` conserva el catalogo previo.

## Resultado de herramientas

Cada step devuelve uno de cuatro estados:

| Estado | Significado | Resultado hacia controlador |
|---|---|---|
| `PASS` | Inspeccion ejecutada y aceptada | `OK` si todos los requeridos pasan |
| `FAIL` | Inspeccion ejecutada y pieza rechazada | `NG` |
| `ERROR` | No existe decision de producto por una falla | `ERROR` |
| `TIMEOUT` | No existe decision dentro del plazo | `ERROR` |

Un step opcional puede producir un estado distinto de `PASS` sin rechazar la
receta. Un step requerido conserva su estado como resultado del pipeline.

## DataMatrix

`match_mode` define la comparacion:

- `exact`: el texto completo debe ser identico;
- `prefix`: el texto leido debe comenzar con `expected_code`.

`min_expected_reads` y `max_wrong_reads` cuentan intentos de captura, no objetos
duplicados devueltos por el decoder. Un mismo codigo repetido varias veces en
un intento aporta un solo voto.

La llamada al decoder siempre usa `decode_timeout_ms`. Si la version instalada
de `pylibdmtx` no admite ese timeout, la herramienta devuelve `ERROR`; nunca cae
a una decodificacion sin limite que pueda impedir una cancelacion.
