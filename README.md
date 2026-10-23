[![CI](https://github.com/MafeLopezQuintana/asistente-regalos-ecommerce/actions/workflows/ci.yml/badge.svg)](https://github.com/MafeLopezQuintana/asistente-regalos-ecommerce/actions/workflows/ci.yml)
![Recomendador de regalos: ¿Qué le regalo?](portada-regalos.png)

# Asistente de regalos para e-commerce

Proyecto Final Henry · Presente Analytics

Asistente que, a partir de un cuestionario de 5 preguntas, sugiere regalos individuales y combos dentro del presupuesto, usando modelos de recomendación entrenados con compras reales (Online Retail II).

## Índice

- [Equipo y roles](#equipo-y-roles)
- [Cómo correr el proyecto](#cómo-correr-el-proyecto)
- [Estructura del repositorio](#estructura-del-repositorio)
- [1. Calidad de datos](#1-calidad-de-datos)
- [2. Categorías e intereses](#2-categorías-e-intereses)
- [3. EDA y visualizaciones](#3-eda-y-visualizaciones)
- [4. Modelos](#4-modelos)
- [5. Justificación del modelo y plan de validación](#5-justificación-del-modelo-y-plan-de-validación)
- [6. Demo en Streamlit](#6-demo-en-streamlit)
- [7. Pipeline reproducible y monitoreo](#7-pipeline-reproducible-y-monitoreo)
- [Limitaciones](#limitaciones)

## Equipo y roles

Marco Scrum y metodología CRISP-DM. Los roles son formales, para la documentación del PF: todos programamos y aportamos por igual a todo el proyecto.

| Integrante | Rol formal | Aporte adicional | Frente técnico | LinkedIn |
| --- | --- | --- | --- | --- |
| Franco Correa | Liderazgo técnico (Data Team) | Visualización y dashboards | Modelado | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/franco-correa-a6060624a/) |
| Ma Fernanda López Quintana | Project Manager | Visualización y dashboards | Demo en Streamlit y README | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mar%C3%ADa-fernanda-l%C3%B3pez-quintana/) |
| Cristian Durán | Business Intelligence | Visualización | EDA y Power BI | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/cristian-duran-programacion/) |
| Ezequiel Irianni | Liderazgo técnico (Data Team) | Documentación y Git | Modelado | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ezequielirianni/) |
| Mauricio Melgarejo | Data Engineer | Documentación y Git | Ingeniería de datos | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mauricio-daniel-melgarejo-amaro-482596105/) |

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

**Generar el catálogo de la app** (necesita el paso anterior):

```bash
python -m src.data.catalogo_app
```

**Entrenar y evaluar los modelos:** abrir `notebooks/04_modelos.ipynb` y ejecutar todas las celdas (necesita `data/processed/online_retail_modelo.parquet`). Las corridas quedan registradas en MLflow; para verlas, desde la raíz del repo:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

**Correr el monitoreo** (simulación mes a mes, necesita `data/processed/online_retail_modelo.parquet`; las corridas quedan en MLflow con `etapa="monitoreo"`):

```bash
python -m src.models.monitoreo
```

**Generar el modelo final de la app** (necesita `data/processed/online_retail_modelo.parquet`; entrena el item-item con todos los datos y genera `models/modelo_final.pkl`):

```bash
python -m src.models.asistente
```

**Registrar el modelo final en MLflow** (después del paso anterior; guarda `models/modelo_final.pkl` como artefacto, con sus parámetros, el período de datos, las métricas de referencia y la versión del código, con `etapa="modelo_final"`):

```bash
python -m src.models.registrar_modelo
```

**Correr los tests:**

```bash
python -m pytest
```

**Abrir la demo en Streamlit** (local):

```bash
streamlit run app.py
```

La versión publicada está en https://quele-regalo.streamlit.app (ver [6. Demo en Streamlit](#6-demo-en-streamlit)).

## Estructura del repositorio

```
asistente-regalos-ecommerce/
├── .github/
│   └── workflows/
│       └── ci.yml                       # Integración continua
├── .streamlit/
│   └── config.toml                      # Configuración de Streamlit
├── assets/
│   └── portada.png                      # Imagen de la aplicación
├── docs/
│   ├── Manual_Usuario_Que_Regalo.docx    # Manual de usuario editable
│   └── Manual_Usuario_Que_Regalo.pdf     # Manual de usuario en PDF
├── models/
│   ├── catalogo_app.parquet              # Catálogo utilizado por la aplicación
│   ├── intereses.csv                     # Datos de intereses
│   └── modelo_final.pkl                  # Modelo final serializado
├── notebooks/
│   ├── img/                             # Imágenes del análisis de categorías
│   ├── 01_calidad_datos.ipynb            # Calidad y limpieza de datos
│   ├── 02b_categorias.ipynb              # Construcción y análisis de categorías
│   ├── 03_eda.ipynb                      # Análisis exploratorio
│   └── 04_modelos.ipynb                  # Validación y comparación de modelos
├── reports/
│   ├── figures/                         # Gráficos de análisis y modelos
│   ├── comparacion_modelos.csv           # Resultados de comparación
│   ├── decision_mayoristas.csv           # Reporte sobre mayoristas
│   └── diversidad_test.csv               # Resultados de diversidad
├── src/
│   ├── data/
│   │   ├── catalogo_app.py               # Preparación del catálogo de la app
│   │   └── clean.py                      # Limpieza de datos
│   ├── features/
│   │   ├── __init__.py
│   │   └── build_features.py             # Construcción de características
│   ├── models/
│   │   ├── __init__.py
│   │   ├── asistente.py                  # Lógica del asistente de recomendaciones
│   │   ├── evaluate.py                   # Evaluación de modelos
│   │   ├── monitoreo.py                  # Monitoreo del recomendador
│   │   ├── registrar_modelo.py           # Registro del modelo
│   │   └── train.py                      # Entrenamiento de modelos
│   └── utils/
│       └── mlflow_utils.py               # Utilidades de MLflow
├── tests/
│   ├── test_asistente.py
│   ├── test_build_features.py
│   ├── test_catalogo_app.py
│   ├── test_clean.py
│   ├── test_diversidad.py
│   ├── test_modelos.py
│   ├── test_monitoreo.py
│   └── test_registrar_modelo.py
├── .gitignore                           # Archivos y carpetas excluidos de Git
├── app.py                               # Aplicación en Streamlit
├── portada-regalos.png                   # Portada del README
├── pytest.ini                           # Configuración de pytest
├── requirements.txt                     # Dependencias del proyecto
├── README_EDA.md                         # Informe del análisis exploratorio
└── README.md                            # Documentación principal
```

## 1. Calidad de datos

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

**Tests:** `tests/test_clean.py` (14 tests).

**Detalle completo:** `notebooks/01_calidad_datos.ipynb`

Los dos archivos Parquet se generan con `python -m src.data.clean` (ver [Cómo correr el proyecto](#cómo-correr-el-proyecto)). Los datasets no se suben al repositorio.

## 2. Categorías e intereses

### Categorías de producto

Se generan 28 categorías desde `description` (TF-IDF + K-Means), con cada decisión (K, bigramas) comparada en vivo contra alternativas antes de elegirse. No hay un K matemáticamente óptimo: Elbow y Silhouette no marcan un punto de corte claro; se elige por practicidad de formulario.

El 26,6% del catálogo sin vocabulario distintivo queda bajo "Variedad / Sorpresa", considerada una categoría de negocio válida.

**Código:** `src/features/build_features.py`

**Cómo generarlo:** `python -m src.features.build_features` (desde la raíz del repo) — no `python src/features/build_features.py` a secas, porque ese import relativo necesita que Python lo trate como parte del paquete `src`.

**Tests:** `tests/test_build_features.py` (8/8 pasando, según la entrega de categorías).

**Detalle:** `notebooks/02b_categorias.ipynb`

**Salida:** `data/processed/catalogo_categorizado.parquet` (28 categorías, no se sube al repo).

**Modelos congelados:** `data/processed/modelos_categorias.pkl` (no se sube al repo) — vectorizer y K-Means ya entrenados. Productos nuevos se categorizan con `categorizar_productos_nuevos()` sin re-entrenar todo el catálogo, evitando que el número de cada cluster se mueva.

### Intereses del cuestionario

Al revisar los 4.725 productos uno por uno vimos que K-Means agrupa por palabras repetidas (colores, "SET", "DESIGN") y no por tipo de producto: "Sets y combos" mezcla vajilla, velas y tarjetas, y dentro de "Variedad / Sorpresa" hay juguetes, papelería y artículos de jardín. Por eso los intereses del cuestionario no salen de los clusters: cada interés tiene su lista de palabras clave, se evalúan en orden y gana la primera que coincide (con límite de palabra, para que RING no coincida con STRING). Lo que no coincide con ninguna va a "¡Sorprendeme!".

| Interés | Productos | Precio mediano (£) |
|---|---|---|
| Decoración y hogar | 1.172 | 2,89 |
| Cocina y repostería | 825 | 2,55 |
| Accesorios | 717 | 2,95 |
| Papelería y manualidades | 454 | 0,85 |
| Fiestas y celebraciones | 448 | 1,45 |
| Velas y aromas | 431 | 1,95 |
| ¡Sorprendeme! | 254 | 1,67 |
| Niños y juegos | 227 | 2,10 |
| Jardín y flores | 168 | 3,94 |

Se excluyen 29 productos que no corresponden a un asistente de regalos: vales de regalo, ítems que no son producto (una imagen, rellenos de almohadón) y artículos relacionados con drogas o de humor adulto.

**Código:** `src/data/catalogo_app.py` · **Tests:** `tests/test_catalogo_app.py` (22)

**Salida (se sube al repo porque la lee la app):** `models/catalogo_app.parquet` (4.696 productos, 112 KB; columnas `stock_code`, `description`, `price`, `category`, `interes`) y `models/intereses.csv` (tabla interés → categorías principales del catálogo).

## 3. EDA y visualizaciones

Análisis exploratorio completo en [`notebooks/03_eda.ipynb`](notebooks/03_eda.ipynb), con un informe ejecutivo de los hallazgos y lo que implican para el asistente en [`README_EDA.md`](README_EDA.md). Los gráficos están en `reports/figures/`; el dashboard de Power BI queda para la presentación final.

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


## 4. Modelos

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

Cobertura = productos distintos que el modelo recomendó alguna vez, sobre los 4.456 productos que existen en el período de desarrollo (no sobre los 4.725 del dataset completo).

**Diversidad intra-lista@5** (1 − similitud promedio entre los pares de las 5 recomendaciones, medida para los tres modelos con la misma regla: la co-compra del item-item entrenado con el desarrollo):

| Modelo | Hit Rate@5 | Diversidad@5 |
|---|---|---|
| **Item-item** | **8,4%** | 0,780 |
| SVD | 7,0% | 0,805 |
| Popularidad | 1,8% | 0,822 |

Como era esperable, el item-item es el menos diverso, porque la referencia es la misma información que usa para recomendar. Pero la diferencia es chica: acierta 4,6 veces más que el baseline perdiendo solo 0,04 de diversidad. La ganancia en acierto no viene de recomendar todo parecido. En la app la diversidad es algo mayor, porque `buscar_ideas_regalo` además saltea las variantes del producto de referencia (`reports/diversidad_test.csv`, notebook 04).

**Mayoristas:** entrenar sin ellos no mejora las recomendaciones para compras no mayoristas: Hit Rate@5 de 10,6% contra 10,5% entrenando con todos, sobre 4.115 casos (una diferencia muy por debajo del margen de error, que es de ±0,9 puntos). Con la popularidad, sacarlos incluso empeora (2,9% contra 3,2%). Por eso el modelo final se entrena con todos los datos. La comparación se hizo dentro del desarrollo, para no usar el test (`reports/decision_mayoristas.csv`, notebook 04).

![Comparación final de modelos](reports/figures/04_comparacion_final.png)

### Modelo final y funciones de la app

Elegido el modelo, `src/models/asistente.py` reentrena el item-item (`min_facturas=5`, tope de 200 productos por factura) con **todos los datos** (la evaluación ya se hizo sobre el corte temporal) y lo congela en `models/modelo_final.pkl`. El archivo no guarda el objeto entero sino lo que usa la app: los **20 productos que más se compran con cada producto** (con su similitud y en cuántos pedidos se compraron juntos), el **ranking de popularidad** y los parámetros y métricas de referencia. Pesa unos 4 MB y la app lo lee sin depender de las clases de `train.py`.

Las dos funciones reciben las respuestas del cuestionario tal como las guarda la app (`resumen_preferencias`):

- **`buscar_ideas_regalo(resumen, catalogo, modelo_final, k=5)`**: hasta 5 regalos. Primero los que más se compran con el producto de referencia (fuente `co-compra`, motivo *"Se compra junto con … (en N pedidos)"*); si no hay referencia o no alcanzan, los más vendidos que cumplen los filtros (fuente `popularidad`). No sugiere variantes (el mismo producto en otro color o tamaño) de la referencia ni de otra idea ya elegida.
- **`armar_combos(resumen, catalogo, modelo_final, n_combos=3)`**: hasta 3 combos de 3 productos que se compran juntos, cuyo total entra en el rango de presupuesto. Cada combo arranca de un producto distinto (la referencia y después las ideas sugeridas) y suma de a uno el que más se compra con los ya elegidos. Los combos no comparten productos ni juntan variantes del mismo producto (descripciones con la mitad o más de las palabras en común, como un mismo portavelas en dos colores).

Ambas cruzan con `models/catalogo_app.parquet`, así que los productos excluidos del catálogo nunca aparecen.

Supuestos de negocio:
- **Precio mínimo de £0,50:** por debajo hay precios unitarios de productos que se venden en packs (lápices a £0,04).
- **Ocasión:** el dataset no la registra. "Navidad / Fiestas" suma el interés *Fiestas y celebraciones* a los elegidos; las demás ocasiones no filtran.
- **¡Sorprendeme!** no filtra por interés.
- **Combos y rango de presupuesto:** si no se llega a 3 combos dentro del rango (por ejemplo, £15 con productos de £2), se completa con los más cercanos, desde la mitad del mínimo y nunca por encima del máximo; la app los marca como "por debajo del mínimo".

**Tests:** `tests/test_asistente.py` (27) y `tests/test_diversidad.py` (7).

## 5. Justificación del modelo y plan de validación

### Plan de validación

1. **Test reservado desde el principio:** el 20% más reciente de las facturas (19/08/2011 al 09/12/2011)
   se separa antes de cualquier prueba y se usa **una sola vez**, al final. Así la cifra que se reporta
   no está influida por la elección de parámetros.
2. **Validación cruzada temporal** sobre el 80% restante: 3 folds expansivos, siempre entrenando con el
   pasado y validando con el período siguiente. Ahí se comparan 11 configuraciones y se eligen los
   parámetros de cada modelo. El desvío entre folds se usa como referencia descriptiva de variabilidad, no como una
   prueba de significancia estadística. El notebook selecciona automáticamente el mayor Hit Rate medio
   de cada familia; permite ajustar manualmente la selección para priorizar simplicidad.
3. **Reentrenamiento** de las configuraciones elegidas con todo el desarrollo y **comparación final**
   sobre el test, con los mismos casos para los tres modelos.
4. **Modo ancla como principal** (el modelo ve un producto, como en el asistente) y modo carrito como
   referencia (ve todos los demás productos de la factura).
5. Todas las corridas quedan en MLflow (`etapa = validacion` y `etapa = test_final`), con parámetros y métricas.

### Por qué item-item

Criterios, en este orden: Hit Rate@5 en test, NDCG@5 para desempatar, cobertura del catálogo y explicabilidad.

1. **Hit Rate@5:** 8,4% en test, más de 4 veces el baseline (1,8%) y por encima del SVD (7,0%).
   El orden es el mismo en la validación (9,4% / 7,7% / 3,2%), lo que respalda la elección en los períodos evaluados, sin garantizar el resultado en períodos futuros.
2. **NDCG@5:** también el mejor (0,059): cuando acierta, el producto aparece más arriba.
3. **Cobertura:** recomienda el 61,6% del catálogo conocido en desarrollo, contra el 53,5% del SVD y el 0,1% del baseline.
4. **Explicabilidad:** se explica en una frase ("otros clientes lo compraron junto con este"), lo que
   permite mostrarle al usuario por qué se le sugiere cada regalo.
5. **Modo carrito:** con varios productos a la vista llega al 19,9%, casi el triple que el SVD. Es la
   base de `armar_combos` (Sprint 2).

**Parámetros elegidos** (validación cruzada, ver `notebooks/04_modelos.ipynb`):

- `min_facturas = 5`: con 3, 5 y 10 el Hit Rate medio es similar (9,0%–9,1%); con 10 baja la cobertura.
  La búsqueda de este umbral se hizo en item-item; en SVD se mantuvo el valor 5 por defecto.
- Facturas bulk **no se excluyen**: excluirlas no cambia el Hit Rate y baja un poco la cobertura.
- `max_productos_factura = 200`: se ignoran al construir la matriz de item-item y SVD las facturas de más de 200 productos distintos
  (reposiciones de medio catálogo). La mejora es chica, pero se repite en el item-item y en el SVD y sube la cobertura.
- SVD con 50 componentes: sin tope, 100 mejora levemente el Hit Rate medio (7,5% frente a
  7,4%), con una diferencia menor que el desvío entre folds; con 20 baja a 6,7%. La configuración
  elegida combina 50 componentes y tope 200 (7,7%). El SVD queda documentado como
  alternativa: encuentra relaciones indirectas, pero no supera al item-item en las métricas de la comparación final.
- Ambos modelos completan con popularidad cuando faltan recomendaciones; ese respaldo se entrena
  con todo el desarrollo, sin aplicar el tope de 200 productos.

**Limitaciones:** aprende de compras (feedback implícito), no de satisfacción; los datos son de 2009-2011;
las métricas son offline y el efecto real sobre las ventas se mediría con un test A/B. Solo se
evalúan facturas con al menos dos productos conocidos en desarrollo (7.190 casos de 7.881 facturas
de test); estos resultados no miden la recomendación de productos nuevos. Los productos se identifican
por `stock_code`; la descripción se usa para mostrarlos al usuario.

El test cubre parte de la temporada previa a Navidad de 2011, hasta el 9 de diciembre. Los tres modelos
tienen menor Hit Rate@5 que en validación; el baseline cae de 3,2% a 1,8%. La estacionalidad es una
posible explicación, pero estas métricas por sí solas no demuestran la causa de la caída.


### Plan de monitoreo

El monitoreo busca detectar cambios en la calidad de las recomendaciones del modelo item-item después de su integración con la aplicación.

Se distinguirán la evaluación del modelo sobre compras históricas y las pruebas de las recomendaciones que recibe el usuario, porque los filtros de presupuesto e intereses pueden modificar los resultados originales del modelo.

#### a. Referencia inicial

Se conservarán como referencia los resultados de la evaluación final en modo ancla:

| Indicador | Resultado de referencia |
|---|---:|
| Hit Rate@5 | 8,4 % |
| NDCG@5 | 0,059 |
| Cobertura del catálogo | 61,6 % |
| Casos evaluados | 7.190 |
| Diversidad intra-lista@5 | 0,780 |


Estos valores describen el desempeño del modelo sobre el test final y se conservan como referencia descriptiva. Para la regla de alerta del monitoreo se utilizará el Hit Rate@5 medio de validación cruzada temporal (9,4 %), según lo detallado en el punto e. Para asegurar la comparabilidad entre evaluaciones, se deberán documentar el modo de evaluación, la cantidad de recomendaciones, la construcción de los casos y el catálogo utilizado como denominador de cobertura.

#### b. Controles propuestos

| Dimensión | Control | Propósito |
|---|---|---|
| Acierto | Hit Rate@5 y NDCG@5 | Detectar si disminuyen los aciertos o empeora su posición. |
| Alcance | Cobertura del catálogo | Identificar concentración en pocos productos. |
| Variedad | Diversidad intra-lista@5 (1 − similitud promedio de co-compra entre las 5 recomendaciones). | Detectar si las recomendaciones se vuelven redundantes, con grupos de productos que casi siempre se compran juntos. |
| Calidad de datos | Campos necesarios completos, precios válidos y códigos compatibles con el modelo | Detectar problemas del catálogo. |
| Funcionamiento de la aplicación | Recomendaciones dentro del presupuesto, sin duplicados y con explicación | Verificar las condiciones del producto. |
| Casos sin resultados | Frecuencia de consultas sin sugerencias y uso del respaldo de popularidad | Detectar dificultades para atender determinadas consultas. |

La cobertura y la diversidad se analizarán junto con las métricas de acierto: una mayor variedad de productos, por sí sola, no demuestra mejores recomendaciones.

#### c. Frecuencia y datos de evaluación

El script `src/models/monitoreo.py`, implementado en el PR #17, realiza una simulación mensual de monitoreo con los datos históricos disponibles.

Se simula que el modelo entra en producción el 19/08/2011: se entrena una sola vez con el período de desarrollo y se evalúa sobre las compras posteriores, agrupadas por mes y sin dividir facturas. El modelo permanece fijo durante la evaluación, sin reentrenarse entre períodos.

Como el proyecto utiliza un dataset histórico cerrado, esta ejecución demuestra el funcionamiento del proceso de monitoreo, pero no constituye una evaluación con transacciones nuevas. Repetirla sobre los mismos datos permite comprobar la reproducibilidad, sin aportar evidencia independiente de desempeño futuro.

En una implementación con transacciones nuevas, se propone mantener una revisión mensual, considerando el volumen de casos y la incertidumbre de las métricas para interpretar los resultados.

#### d. Registro y trazabilidad

El script implementado en el PR #17 registra cada período mensual en MLflow con los tags `etapa="monitoreo"` y `tipo="simulacion"`.

Cada corrida incluye:

- Versión del código, identificada mediante el commit de Git.
- Fuente de los datos, fecha de corte del entrenamiento y mes evaluado.
- Parámetros del modelo, semilla y cantidad de recomendaciones.
- Cantidad de casos evaluados y facturas excluidas de la evaluación.
- Hit Rate@5, NDCG@5 y cobertura del catálogo.
- Hit Rate@5 del baseline sobre los mismos casos.
- Porcentaje de productos nuevos y de facturas evaluables.
- Límite superior del intervalo de confianza del 95 % del Hit Rate@5.
- Referencia de validación utilizada y estado de la alerta.

La configuración del monitoreo utiliza el modo ancla. La versión del código permite consultar los criterios de construcción de casos y cálculo de las métricas utilizados en cada ejecución.

Las pruebas del resultado final de la aplicación, como el cumplimiento del presupuesto, la ausencia de duplicados y las explicaciones de las recomendaciones, se documentarán por separado de las métricas del modelo.

#### e. Criterios de revisión y acciones

Una caída en Hit Rate@5 o NDCG@5 motivará una revisión del período evaluado, el volumen de casos, la calidad de los datos y los cambios en el catálogo.

También se analizarán reducciones de cobertura, concentración de recomendaciones y mayor frecuencia de consultas sin resultados.

Como referencia inicial de alerta se utilizará el Hit Rate@5 medio de item-item en validación cruzada temporal (9,4 %, modo ancla). Se marcará un período cuando el límite superior del intervalo de confianza del 95 % de su Hit Rate@5 quede por debajo de esa referencia, según el cálculo implementado en `src/models/monitoreo.py`.

Esta señal motivará una revisión de los datos, el volumen de casos y los cambios en el catálogo. Se utilizará como criterio inicial de revisión, sujeto a seguimiento, y no implicará un reentrenamiento automático.

Los incumplimientos de reglas del producto, como superar el presupuesto o recomendar códigos inexistentes en el catálogo, se tratarán como errores de funcionamiento.

Ante un problema se propone:

1. Verificar los datos y la integración.
2. Analizar si el cambio se concentra en determinadas categorías o consultas.
3. Determinar si corresponde corregir datos, filtros o modelo.
4. Si se propone reentrenar, comparar la nueva versión con la vigente mediante validación temporal antes de reemplazarla.

Los resultados de monitoreo no se utilizarán para ajustar repetidamente el modelo y seguir presentando ese mismo período como una evaluación independiente.

#### f. Responsabilidades propuestas

| Responsable | Aporte |
|---|---|
| Franco — Validación de modelos | Definir el protocolo, revisar la comparabilidad de las métricas, interpretar los resultados y documentar conclusiones y limitaciones. |
| Ezequiel — Modelado | Acordar e implementar las métricas necesarias y participar en el análisis del comportamiento del modelo. |
| Mauricio — Pipeline y monitoreo | Implementar la ejecución reproducible y el registro de las corridas en MLflow. |


## 6. Demo en Streamlit

**¿Qué le regalo?** permite registrar preferencias y descubrir regalos individuales y combos dentro del presupuesto, con sugerencias basadas en el catálogo y en compras históricas.

🎁 **App pública:** [Abrir ¿Qué le regalo?](https://quele-regalo.streamlit.app)

📖 **[Manual de usuario](docs/Manual_Usuario_Que_Regalo.pdf)**

### Funcionalidades disponibles

- Selección del presupuesto total para un regalo o combo:
  - De £0 a £2.
  - De £2 a £5.
  - De £5 a £15.
  - De £15 a £30.
  - Más de £30.
- Selección de uno o varios intereses, o solo «¡Sorprendeme!».
- Elección de la ocasión y del formato: regalo individual, combo o ambas opciones.
- Búsqueda y selección opcional de un producto de referencia del catálogo.
- Visualización de su nombre, precio y código en el resumen.
- Validaciones para evitar respuestas contradictorias.
- Resumen de las preferencias al enviar el formulario.
- Hasta cinco ideas de regalos individuales, con precio, interés y motivo de recomendación.
- Hasta tres combos, con sus productos, motivos y precio total.
- Avisos cuando no se encuentran opciones, con sugerencias para ajustar la búsqueda.
- Tarjeta opcional con destinatario, dedicatoria de hasta 300 caracteres y remitente.
- Vista previa de la tarjeta y conservación de las preferencias y los resultados mientras se personaliza.

### Cómo usarla

1. Elegí el presupuesto total.
2. Completá los intereses, la ocasión y el formato del regalo.
3. Si ya viste un producto que podría gustarle, seleccionalo como referencia.
4. Tocá «Ver mis preferencias» y bajá hasta «Ideas para sorprender».
5. Explorá los regalos y combos, y agregá una tarjeta si querés.

Si cambiás tus preferencias, volvé a tocar «Ver mis preferencias» para actualizar los resultados.

### Cómo se generan las sugerencias

El presupuesto y los intereses filtran los productos del catálogo. «¡Sorprendeme!» permite explorar sin filtrar por interés. Con un producto de referencia, se priorizan sus complementos según el modelo item-item; si no hay referencia o no alcanzan los candidatos, se completa con los productos más populares que cumplen los filtros.

Los combos combinan relaciones de co-compra y popularidad, evitando repetir productos entre combos y juntar variantes del mismo producto. La ocasión «Navidad / Fiestas» suma el interés Fiestas y celebraciones a los elegidos; las demás ocasiones no modifican el filtro.

### Precios y alcance

Los precios se expresan en **libras esterlinas (£)** y corresponden al catálogo histórico de origen. En los combos, el presupuesto máximo se aplica al conjunto completo; pueden mostrarse alternativas por debajo del mínimo del rango, con un aviso.

Es una demo académica: no consulta stock ni precios actuales, no procesa compras, pagos o envíos y no envía la tarjeta personalizada.

**Código de la interfaz:** [`app.py`](app.py)

## 7. Pipeline reproducible y monitoreo

El proyecto se puede reproducir y revisar gracias a dos piezas: los tests corren solos en cada Pull Request (GitHub Actions) y todos los experimentos de modelado quedan registrados en un mismo lugar (MLflow).

### 7.1 Integración continua (GitHub Actions)

El workflow `.github/workflows/ci.yml` se ejecuta en cada Pull Request contra `main` y en cada push a `main`, sobre una máquina limpia de GitHub (Ubuntu):

| Paso | Qué hace |
|---|---|
| Clonar el repo | Descarga el código de la rama del PR |
| Configurar Python 3.11 | La misma versión indicada en "Cómo correr el proyecto" |
| Instalar dependencias | `pip install -r requirements.txt` |
| Correr los tests | `pytest tests/ -v` |

El resultado (verde o rojo) aparece en el PR antes de que alguien lo apruebe. Hoy corren 120 tests:

| Archivo | Tests | Qué cubren |
|---|---|---|
| `tests/test_clean.py` | 14 | Filtros de limpieza, segmentación de clientes, facturas bulk, catálogo y cuatro bugs encontrados en la revisión (solapamiento entre hojas del Excel, cancelaciones, clientes anónimos, códigos no-producto) |
| `tests/test_build_features.py` | 8 | Clustering de productos y asignación de las categorías |
| `tests/test_catalogo_app.py` | 22 | Reglas de intereses, exclusiones y que el catálogo de la app no tenga productos sin precio o categoría |
| `tests/test_modelos.py` | 32 | Corte temporal y folds, métricas, los tres modelos y el registro en MLflow |
| `tests/test_monitoreo.py` | 9 | Separación por mes sin partir facturas, % de productos nuevos, intervalo de confianza de Wilson, alerta de referencia, facturas excluidas y registro en MLflow |
| `tests/test_registrar_modelo.py` | 1 | Registro del modelo final en MLflow (etapa, parámetros, métricas y el `.pkl` como artefacto) con una base temporal |
| `tests/test_asistente.py` | 27 | Modelo final (vecinos, pedidos en común, guardado), sugerencias y combos con presupuesto, intereses, ocasión, variantes y motivo |
| `tests/test_diversidad.py` | 7 | Diversidad intra-lista (valores extremos e intermedios, productos fuera de la referencia) y que `evaluar()` solo la sume si se pide |

Decisiones tomadas:

- **`requirements.txt` con versiones fijas de las dependencias directas, no `pip freeze`.** El freeze incluía paquetes que solo existen en Windows (`pywin32`) o que piden otra versión de Python, y la CI fallaba en Ubuntu.
- **`pytest.ini` con `pythonpath = .`**, para que `from src...` funcione igual en la CI que en cada máquina, sin modificar `sys.path` dentro de los tests.
- **Los tests no usan el dataset real**, que no está en el repo: cada test arma un DataFrame chico con el caso que quiere probar.
- **Los tests de MLflow escriben en una base temporal**, para no mezclarse con las corridas reales del equipo.

### 7.2 Registro de experimentos (MLflow)

`src/utils/mlflow_utils.py` tiene una sola función, `registrar_corrida()`, que usa todo el equipo para registrar parámetros, métricas y, opcionalmente, el modelo entrenado. Así todas las corridas quedan en el mismo experimento y se pueden comparar.

- **Experimento:** `asistente-regalos-ecommerce`.
- **Dónde se guarda:** `mlflow.db` (base SQLite) y `mlartifacts/`, en la raíz del repo sin importar desde qué carpeta se ejecute: la ruta se calcula a partir de la ubicación del archivo, así un notebook y un script escriben en la misma base.
- **Modelos guardados con `joblib`:** nuestros modelos no son estimadores de scikit-learn, y así se puede guardar cualquier objeto.
- **No se suben al repo** (están en `.gitignore`): las corridas se regeneran ejecutando el notebook.
- **Etapas, con el tag `etapa`:** `validacion` y `test_final` (detalle en la sección 4, MLflow) , `monitoreo` (una corrida por mes de la simulación de monitoreo, 7.3) y `modelo_final` (la versión del modelo que usa la app, con el `.pkl` como artefacto).

Para verlas: `mlflow ui --backend-store-uri sqlite:///mlflow.db`, abrir http://127.0.0.1:5000 y elegir la vista **Model training**.

### 7.3 Monitoreo

`src/models/monitoreo.py` simula que el modelo elegido (item-item, `min_facturas=5`, tope de 200 productos por factura) entra en producción el día del corte temporal (19/08/2011): se entrena una sola vez con el período de desarrollo y se reevalúa mes a mes, **sin reentrenar**, con la misma `evaluar()` de `src/models/evaluate.py`. Como el dataset es histórico, es una **simulación de monitoreo**: cada mes queda en MLflow con `etapa="monitoreo"` y `tipo="simulacion"`, junto con la versión del código, la fuente de los datos y las facturas excluidas. El protocolo para interpretar los resultados está en la sección 5 (Plan de monitoreo).

```bash
python -m src.models.monitoreo
```

Por cada mes se registra Hit Rate@5, NDCG@5, cobertura, el Hit Rate@5 del baseline sobre los mismos casos y el **% de productos nuevos** (productos vendidos en el mes que el modelo nunca vio al entrenar).

**Alerta de referencia:** el mes se marca si su Hit Rate@5 queda por debajo de la referencia de validación (9,4%) incluso tomando el límite superior de su intervalo de confianza de Wilson del 95%. Así, un mes con pocos casos no dispara la alerta solo por azar. Es una referencia para revisar el período, no un umbral definitivo.

| Mes | Casos | Hit Rate@5 | Baseline | IC 95% superior | Productos nuevos | Alerta |
|---|---|---|---|---|---|---|
| 2011-08 (desde el 19) | 471 | 9,1% | 1,5% | 12,1% | 0,6% | No |
| 2011-09 | 1.692 | 10,4% | 2,2% | 11,9% | 4,6% | No |
| 2011-10 | 1.784 | 7,1% | 1,9% | 8,4% | 8,2% | **Sí** |
| 2011-11 | 2.500 | 8,0% | 2,0% | 9,1% | 9,0% | **Sí** |
| 2011-12 (hasta el 9) | 743 | 7,7% | 1,9% | 9,8% | 9,4% | No |

En octubre y noviembre el Hit Rate cae por debajo de lo esperado y, en esos mismos meses, crece la proporción de productos que el modelo no conoce. Coincide con la temporada previa a Navidad, cuando cambia el catálogo. No demuestra la causa, pero es la señal que se usaría para decidir reentrenar. En diciembre el valor también es bajo, pero con pocos casos el intervalo no permite confirmarlo. En todos los meses el modelo se mantiene unas 4 veces por encima del baseline.

**Tests:** `tests/test_monitoreo.py` (9): separación por mes sin partir facturas, % de productos nuevos, intervalo de confianza de Wilson (incluido el caso de 0 aciertos), alerta de referencia, facturas excluidas y registro en MLflow con una base temporal.


## Limitaciones

Este proyecto es un prototipo académico desarrollado para el Proyecto Final de Henry.

- **Datos históricos:** utiliza transacciones de Online Retail II de 2009 a 2011, con foco en Reino Unido. No representa un catálogo comercial actualizado.
- **Precios de referencia:** los importes están expresados en libras esterlinas (£). No se consultan precios actuales, stock, costos de envío ni conversiones de moneda.
- **Alcance de la app:** genera ideas de regalos individuales y combos, muestra sus precios y motivos de recomendación y permite personalizar una tarjeta. La cantidad de resultados depende de los productos que cumplen los filtros.
- **Preferencias y modelo:** el presupuesto y los intereses se aplican como filtros; el producto de referencia guía la búsqueda de complementos por co-compra, con popularidad como respaldo. La ocasión solo modifica el filtro para «Navidad / Fiestas», que suma Fiestas y celebraciones cuando se filtra por intereses. Las demás ocasiones se registran, pero no cambian las sugerencias. El formato determina si se muestran regalos, combos o ambas opciones.
- **Presupuesto de combos:** el total nunca supera el máximo elegido. Si no hay suficientes opciones dentro del rango, pueden mostrarse combos por debajo del mínimo, desde la mitad de ese mínimo, con un aviso. El rango «Más de £30» tiene un máximo interno de £1.000.
- **Interpretación de las compras:** que dos productos se compren juntos no garantiza que sean adecuados como regalo ni que reflejen los gustos del destinatario.
- **Evaluación offline:** las métricas se calculan con transacciones históricas. No miden satisfacción ni demuestran un aumento real de ventas.
- **Sin operación comercial:** la app no procesa compras, pagos ni envíos, y tampoco envía la tarjeta personalizada.
