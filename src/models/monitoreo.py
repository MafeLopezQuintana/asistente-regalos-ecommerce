"""
Monitoreo del modelo elegido (item-item) mes a mes.

Simulamos que el modelo se puso en producción el día del corte temporal
(19/08/2011): se entrena una sola vez con el período de desarrollo y después
se reevalúa, sin reentrenar, sobre cada mes que vino después. Es lo que haría
el equipo en la realidad: mirar todos los meses si el modelo sigue acertando.

Por cada mes se mide:
  - Hit Rate@5, NDCG@5 y cobertura, con la misma evaluar() de evaluate.py.
  - Hit Rate@5 del baseline (popularidad) sobre los mismos casos, como contexto.
  - pct_productos_nuevos: % de productos vendidos en el mes que el modelo nunca
    vio. Si sube, el catálogo está cambiando y el modelo se queda sin datos.

Alerta de referencia: el mes se marca si su Hit Rate@5 está por debajo de
la referencia de validación (9,4%, sección 5 del README) incluso tomando el
límite superior de su intervalo de confianza de Wilson del 95%. Así un mes con pocos
casos no dispara la alerta solo por azar. Es una referencia para revisar,
no un umbral definitivo (acordado con validación).

Como el dataset es histórico, es una simulación de monitoreo: cada mes queda
en MLflow con etapa="monitoreo" y tipo="simulacion", junto con la versión del
código y la fuente de los datos, para poder reproducir la corrida.

Uso, desde la raíz del repo:
    python -m src.models.monitoreo
"""
import subprocess

import numpy as np
import pandas as pd

from src.models.evaluate import (COL_FACTURA, COL_FECHA, COL_PRODUCTO, RUTA_DATOS_MODELO,
                                 cargar_datos_modelo, construir_casos, corte_temporal, evaluar)
from src.models.train import ItemItem, Popularidad

# Configuración elegida en la validación cruzada (README, sección 5)
PARAMS_MODELO = {"min_facturas": 5, "max_productos_factura": 200}
# Hit Rate@5 medio de item-item en la validación cruzada temporal (README, sección 5)
REFERENCIA_HIT_RATE = 0.094
PROPORCION_TRAIN = 0.8
K = 5
SEMILLA = 42


def separar_por_mes(df, col_factura=COL_FACTURA, col_fecha=COL_FECHA):
    """Divide las facturas por mes (según su fecha), sin partir ninguna factura.

    Devuelve un diccionario {"2011-09": df_del_mes, ...} ordenado por fecha.
    """
    fecha_por_factura = df.groupby(col_factura)[col_fecha].min()
    mes = df[col_factura].map(fecha_por_factura).dt.to_period("M").astype(str)
    return {m: grupo.copy() for m, grupo in df.groupby(mes, sort=True)}


def pct_productos_nuevos(df_mes, productos_conocidos, col_producto=COL_PRODUCTO):
    """% de productos distintos vendidos en el mes que el modelo nunca vio al entrenar."""
    vendidos = set(df_mes[col_producto].unique())
    if not vendidos:
        return 0.0
    return 100 * len(vendidos - set(productos_conocidos)) / len(vendidos)


def limite_superior_ic95(proporcion, n, z=1.96):
    """Límite superior del intervalo de confianza de Wilson del 95% de una proporción.

    Con más casos el intervalo es más angosto, así que un mes chico necesita
    caer más para dar alerta. Se usa Wilson y no la aproximación normal
    (p + z * raíz(p(1-p)/n)) porque la normal falla en los extremos: con 0
    aciertos da un intervalo de ancho cero y dispararía una falsa alarma en
    un mes con muy pocos casos. Wilson siempre queda entre 0 y 1.
    """
    centro = proporcion + z**2 / (2 * n)
    margen = z * np.sqrt(proporcion * (1 - proporcion) / n + z**2 / (4 * n**2))
    return (centro + margen) / (1 + z**2 / n)


def version_codigo():
    """Commit de git con el que se corre el monitoreo, para poder reproducirlo."""
    try:
        resultado = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                   capture_output=True, text=True, check=True)
        return resultado.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconocida"


def monitorear(df, params_modelo=None, referencia=REFERENCIA_HIT_RATE,
               proporcion_train=PROPORCION_TRAIN, k=K, semilla=SEMILLA,
               registrar_mlflow=True, experimento=None, tracking_uri=None,
               fuente_datos=RUTA_DATOS_MODELO):
    """Entrena una vez con el desarrollo y evalúa el modelo en cada mes posterior.

    Devuelve un DataFrame con una fila por mes. Si registrar_mlflow=True, cada
    mes queda como una corrida con tag etapa="monitoreo".
    """
    params_modelo = params_modelo or PARAMS_MODELO
    desarrollo, posterior, fecha_corte = corte_temporal(df, proporcion_train)

    modelo = ItemItem(**params_modelo).fit(desarrollo)
    baseline = Popularidad().fit(desarrollo)
    conocidos = set(desarrollo[COL_PRODUCTO].unique())

    filas = []
    for mes, df_mes in separar_por_mes(posterior).items():
        casos, info = construir_casos(df_mes, conocidos, modo="ancla", semilla=semilla)
        if not casos:
            continue

        metricas = evaluar(modelo, casos, k=k)
        hit_rate = metricas[f"hit_rate_at_{k}"]
        limite = limite_superior_ic95(hit_rate, metricas["casos"])
        filas.append({
            "mes": mes,
            **metricas,
            f"hit_rate_at_{k}_baseline": evaluar(baseline, casos, k=k)[f"hit_rate_at_{k}"],
            "pct_productos_nuevos": pct_productos_nuevos(df_mes, conocidos),
            "pct_facturas_evaluables": info.get("pct_facturas_evaluables", 0.0),
            "facturas_mes": info["facturas_evaluadas"],
            "facturas_excluidas": info["facturas_evaluadas"] - metricas["casos"],
            "ic95_superior": limite,
            "alerta": bool(limite < referencia),
        })

    resultado = pd.DataFrame(filas)

    if registrar_mlflow:
        from src.utils.mlflow_utils import registrar_corrida

        destino = {}
        if experimento is not None:
            destino["experimento"] = experimento
        if tracking_uri is not None:
            destino["tracking_uri"] = tracking_uri

        parametros = {**modelo.get_params(), "k": k, "semilla": semilla,
                      "referencia_hit_rate": referencia,
                      "fecha_corte": str(fecha_corte.date()),
                      "version_codigo": version_codigo(),
                      "fuente_datos": str(fuente_datos)}
        for _, fila in resultado.iterrows():
            metricas = {c: float(fila[c]) for c in resultado.columns
                        if c not in ("mes", "alerta")}
            registrar_corrida(f"monitoreo_{fila['mes']}", {**parametros, "mes": fila["mes"]},
                              metricas, tags={"etapa": "monitoreo", "tipo": "simulacion",
                                              "familia": "item_item",
                                              "mes": fila["mes"],
                                              "alerta": str(fila["alerta"]).lower()},
                              **destino)

    return resultado


def main():
    resultado = monitorear(cargar_datos_modelo())
    tabla = resultado[["mes", "casos", "facturas_excluidas", f"hit_rate_at_{K}", f"hit_rate_at_{K}_baseline",
                       "ic95_superior", "pct_productos_nuevos", "alerta"]].copy()
    for col in (f"hit_rate_at_{K}", f"hit_rate_at_{K}_baseline", "ic95_superior"):
        tabla[col] = (100 * tabla[col]).round(1)
    tabla["pct_productos_nuevos"] = tabla["pct_productos_nuevos"].round(1)

    print(f"Simulación de monitoreo. Referencia (validación): Hit Rate@{K} = "
          f"{100 * REFERENCIA_HIT_RATE:.1f}%\n")
    print(tabla.to_string(index=False))
    print(f"\nMeses por debajo de la referencia: {int(resultado['alerta'].sum())} de {len(resultado)}")
    print("Corridas registradas en MLflow con etapa='monitoreo'.")


if __name__ == "__main__":
    main()
