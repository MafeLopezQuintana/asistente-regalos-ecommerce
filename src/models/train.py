"""
Matriz factura-producto y modelos de recomendación.

  - construir_matriz: matriz binaria factura x producto (base del item-item y del SVD).
  - Popularidad: el baseline contra el que se comparan los demás modelos.
  - filtrar_para_entrenar: filtros de facturas y productos previos al item-item y al SVD.
  - ItemItem: KNN entre productos por co-compra (similitud coseno).
  - SVD: factores latentes de productos sobre la matriz factura x producto.

Todos los modelos exponen la misma interfaz:
    fit(df_train) -> self
    recomendar(anclas, k) -> lista de stock_code (sin incluir las anclas)
    get_params() -> dict con sus parámetros (para MLflow)
    n_productos -> cantidad de productos que conoce (para la cobertura)
"""
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD

# Contrato de datos definido en src/data/clean.py (snake_case)
COL_FACTURA = "invoice_no"
COL_PRODUCTO = "stock_code"
COL_CLIENTE = "customer_id"
COL_CANTIDAD = "quantity"
COL_BULK = "factura_bulk"


# ---------------------------------------------------------------------------
# Matriz factura-producto
# ---------------------------------------------------------------------------
def construir_matriz(df, col_factura=COL_FACTURA, col_producto=COL_PRODUCTO):
    """Matriz binaria: fila = factura, columna = producto, 1 si estuvo en la factura.

    Es dispersa (scipy.sparse): solo guarda los 1. Una tabla común de ~31.000
    facturas x ~4.600 productos ocuparía más de 1 GB, casi todo ceros.

    Devuelve (matriz, lista_de_facturas, lista_de_productos). El índice de cada
    lista coincide con la fila o columna de la matriz. Los productos quedan
    ordenados por código.
    """
    facturas = pd.Categorical(df[col_factura])
    productos = pd.Categorical(df[col_producto])

    matriz = sparse.csr_matrix(
        (np.ones(len(df), dtype=np.float32), (facturas.codes, productos.codes)),
        shape=(len(facturas.categories), len(productos.categories)),
    )
    matriz.sum_duplicates()
    matriz.data[:] = 1.0  # binaria: presencia, no cantidad (decisión del equipo)

    return matriz, list(facturas.categories), list(productos.categories)


# ---------------------------------------------------------------------------
# Baseline: popularidad
# ---------------------------------------------------------------------------
class Popularidad:
    """Recomienda siempre los productos más populares, salvo los que ya están en las anclas.

    criterio="facturas":  en cuántas facturas distintas aparece (coherente con la
                          matriz binaria: un pedido de 500 unidades cuenta como uno de 1).
    criterio="ponderada": unidades vendidas x clientes distintos (versión de la guía;
                          sigue influida por las compras mayoristas porque usa unidades).
    """

    def __init__(self, criterio="facturas"):
        if criterio not in ("facturas", "ponderada"):
            raise ValueError("criterio debe ser 'facturas' o 'ponderada'")
        self.criterio = criterio
        self.ranking = []
        self.n_productos = 0

    def get_params(self):
        return {"modelo": "popularidad", "criterio": self.criterio}

    def fit(self, df, col_factura=COL_FACTURA, col_producto=COL_PRODUCTO,
            col_cliente=COL_CLIENTE, col_cantidad=COL_CANTIDAD):
        if self.criterio == "facturas":
            score = df.groupby(col_producto)[col_factura].nunique()
        else:
            stats = df.groupby(col_producto).agg(
                unidades=(col_cantidad, "sum"),
                clientes=(col_cliente, "nunique"),
            )
            score = stats["unidades"] * stats["clientes"]

        # Desempate por código, para que el ranking sea siempre el mismo
        tabla = score.rename("score").reset_index()
        tabla = tabla.sort_values(["score", col_producto], ascending=[False, True])
        self.ranking = tabla[col_producto].tolist()
        self.n_productos = len(self.ranking)
        return self

    def recomendar(self, anclas, k=5, excluir=()):
        bloqueados = set(anclas) | set(excluir)
        recs = []
        for producto in self.ranking:
            if producto not in bloqueados:
                recs.append(producto)
                if len(recs) == k:
                    break
        return recs


# ---------------------------------------------------------------------------
# Filtros previos al entrenamiento (compartidos por item-item y SVD)
# ---------------------------------------------------------------------------
def filtrar_para_entrenar(df, min_facturas=5, max_productos_factura=None, excluir_bulk=False,
                          col_factura=COL_FACTURA, col_producto=COL_PRODUCTO):
    """Deja solo las facturas y productos con los que se entrena el modelo.

    - excluir_bulk: saca las facturas marcadas como factura_bulk. Si se pide y la
      columna no existe, da error (antes se ignoraba en silencio y el resultado
      parecía "sin bulk" cuando en realidad las incluía).
    - max_productos_factura: saca las facturas con más productos distintos que ese tope.
    - min_facturas: deja los productos que aparecen en al menos esa cantidad de facturas.
    """
    datos = df
    if excluir_bulk:
        if COL_BULK not in datos.columns:
            raise ValueError(f"excluir_bulk=True necesita la columna '{COL_BULK}' "
                             "(la genera src/data/clean.py)")
        datos = datos[~datos[COL_BULK].astype(bool)]
    if max_productos_factura is not None:
        tam = datos.groupby(col_factura)[col_producto].transform("nunique")
        datos = datos[tam <= max_productos_factura]

    apariciones = datos.groupby(col_producto)[col_factura].nunique()
    frecuentes = apariciones.index[apariciones >= min_facturas]
    return datos[datos[col_producto].isin(frecuentes)]


# ---------------------------------------------------------------------------
# Item-item: KNN entre productos por co-compra
# ---------------------------------------------------------------------------
class ItemItem:
    """Recomienda los productos que más se compran junto con las anclas.

    Similitud coseno entre columnas de la matriz binaria:
        similitud(A, B) = facturas con A y B juntos / raíz(facturas con A x facturas con B)
    Para varias anclas (modo carrito) se suman sus similitudes.

    Parámetros:
      min_facturas: cantidad mínima de facturas en las que debe aparecer un producto.
          El valor 5 es un valor inicial por defecto, no un hiperparámetro óptimo.
          El valor definitivo debe seleccionarse mediante validación cruzada temporal.
          También evita similitudes altas entre productos raros que coincidieron
          pocas veces por casualidad.

      max_productos_factura: si se indica, ignora facturas con más productos distintos
          (pedidos de reposición de medio catálogo generan pares sin relación real).

      excluir_bulk: si True, ignora las facturas marcadas como factura_bulk.

      completar_con_popularidad: si el ancla no tiene vecinos suficientes
          (producto raro o sin co-compras), completa el top k con los más populares.
    
    """

    def __init__(self, min_facturas=5, max_productos_factura=None, excluir_bulk=False,
                 completar_con_popularidad=True):
        self.min_facturas = min_facturas
        self.max_productos_factura = max_productos_factura
        self.excluir_bulk = excluir_bulk
        self.completar_con_popularidad = completar_con_popularidad
        self.similitud = None
        self.productos = []
        self._posicion = {}
        self._popularidad = None
        self.n_productos = 0

    def get_params(self):
        return {
            "modelo": "item_item",
            "min_facturas": self.min_facturas,
            "max_productos_factura": self.max_productos_factura,
            "excluir_bulk": self.excluir_bulk,
            "completar_con_popularidad": self.completar_con_popularidad,
        }

    def fit(self, df, col_factura=COL_FACTURA, col_producto=COL_PRODUCTO):
        # El respaldo y la cobertura usan TODOS los productos de train,
        # igual que el baseline, para que la comparación sea justa.
        self._popularidad = Popularidad("facturas").fit(df, col_factura, col_producto)
        self.n_productos = self._popularidad.n_productos

        datos = filtrar_para_entrenar(df, self.min_facturas, self.max_productos_factura,
                                      self.excluir_bulk, col_factura, col_producto)

        matriz, _, self.productos = construir_matriz(datos, col_factura, col_producto)
        self._posicion = {p: i for i, p in enumerate(self.productos)}

        # Coseno sobre columnas binarias: normalizar cada columna y multiplicar
        normas = np.sqrt(np.asarray(matriz.sum(axis=0)).ravel())
        normas[normas == 0] = 1.0
        normalizada = matriz @ sparse.diags(1.0 / normas)
        similitud = (normalizada.T @ normalizada).tocsr()
        similitud.setdiag(0)          # un producto no es vecino de sí mismo
        similitud.eliminate_zeros()
        self.similitud = similitud
        return self

    def recomendar(self, anclas, k=5):
        indices = [self._posicion[a] for a in anclas if a in self._posicion]
        recs = []
        if indices:
            puntajes = np.asarray(self.similitud[indices].sum(axis=0)).ravel()
            puntajes[indices] = 0.0
            # stable: a igual puntaje, desempata por código (los productos están ordenados)
            orden = np.argsort(-puntajes, kind="stable")
            for i in orden[:k]:
                if puntajes[i] <= 0:
                    break
                recs.append(self.productos[i])

        if self.completar_con_popularidad and len(recs) < k:
            recs += self._popularidad.recomendar(anclas, k=k - len(recs), excluir=recs)
        return recs

# ---------------------------------------------------------------------------
# SVD: factores latentes de productos
# ---------------------------------------------------------------------------
class SVD:
    """
   Parámetros:
    n_components: cantidad de factores latentes a conservar.
        El valor definido por defecto es inicial y no representa necesariamente
        la configuración óptima. El valor definitivo se seleccionará mediante
        validación cruzada temporal.

    min_facturas: cantidad mínima de facturas en las que debe aparecer un producto
        para ingresar al espacio latente. El valor por defecto es inicial y debe
        validarse mediante cross-validation temporal.

    max_productos_factura: si se indica, ignora facturas con más productos
        distintos que ese límite. Su conveniencia puede evaluarse durante
        la validación temporal.

    excluir_bulk: si True, ignora las facturas marcadas como factura_bulk.
        La inclusión o exclusión de estas facturas se comparará mediante
        validación temporal.

    completar_con_popularidad: completa el top k cuando no hay suficientes
        candidatos latentes o cuando el ancla es desconocida.

    random_state: semilla de TruncatedSVD para obtener resultados reproducibles.
"""

    def __init__(self, n_components=50, min_facturas=5,
                 max_productos_factura=None, excluir_bulk=False,
                 completar_con_popularidad=True, random_state=42):
        if n_components < 1:
            raise ValueError("n_components debe ser >= 1")
        self.n_components = n_components
        self.min_facturas = min_facturas
        self.max_productos_factura = max_productos_factura
        self.excluir_bulk = excluir_bulk
        self.completar_con_popularidad = completar_con_popularidad
        self.random_state = random_state

        self.productos = []
        self._posicion = {}
        self._popularidad = None
        self._svd = None
        self._embeddings = None
        self.n_componentes_efectivos = 0
        self.varianza_explicada = 0.0
        self.n_productos = 0

    def get_params(self):
        return {
            "modelo": "svd",
            "n_components": self.n_components,
            "min_facturas": self.min_facturas,
            "max_productos_factura": self.max_productos_factura,
            "excluir_bulk": self.excluir_bulk,
            "completar_con_popularidad": self.completar_con_popularidad,
            "random_state": self.random_state,
        }

    def fit(self, df, col_factura=COL_FACTURA, col_producto=COL_PRODUCTO):
        # Mismo respaldo y denominador de cobertura que Popularidad e ItemItem.
        self._popularidad = Popularidad("facturas").fit(df, col_factura, col_producto)
        self.n_productos = self._popularidad.n_productos

        datos = filtrar_para_entrenar(df, self.min_facturas, self.max_productos_factura,
                                      self.excluir_bulk, col_factura, col_producto)

        if datos.empty:
            self.productos = []
            self._posicion = {}
            self._svd = None
            self._embeddings = None
            self.n_componentes_efectivos = 0
            self.varianza_explicada = 0.0
            return self

        matriz, _, self.productos = construir_matriz(datos, col_factura, col_producto)
        self._posicion = {p: i for i, p in enumerate(self.productos)}

        # El rango útil no puede superar la menor dimensión de la matriz.
        max_componentes = min(matriz.shape) - 1
        if max_componentes < 1:
            self._svd = None
            self._embeddings = None
            self.n_componentes_efectivos = 0
            self.varianza_explicada = 0.0
            return self

        n_eff = min(self.n_components, max_componentes)
        self.n_componentes_efectivos = n_eff
        self._svd = TruncatedSVD(
            n_components=n_eff,
            algorithm="randomized",
            random_state=self.random_state,
        )
        self._svd.fit(matriz)

        # components_.T = V; multiplicar por los valores singulares da V * Sigma,
        # las coordenadas de cada producto en el espacio latente truncado.
        embeddings = self._svd.components_.T * self._svd.singular_values_

        # Normalización L2 para que producto punto == similitud coseno.
        normas = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normas[normas == 0] = 1.0
        self._embeddings = embeddings / normas
        self.varianza_explicada = float(self._svd.explained_variance_ratio_.sum())
        return self

    def recomendar(self, anclas, k=5):
        indices = [self._posicion[a] for a in anclas if a in self._posicion]
        recs = []

        if indices and self._embeddings is not None:
            # Cada embedding está normalizado. Sumar los productos punto equivale
            # a sumar la similitud coseno con cada ancla, como hace ItemItem.
            puntajes = self._embeddings @ self._embeddings[indices].T
            puntajes = np.asarray(puntajes.sum(axis=1)).ravel()
            puntajes[indices] = -np.inf

            orden = np.argsort(-puntajes, kind="stable")
            for i in orden:
                if not np.isfinite(puntajes[i]):
                    continue
                # En el espacio latente puede haber similitudes negativas; para
                # recomendaciones exigimos afinidad positiva.
                if puntajes[i] <= 0:
                    break
                recs.append(self.productos[i])
                if len(recs) == k:
                    break

        if self.completar_con_popularidad and len(recs) < k:
            recs += self._popularidad.recomendar(
                anclas, k=k - len(recs), excluir=recs
            )
        return recs

