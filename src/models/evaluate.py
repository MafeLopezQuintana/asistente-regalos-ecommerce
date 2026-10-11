"""
Evaluación offline de los recomendadores.

Contiene:
  - cargar_datos_modelo: lee el Parquet que genera src/data/clean.py.
  - corte_temporal: separa train y test por fecha, sin partir facturas.
  - hit_rate_at_k y ndcg_at_k: las métricas prometidas en la Propuesta.
  - construir_casos: arma los casos de prueba (qué ve el modelo y qué tiene que adivinar).
  - evaluar: corre un modelo sobre esos casos y devuelve las métricas promedio.
  - folds_temporales y evaluar_cv_temporal: validación cruzada temporal para elegir parámetros.
  - comparar_modelos: evalúa varios modelos sobre los MISMOS casos y los registra en MLflow.

El registro en MLflow pasa por src/utils/mlflow_utils.registrar_corrida, igual para
todo el equipo: un solo experimento, la base mlflow.db en la raíz del repo y el tag
"etapa" para separar "validacion" (evaluar_cv_temporal) de "test_final" (comparar_modelos).

Cualquier modelo (baseline, item-item, SVD) se evalúa igual, siempre que tenga
un método recomendar(anclas, k) que devuelva una lista de stock_code y un
atributo n_productos.
"""
import numpy as np
import pandas as pd

# Contrato de datos definido en src/data/clean.py (snake_case)
COL_FACTURA = "invoice_no"
COL_PRODUCTO = "stock_code"
COL_FECHA = "invoice_date"

RUTA_DATOS_MODELO = "data/processed/online_retail_modelo.parquet"


def cargar_datos_modelo(ruta=RUTA_DATOS_MODELO):
    """Lee el dataset limpio del modelo (incluye ventas sin cliente)."""
    return pd.read_parquet(ruta)


# ---------------------------------------------------------------------------
# Separación train / test
# ---------------------------------------------------------------------------
def corte_temporal(df, proporcion_train=0.8, col_factura=COL_FACTURA, col_fecha=COL_FECHA):
    """Separa por fecha: el primer 80% de las facturas (en el tiempo) va a train.

    Se corta por factura y no por fila, para que ningún pedido quede partido
    entre train y test. Devuelve (df_train, df_test, fecha_corte).
    """
    fecha_por_factura = df.groupby(col_factura)[col_fecha].min()
    fecha_corte = fecha_por_factura.quantile(proporcion_train)
    facturas_train = fecha_por_factura.index[fecha_por_factura <= fecha_corte]

    en_train = df[col_factura].isin(facturas_train)
    return df[en_train].copy(), df[~en_train].copy(), fecha_corte


def folds_temporales(df_desarrollo, n_folds=3, col_factura=COL_FACTURA, col_fecha=COL_FECHA):
    """Genera folds temporales expansivos sin partir facturas.

    Está pensado para usarse SOLO sobre el conjunto de desarrollo; el test final
    debe reservarse antes con ``corte_temporal`` y no participar de estos folds.

    Las fechas únicas del desarrollo se dividen en ``n_folds + 1`` bloques
    consecutivos. En cada fold el entrenamiento acumula todos los bloques
    anteriores y la validación usa únicamente el bloque siguiente. Por ejemplo,
    con 3 folds:

        fold 1: bloque 1       -> valida bloque 2
        fold 2: bloques 1 + 2 -> valida bloque 3
        fold 3: bloques 1-3   -> valida bloque 4

    Devuelve una lista de diccionarios con ``train``, ``valid`` y metadatos del
    rango temporal. La división se hace a nivel factura usando la fecha mínima
    de cada factura, para que una misma compra nunca quede en ambos conjuntos.
    """
    if n_folds < 1:
        raise ValueError("n_folds debe ser >= 1")
    if df_desarrollo.empty:
        raise ValueError("df_desarrollo no puede estar vacío")

    fecha_por_factura = (df_desarrollo.groupby(col_factura)[col_fecha]
                         .min()
                         .sort_values())
    fechas_unicas = pd.Index(fecha_por_factura.unique()).sort_values()

    if len(fechas_unicas) < n_folds + 1:
        raise ValueError(
            f"Se necesitan al menos {n_folds + 1} fechas distintas para {n_folds} folds"
        )

    bloques = [pd.Index(b) for b in np.array_split(fechas_unicas.to_numpy(), n_folds + 1)]
    folds = []

    for numero in range(1, n_folds + 1):
        fechas_train = pd.Index(np.concatenate([b.to_numpy() for b in bloques[:numero]]))
        fechas_valid = bloques[numero]

        facturas_train = fecha_por_factura.index[fecha_por_factura.isin(fechas_train)]
        facturas_valid = fecha_por_factura.index[fecha_por_factura.isin(fechas_valid)]

        train = df_desarrollo[df_desarrollo[col_factura].isin(facturas_train)].copy()
        valid = df_desarrollo[df_desarrollo[col_factura].isin(facturas_valid)].copy()

        folds.append({
            "fold": numero,
            "train": train,
            "valid": valid,
            "fecha_train_desde": fecha_por_factura.loc[facturas_train].min(),
            "fecha_train_hasta": fecha_por_factura.loc[facturas_train].max(),
            "fecha_valid_desde": fecha_por_factura.loc[facturas_valid].min(),
            "fecha_valid_hasta": fecha_por_factura.loc[facturas_valid].max(),
            "facturas_train": len(facturas_train),
            "facturas_valid": len(facturas_valid),
        })

    return folds


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def hit_rate_at_k(recomendados, objetivo, k=5):
    """1 si el producto objetivo está entre los primeros k recomendados, 0 si no."""
    return int(objetivo in list(recomendados)[:k])


def ndcg_at_k(recomendados, objetivo, k=5):
    """Premia que el acierto aparezca más arriba: 1.0 en el primer lugar, 0.63 en el segundo..."""
    top = list(recomendados)[:k]
    if objetivo not in top:
        return 0.0
    return 1.0 / np.log2(top.index(objetivo) + 2)


# ---------------------------------------------------------------------------
# Casos de prueba
# ---------------------------------------------------------------------------
def construir_casos(df_test, productos_conocidos, modo="ancla", semilla=42,
                    col_factura=COL_FACTURA, col_producto=COL_PRODUCTO):
    """Arma un caso de prueba por cada factura de test con 2+ productos distintos.

    En cada factura se esconde un producto al azar (el "oculto") y el modelo
    tiene que adivinarlo a partir de los otros.

    modo="ancla":   el modelo ve UN producto de la factura (como en la demo).
    modo="carrito": el modelo ve TODOS los demás productos de la factura.

    Solo se usan productos que existen en train (el modelo no puede recomendar
    algo que nunca vio); cuántas facturas se pierden por eso queda en `info`.
    La semilla fija hace que los casos sean siempre los mismos.
    """
    if modo not in ("ancla", "carrito"):
        raise ValueError("modo debe ser 'ancla' o 'carrito'")

    rng = np.random.default_rng(semilla)
    conocidos = set(productos_conocidos)
    casos = []
    info = {"facturas_evaluadas": 0, "facturas_2+_productos": 0, "casos": 0}

    for factura, productos in df_test.groupby(col_factura)[col_producto]:
        info["facturas_evaluadas"] += 1
        distintos = sorted(set(productos))  # sorted: mismo orden en cada corrida
        if len(distintos) < 2:
            continue
        info["facturas_2+_productos"] += 1

        validos = [p for p in distintos if p in conocidos]
        if len(validos) < 2:
            continue

        oculto = validos[rng.integers(len(validos))]
        resto = [p for p in validos if p != oculto]
        anclas = [resto[rng.integers(len(resto))]] if modo == "ancla" else resto
        casos.append({"factura": factura, "anclas": anclas, "oculto": oculto})

    info["casos"] = len(casos)
    if info["facturas_2+_productos"]:
        info["pct_facturas_evaluables"] = round(
            100 * info["casos"] / info["facturas_2+_productos"], 1)
    return casos, info


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------
def evaluar(modelo, casos, k=5):
    """Corre el modelo sobre todos los casos y promedia las métricas.

    cobertura_catalogo: qué porcentaje de los productos que conoce el modelo
    llegó a recomendar alguna vez. Un modelo que siempre recomienda lo mismo
    (como el baseline) tiene cobertura muy baja aunque acierte bastante.
    """
    if not casos:
        raise ValueError("No hay casos para evaluar")

    hits, ndcgs, recomendados_alguna_vez = [], [], set()
    for caso in casos:
        recs = modelo.recomendar(caso["anclas"], k=k)
        hits.append(hit_rate_at_k(recs, caso["oculto"], k))
        ndcgs.append(ndcg_at_k(recs, caso["oculto"], k))
        recomendados_alguna_vez.update(recs)

    # Nombres sin "@": MLflow no acepta ese carácter en las métricas
    return {
        f"hit_rate_at_{k}": float(np.mean(hits)),
        f"ndcg_at_{k}": float(np.mean(ndcgs)),
        "cobertura_catalogo": len(recomendados_alguna_vez) / modelo.n_productos,
        "casos": len(casos),
    }


def _registrar(nombre, parametros, metricas, tags, modelo=None,
               experimento=None, tracking_uri=None):
    """Llama a registrar_corrida; experimento y tracking_uri solo si se indican
    (si no, usa los del equipo). El import va acá para que evaluate.py no cargue
    MLflow cuando no se registra nada (por ejemplo, desde Streamlit)."""
    from src.utils.mlflow_utils import registrar_corrida

    destino = {}
    if experimento is not None:
        destino["experimento"] = experimento
    if tracking_uri is not None:
        destino["tracking_uri"] = tracking_uri
    return registrar_corrida(nombre, parametros, metricas, modelo=modelo, tags=tags, **destino)


def evaluar_cv_temporal(df_desarrollo, constructores_modelos, n_folds=3, k=5,
                        modo="ancla", semilla=42, registrar_mlflow=False,
                        tags=None, tags_por_modelo=None, experimento=None, tracking_uri=None,
                        col_factura=COL_FACTURA, col_producto=COL_PRODUCTO,
                        col_fecha=COL_FECHA):
    """Evalúa configuraciones de modelos con validación cruzada temporal.

    ``constructores_modelos`` es un diccionario ``{nombre: callable}``; cada
    callable debe crear una instancia NUEVA del modelo. Esto es necesario porque
    cada fold se entrena desde cero únicamente con su pasado. Ejemplo::

        {
            "popularidad": lambda: Popularidad(),
            "item_min5": lambda: ItemItem(min_facturas=5),
        }

    Todos los modelos de un mismo fold se evalúan sobre exactamente los mismos
    casos. Devuelve ``(detalle, resumen)``:
      - detalle: una fila por modelo y fold;
      - resumen: media y desvío de Hit Rate, NDCG y cobertura por modelo.

    Esta función NO debe recibir el test final. Primero se reserva ese 20% con
    ``corte_temporal`` y luego se pasa aquí únicamente el conjunto de desarrollo.

    Si ``registrar_mlflow=True``, cada configuración queda como una corrida con
    tag ``etapa="validacion"``: parámetros del modelo más n_folds, k, modo y
    semilla, y la media y el desvío de cada métrica. ``tags`` se agrega a todas
    las corridas y ``tags_por_modelo`` ({nombre: dict}) a cada una (por ejemplo, la familia).
    """
    if not constructores_modelos:
        raise ValueError("constructores_modelos no puede estar vacío")

    folds = folds_temporales(
        df_desarrollo, n_folds=n_folds,
        col_factura=col_factura, col_fecha=col_fecha,
    )
    filas = []

    for fold in folds:
        train = fold["train"]
        valid = fold["valid"]
        productos_conocidos = set(train[col_producto].unique())
        casos, info_casos = construir_casos(
            valid, productos_conocidos, modo=modo, semilla=semilla,
            col_factura=col_factura, col_producto=col_producto,
        )
        if not casos:
            raise ValueError(
                f"El fold {fold['fold']} no tiene casos evaluables; "
                "revise el número de folds o el tamaño de los datos"
            )

        for nombre, construir_modelo in constructores_modelos.items():
            modelo = construir_modelo()
            modelo.fit(train)
            metricas = evaluar(modelo, casos, k=k)
            filas.append({
                "fold": fold["fold"],
                "modelo": nombre,
                "fecha_train_desde": fold["fecha_train_desde"],
                "fecha_train_hasta": fold["fecha_train_hasta"],
                "fecha_valid_desde": fold["fecha_valid_desde"],
                "fecha_valid_hasta": fold["fecha_valid_hasta"],
                "facturas_train": fold["facturas_train"],
                "facturas_valid": fold["facturas_valid"],
                "pct_facturas_evaluables": info_casos.get("pct_facturas_evaluables", 0.0),
                **metricas,
            })

    detalle = pd.DataFrame(filas)
    metricas_cv = [f"hit_rate_at_{k}", f"ndcg_at_{k}", "cobertura_catalogo"]

    resumen_partes = []
    for nombre, grupo in detalle.groupby("modelo", sort=False):
        fila = {"modelo": nombre, "folds": int(grupo["fold"].nunique())}
        for metrica in metricas_cv:
            fila[f"{metrica}_media"] = float(grupo[metrica].mean())
            fila[f"{metrica}_std"] = float(grupo[metrica].std(ddof=0))
        fila["casos_total"] = int(grupo["casos"].sum())
        resumen_partes.append(fila)

    resumen = (pd.DataFrame(resumen_partes)
               .sort_values(f"hit_rate_at_{k}_media", ascending=False)
               .reset_index(drop=True))

    if registrar_mlflow:
        for _, fila in resumen.iterrows():
            nombre = fila["modelo"]
            parametros = {**constructores_modelos[nombre]().get_params(),
                          "n_folds": n_folds, "k": k, "modo": modo, "semilla": semilla}
            metricas = {c: float(fila[c]) for c in resumen.columns
                        if c.endswith(("_media", "_std"))}
            metricas["casos_total"] = int(fila["casos_total"])
            etiquetas = {"etapa": "validacion", **(tags or {}),
                         **(tags_por_modelo or {}).get(nombre, {})}
            _registrar(nombre, parametros, metricas, etiquetas,
                       experimento=experimento, tracking_uri=tracking_uri)

    return detalle, resumen


def comparar_modelos(modelos, casos, k=5, registrar_mlflow=True, params_comunes=None,
                     tags=None, tags_por_modelo=None, guardar_modelos=False,
                     experimento=None, tracking_uri=None):
    """Evalúa varios modelos sobre los MISMOS casos y devuelve una tabla ordenada.

    modelos: diccionario {nombre_de_la_corrida: modelo_entrenado}.
    Si registrar_mlflow=True, cada modelo queda como una corrida con tag
    ``etapa="test_final"``, sus parámetros (get_params() más params_comunes) y
    sus métricas. ``tags`` se agrega a todas las corridas y ``tags_por_modelo``
    ({nombre: dict}) a cada una. Con guardar_modelos=True, cada modelo se guarda
    como artefacto (joblib), para recuperarlo sin reentrenar. Es el equivalente
    a compare_models() de PyCaret, hecho para recomendadores.
    """
    filas = []
    for nombre, modelo in modelos.items():
        metricas = evaluar(modelo, casos, k=k)
        params = dict(params_comunes or {})
        if hasattr(modelo, "get_params"):
            params.update(modelo.get_params())

        if registrar_mlflow:
            etiquetas = {"etapa": "test_final", **(tags or {}),
                         **(tags_por_modelo or {}).get(nombre, {})}
            _registrar(nombre, params, metricas, etiquetas,
                       modelo=modelo if guardar_modelos else None,
                       experimento=experimento, tracking_uri=tracking_uri)

        filas.append({"modelo": nombre, **metricas})

    return (pd.DataFrame(filas)
            .sort_values(f"hit_rate_at_{k}", ascending=False)
            .reset_index(drop=True))
