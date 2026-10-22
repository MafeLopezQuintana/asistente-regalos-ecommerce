import pandas as pd
import pytest

from src.models.asistente import construir_modelo_final, guardar_modelo_final
from src.models.registrar_modelo import registrar_modelo_final


@pytest.fixture
def ruta_modelo(tmp_path):
    """Un modelo final chico, guardado en una carpeta temporal (no el del repo)."""
    pedidos = [["A", "B"]] * 6 + [["A", "C"]] * 3 + [["B", "C"]] * 2
    filas = [(f"F{i}", p, pd.Timestamp("2011-01-01") + pd.Timedelta(days=i))
             for i, productos in enumerate(pedidos) for p in productos]
    ventas = pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])
    modelo = construir_modelo_final(ventas, params={"min_facturas": 1})
    return guardar_modelo_final(modelo, tmp_path / "modelo_final.pkl")


def test_registra_el_modelo_final_en_mlflow(ruta_modelo, tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"  # base temporal, no la del repo
    run_id = registrar_modelo_final(ruta_modelo, experimento="test-modelo-final", tracking_uri=uri)

    mlflow.set_tracking_uri(uri)
    corrida = mlflow.get_run(run_id)
    assert corrida.data.tags["etapa"] == "modelo_final"
    assert corrida.data.params["min_facturas"] == "1"
    assert corrida.data.params["datos_desde"] == "2011-01-01"
    assert "version_codigo" in corrida.data.params
    assert corrida.data.metrics["facturas_entrenamiento"] == 11
    assert "referencia_hit_rate_at_5" in corrida.data.metrics

    # El .pkl queda guardado como artefacto de la corrida
    artefactos = [a.path for a in mlflow.MlflowClient().list_artifacts(run_id)]
    assert "modelo_final.pkl" in artefactos
