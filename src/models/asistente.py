"""
Asistente de regalos: el modelo final que usa la app de Streamlit.

El modelo elegido (item-item, ver README sección 4) se reentrena con TODOS los
datos y se congela en models/modelo_final.pkl. El archivo no guarda el objeto
ItemItem completo sino lo que la app necesita, con tipos simples (DataFrames):
  - vecinos: los 20 productos que más se compran con cada producto, con su
    similitud y en cuántos pedidos se compraron juntos (para el "por qué").
  - popularidad: en cuántos pedidos aparece cada producto (respaldo cuando no
    hay producto de referencia o no alcanzan los vecinos).
  - parámetros, métricas de referencia y fechas de los datos, para saber qué
    versión del modelo está usando la app.

buscar_ideas_regalo recibe las respuestas del cuestionario tal como las guarda
app.py (st.session_state["resumen_preferencias"]) y devuelve las sugerencias
con el motivo por el que aparece cada una.

armar_combos usa las mismas respuestas y arma combos de productos que se
compran juntos, cuyo total entra en el rango de presupuesto.

Uso, desde la raíz del repo:
    python -m src.models.asistente
"""
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.evaluate import COL_FACTURA, COL_FECHA, COL_PRODUCTO, cargar_datos_modelo
from src.models.train import ItemItem, construir_matriz, filtrar_para_entrenar

# Rutas ancladas a la raíz del repo (src/models/ -> parents[2]), así funcionan
# igual desde la terminal, desde notebooks/ o desde Streamlit.
RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_MODELO = RAIZ_REPO / "models" / "modelo_final.pkl"
RUTA_CATALOGO = RAIZ_REPO / "models" / "catalogo_app.parquet"

# Configuración elegida en la validación cruzada temporal (README, sección 4)
PARAMS_MODELO = {"min_facturas": 5, "max_productos_factura": 200}
# Resultado del modelo elegido en el test final (README, sección 4)
METRICAS_REFERENCIA = {"hit_rate_at_5": 0.084, "ndcg_at_5": 0.059, "cobertura_catalogo": 0.616}
TOP_VECINOS = 20

# Reglas de negocio del asistente
INTERES_SORPRENDEME = "¡Sorprendeme!"
# Precios por debajo de este valor son precios unitarios de productos que se venden
# en packs (lápices a £0,04): no se muestran como regalo.
PRECIO_MINIMO_REGALO = 0.50
# Supuesto documentado: el dataset no tiene la ocasión de compra. "Navidad / Fiestas"
# suma el interés Fiestas y celebraciones a los elegidos; las demás ocasiones no filtran.
INTERESES_POR_OCASION = {"Navidad / Fiestas": "Fiestas y celebraciones"}

# Combos: cantidad de productos buscada y máxima (se suman más solo si el total
# todavía no llega al mínimo del rango de presupuesto).
PRODUCTOS_POR_COMBO = 3
MAXIMO_PRODUCTOS_COMBO = 5
# Dos productos cuyas descripciones comparten este porcentaje de palabras o más
# se consideran variantes del mismo producto (WHITE / RED HANGING HEART T-LIGHT
# HOLDER comparten 4 de 6 palabras) y no van juntos en un combo.
UMBRAL_VARIANTE = 0.5
# Si ningún combo llega al mínimo del rango (ej.: £15 con productos de £2), se aceptan
# los que llegan al menos a esta fracción del mínimo, como opción más cercana.
FRACCION_MINIMA_COMBO = 0.5

FUENTE_CO_COMPRA = "co-compra"
FUENTE_POPULARIDAD = "popularidad"
FUENTE_REFERENCIA = "referencia"
COLUMNAS_SALIDA = ["stock_code", "description", "price", "interes", "motivo", "fuente"]
COLUMNAS_COMBOS = ["combo"] + COLUMNAS_SALIDA + ["total_combo"]


# ---------------------------------------------------------------------------
# Modelo final
# ---------------------------------------------------------------------------
def _tabla_vecinos(modelo, conteos, top):
    """Los `top` vecinos de cada producto según la similitud del item-item."""
    similitud = modelo.similitud.tocsr()
    filas = []
    for i, producto in enumerate(modelo.productos):
        inicio, fin = similitud.indptr[i], similitud.indptr[i + 1]
        columnas, valores = similitud.indices[inicio:fin], similitud.data[inicio:fin]
        if len(valores) == 0:
            continue
        # A igual similitud desempata por código (los productos están ordenados)
        orden = np.lexsort((columnas, -valores))[:top]
        for rango, j in enumerate(orden, start=1):
            vecino = columnas[j]
            filas.append((producto, modelo.productos[vecino], float(valores[j]),
                          int(conteos[i, vecino]), rango))
    return pd.DataFrame(filas, columns=["stock_code", "vecino", "similitud", "co_compras", "rango"])


def construir_modelo_final(df, params=None, top=TOP_VECINOS, metricas=None):
    """Entrena el item-item con `df` y arma el diccionario que se guarda en el .pkl."""
    params = {**PARAMS_MODELO, **(params or {})}
    modelo = ItemItem(**params).fit(df)

    # Pedidos en los que cada par se compró junto, sobre los mismos datos filtrados
    # con los que se calculó la similitud.
    datos = filtrar_para_entrenar(df, params["min_facturas"], params.get("max_productos_factura"),
                                  params.get("excluir_bulk", False))
    matriz, _, productos = construir_matriz(datos)
    assert productos == modelo.productos
    conteos = (matriz.T @ matriz).tocsr()

    popularidad = (df.groupby(COL_PRODUCTO)[COL_FACTURA].nunique().rename("pedidos")
                   .reset_index().sort_values(["pedidos", COL_PRODUCTO], ascending=[False, True])
                   .reset_index(drop=True))

    return {
        "version": 1,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "parametros": modelo.get_params(),
        "metricas_referencia": metricas if metricas is not None else METRICAS_REFERENCIA,
        "datos": {
            "facturas": int(df[COL_FACTURA].nunique()),
            "desde": str(pd.to_datetime(df[COL_FECHA]).min().date()) if COL_FECHA in df else None,
            "hasta": str(pd.to_datetime(df[COL_FECHA]).max().date()) if COL_FECHA in df else None,
        },
        "vecinos": _tabla_vecinos(modelo, conteos, top),
        "popularidad": popularidad,
    }


def guardar_modelo_final(modelo_final, ruta=RUTA_MODELO):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Las claves con "_" son índices que se arman en memoria al usar el modelo
    with open(ruta, "wb") as f:
        pickle.dump({k: v for k, v in modelo_final.items() if not k.startswith("_")}, f)
    return ruta


def cargar_modelo_final(ruta=RUTA_MODELO):
    """Lee models/modelo_final.pkl (en la app, cargarlo una sola vez con st.cache_resource)."""
    with open(ruta, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Sugerencias para la app
# ---------------------------------------------------------------------------
def _intereses_validos(resumen):
    """Intereses que se aceptan, o None si no se filtra por interés."""
    elegidos = set(resumen.get("intereses") or [])
    if not elegidos or INTERES_SORPRENDEME in elegidos:
        return None
    extra = INTERESES_POR_OCASION.get(resumen.get("ocasion"))
    return elegidos | {extra} if extra else elegidos


def _filtrar_catalogo(catalogo, resumen):
    """Productos del catálogo que cumplen presupuesto e intereses."""
    minimo = max(float(resumen.get("precio_minimo") or 0), PRECIO_MINIMO_REGALO)
    maximo = float(resumen.get("precio_maximo") or np.inf)
    filtrado = catalogo[catalogo["price"].between(minimo, maximo)]
    validos = _intereses_validos(resumen)
    if validos is not None:
        filtrado = filtrado[filtrado["interes"].isin(validos)]
    return filtrado


def buscar_ideas_regalo(resumen, catalogo, modelo_final, k=5):
    """Sugerencias de regalo para las respuestas del cuestionario.

    resumen : dict
        El que guarda app.py en st.session_state["resumen_preferencias"]. Usa
        precio_minimo, precio_maximo, intereses, ocasion y producto_codigo.
    catalogo : DataFrame
        models/catalogo_app.parquet (stock_code, description, price, interes).
    modelo_final : dict
        El de cargar_modelo_final().

    Primero van los productos que más se compran con el producto de referencia
    (fuente "co-compra"); si no hay referencia o no alcanzan, se completa con
    los más vendidos que cumplen los filtros (fuente "popularidad"). Se saltean
    las variantes del producto de referencia (el mismo producto en otro color). Devuelve
    hasta k filas con COLUMNAS_SALIDA; vacío si nada entra en el presupuesto.
    """
    candidatos = _filtrar_catalogo(catalogo, resumen).set_index("stock_code")
    referencia = resumen.get("producto_codigo")
    elegidos, filas = {referencia}, []
    nombre = catalogo.loc[catalogo["stock_code"] == referencia, "description"]
    nombre = nombre.iloc[0] if len(nombre) else referencia

    def agregar(codigo, motivo, fuente):
        if codigo in elegidos or codigo not in candidatos.index or len(filas) >= k:
            return
        # El mismo producto en otro color no es una idea nueva (ej.: WHITE / RED HANGING HEART)
        if referencia and _es_variante(candidatos.at[codigo, "description"], nombre):
            return
        producto = candidatos.loc[codigo]
        filas.append({"stock_code": codigo, "description": producto["description"],
                      "price": float(producto["price"]), "interes": producto["interes"],
                      "motivo": motivo, "fuente": fuente})
        elegidos.add(codigo)

    if referencia:
        vecinos = modelo_final["vecinos"]
        vecinos = vecinos[vecinos["stock_code"] == referencia].sort_values("rango")
        for fila in vecinos.itertuples():
            pedidos = "1 pedido" if fila.co_compras == 1 else f"{fila.co_compras} pedidos"
            agregar(fila.vecino, f"Se compra junto con {nombre} (en {pedidos})", FUENTE_CO_COMPRA)

    for codigo in modelo_final["popularidad"]["stock_code"]:
        if len(filas) >= k:
            break
        if codigo in candidatos.index:
            interes = candidatos.at[codigo, "interes"]
            donde = "de la tienda" if interes == INTERES_SORPRENDEME else f"en {interes}"
            agregar(codigo, f"Uno de los más vendidos {donde}", FUENTE_POPULARIDAD)

    return pd.DataFrame(filas, columns=COLUMNAS_SALIDA)


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------
def _indices(modelo_final):
    """Dos índices de la tabla de vecinos, armados una vez y guardados en memoria:
    pares {(producto, vecino): (similitud, co_compras)} y vecinos_de {producto: [(vecino, similitud)]}.
    """
    if "_pares" not in modelo_final:
        v = modelo_final["vecinos"]
        pares, vecinos_de = {}, {}
        for a, b, sim, co in zip(v["stock_code"], v["vecino"], v["similitud"], v["co_compras"]):
            pares[(a, b)] = (sim, co)
            vecinos_de.setdefault(a, []).append((b, sim))
        modelo_final["_pares"], modelo_final["_vecinos_de"] = pares, vecinos_de
    return modelo_final["_pares"], modelo_final["_vecinos_de"]


def _par(pares, a, b):
    """Similitud y pedidos juntos de un par (0 si ninguno está en el top del otro)."""
    return pares.get((a, b)) or pares.get((b, a)) or (0.0, 0)


def _es_variante(desc_a, desc_b, umbral=UMBRAL_VARIANTE):
    """True si las descripciones comparten tantas palabras que son el mismo producto."""
    a, b = set(str(desc_a).upper().split()), set(str(desc_b).upper().split())
    return bool(a | b) and len(a & b) / len(a | b) >= umbral


def armar_combos(resumen, catalogo, modelo_final, n_combos=3,
                 productos_por_combo=PRODUCTOS_POR_COMBO):
    """Combos de productos que se compran juntos, con el total dentro del presupuesto.

    Cada combo arranca de un producto distinto (el de referencia, si entra en el
    presupuesto, y después las sugerencias de buscar_ideas_regalo) y suma de a
    uno el candidato que más se compra con los ya elegidos, siempre que el total
    no supere el máximo y no sea una variante de otro producto del combo. Si se
    acaban los vecinos, completa con los más vendidos. Se queda con los combos
    de 2 o más productos cuyo total cae dentro del rango; si ninguno llega al
    mínimo, devuelve los más cercanos (desde la mitad del mínimo y nunca por
    encima del máximo). Los combos no comparten productos ni arrancan de
    variantes del mismo producto.

    Devuelve una fila por producto con COLUMNAS_COMBOS (vacío si no se pudo
    armar ninguno).
    """
    minimo = float(resumen.get("precio_minimo") or 0)
    maximo = float(resumen.get("precio_maximo") or np.inf)
    # Para los productos sueltos del combo vale cualquier precio hasta el máximo
    candidatos = _filtrar_catalogo(catalogo, {**resumen, "precio_minimo": 0}).set_index("stock_code")
    pares, vecinos_de = _indices(modelo_final)
    populares = [c for c in modelo_final["popularidad"]["stock_code"] if c in candidatos.index]

    def fila(codigo, motivo, fuente):
        producto = candidatos.loc[codigo]
        return {"stock_code": codigo, "description": producto["description"],
                "price": float(producto["price"]), "interes": producto["interes"],
                "motivo": motivo, "fuente": fuente}

    semillas = []
    referencia = resumen.get("producto_codigo")
    if referencia in candidatos.index:
        semillas.append((referencia, "Producto de referencia", FUENTE_REFERENCIA))
    ideas = buscar_ideas_regalo({**resumen, "precio_minimo": 0}, catalogo, modelo_final, k=10)
    semillas += list(zip(ideas["stock_code"], ideas["motivo"], ideas["fuente"]))

    combos, cercanos, usados = [], [], set()
    for codigo, motivo, fuente in semillas:
        if len(combos) >= n_combos:
            break
        # Cada combo arranca de un producto nuevo, que no sea variante de uno ya usado
        if codigo in usados or any(_es_variante(candidatos.at[codigo, "description"],
                                                candidatos.at[u, "description"]) for u in usados):
            continue
        combo = [fila(codigo, motivo, fuente)]
        total = combo[0]["price"]

        while len(combo) < MAXIMO_PRODUCTOS_COMBO and (len(combo) < productos_por_combo or total < minimo):
            elegidos = {f["stock_code"] for f in combo}
            # Candidatos: vecinos de los elegidos, con puntaje = suma de similitudes
            puntajes = {}
            for e in elegidos:
                for b, sim in vecinos_de.get(e, []):
                    if b not in elegidos and b in candidatos.index:
                        puntajes[b] = puntajes.get(b, 0.0) + sim
            orden = sorted(puntajes, key=lambda c: (-puntajes[c], c)) + populares
            siguiente = None
            for c in orden:
                # Tampoco repite productos de otros combos, así cada combo es distinto
                if c in elegidos or c in usados or total + candidatos.at[c, "price"] > maximo:
                    continue
                if any(_es_variante(candidatos.at[c, "description"], f["description"]) for f in combo):
                    continue
                siguiente = c
                break
            if siguiente is None:
                break
            if siguiente in puntajes:
                socio = max(elegidos, key=lambda e: _par(pares, e, siguiente)[0])
                pedidos = _par(pares, socio, siguiente)[1]
                nombre = candidatos.at[socio, "description"]
                texto = "1 pedido" if pedidos == 1 else f"{pedidos} pedidos"
                combo.append(fila(siguiente, f"Se compra junto con {nombre} (en {texto})",
                                  FUENTE_CO_COMPRA))
            else:
                combo.append(fila(siguiente, "Uno de los más vendidos para completar el combo",
                                  FUENTE_POPULARIDAD))
            total += combo[-1]["price"]

        if len(combo) >= 2:
            if total >= minimo:
                combos.append(combo)
            elif total >= minimo * FRACCION_MINIMA_COMBO:
                cercanos.append(combo)
            usados |= {f["stock_code"] for f in combo}

    # Si ningún combo llega al mínimo del rango, se devuelven los más cercanos
    # (al menos la mitad del mínimo y nunca por encima del máximo).
    combos = combos or sorted(cercanos, key=lambda c: -sum(f["price"] for f in c))[:n_combos]
    filas = []
    for numero, combo in enumerate(combos, start=1):
        total = round(sum(f["price"] for f in combo), 2)
        filas += [{"combo": numero, **f, "total_combo": total} for f in combo]
    return pd.DataFrame(filas, columns=COLUMNAS_COMBOS)


# ---------------------------------------------------------------------------
def main():
    df = cargar_datos_modelo()
    modelo_final = construir_modelo_final(df)
    ruta = guardar_modelo_final(modelo_final)

    vecinos = modelo_final["vecinos"]
    print(f"Modelo final: item-item {PARAMS_MODELO}, entrenado con "
          f"{modelo_final['datos']['facturas']:,} facturas "
          f"({modelo_final['datos']['desde']} a {modelo_final['datos']['hasta']})")
    print(f"Productos con vecinos: {vecinos['stock_code'].nunique():,} · "
          f"filas de vecinos: {len(vecinos):,}")
    print(f"Guardado en {ruta} ({ruta.stat().st_size / 1024 ** 2:.1f} MB)\n")

    catalogo = pd.read_parquet(RUTA_CATALOGO)
    ejemplo = modelo_final["popularidad"]["stock_code"].iloc[0]
    resumen = {"precio_minimo": 0, "precio_maximo": 30, "intereses": [INTERES_SORPRENDEME],
               "ocasion": "Cumpleaños", "producto_codigo": ejemplo}
    print(f"Ejemplo con el producto más vendido como referencia ({ejemplo}):")
    print(buscar_ideas_regalo(resumen, catalogo, modelo_final).to_string(index=False))
    print("\nCombos de £5 a £15 con la misma referencia:")
    combos = armar_combos({**resumen, "precio_minimo": 5, "precio_maximo": 15}, catalogo, modelo_final)
    print(combos.to_string(index=False))


if __name__ == "__main__":
    main()
