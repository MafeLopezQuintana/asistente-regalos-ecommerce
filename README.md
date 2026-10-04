![Recomendador de regalos: ¿Qué le regalo?](portada-regalos.png)
# henry-pf-ecommerce
Proyecto Final de Data Science Henry | Sistema de recomendación para e-commerce.
## Calidad de datos

**Dataset:** [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (UCI, Chen 2012) — 1.067.371 filas, 2009-2011.

**Problemas encontrados y cómo se trataron:**

| Filtro | Filas antes | Filas después | Qué saca |
|---|---|---|---|
| Cancelaciones | 1.067.371 | 1.047.877 | Facturas que empiezan con "C" |
| Cantidad y precio > 0 | 1.047.877 | 1.041.670 | Incluye ajustes contables (ej. stock_code "B" = deuda incobrable) y pérdidas de depósito ("lost", "damages") |
| Códigos no-producto | 1.041.670 | 1.037.427 | POST, DOT, M, BANK CHARGES, AMAZONFEE, CRUK, B |
| Duplicados | 1.037.427 | 993.249 | Se agrupan y **suman** cantidades (no se descartan filas: evita perder unidades reales) |
| Descripción vacía | 993.249 | 993.249 | — |
| Con cliente identificado (según el dataset de salida) | 993.249 | 766.521 | Solo aplica al dataset de RFM, ver abajo |

**Decisiones clave:**
- **Dos datasets de salida**, no uno: `online_retail_rfm.parquet` (766.521 filas, exige cliente — para RFM y segmentación) y `online_retail_modelo.parquet` (993.249 filas, conserva ventas sin cliente — el modelo de recomendación no necesita saber quién compró, y descartarlas le escondía el 12,4% del catálogo de productos).
- **Formato Parquet, no CSV**: CSV pierde los tipos de dato al releerse (`invoice_date` vuelve a ser texto, `customer_id` se corrompe a `13085.0`). Parquet los conserva.
- **Segmentación mayorista/minorista**: percentil 95 de unidades totales compradas por cliente.
**Facturas "bulk" (posible reposición al por mayor):** marcadas con una columna (`factura_bulk`), no eliminadas del dataset general. La decisión de excluirlas o no del modelo de recomendación se evalúa en Modelado, comparando métricas con y sin ellas.

**Código:** `src/data/clean.py` · **Tests:** `tests/test_clean.py` (10/10 pasando) · **Detalle completo:** `notebooks/01_calidad_datos.ipynb`

## Categorías de producto

Se generan 29 categorías desde `description` (TF-IDF + K-Means), 
validadas con 4 métodos (Elbow, Silhouette, Gap Statistic, 
Tibshirani) que confirmaron el límite real de separación por texto.
El 29,8% del catálogo sin vocabulario distintivo queda bajo 
"Variedad / Sorpresa" — una categoría de negocio válida, no un error.

**Código:** `src/features/build_features.py` · **Tests:** 
`tests/test_build_features.py` (7/7 pasando) · **Detalle:** 
`notebooks/02b_categorias.ipynb` · **Salida:** 
`data/processed/catalogo_categorizado.parquet` (29 categorías, no se sube al repo)