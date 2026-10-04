# src/data/clean.py
from pathlib import Path
import pandas as pd

RENAME = {
    'Invoice': 'invoice_no', 'InvoiceNo': 'invoice_no', 'StockCode': 'stock_code',
    'Description': 'description', 'Quantity': 'quantity', 'InvoiceDate': 'invoice_date',
    'Price': 'unit_price', 'UnitPrice': 'unit_price', 'Customer ID': 'customer_id',
    'CustomerID': 'customer_id', 'Country': 'country'
}
CODIGOS_NO_PRODUCTO = ['POST', 'DOT', 'M', 'BANK CHARGES', 'AMAZONFEE', 'B', 'CRUK',
                       'ADJUST', 'ADJUST2', 'D', 'C2', '23444', '23574', 'S',
                       'TEST001', 'TEST002']
PERCENTIL_MAYORISTA = 0.95
MULTIPLO_BULK = 6
MIN_PRODUCTOS_BULK = 5
VENTANA_CANCELACION_HORAS = 6  # validado: la densidad de coincidencias cae al nivel de ruido después de esto

def cargar_datos(path) -> pd.DataFrame:
    """Carga el dataset desde .xlsx, .csv o .parquet y normaliza nombres de columna.

    Detecta el formato por extensión. Si ya es .parquet, asume que pasó por
    normalizar_tipos() antes y lo devuelve tal cual, sin volver a renombrar.
    Para .xlsx con 2 hojas, saca de la segunda las facturas que se solapan
    con la primera (confirmado: 1.088 facturas de diciembre 2010 aparecen
    en ambas) — si no, la suma de duplicados más adelante las cuenta doble.
    Solo se sacan si son copias idénticas; si no, se dejan las dos y hay
    que revisar a mano.
    """
    path = Path(path)
    if path.suffix in ('.xlsx', '.xls'):
        hojas = [h.rename(columns=RENAME) for h in pd.read_excel(path, sheet_name=None).values()]
        if len(hojas) == 2:
            comunes = set(hojas[0]['invoice_no']) & set(hojas[1]['invoice_no'])
            if comunes:
                cols = list(hojas[0].columns)
                d0 = hojas[0][hojas[0]['invoice_no'].isin(comunes)].sort_values(cols).reset_index(drop=True)
                d1 = hojas[1][hojas[1]['invoice_no'].isin(comunes)].sort_values(cols).reset_index(drop=True)
                if d0.equals(d1):
                    hojas[1] = hojas[1][~hojas[1]['invoice_no'].isin(comunes)]
        return pd.concat(hojas, ignore_index=True)
    elif path.suffix == '.csv':
        return pd.read_csv(path).rename(columns=RENAME)
    elif path.suffix == '.parquet':
        return pd.read_parquet(path)
    else:
        raise ValueError(f'Formato no soportado: {path.suffix}')

def normalizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Fuerza tipos de dato consistentes en las columnas clave.

    Sin esto, al releer un CSV invoice_date vuelve a ser texto y customer_id
    vuelve a ser float (mostrando 13085.0 en vez de 13085).
    """
    df = df.copy()
    for col in ['invoice_no', 'stock_code', 'description', 'country']:
        df[col] = df[col].astype('string').str.strip()
    df['stock_code'] = df['stock_code'].str.upper()  # 85123a y 85123A son el mismo producto
    df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce')
    df['customer_id'] = pd.to_numeric(df['customer_id'], errors='coerce').astype('Int64')
    return df

def limpiar_datos(df: pd.DataFrame, conservar_sin_cliente: bool = False, ventana_cancelacion_horas: float = VENTANA_CANCELACION_HORAS):
    """Aplica los filtros de calidad de datos y devuelve (df_limpio, log).

    Filtros, en orden: compras con cancelación exacta dentro de la ventana
    (mismo cliente, producto y cantidad, cancelada pocas horas después —
    el caso real encontrado fue de 12 minutos; 6 horas es donde la
    densidad de coincidencias cae al nivel de ruido de fondo, medido
    sobre el dataset real), cancelaciones, cantidad/precio positivos,
    códigos no-producto, duplicados (sumando quantity en vez de descartar
    filas, para no perder unidades reales), descripción no vacía, y
    customer_id (salvo conservar_sin_cliente=True: el modelo de
    recomendación no necesita saber quién compró, solo RFM y mayoristas
    lo necesitan).

    El log devuelto es la tabla "antes y después" para el README.
    """
    log = []
    def _paso(nombre, df):
        log.append({'paso': nombre, 'filas': len(df), 'facturas': df['invoice_no'].nunique()})

    _paso('inicial', df)

    # Compras que en realidad nunca se concretaron: tienen su cancelación
    # exacta (mismo cliente, producto, cantidad) pocas horas después.
    # Se excluyen las filas sin customer_id: pandas trata NaN == NaN como
    # un match al cruzar tablas, lo que emparejaría compras y cancelaciones
    # de clientes anónimos DISTINTOS solo por compartir producto y cantidad.
    con_cliente = df['customer_id'].notna()
    cancelaciones = df[df['invoice_no'].str.startswith('C').fillna(False) & con_cliente][
        ['customer_id', 'stock_code', 'quantity', 'invoice_date']
    ].copy()
    cancelaciones['quantity'] = cancelaciones['quantity'].abs()
    compras = df[~df['invoice_no'].str.startswith('C').fillna(False) & con_cliente].copy()
    compras['_idx_original'] = compras.index
    match = compras.merge(cancelaciones, on=['customer_id', 'stock_code', 'quantity'], suffixes=('', '_cancelacion'))
    match['horas'] = (match['invoice_date_cancelacion'] - match['invoice_date']).dt.total_seconds() / 3600
    indices_canceladas = match.loc[
        (match['horas'] > 0) & (match['horas'] <= ventana_cancelacion_horas), '_idx_original'
    ].unique()
    df = df.drop(index=indices_canceladas)
    _paso('sin compras con cancelación exacta', df)

    df = df[~df['invoice_no'].str.startswith('C').fillna(False)]
    _paso('sin cancelaciones', df)
    df = df[(df['quantity'] > 0) & (df['unit_price'] > 0)]
    _paso('cantidad y precio > 0', df)
    df = df[~df['stock_code'].isin(CODIGOS_NO_PRODUCTO)]
    _paso('sin códigos no-producto', df)
    columnas_excepto_cantidad = [c for c in df.columns if c != 'quantity']
    df = df.groupby(columnas_excepto_cantidad, as_index=False, dropna=False)['quantity'].sum()
    _paso('sin duplicados (cantidades sumadas)', df)
    df = df.dropna(subset=['description'])
    _paso('sin descripción vacía', df)
    if not conservar_sin_cliente:
        df = df.dropna(subset=['customer_id'])
        _paso('con customer_id', df)
    return df.reset_index(drop=True), pd.DataFrame(log)

def segmentar_clientes(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega la columna 'segmento': mayorista, minorista o sin_cliente.

    Mayorista = por encima del percentil 95 de unidades totales compradas.
    """
    df = df.copy()
    unidades = df.groupby('customer_id')['quantity'].sum()
    umbral = unidades.quantile(PERCENTIL_MAYORISTA)
    mayoristas = unidades[unidades > umbral].index
    df['segmento'] = 'minorista'
    df.loc[df['customer_id'].isin(mayoristas), 'segmento'] = 'mayorista'
    df.loc[df['customer_id'].isna(), 'segmento'] = 'sin_cliente'
    return df

def marcar_facturas_bulk(df: pd.DataFrame, proporcion_minima: float = 0.8) -> pd.DataFrame:
    """Agrega 'factura_bulk': True si la factura parece reposición al por mayor.

    Se mide por proporción de líneas en múltiplos de 6 (no el 100%: una
    sola excepción en una factura de 1.110 productos no debería descartarla)
    y un mínimo de productos distintos, para no marcar como bulk una
    factura de 1 sola línea. Umbral 0.8 validado contra la distribución
    real (da 7,1% de las facturas).
    """
    df = df.copy()
    proporcion_multiplo = (df['quantity'] % MULTIPLO_BULK == 0).groupby(df['invoice_no']).transform('mean')
    n_productos = df.groupby('invoice_no')['stock_code'].transform('nunique')
    df['factura_bulk'] = (proporcion_multiplo >= proporcion_minima) & (n_productos >= MIN_PRODUCTOS_BULK)
    return df

def catalogo_productos(df: pd.DataFrame) -> pd.DataFrame:
    """Arma una fila por producto, con su descripción más frecuente y precio típico.

    Precio típico = mediana, no promedio: el mismo producto se vende a
    precios distintos según la fecha, y la mediana no se deja arrastrar
    por un outlier.
    """
    return df.dropna(subset=['description']).groupby('stock_code').agg(
        description=('description', lambda s: s.value_counts().idxmax()),
        precio=('unit_price', 'median')
    ).reset_index()

def pipeline_completo(path_entrada: str, path_salida: str = 'data/processed/online_retail_clean.parquet', conservar_sin_cliente: bool = False):
    """Corre todo el proceso: cargar, limpiar, segmentar, marcar bulk y guardar.

    Imprime el log de limpieza y devuelve (df_final, log).
    """
    df = normalizar_tipos(cargar_datos(path_entrada))
    df, log = limpiar_datos(df, conservar_sin_cliente=conservar_sin_cliente)
    df = marcar_facturas_bulk(segmentar_clientes(df))
    Path(path_salida).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path_salida, index=False)
    print(pd.DataFrame(log).to_string(index=False))
    return df, log

if __name__ == '__main__':
    pipeline_completo('data/raw/online_retail_II.xlsx', 'data/processed/online_retail_rfm.parquet')
    pipeline_completo('data/raw/online_retail_II.xlsx', 'data/processed/online_retail_modelo.parquet', conservar_sin_cliente=True)