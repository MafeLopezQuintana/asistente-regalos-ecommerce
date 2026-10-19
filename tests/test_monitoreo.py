import pandas as pd
import pytest

from src.models.monitoreo import (limite_superior_ic95, monitorear, pct_productos_nuevos,
                                  separar_por_mes)


@pytest.fixture
def df_meses():
    """Seis meses de facturas: A y B siempre juntos, C y D siempre juntos.

    En el último mes aparece E, un producto que el modelo no vio al entrenar.
    """
    filas = []
    for i, fecha in enumerate(pd.date_range("2011-01-05", periods=60, freq="3D")):
        productos = ["A", "B"] if i % 2 == 0 else ["C", "D"]
        if fecha >= pd.Timestamp("2011-06-01"):
            productos = productos + ["E"]
        filas += [(f"F{i}", p, fecha) for p in productos]
    return pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])


# --- Funciones auxiliares ---------------------------------------------------------
def test_separar_por_mes_no_parte_facturas():
    # F1 tiene una línea el 31/01 y otra el 01/02: va entera a enero (fecha mínima)
    d = pd.DataFrame({
        "invoice_no": ["F1", "F1", "F2"],
        "stock_code": ["A", "B", "A"],
        "invoice_date": pd.to_datetime(["2011-01-31", "2011-02-01", "2011-02-10"]),
    })
    meses = separar_por_mes(d)
    assert list(meses) == ["2011-01", "2011-02"]
    assert set(meses["2011-01"]["invoice_no"]) == {"F1"}
    assert set(meses["2011-02"]["invoice_no"]) == {"F2"}


def test_pct_productos_nuevos():
    d = pd.DataFrame({"stock_code": ["A", "B", "C", "D"]})
    assert pct_productos_nuevos(d, {"A", "B", "C"}) == 25.0
    assert pct_productos_nuevos(d, {"A", "B", "C", "D"}) == 0.0


def test_intervalo_mas_angosto_con_mas_casos():
    # Mismo Hit Rate: con más casos el límite superior queda más cerca del valor
    assert limite_superior_ic95(0.08, 2500) < limite_superior_ic95(0.08, 500)
    assert limite_superior_ic95(0.08, 500) > 0.08


# --- Monitoreo completo ------------------------------------------------------------
def test_monitorear_una_fila_por_mes_posterior_al_corte(df_meses):
    resultado = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                           registrar_mlflow=False)
    assert list(resultado["mes"]) == sorted(resultado["mes"])
    assert resultado["mes"].min() >= "2011-05"
    assert {"hit_rate_at_1", "hit_rate_at_1_baseline", "pct_productos_nuevos",
            "ic95_superior", "alerta"} <= set(resultado.columns)


def test_monitorear_detecta_productos_nuevos(df_meses):
    resultado = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                           registrar_mlflow=False).set_index("mes")
    assert resultado.loc["2011-06", "pct_productos_nuevos"] > 0


def test_alerta_segun_referencia(df_meses):
    # Pares perfectos: el modelo acierta siempre. Con referencia 0 nunca alerta;
    # con una referencia imposible (más de 100%) alerta todos los meses.
    sin_alerta = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                            referencia=0.0, registrar_mlflow=False)
    con_alerta = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                            referencia=1.5, registrar_mlflow=False)
    assert not sin_alerta["alerta"].any()
    assert con_alerta["alerta"].all()


def test_monitorear_registra_en_mlflow(df_meses, tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"  # base temporal, no la del repo
    resultado = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                           experimento="test-monitoreo", tracking_uri=uri)

    mlflow.set_tracking_uri(uri)
    corridas = mlflow.search_runs(experiment_names=["test-monitoreo"])
    assert len(corridas) == len(resultado)
    assert (corridas["tags.etapa"] == "monitoreo").all()
    assert set(corridas["tags.mes"]) == set(resultado["mes"])
    assert "metrics.hit_rate_at_1" in corridas.columns
    assert (corridas["tags.tipo"] == "simulacion").all()
    assert corridas["params.version_codigo"].notna().all()
    assert "metrics.facturas_excluidas" in corridas.columns


def test_facturas_excluidas_cuadran(df_meses):
    # Cada factura del mes es un caso o queda excluida (menos de 2 productos conocidos)
    resultado = monitorear(df_meses, params_modelo={"min_facturas": 1}, k=1,
                           registrar_mlflow=False)
    assert (resultado["facturas_excluidas"] >= 0).all()
    assert (resultado["casos"] + resultado["facturas_excluidas"] == resultado["facturas_mes"]).all()
