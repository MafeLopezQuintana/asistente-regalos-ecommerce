![Recomendador de regalos: ¿Qué le regalo?](portada-regalos.png)

# Asistente de regalos para e-commerce

Proyecto Final Henry · Presente Analytics

Asistente que, a partir de un cuestionario de 5 preguntas, sugiere regalos individuales y combos dentro del presupuesto, usando modelos de recomendación entrenados con compras reales (Online Retail II).

## Equipo y roles

Marco Scrum y metodología CRISP-DM. Los roles son formales, para la documentación del PF: todos programamos y aportamos por igual a todo el proyecto.

| Integrante | Rol formal | Aporte adicional | Frente técnico |
| --- | --- | --- | --- |
| Franco | Product Owner | Visualización y dashboards | Modelado |
| Mafe | Scrum Master | Visualización y dashboards | Demo en Streamlit y README |
| Cristian | Liderazgo técnico (Data Team) | Visualización | EDA y Power BI |
| Ezequiel | Liderazgo técnico (Data Team) | Documentación y Git | Modelado |
| Mauricio | Liderazgo técnico (Data Team) | Documentación y Git | Ingeniería de datos |

## Cómo correr el proyecto

**Versión de Python:** 3.11 (la misma que usa la CI del repositorio, en `.github/workflows/ci.yml`).

**Instalar dependencias:**

```bash
pip install -r requirements.txt
```

**Generar los datasets limpios** (el Excel original no se sube al repo — colocalo en `data/raw/online_retail_II.xlsx` antes de correr esto):

```bash
python -m src.data.clean
```

Genera `data/processed/online_retail_rfm.parquet` y `data/processed/online_retail_modelo.parquet`.

**Generar las categorías de producto:**

```bash
python -m src.features.build_features
```

Pendiente de completar: comando para abrir la demo en Streamlit (Mafe).

## 1. Calidad de datos (Mauricio)

**Dataset:** [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) (UCI, Chen 2012) — 1.067.371 filas, 2009-2011.

**Problemas encontrados y cómo se trataron:**

| Filtro | Filas antes | Filas después | Qué saca |
| --- | --- | --- | --- |
| Solapamiento entre hojas del Excel | 1.067.371 | 1.044.848 | 1.088 facturas de diciembre 2010 duplicadas entre las 2 hojas del archivo original |
| Compras con cancelación exacta | 1.044.848 | 1.043.498 | Compras que en realidad nunca se concretaron: mismo cliente, producto y cantidad que una cancelación dentro de las 6 horas siguientes |
| Cancelaciones | 1.043.498 | 1.024.333 | Facturas que empiezan con "C" |
| Cantidad y precio > 0 | 1.024.333 | 1.018.304 | Incluye ajustes contables (ej. stock_code "B" = deuda incobrable) y pérdidas de depósito ("lost", "damages") |
| Códigos no-producto | 1.018.304 | 1.013.814 | POST, DOT, M, BANK CHARGES, AMAZONFEE, CRUK, B, ADJUST, ADJUST2, D, C2, 23444, 23574, S, TEST001, TEST002 |
| Duplicados | 1.013.814 | 991.648 | Se agrupan y **suman** cantidades (no se descartan filas: evita perder unidades reales) |
| Descripción vacía | 991.648 | 991.648 | — |
| Con cliente identificado (según el dataset de salida) | 991.648 | 764.946 | Solo aplica al dataset de RFM, ver abajo |

**Decisiones clave:**

- **Dos datasets de salida**, no uno: `online_retail_rfm.parquet` (764.946 filas, exige cliente — para RFM y segmentación) y `online_retail_modelo.parquet` (991.648 filas, conserva ventas sin cliente — el modelo de recomendación no necesita saber quién compró).
- **Formato Parquet, no CSV:** en las pruebas de lectura del equipo, CSV no conservó los tipos esperados (`invoice_date` volvió a ser texto y `customer_id` se leyó como `13085.0`). Parquet conserva los tipos de datos.
- **El Excel trae las 2 hojas con un solapamiento real** (1.088 facturas de diciembre 2010 duplicadas entre ambas). Se detecta y saca antes de unirlas, para no contarlas dos veces.
- **Segmentación mayorista/minorista:** percentil 95 de unidades totales compradas por cliente.
- **Códigos `GIFT_` y `PADS` se conservan**, pese a precio cero o casi nulo: tienen descripción de producto real (vales de regalo con monto, "PADS TO MATCH ALL CUSHIONS"), a diferencia de los códigos administrativos excluidos (POST, D, M, etc.), que no describen ningún producto.
- **Facturas "bulk" (posible reposición al por mayor):** marcadas con una columna (`factura_bulk`), no eliminadas del dataset general. La decisión de excluirlas o no del modelo de recomendación se evalúa en Modelado, comparando métricas con y sin ellas.

**Código:** `src/data/clean.py`

**Tests:** `tests/test_clean.py` (10/10 pasando, según la entrega de calidad de datos).

**Detalle completo:** `notebooks/01_calidad_datos.ipynb`

Pendiente de completar: instrucciones para generar y cargar los dos archivos Parquet. Los datasets no se suben al repositorio.

## 2. Categorías e intereses (Mauricio)

### Categorías de producto

Se generan 28 categorías desde `description` (TF-IDF + K-Means), con cada decisión (K, bigramas) comparada en vivo contra alternativas antes de elegirse. No hay un K matemáticamente óptimo: Elbow y Silhouette no marcan un punto de corte claro; se elige por practicidad de formulario.

El 26,6% del catálogo sin vocabulario distintivo queda bajo "Variedad / Sorpresa", considerada una categoría de negocio válida.

**Código:** `src/features/build_features.py`

**Cómo generarlo:** `python -m src.features.build_features` (desde la raíz del repo) — no `python src/features/build_features.py` a secas, porque ese import relativo necesita que Python lo trate como parte del paquete `src`.

**Tests:** `tests/test_build_features.py` (8/8 pasando, según la entrega de categorías).

**Detalle:** `notebooks/02b_categorias.ipynb`

**Salida:** `data/processed/catalogo_categorizado.parquet` (28 categorías, no se sube al repo).

**Modelos congelados:** `data/processed/modelos_categorias.pkl` (no se sube al repo) — vectorizer y K-Means ya entrenados. Productos nuevos se categorizan con `categorizar_productos_nuevos()` sin re-entrenar todo el catálogo, evitando que el número de cada cluster se mueva.

Pendiente de completar: relación entre las categorías del catálogo y los intereses del cuestionario.

## 3. EDA y visualizaciones (Cristian)

Análisis exploratorio completo en [`notebooks/03_EDA.ipynb`](notebooks/03_EDA.ipynb), con un resumen en [`README_EDA.md`](README_EDA.md). Los gráficos están en `reports/figures/`; el dashboard de Power BI queda para la presentación final.

Datos: Online Retail II (diciembre 2009 a diciembre 2011), 991.648 filas y 39.402 facturas. Cifras en libras (£); ingreso = cantidad × precio unitario.

### Gráficos

![Ventas por mes](reports/figures/01_ventas_por_mes.png)

*Septiembre a noviembre se destacan en los dos años. Diciembre 2011 se excluye porque solo tiene 9 días de datos.*

![Productos que más venden](reports/figures/02_top_productos.png)

*Los productos más vendidos por unidades no son los que más facturan: WORLD WAR 2 GLIDERS lidera en unidades (106.331) y REGENCY CAKESTAND 3 TIER en ingresos (£329.342).*

### Tres hallazgos

1. **Las ventas se concentran entre septiembre y noviembre:** esos tres meses suman el **37% de los ingresos** de los dos años (36% y 38% en cada año), y noviembre llega a £1,43 M y £1,45 M, más del doble de un mes típico (£0,68 M) → el asistente tiene en cuenta la época del año y prioriza lo navideño desde septiembre.

2. **Pocos clientes concentran el volumen:** el 5% de los clientes (293) compra el **53,5% de las unidades** → el asistente no puede guiarse solo por lo más comprado en total, y se evalúa recomendar únicamente productos que también compran clientes minoristas.

3. **Productos baratos y pedidos de varios productos:** el producto típico cuesta **£2,10** (3 de cada 4 cuestan £4,25 o menos) y un pedido típico lleva **15 productos distintos** → el asistente trabaja con presupuestos bajos por producto y puede sugerir varios productos (combos) dentro de un mismo presupuesto.


## 4. Modelos (Ezequiel y Franco)

El sistema recomienda productos complementarios a partir de un producto elegido (**ancla**): aprende
qué productos suelen aparecer juntos en una misma factura. Los modelos se entrenan con
`data/processed/online_retail_modelo.parquet`, que conserva las ventas sin cliente porque para
recomendar por co-compra no hace falta saber quién compró.

### Modelos

| Modelo | Archivo | Lógica |
|---|---|---|
| Popularidad (baseline) | `src/models/train.py` | Recomienda los productos que aparecen en más facturas, salvo el ancla |
| Item-item (KNN entre productos) | `src/models/train.py` | Similitud coseno entre productos sobre la matriz binaria factura × producto: recomienda los que más se compran junto con el ancla |
| SVD | `src/models/train.py` | Factorización de la misma matriz; recomienda por similitud entre los factores de cada producto |

La matriz es **binaria** (el producto estuvo o no en la factura): la cantidad comprada no pesa,
para que las compras mayoristas no distorsionen las relaciones entre productos.

### Interfaz común

Cualquier modelo nuevo se puede comparar con los demás si implementa:

- `fit(df_train)`: entrena y devuelve el propio modelo.
- `recomendar(anclas, k)`: devuelve `k` códigos de producto, nunca las anclas.
- `get_params()`: diccionario con su configuración (se registra en MLflow).
- `n_productos`: cantidad de productos que conoce (para la cobertura).

### Cómo se evalúa

1. **Corte temporal** (`corte_temporal`): el 80% más antiguo de las facturas es desarrollo y el 20%
   más reciente es test. Ninguna factura queda partida.
2. **Validación cruzada temporal** (`evaluar_cv_temporal`) dentro del desarrollo, con folds expansivos
   (siempre se entrena con el pasado y se valida con el período siguiente), para elegir parámetros
   sin mirar el test.
3. Los modelos elegidos se **reentrenan con todo el desarrollo**.
4. **Comparación final** (`comparar_modelos`) sobre el test, **una sola vez**.

En cada factura de evaluación con 2 o más productos se esconde uno al azar (semilla fija) y se mide
si el modelo lo recupera:

- **Modo ancla (principal):** el modelo ve un solo producto de la factura, igual que en el asistente,
  donde el usuario elige un producto de referencia. Con este modo se eligen los parámetros y el modelo.
- **Modo carrito (referencia):** el modelo ve todos los demás productos de la factura. Es la formulación
  de la propuesta y la base de `armar_combos` (Sprint 2); se reporta al lado, sin usarse para elegir.

| Métrica | Qué mide |
|---|---|
| Hit Rate@5 (KPI principal) | Porcentaje de casos en que el producto escondido está entre las 5 recomendaciones |
| NDCG@5 | Igual, pero premia que el acierto esté más arriba en la lista |
| Cobertura de catálogo | Porcentaje de productos que el modelo llega a recomendar alguna vez |

### MLflow

Todas las corridas se registran con `registrar_corrida()` (`src/utils/mlflow_utils.py`), igual que
el resto del equipo: un solo experimento, `asistente-regalos-ecommerce`, con la base `mlflow.db` y
los artefactos en `mlartifacts/`, ambos en la raíz del repo (sin importar desde qué carpeta se
ejecute). Las etapas se separan con el tag `etapa`:

- `validacion`: una corrida por configuración probada (`evaluar_cv_temporal(..., registrar_mlflow=True)`),
  con la media y el desvío entre folds. Es la justificación con números de cada parámetro elegido.
- `test_final`: una corrida por modelo en la comparación final (`comparar_modelos`), con el modelo
  entrenado guardado como artefacto, y una corrida de resumen con la tabla y el gráfico.

Cada corrida lleva además el tag `familia` (popularidad, item_item, svd).
Para verlas, desde la raíz: `mlflow ui --backend-store-uri sqlite:///mlflow.db` y filtrar, por
ejemplo, con `tags.etapa = "validacion"`. `mlflow.db` y `mlartifacts/` no se suben al repo: las
corridas se regeneran ejecutando el notebook.

### Notebook

`notebooks/04_modelos.ipynb` reúne todo el modelado: corte temporal, casos de prueba, los tres
modelos, validación cruzada temporal de 11 configuraciones, reentrenamiento de las elegidas y
comparación final sobre el test.

**Tests:** `tests/test_modelos.py` (32 tests: corte y folds temporales, métricas, casos, matriz,
los tres modelos, filtros de entrenamiento y el registro en MLflow con una base temporal). La CI los corre en cada PR; a mano,
desde la raíz: `python -m pytest tests/ -v`.

### Resultados (test, modo ancla)

Test: agosto a diciembre de 2011 (7.190 casos), un período que ningún modelo vio al entrenar.

| Modelo | Configuración | Hit Rate@5 | NDCG@5 | Cobertura | Hit Rate@5 carrito (ref.) |
|---|---|---|---|---|---|
| **Item-item** | min_facturas=5, tope 200 productos por factura | **8,4%** | **0,059** | **61,6%** | **19,9%** |
| SVD | 50 componentes, tope 200 | 7,0% | 0,048 | 53,5% | 7,0% |
| Popularidad (baseline) | criterio "facturas" | 1,8% | 0,011 | 0,1% | 2,3% |

![Comparación final de modelos](reports/figures/04_comparacion_final.png)

## 5. Justificación del modelo y plan de validación (Franco)

Pendiente de completar: por qué se eligió el modelo final y cómo se valida.

## 6. Demo en Streamlit (Mafe)

Pendiente de completar: qué hace cada pantalla, cómo se usa y el link público.

## 7. Pipeline reproducible y monitoreo (Mauricio)

Pendiente de completar: GitHub Actions, MLflow y cómo se reevalúa el modelo.

## Limitaciones

Pendiente de completar: qué no cubre este prototipo.
