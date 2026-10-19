from pathlib import Path

import pandas as pd
import pytest

from src.models.asistente import (COLUMNAS_COMBOS, COLUMNAS_SALIDA, FUENTE_CO_COMPRA,
                                  FUENTE_POPULARIDAD, INTERES_SORPRENDEME, PRECIO_MINIMO_REGALO,
                                  RUTA_MODELO, _es_variante, armar_combos, buscar_ideas_regalo,
                                  cargar_modelo_final, construir_modelo_final,
                                  guardar_modelo_final)


@pytest.fixture
def ventas():
    """Pedidos inventados: la vela A se compra casi siempre con B y a veces con C.

    D y E son populares pero nunca van con A. F aparece en un solo pedido.
    """
    pedidos = (
        [["A", "B"]] * 6 + [["A", "B", "C"]] * 3 + [["A", "C"]] * 2
        + [["D", "E"]] * 8 + [["D"]] * 4 + [["E", "G"]] * 5 + [["F", "D"]]
    )
    filas = [(f"F{i}", p, pd.Timestamp("2011-01-01") + pd.Timedelta(days=i))
             for i, productos in enumerate(pedidos) for p in productos]
    return pd.DataFrame(filas, columns=["invoice_no", "stock_code", "invoice_date"])


@pytest.fixture
def catalogo():
    return pd.DataFrame({
        "stock_code": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "description": ["VELA ROJA", "PORTAVELAS", "FÓSFOROS", "TAZA", "PLATO",
                        "LÁPIZ", "GUIRNALDA NAVIDAD", "TARJETA"],
        "price": [3.0, 4.0, 1.0, 6.0, 8.0, 0.10, 2.5, 1.5],
        "interes": ["Velas y aromas", "Velas y aromas", "Velas y aromas",
                    "Cocina y repostería", "Cocina y repostería",
                    "Papelería y manualidades", "Fiestas y celebraciones",
                    "Papelería y manualidades"],
    })


@pytest.fixture
def modelo(ventas):
    return construir_modelo_final(ventas, params={"min_facturas": 1, "max_productos_factura": None})


def resumen(**cambios):
    base = {"precio_minimo": 0, "precio_maximo": 30, "intereses": [INTERES_SORPRENDEME],
            "ocasion": "Cumpleaños", "producto_codigo": None}
    return {**base, **cambios}


# --- Modelo final -------------------------------------------------------------------
def test_vecinos_ordenados_y_sin_el_mismo_producto(modelo):
    vecinos = modelo["vecinos"]
    assert (vecinos["stock_code"] != vecinos["vecino"]).all()
    de_a = vecinos[vecinos["stock_code"] == "A"].sort_values("rango")
    assert list(de_a["vecino"]) == ["B", "C"]               # B va más veces con A que C
    assert de_a["similitud"].is_monotonic_decreasing


def test_co_compras_cuenta_pedidos_juntos(modelo):
    de_a = modelo["vecinos"].set_index(["stock_code", "vecino"])
    assert de_a.loc[("A", "B"), "co_compras"] == 9
    assert de_a.loc[("A", "C"), "co_compras"] == 5


def test_respeta_el_tope_de_vecinos(ventas):
    modelo = construir_modelo_final(ventas, params={"min_facturas": 1}, top=1)
    assert modelo["vecinos"].groupby("stock_code").size().max() == 1


def test_popularidad_ordenada_por_pedidos(modelo):
    assert modelo["popularidad"]["stock_code"].iloc[0] == "D"   # 13 pedidos
    assert modelo["popularidad"]["pedidos"].is_monotonic_decreasing


def test_guardar_y_cargar(modelo, tmp_path):
    ruta = guardar_modelo_final(modelo, tmp_path / "modelo_final.pkl")
    cargado = cargar_modelo_final(ruta)
    assert cargado["parametros"] == modelo["parametros"]
    pd.testing.assert_frame_equal(cargado["vecinos"], modelo["vecinos"])


# --- buscar_ideas_regalo --------------------------------------------------------------
def test_con_referencia_primero_lo_que_se_compra_junto(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(producto_codigo="A"), catalogo, modelo)
    assert list(ideas.columns) == COLUMNAS_SALIDA
    assert list(ideas["stock_code"][:2]) == ["B", "C"]
    assert (ideas["fuente"][:2] == FUENTE_CO_COMPRA).all()
    assert "VELA ROJA" in ideas["motivo"].iloc[0] and "9 pedidos" in ideas["motivo"].iloc[0]


def test_no_sugiere_variantes_de_la_referencia(modelo, catalogo):
    catalogo = catalogo.copy()
    catalogo.loc[catalogo["stock_code"] == "B", "description"] = "VELA ROJA GRANDE"
    ideas = buscar_ideas_regalo(resumen(producto_codigo="A"), catalogo, modelo)
    assert "B" not in set(ideas["stock_code"])             # VELA ROJA / VELA ROJA GRANDE
    assert ideas["stock_code"].iloc[0] == "C"


def test_no_repite_ni_incluye_la_referencia(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(producto_codigo="A"), catalogo, modelo, k=10)
    assert "A" not in set(ideas["stock_code"])
    assert ideas["stock_code"].is_unique


def test_sin_referencia_usa_popularidad(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(), catalogo, modelo, k=2)
    assert list(ideas["stock_code"]) == ["D", "E"]
    assert (ideas["fuente"] == FUENTE_POPULARIDAD).all()


def test_completa_con_popularidad_si_faltan_vecinos(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(producto_codigo="A"), catalogo, modelo, k=4)
    assert len(ideas) == 4
    assert list(ideas["fuente"]) == [FUENTE_CO_COMPRA] * 2 + [FUENTE_POPULARIDAD] * 2


def test_respeta_presupuesto_y_precio_minimo(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(precio_minimo=2, precio_maximo=5), catalogo, modelo, k=10)
    assert ideas["price"].between(2, 5).all()
    todas = buscar_ideas_regalo(resumen(precio_maximo=2), catalogo, modelo, k=10)
    assert (todas["price"] >= PRECIO_MINIMO_REGALO).all()   # el lápiz de £0,10 no aparece
    assert "F" not in set(todas["stock_code"])


def test_filtra_por_intereses(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(intereses=["Cocina y repostería"]), catalogo, modelo, k=10)
    assert set(ideas["interes"]) == {"Cocina y repostería"}


def test_navidad_suma_fiestas(modelo, catalogo):
    pedido = resumen(intereses=["Cocina y repostería"], ocasion="Navidad / Fiestas")
    ideas = buscar_ideas_regalo(pedido, catalogo, modelo, k=10)
    assert "Fiestas y celebraciones" in set(ideas["interes"])


def test_referencia_sin_historial_no_falla(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(producto_codigo="H"), catalogo, modelo, k=3)
    assert len(ideas) == 3 and (ideas["fuente"] == FUENTE_POPULARIDAD).all()


def test_sin_resultados_devuelve_tabla_vacia(modelo, catalogo):
    ideas = buscar_ideas_regalo(resumen(precio_minimo=100, precio_maximo=200), catalogo, modelo)
    assert ideas.empty and list(ideas.columns) == COLUMNAS_SALIDA


# --- armar_combos ------------------------------------------------------------------------
def test_combo_arranca_por_la_referencia_y_suma_lo_que_va_junto(modelo, catalogo):
    combos = armar_combos(resumen(producto_codigo="A", precio_minimo=5, precio_maximo=10),
                          catalogo, modelo)
    assert list(combos.columns) == COLUMNAS_COMBOS
    primero = combos[combos["combo"] == 1]
    assert list(primero["stock_code"][:2]) == ["A", "B"]          # B es lo que más va con A
    assert primero["fuente"].iloc[0] == "referencia"
    assert primero["motivo"].iloc[1].startswith("Se compra junto con VELA ROJA")


def test_total_del_combo_dentro_del_presupuesto(modelo, catalogo):
    combos = armar_combos(resumen(precio_minimo=5, precio_maximo=15), catalogo, modelo)
    # Con estos datos alcanza el mínimo, así que todos los combos caen dentro del rango
    assert not combos.empty
    totales = combos.groupby("combo")["price"].sum()
    assert totales.between(5, 15).all()
    assert (combos.groupby("combo")["total_combo"].first().round(2) == totales.round(2)).all()


def test_combos_de_al_menos_dos_productos_sin_repetir(modelo, catalogo):
    combos = armar_combos(resumen(precio_maximo=30), catalogo, modelo)
    assert (combos.groupby("combo").size() >= 2).all()
    assert not combos.duplicated(["combo", "stock_code"]).any()


def test_combo_no_junta_variantes_del_mismo_producto():
    assert _es_variante("WHITE HANGING HEART T-LIGHT HOLDER", "RED HANGING HEART T-LIGHT HOLDER")
    assert not _es_variante("WHITE HANGING HEART T-LIGHT HOLDER", "JUMBO BAG RED RETROSPOT")


def test_combos_no_comparten_productos(modelo, catalogo):
    combos = armar_combos(resumen(precio_maximo=30), catalogo, modelo)
    assert combos["stock_code"].is_unique


def test_si_no_llega_al_minimo_devuelve_lo_mas_cercano_sin_pasarse(modelo, catalogo):
    combos = armar_combos(resumen(intereses=["Velas y aromas"], precio_minimo=15, precio_maximo=30),
                          catalogo, modelo)
    assert not combos.empty                               # A + B + C = £8: no llega a £15
    assert (combos.groupby("combo")["price"].sum() <= 30).all()


def test_combos_respetan_intereses(modelo, catalogo):
    combos = armar_combos(resumen(intereses=["Cocina y repostería"], precio_maximo=30), catalogo, modelo)
    assert set(combos["interes"]) <= {"Cocina y repostería"}


def test_sin_combos_posibles_devuelve_tabla_vacia(modelo, catalogo):
    combos = armar_combos(resumen(precio_minimo=100, precio_maximo=200), catalogo, modelo)
    assert combos.empty and list(combos.columns) == COLUMNAS_COMBOS


def test_guardar_no_incluye_indices_en_memoria(modelo, catalogo, tmp_path):
    armar_combos(resumen(), catalogo, modelo)                  # arma los índices en memoria
    cargado = cargar_modelo_final(guardar_modelo_final(modelo, tmp_path / "m.pkl"))
    assert not any(clave.startswith("_") for clave in cargado)


# --- Archivo generado (el que lee Streamlit) --------------------------------------------
@pytest.mark.skipif(not Path(RUTA_MODELO).exists(), reason="Correr antes: python -m src.models.asistente")
def test_archivo_modelo_final_listo_para_la_app():
    assert Path(RUTA_MODELO).stat().st_size < 25 * 1024 * 1024
    modelo = cargar_modelo_final()
    assert {"vecinos", "popularidad", "parametros"} <= set(modelo)
    assert modelo["vecinos"].groupby("stock_code").size().max() <= 20
