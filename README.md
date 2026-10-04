![Recomendador de regalos: ¿Qué le regalo?](portada-regalos.png)
# henry-pf-ecommerce
Proyecto Final de Data Science Henry | Sistema de recomendación para e-commerce.
## Calidad de datos

**Dataset:** [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (UCI, Chen 2012) — 1.067.371 filas, 2009-2011.

**Problemas encontrados y cómo se trataron:**

| Filtro | Filas antes | Filas después | Qué saca |
|---|---|---|---|
| Compras con cancelación exacta | 1.044.848 | 1.043.498 | Compras que en realidad nunca se concretaron: misma cliente, producto y cantidad que una cancelación dentro de las 6 horas siguientes |
| Cancelaciones | 1.043.498 | 1.024.333 | Facturas que empiezan con "C" |
| Cantidad y precio > 0 | 1.024.333 | 1.018.304 | Incluye ajustes contables (ej. stock_code "B" = deuda incobrable) y pérdidas de depósito ("lost", "damages") |
| Códigos no-producto | 1.018.304 | 1.013.814 | POST, DOT, M, BANK CHARGES, AMAZONFEE, CRUK, B, ADJUST, ADJUST2, D, C2, 23444, 23574, S, TEST001, TEST002 |
| Duplicados | 1.013.814 | 991.648 | Se agrupan y **suman** cantidades (no se descartan filas: evita perder unidades reales) |
| Descripción vacía | 991.648 | 991.648 | — |
| Con cliente identificado (según el dataset de salida) | 991.648 | 764.946 | Solo aplica al dataset de RFM, ver abajo |

**Decisiones clave:**
- **Dos datasets de salida**, no uno: `online_retail_rfm.parquet` (764.946 filas, exige cliente — para RFM y segmentación) y `online_retail_modelo.parquet` (991.648 filas, conserva ventas sin cliente — el modelo de recomendación no necesita saber quién compró).
- **Formato Parquet, no CSV**: CSV pierde los tipos de dato al releerse (`invoice_date` vuelve a ser texto, `customer_id` se corrompe a `13085.0`). Parquet los conserva.
- **El Excel trae las 2 hojas con un solapamiento real** (1.088 facturas de diciembre 2010 duplicadas entre ambas) — se detecta y saca antes de unirlas, para no contarlas dos veces.
- **Segmentación mayorista/minorista**: percentil 95 de unidades totales compradas por cliente.
**Facturas "bulk" (posible reposición al por mayor):** marcadas con una columna (`factura_bulk`), no eliminadas del dataset general. La decisión de excluirlas o no del modelo de recomendación se evalúa en Modelado, comparando métricas con y sin ellas.

**Código:** `src/data/clean.py` · **Tests:** `tests/test_clean.py` (10/10 pasando) · **Detalle completo:** `notebooks/01_calidad_datos.ipynb`

## Categorías de producto

Se generan 28 categorías desde `description` (TF-IDF + K-Means), con 
cada decisión (K, bigramas) comparada en vivo contra alternativas 
antes de elegirse — no hay un K matemáticamente óptimo (Elbow y 
Silhouette no marcan un punto de corte claro), se elige por 
practicidad de formulario. El 26,6% del catálogo sin vocabulario 
distintivo queda bajo "Variedad / Sorpresa" — una categoría de 
negocio válida, no un error.

**Código:** `src/features/build_features.py` · **Tests:** 
`tests/test_build_features.py` (7/7 pasando) · **Detalle:** 
`notebooks/02b_categorias.ipynb` · **Salida:** 
`data/processed/catalogo_categorizado.parquet` (28 categorías, no se sube al repo)

**Código:** `src/features/build_features.py` · **Tests:** 
`tests/test_build_features.py` (7/7 pasando) · **Detalle:** 
`notebooks/02b_categorias.ipynb` · **Salida:** 
`data/processed/catalogo_categorizado.parquet` (29 categorías, no se sube al repo)