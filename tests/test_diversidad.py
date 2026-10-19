import pandas as pd
import pytest

from src.models.evaluate import construir_casos, diversidad_intra_lista, evaluar
from src.models.train import ItemItem, Popularidad


@pytest.fixture
def referencia():
    """A, B y C siempre se compran juntos; D y E siempre juntos; F con nadie."""
    pedidos = [["A", "B", "C"]] * 5 + [["D", "E"]] * 5 + [["F"]] * 2
    filas = [(f"F{i}", p) for i, productos in enumerate(pedidos) for p in productos]
    df = pd.DataFrame(filas, columns=["invoice_no", "stock_code"])
    return ItemItem(min_facturas=1).fit(df)


def _diversidad(recs, referencia):
    posicion = {p: i for i, p in enumerate(referencia.productos)}
    return diversidad_intra_lista(recs, referencia.similitud.tocsr(), posicion)


def test_productos_que_siempre_van_juntos_dan_cero(referencia):
    assert _diversidad(["A", "B", "C"], referencia) == pytest.approx(0.0, abs=1e-6)


def test_productos_que_nunca_van_juntos_dan_uno(referencia):
    assert _diversidad(["A", "D", "F"], referencia) == pytest.approx(1.0, abs=1e-6)


def test_valor_intermedio_promedia_los_pares(referencia):
    # Pares: A-B (1), A-D (0), B-D (0) -> similitud promedio 1/3
    assert _diversidad(["A", "B", "D"], referencia) == pytest.approx(2 / 3, abs=1e-6)


def test_producto_fuera_de_la_referencia_cuenta_como_distinto(referencia):
    assert _diversidad(["A", "B", "Z"], referencia) == pytest.approx(2 / 3, abs=1e-6)


def test_lista_de_un_producto_no_tiene_pares(referencia):
    assert _diversidad(["A"], referencia) is None


def test_evaluar_suma_diversidad_solo_si_se_pide(referencia):
    test = pd.DataFrame({"invoice_no": ["T1", "T1", "T2", "T2"],
                         "stock_code": ["A", "B", "D", "E"]})
    casos, _ = construir_casos(test, set(referencia.productos))
    sin = evaluar(referencia, casos, k=2)
    con = evaluar(referencia, casos, k=2, referencia_diversidad=referencia)
    assert "diversidad_at_2" not in sin
    assert 0.0 <= con["diversidad_at_2"] <= 1.0
    assert {k: v for k, v in con.items() if k != "diversidad_at_2"} == sin


def test_misma_regla_para_cualquier_modelo(referencia):
    # La popularidad no tiene similitud propia: se mide con la referencia común
    df = pd.DataFrame({"invoice_no": ["F1", "F1", "F2"], "stock_code": ["A", "D", "F"]})
    popularidad = Popularidad().fit(df)
    casos = [{"factura": "X", "anclas": ["B"], "oculto": "A"}]
    resultado = evaluar(popularidad, casos, k=3, referencia_diversidad=referencia)
    assert resultado["diversidad_at_3"] == pytest.approx(1.0, abs=1e-6)  # recomienda A, D, F
