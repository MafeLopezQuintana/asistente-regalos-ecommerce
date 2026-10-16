from pathlib import Path

import pandas as pd
import pytest

from src.data.catalogo_app import (EXCLUIDO, INTERES_DEFECTO, REGLAS, RUTA_CATALOGO,
                                   asignar_interes, construir_catalogo_app, tabla_intereses)


@pytest.fixture
def catalogo():
    """Mini catálogo con el contrato de build_features: un producto por caso a cubrir."""
    filas = [
        ("A1", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55, "Corazones"),
        ("A2", "PANTRY ROLLING PIN", 3.75, "Variedad / Sorpresa"),
        ("A3", "Dotcomgiftshop Gift Voucher £10.00", 8.33, "Variedad / Sorpresa"),
        ("A4", "PINK DIAMANTE NECKLACE", 0.0, "Collares"),         # precio 0
        ("A5", "RED RETROSPOT NOTEBOOK", None, "Cuadernos"),        # precio nulo
        ("A6", "SPACE OWL", 1.25, None),                            # categoría nula
        ("A7", "  SPACE FROG ", 1.25, "Variedad / Sorpresa"),       # sin regla y con espacios
    ]
    return pd.DataFrame(filas, columns=["stock_code", "description", "precio", "categoria"])


# --- Reglas de interés ---------------------------------------------------------
@pytest.mark.parametrize("descripcion, esperado", [
    ("SET OF 6 T-LIGHTS SANTA", "Fiestas y celebraciones"),   # Fiestas va antes que Velas
    ("MAGIC DRAWING SLATE DINOSAUR", "Niños y juegos"),
    ("SET/3 VANILLA SCENTED CANDLE IN BOX", "Velas y aromas"),
    ("RUBY GLASS NECKLACE 42\"", "Accesorios"),
    ("SWALLOWS GREETING CARD", "Papelería y manualidades"),
    ("PANTRY SCRUBBING BRUSH", "Cocina y repostería"),
    ("VINTAGE ZINC WATERING CAN SMALL", "Jardín y flores"),
    ("UNION STRIPE CUSHION COVER", "Decoración y hogar"),
    ("SPACE FROG", INTERES_DEFECTO),
])
def test_asigna_interes_esperado(descripcion, esperado):
    assert asignar_interes(descripcion) == esperado


@pytest.mark.parametrize("descripcion", [
    "STRING OF STARS CARD HOLDER",   # RING dentro de STRING no es Accesorios
    "PANTRY SCRUBBING BRUSH",        # PAN dentro de PANTRY no cuenta, PANTRY sí
])
def test_limite_de_palabra_evita_falsos_positivos(descripcion):
    assert asignar_interes(descripcion) != "Accesorios"


def test_no_distingue_mayusculas():
    assert asignar_interes("pink diamante necklace") == "Accesorios"


@pytest.mark.parametrize("descripcion", [
    "Dotcomgiftshop Gift Voucher £50.00", "High Resolution Image",
    "POLYESTER FILLER PAD 45x45cm", "RETRO TIN ASHTRAY,REVOLUTIONARY",
])
def test_excluye_no_regalos(descripcion):
    assert asignar_interes(descripcion) == EXCLUIDO


def test_intereses_coinciden_con_los_esperados():
    # Si se cambia un nombre acá, hay que cambiarlo también en el cuestionario de app.py
    assert list(REGLAS) == [
        "Fiestas y celebraciones", "Niños y juegos", "Velas y aromas", "Accesorios",
        "Papelería y manualidades", "Cocina y repostería", "Jardín y flores", "Decoración y hogar",
    ]


# --- Catálogo para la app --------------------------------------------------------
def test_columnas_del_catalogo_app(catalogo):
    app = construir_catalogo_app(catalogo)
    assert list(app.columns) == ["stock_code", "description", "price", "category", "interes"]


def test_saca_excluidos_y_faltantes(catalogo):
    app = construir_catalogo_app(catalogo)
    assert set(app["stock_code"]) == {"A1", "A2", "A7"}
    assert (app["price"] > 0).all()
    assert app[["price", "category", "interes"]].notna().all().all()
    assert EXCLUIDO not in set(app["interes"])


def test_limpia_espacios_y_usa_interes_por_defecto(catalogo):
    app = construir_catalogo_app(catalogo).set_index("stock_code")
    assert app.loc["A7", "description"] == "SPACE FROG"
    assert app.loc["A7", "interes"] == INTERES_DEFECTO


def test_tabla_intereses_suma_el_total(catalogo):
    app = construir_catalogo_app(catalogo)
    tabla = tabla_intereses(app)
    assert tabla["n_productos"].sum() == len(app)
    assert "Variedad / Sorpresa" not in " ".join(tabla["categorias_principales"])


# --- Archivo generado (el que lee Streamlit) --------------------------------------
@pytest.mark.skipif(not Path(RUTA_CATALOGO).exists(), reason="Correr antes: python -m src.data.catalogo_app")
def test_archivo_catalogo_app_listo_para_la_app():
    assert Path(RUTA_CATALOGO).stat().st_size < 25 * 1024 * 1024
    app = pd.read_parquet(RUTA_CATALOGO)
    assert app["stock_code"].is_unique
    assert app[["price", "category", "interes"]].notna().all().all()
    assert (app["price"] > 0).all()
