"""
Registro del modelo final en MLflow.

Toma models/modelo_final.pkl (lo genera `python -m src.models.asistente`) y lo
guarda en MLflow como una corrida con etapa="modelo_final": los parámetros con
los que se entrenó, las métricas de referencia del test, el período de datos,
la versión del código y el propio archivo .pkl como artefacto. Así queda
registrado qué versión exacta del modelo usa la app, junto a las corridas de
validación, test final y monitoreo.

Uso, desde la raíz del repo:
    python -m src.models.registrar_modelo
"""
from pathlib import Path

from src.models.asistente import RUTA_MODELO, cargar_modelo_final
from src.models.monitoreo import version_codigo


def registrar_modelo_final(ruta=RUTA_MODELO, experimento=None, tracking_uri=None):
    """Registra modelo_final.pkl en MLflow y devuelve el run_id de la corrida."""
    from src.utils.mlflow_utils import registrar_corrida

    ruta = Path(ruta)
    modelo_final = cargar_modelo_final(ruta)
    datos = modelo_final["datos"]
    vecinos = modelo_final["vecinos"]

    parametros = {
        **modelo_final["parametros"],
        "top_vecinos": int(vecinos["rango"].max()),
        "datos_desde": datos["desde"],
        "datos_hasta": datos["hasta"],
        "version_modelo": modelo_final["version"],
        "generado": modelo_final["generado"],
        "version_codigo": version_codigo(),
    }
    metricas = {
        **{f"referencia_{k}": float(v) for k, v in modelo_final["metricas_referencia"].items()},
        "facturas_entrenamiento": int(datos["facturas"]),
        "productos_con_vecinos": int(vecinos["stock_code"].nunique()),
        "tamano_mb": round(ruta.stat().st_size / 1024 ** 2, 2),
    }

    destino = {}
    if experimento is not None:
        destino["experimento"] = experimento
    if tracking_uri is not None:
        destino["tracking_uri"] = tracking_uri

    return registrar_corrida("modelo_final", parametros, metricas,
                             tags={"etapa": "modelo_final", "familia": "item_item"},
                             artefactos=[ruta], **destino)


def main():
    run_id = registrar_modelo_final()
    print(f"Modelo final registrado en MLflow con etapa='modelo_final' (run_id: {run_id}).")


if __name__ == "__main__":
    main()
