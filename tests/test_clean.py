import pandas as pd
import sys
sys.path.append('.')

from src.data.clean import limpiar_datos, segmentar_clientes, marcar_facturas_bulk, catalogo_productos


def fila(**kw):
    """Arma una fila de ejemplo válida, con overrides puntuales por test."""
    base = dict(invoice_no='500001', stock_code='85123A', description='HEART HOLDER',
                quantity=2, invoice_date=pd.to_datetime('2010-01-05 10:00:00'), unit_price=2.5,
                customer_id=12345, country='United Kingdom')
    base.update(kw)
    return base


def test_saca_cancelaciones():
    """Una factura que empieza con 'C' debe desaparecer del resultado."""
    df = pd.DataFrame([fila(), fila(invoice_no='C500002', quantity=-1)])
    resultado, _ = limpiar_datos(df)
    assert not resultado['invoice_no'].str.startswith('C').any()


def test_saca_cantidad_o_precio_no_positivo():
    """Cantidad o precio en 0/negativo no son ventas reales, se descartan."""
    df = pd.DataFrame([fila(), fila(invoice_no='500002', quantity=-3),
                        fila(invoice_no='500003', unit_price=0)])
    resultado, _ = limpiar_datos(df)
    assert len(resultado) == 1


def test_saca_codigos_no_producto():
    """Códigos administrativos (POST, B, etc.) no son productos, se excluyen
    aunque tengan precio positivo."""
    df = pd.DataFrame([fila(), fila(invoice_no='500002', stock_code='B', unit_price=100)])
    resultado, _ = limpiar_datos(df)
    assert 'B' not in resultado['stock_code'].values


def test_duplicados_suman_cantidad_no_se_descartan():
    """3 líneas idénticas de 1 unidad c/u deben consolidarse en 1 línea de 3
    unidades, no perder 2 de las 3 compras reales (bug encontrado en el
    notebook con datos reales: VINTAGE SNAKES & LADDERS x3)."""
    df = pd.DataFrame([fila(quantity=1), fila(quantity=1), fila(quantity=1)])
    resultado, _ = limpiar_datos(df)
    assert len(resultado) == 1
    assert resultado['quantity'].iloc[0] == 3


def test_conservar_sin_cliente_mantiene_ventas():
    """Con conservar_sin_cliente=True, las ventas sin customer_id se quedan
    (el modelo de recomendación no necesita saber quién compró)."""
    df = pd.DataFrame([fila(), fila(invoice_no='500002', customer_id=None)])
    resultado, _ = limpiar_datos(df, conservar_sin_cliente=True)
    assert len(resultado) == 2


def test_sin_cliente_se_elimina_por_defecto():
    """Sin el flag, el comportamiento por defecto sigue exigiendo customer_id
    (para RFM y segmentación mayorista/minorista)."""
    df = pd.DataFrame([fila(), fila(invoice_no='500002', customer_id=None)])
    resultado, _ = limpiar_datos(df)
    assert resultado['customer_id'].notna().all()


def test_log_registra_cada_paso():
    """El log devuelto es la tabla 'antes y después' que va al README —
    tiene que reflejar el conteo real en cada paso."""
    df = pd.DataFrame([fila(), fila(invoice_no='C9', quantity=-1)])
    _, log = limpiar_datos(df)
    assert log['filas'].iloc[0] == 2
    assert 'sin cancelaciones' in log['paso'].values


def test_segmento_valores_validos():
    """segmentar_clientes solo debe producir 3 valores posibles, nunca
    otro texto distinto por error de tipeo."""
    df = pd.DataFrame({'customer_id': [1, 2, 3], 'quantity': [5, 5000, 5]})
    resultado = segmentar_clientes(df)
    assert set(resultado['segmento'].unique()) <= {'mayorista', 'minorista', 'sin_cliente'}


def test_factura_bulk_pide_proporcion_y_minimo_productos():
    """Una factura de 1 sola línea no debe marcarse bulk aunque la cantidad
    sea múltiplo de 6 (bug real: antes el .all() la marcaba igual)."""
    bulk = [fila(invoice_no='B1', stock_code=f'P{i}', quantity=12) for i in range(5)]
    una_linea = [fila(invoice_no='B2', stock_code='Z1', quantity=6)]
    df = pd.DataFrame(bulk + una_linea)
    resultado = marcar_facturas_bulk(df)
    por_factura = resultado.groupby('invoice_no')['factura_bulk'].all()
    assert por_factura['B1'] == True
    assert por_factura['B2'] == False


def test_catalogo_tiene_precio_tipico():
    """El precio típico es la mediana, no el promedio: no se deja arrastrar
    por un outlier de precio (verificado con datos reales en el notebook)."""
    df = pd.DataFrame([fila(unit_price=2.5), fila(invoice_no='2', unit_price=2.5),
                        fila(invoice_no='3', unit_price=100)])
    catalogo = catalogo_productos(df)
    assert catalogo['precio'].iloc[0] == 2.5

def test_solapamiento_entre_hojas_se_detecta():
    """Si 2 hojas de Excel comparten una factura idéntica, se saca de una
    de las 2 antes de unirlas (no se cuenta doble en duplicados después)."""
    hoja1 = pd.DataFrame([fila(invoice_no='500001')])
    hoja2 = pd.DataFrame([fila(invoice_no='500001'), fila(invoice_no='500002')])

    # Simulamos el mismo chequeo que hace cargar_datos() internamente
    comunes = set(hoja1['invoice_no']) & set(hoja2['invoice_no'])
    assert comunes == {'500001'}

    cols = list(hoja1.columns)
    d0 = hoja1[hoja1['invoice_no'].isin(comunes)].sort_values(cols).reset_index(drop=True)
    d1 = hoja2[hoja2['invoice_no'].isin(comunes)].sort_values(cols).reset_index(drop=True)
    assert d0.equals(d1)

    hoja2_sin_solapar = hoja2[~hoja2['invoice_no'].isin(comunes)]
    assert len(hoja2_sin_solapar) == 1
    assert hoja2_sin_solapar.iloc[0]['invoice_no'] == '500002'

def test_cancelacion_elimina_compra_del_mismo_cliente():
    """Una compra con su cancelación exacta (mismo cliente, producto,
    cantidad) dentro de las 6 horas se elimina del dataset limpio."""
    compra = fila(invoice_no='500001', customer_id=111,
                   invoice_date=pd.to_datetime('2010-01-05 10:00:00'))
    cancelacion = fila(invoice_no='C500002', customer_id=111, quantity=-2,
                        invoice_date=pd.to_datetime('2010-01-05 10:30:00'))
    df = pd.DataFrame([compra, cancelacion])

    resultado, _ = limpiar_datos(df)
    assert len(resultado) == 0  # la compra se va por cancelación exacta, la "C" se va por ser cancelación

def test_clientes_anonimos_no_se_emparejan_por_error():
    """Dos compras SIN customer_id, mismo producto y cantidad, NO deben
    tratarse como la misma persona — bug real encontrado en la revisión
    del PR: pandas trata NaN == NaN como match al cruzar tablas."""
    compra_anonima = fila(invoice_no='500001', customer_id=None,
                           invoice_date=pd.to_datetime('2010-01-05 10:00:00'))
    cancelacion_anonima = fila(invoice_no='C500002', customer_id=None, quantity=-2,
                                invoice_date=pd.to_datetime('2010-01-05 10:30:00'))
    df = pd.DataFrame([compra_anonima, cancelacion_anonima])

    resultado, _ = limpiar_datos(df, conservar_sin_cliente=True)
    # La compra anónima NO se debe eliminar por la cancelación (son personas distintas, ambas desconocidas)
    assert len(resultado) == 1
    assert resultado.iloc[0]['invoice_no'] == '500001'

def test_codigos_nuevos_de_la_revision_se_excluyen():
    """TEST001, TEST002 (entradas de prueba) y 23444, 23574 (cargos de
    envío) deben seguir en CODIGOS_NO_PRODUCTO tras la revisión del PR."""
    df = pd.DataFrame([
        fila(invoice_no='500001', stock_code='TEST001', unit_price=4.5),
        fila(invoice_no='500002', stock_code='23444', unit_price=15.0),
    ])
    resultado, _ = limpiar_datos(df)
    assert len(resultado) == 0