import pandas as pd
import pytest

from src.models.evaluate import (comparar_modelos, construir_casos, corte_temporal,
                                 evaluar, evaluar_cv_temporal, folds_temporales, hit_rate_at_k, ndcg_at_k)
from src.models.train import ItemItem, Popularidad, SVD, construir_matriz


@pytest.fixture
def df():
    """Mini dataset con el contrato de clean.py: 5 facturas en 5 días distintos."""
    filas = [
        ("F1", "A", "2010-01-01", 1, 12), ("F1", "B", "2010-01-01", 1, 6),
        ("F2", "A", "2010-01-02", 2, 1), ("F2", "C", "2010-01-02", 2, 2),
        ("F3", "A", "2010-01-03", 1, 24), ("F3", "B", "2010-01-03", 1, 1),
        ("F4", "B", "2010-01-04", 3, 1), ("F4", "C", "2010-01-04", 3, 1),
        ("F5", "A", "2010-01-05", 2, 1), ("F5", "B", "2010-01-05", 2, 1),
        ("F5", "Z", "2010-01-05", 2, 1),  # Z no existe en train
    ]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date", "customer_id", "quantity"])
    d["invoice_date"] = pd.to_datetime(d["invoice_date"])
    d["customer_id"] = d["customer_id"].astype("Int64")
    d["factura_bulk"] = False
    return d


@pytest.fixture
def df_coocurrencia():
    """A y B siempre juntos; C y D siempre juntos; E aparece una sola vez con A."""
    facturas = [["A", "B"]] * 6 + [["C", "D"]] * 6 + [["A", "E"]]
    filas = [(f"F{i}", p) for i, prods in enumerate(facturas) for p in prods]
    return pd.DataFrame(filas, columns=["invoice_no", "stock_code"])


# --- Corte temporal ---------------------------------------------------------
def test_corte_no_superpone_fechas(df):
    train, test, _ = corte_temporal(df, 0.8)
    assert train["invoice_date"].max() < test["invoice_date"].min()


def test_corte_no_parte_facturas(df):
    train, test, _ = corte_temporal(df, 0.8)
    assert not set(train["invoice_no"]) & set(test["invoice_no"])
    assert len(train) + len(test) == len(df)


def test_folds_temporales_son_expansivos_y_sin_leakage():
    filas = []
    for i in range(1, 9):
        fecha = f"2010-01-{i:02d}"
        filas += [(f"F{i}", "A", fecha), (f"F{i}", "B", fecha)]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])
    d["invoice_date"] = pd.to_datetime(d["invoice_date"])

    folds = folds_temporales(d, n_folds=3)
    assert len(folds) == 3

    tamanios_train = []
    facturas_validacion = []
    for fold in folds:
        train, valid = fold["train"], fold["valid"]
        assert not set(train["invoice_no"]) & set(valid["invoice_no"])
        assert train["invoice_date"].max() < valid["invoice_date"].min()
        tamanios_train.append(train["invoice_no"].nunique())
        facturas_validacion.append(set(valid["invoice_no"]))

    assert tamanios_train == sorted(tamanios_train)
    assert all(a.isdisjoint(b) for i, a in enumerate(facturas_validacion)
               for b in facturas_validacion[i + 1:])


def test_folds_temporales_rechaza_pocas_fechas(df):
    with pytest.raises(ValueError):
        folds_temporales(df, n_folds=5)


# --- Métricas ---------------------------------------------------------------
def test_hit_rate():
    assert hit_rate_at_k(["A", "B", "C"], "C", k=3) == 1
    assert hit_rate_at_k(["A", "B", "C"], "C", k=2) == 0


def test_ndcg_premia_posicion():
    assert ndcg_at_k(["X", "B"], "X") == 1.0
    assert ndcg_at_k(["A", "X"], "X") == pytest.approx(0.6309, abs=1e-4)
    assert ndcg_at_k(["A", "B"], "X") == 0.0


# --- Casos de prueba --------------------------------------------------------
def test_casos_reproducibles_y_validos(df):
    train, test, _ = corte_temporal(df, 0.8)
    conocidos = set(train["stock_code"])
    casos1, info = construir_casos(test, conocidos, semilla=1)
    casos2, _ = construir_casos(test, conocidos, semilla=1)
    assert casos1 == casos2
    for c in casos1:
        assert c["oculto"] not in c["anclas"]
        assert c["oculto"] in conocidos and set(c["anclas"]) <= conocidos
    assert info["facturas_2+_productos"] >= info["casos"]


def test_modo_carrito_usa_todo_el_resto(df):
    casos, _ = construir_casos(df, set(df["stock_code"]), modo="carrito")
    caso_f5 = next(c for c in casos if c["factura"] == "F5")
    assert len(caso_f5["anclas"]) == 2


# --- Matriz -----------------------------------------------------------------
def test_matriz_binaria(df):
    duplicada = pd.concat([df, df.iloc[[0]]])  # F1-A repetida
    matriz, facturas, productos = construir_matriz(duplicada)
    assert matriz.shape == (len(facturas), len(productos))
    assert matriz.max() == 1.0
    assert matriz.sum() == len(df.drop_duplicates(["invoice_no", "stock_code"]))


# --- Baseline ---------------------------------------------------------------
def test_popularidad_excluye_anclas(df):
    recs = Popularidad().fit(df).recomendar(["A"], k=2)
    assert "A" not in recs and len(recs) == 2


def test_popularidad_por_facturas(df):
    # A y B están en 4 facturas, C en 2: desempata por código (A antes que B)
    assert Popularidad().fit(df).ranking[:3] == ["A", "B", "C"]


# --- Item-item --------------------------------------------------------------
def test_itemitem_vecino_es_el_que_se_compra_junto(df_coocurrencia):
    modelo = ItemItem(min_facturas=1).fit(df_coocurrencia)
    assert modelo.recomendar(["A"], k=1) == ["B"]
    assert modelo.recomendar(["C"], k=1) == ["D"]


def test_itemitem_no_recomienda_las_anclas(df_coocurrencia):
    modelo = ItemItem(min_facturas=1).fit(df_coocurrencia)
    recs = modelo.recomendar(["A", "B"], k=5)
    assert "A" not in recs and "B" not in recs


def test_itemitem_min_facturas_deja_afuera_productos_raros(df_coocurrencia):
    modelo = ItemItem(min_facturas=2, completar_con_popularidad=False).fit(df_coocurrencia)
    assert "E" not in modelo.productos
    assert "E" not in modelo.recomendar(["A"], k=5)


def test_itemitem_modo_carrito_suma_similitudes(df_coocurrencia):
    modelo = ItemItem(min_facturas=1, completar_con_popularidad=False).fit(df_coocurrencia)
    # Con A y C como anclas, sus dos vecinos (B y D) tienen que aparecer
    assert set(modelo.recomendar(["A", "C"], k=2)) == {"B", "D"}


def test_itemitem_completa_con_popularidad_si_el_ancla_es_desconocida(df_coocurrencia):
    modelo = ItemItem(min_facturas=1).fit(df_coocurrencia)
    recs = modelo.recomendar(["NO_EXISTE"], k=3)
    assert len(recs) == 3


def test_itemitem_excluye_facturas_bulk(df_coocurrencia):
    d = df_coocurrencia.copy()
    d["factura_bulk"] = d["stock_code"].isin(["C", "D"])  # marca las facturas de C y D
    modelo = ItemItem(min_facturas=1, excluir_bulk=True).fit(d)
    assert "C" not in modelo.productos and "D" not in modelo.productos


def test_itemitem_excluir_bulk_sin_columna_da_error(df_coocurrencia):
    # df_coocurrencia no tiene factura_bulk: pedir excluirlas tiene que fallar, no ignorarse
    with pytest.raises(ValueError, match="factura_bulk"):
        ItemItem(min_facturas=1, excluir_bulk=True).fit(df_coocurrencia)


# --- Evaluación y comparación ----------------------------------------------
def test_cv_temporal_reentrena_y_resume_modelos():
    filas = []
    patrones = [
        ["A", "B"], ["A", "B"], ["A", "C"], ["A", "B"],
        ["A", "B"], ["A", "C"], ["A", "B"], ["A", "B"],
    ]
    for i, prods in enumerate(patrones, start=1):
        fecha = pd.Timestamp("2010-01-01") + pd.Timedelta(days=i - 1)
        filas += [(f"F{i}", p, fecha) for p in prods]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])

    constructores = {
        "popularidad": lambda: Popularidad(),
        "item_item": lambda: ItemItem(min_facturas=1),
    }
    detalle, resumen = evaluar_cv_temporal(d, constructores, n_folds=3, k=1)

    assert len(detalle) == 6  # 2 modelos x 3 folds
    assert set(detalle["modelo"]) == {"popularidad", "item_item"}
    assert (detalle.groupby("fold")["casos"].nunique() == 1).all()
    assert set(resumen["modelo"]) == {"popularidad", "item_item"}
    assert (resumen["folds"] == 3).all()
    assert "hit_rate_at_1_media" in resumen.columns
    assert "hit_rate_at_1_std" in resumen.columns


def test_evaluar_devuelve_metricas(df):
    modelo = Popularidad().fit(df)
    casos, _ = construir_casos(df, modelo.ranking)
    resultado = evaluar(modelo, casos, k=5)
    assert 0 <= resultado["hit_rate_at_5"] <= 1
    assert resultado["casos"] == len(casos)


def test_comparar_modelos_usa_los_mismos_casos_y_ordena(df_coocurrencia):
    modelos = {"popularidad": Popularidad().fit(df_coocurrencia),
               "item_item": ItemItem(min_facturas=1).fit(df_coocurrencia)}
    casos, _ = construir_casos(df_coocurrencia, modelos["popularidad"].ranking)
    tabla = comparar_modelos(modelos, casos, k=1, registrar_mlflow=False)
    assert set(tabla["modelo"]) == {"popularidad", "item_item"}
    assert (tabla["casos"] == len(casos)).all()
    assert tabla["hit_rate_at_1"].is_monotonic_decreasing
    assert tabla.loc[0, "modelo"] == "item_item"  # en estos datos la co-compra gana


def test_comparar_modelos_registra_en_mlflow(df_coocurrencia, tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"  # base temporal, no la del repo
    modelos = {"item_item": ItemItem(min_facturas=1).fit(df_coocurrencia)}
    casos, _ = construir_casos(df_coocurrencia, modelos["item_item"]._popularidad.ranking)
    comparar_modelos(modelos, casos, k=1, experimento="test-experimento", tracking_uri=uri,
                     tags_por_modelo={"item_item": {"familia": "item_item"}}, guardar_modelos=True)

    mlflow.set_tracking_uri(uri)
    corridas = mlflow.search_runs(experiment_names=["test-experimento"])
    assert len(corridas) == 1
    assert "metrics.hit_rate_at_1" in corridas.columns
    assert corridas.loc[0, "params.min_facturas"] == "1"
    assert corridas.loc[0, "tags.etapa"] == "test_final"
    assert corridas.loc[0, "tags.familia"] == "item_item"
    # el modelo quedó guardado como artefacto y se puede recuperar
    artefactos = mlflow.MlflowClient().list_artifacts(corridas.loc[0, "run_id"], "modelo")
    assert [a.path for a in artefactos] == ["modelo/item_item.joblib"]


def test_cv_temporal_registra_una_corrida_por_configuracion(tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    filas = []
    for i, prods in enumerate([["A", "B"], ["A", "B"], ["A", "C"], ["A", "B"],
                               ["A", "B"], ["A", "C"], ["A", "B"], ["A", "B"]], start=1):
        fecha = pd.Timestamp("2010-01-01") + pd.Timedelta(days=i - 1)
        filas += [(f"F{i}", p, fecha) for p in prods]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])

    constructores = {"popularidad": lambda: Popularidad(),
                     "item_item": lambda: ItemItem(min_facturas=1)}
    evaluar_cv_temporal(d, constructores, n_folds=3, k=1, registrar_mlflow=True,
                        experimento="test-cv", tracking_uri=uri,
                        tags_por_modelo={"item_item": {"familia": "item_item"}})

    mlflow.set_tracking_uri(uri)
    corridas = mlflow.search_runs(experiment_names=["test-cv"])
    assert set(corridas["tags.mlflow.runName"]) == {"popularidad", "item_item"}
    assert (corridas["tags.etapa"] == "validacion").all()
    assert {"metrics.hit_rate_at_1_media", "metrics.hit_rate_at_1_std"} <= set(corridas.columns)
    assert (corridas["params.n_folds"] == "3").all()
    fila_item = corridas[corridas["tags.mlflow.runName"] == "item_item"].iloc[0]
    assert fila_item["tags.familia"] == "item_item"


def test_cv_temporal_no_registra_por_defecto(monkeypatch):
    # Sin registrar_mlflow=True no se llama a registrar_corrida
    import src.utils.mlflow_utils as mlflow_utils

    def no_deberia_llamarse(*args, **kwargs):
        raise AssertionError("registró en MLflow sin pedirlo")

    monkeypatch.setattr(mlflow_utils, "registrar_corrida", no_deberia_llamarse)
    filas = [(f"F{i}", p, pd.Timestamp("2010-01-01") + pd.Timedelta(days=i))
             for i in range(8) for p in ("A", "B")]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])
    evaluar_cv_temporal(d, {"popularidad": lambda: Popularidad()}, n_folds=3, k=1)


# --- SVD --------------------------------------------------------------------
def test_svd_vecino_latente_recupera_coocurrencia(df_coocurrencia):
    modelo = SVD(n_components=2, min_facturas=1,
                 completar_con_popularidad=False).fit(df_coocurrencia)
    assert modelo.recomendar(["A"], k=1) == ["B"]
    assert modelo.recomendar(["C"], k=1) == ["D"]


def test_svd_no_recomienda_ancla_y_es_reproducible(df_coocurrencia):
    m1 = SVD(n_components=2, min_facturas=1, random_state=7).fit(df_coocurrencia)
    m2 = SVD(n_components=2, min_facturas=1, random_state=7).fit(df_coocurrencia)
    r1 = m1.recomendar(["A"], k=3)
    r2 = m2.recomendar(["A"], k=3)
    assert "A" not in r1
    assert r1 == r2


def test_svd_min_facturas_deja_afuera_producto_raro(df_coocurrencia):
    modelo = SVD(n_components=2, min_facturas=2,
                 completar_con_popularidad=False).fit(df_coocurrencia)
    assert "E" not in modelo.productos
    assert "E" not in modelo.recomendar(["A"], k=5)


def test_svd_excluye_facturas_bulk(df_coocurrencia):
    d = df_coocurrencia.copy()
    d["factura_bulk"] = d["stock_code"].isin(["C", "D"])
    modelo = SVD(n_components=2, min_facturas=1, excluir_bulk=True).fit(d)
    assert "C" not in modelo.productos and "D" not in modelo.productos


def test_svd_ancla_desconocida_completa_con_popularidad(df_coocurrencia):
    modelo = SVD(n_components=2, min_facturas=1).fit(df_coocurrencia)
    assert len(modelo.recomendar(["NO_EXISTE"], k=3)) == 3


def test_svd_parametros_y_diagnosticos(df_coocurrencia):
    modelo = SVD(n_components=2, min_facturas=1, random_state=11).fit(df_coocurrencia)
    params = modelo.get_params()
    assert params["modelo"] == "svd"
    assert params["n_components"] == 2
    assert params["random_state"] == 11
    assert modelo.n_componentes_efectivos == 2
    assert 0.0 <= modelo.varianza_explicada <= 1.0


def test_svd_excluir_bulk_sin_columna_da_error(df_coocurrencia):
    with pytest.raises(ValueError, match="factura_bulk"):
        SVD(n_components=2, min_facturas=1, excluir_bulk=True).fit(df_coocurrencia)


def test_cv_temporal_acepta_svd():
    filas = []
    for i in range(1, 13):
        fecha = f"2010-01-{i:02d}"
        productos = ["A", "B"] if i % 2 else ["A", "C"]
        filas += [(f"F{i}", p, fecha) for p in productos]
    d = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])
    d["invoice_date"] = pd.to_datetime(d["invoice_date"])
    d["factura_bulk"] = False

    constructores = {
        "popularidad": lambda: Popularidad(),
        "svd_2": lambda: SVD(n_components=2, min_facturas=1),
    }
    detalle, resumen = evaluar_cv_temporal(
        d, constructores, n_folds=3, k=2, semilla=3
    )
    assert set(detalle["modelo"]) == {"popularidad", "svd_2"}
    assert (detalle.groupby("fold")["casos"].nunique() == 1).all()
    assert set(resumen["modelo"]) == {"popularidad", "svd_2"}

