"""
Utilidades para registrar experimentos en MLflow de forma consistente
entre los distintos modelos del equipo (popularidad, item-item, SVD, monitoreo).

Todas las corridas van al mismo experimento y a la misma base (mlflow.db en la
raíz del repo), sin importar desde qué carpeta se ejecute (notebooks/, raíz,
script de monitoreo). Las etapas se distinguen con el tag "etapa":
"validacion", "test_final" o "monitoreo".

Para ver las corridas, desde la raíz del repo:
    mlflow ui --backend-store-uri sqlite:///mlflow.db

Uso típico:

    from src.utils.mlflow_utils import registrar_corrida

    registrar_corrida(
        nombre_modelo="item_item_min5",
        parametros=modelo.get_params(),
        metricas={"hit_rate_at_5": 0.091, "ndcg_at_5": 0.062, "cobertura": 0.64},
        tags={"etapa": "test_final", "autor": "ezequiel", "familia": "item_item"},
    )
"""
import tempfile
from pathlib import Path

import joblib
import mlflow

# Un solo experimento para todo el equipo: las corridas quedan juntas y comparables.
EXPERIMENTO = "asistente-regalos-ecommerce"

# Base anclada a la raíz del repo (src/utils/ -> parents[2]). Con una ruta relativa,
# cada carpeta desde la que se ejecuta crearía su propio mlflow.db.
RAIZ_REPO = Path(__file__).resolve().parents[2]
TRACKING_URI = f"sqlite:///{(RAIZ_REPO / 'mlflow.db').as_posix()}"


def registrar_corrida(nombre_modelo, parametros, metricas, modelo=None, tags=None,
                      artefactos=None, experimento=EXPERIMENTO, tracking_uri=TRACKING_URI):
    """Registra una corrida de entrenamiento o evaluación en MLflow.

    nombre_modelo : str
        Nombre corto de la corrida (ej. "item_item_min5", "svd_n50").
    parametros : dict
        Hiperparámetros (en nuestros modelos, modelo.get_params()).
    metricas : dict
        Métricas de evaluación (ej. {"hit_rate_at_5": 0.09, "ndcg_at_5": 0.06}).
    modelo : objeto entrenado, opcional
        Se guarda con joblib como artefacto, así funciona con cualquier objeto
        (nuestros modelos no son estimadores de sklearn). Para recuperarlo hace
        falta poder importar src.models.
    tags : dict, opcional
        Etiquetas para filtrar (ej. {"etapa": "validacion", "autor": "franco"}).
    artefactos : lista de rutas, opcional
        Archivos a adjuntar (tablas, gráficos).
    experimento, tracking_uri : opcionales
        Por defecto, el experimento del equipo en mlflow.db de la raíz. Los tests
        pasan una base temporal para no ensuciar la real.

    Devuelve el run_id de la corrida.
    """
    mlflow.set_tracking_uri(tracking_uri)
    if mlflow.get_experiment_by_name(experimento) is None:
        # Sin esto, MLflow guarda los artefactos en ./mlruns de la carpeta actual
        # aunque la base esté anclada. Los dejamos junto a la base.
        base = Path(tracking_uri.replace("sqlite:///", ""))
        mlflow.create_experiment(experimento,
                                 artifact_location=(base.parent / "mlartifacts").as_uri())
    mlflow.set_experiment(experimento)

    with mlflow.start_run(run_name=nombre_modelo) as corrida:
        mlflow.log_params(parametros)
        mlflow.log_metrics(metricas)
        if tags:
            mlflow.set_tags(tags)
        for ruta in artefactos or []:
            mlflow.log_artifact(str(ruta))
        if modelo is not None:
            with tempfile.TemporaryDirectory() as tmp:
                ruta = Path(tmp) / f"{nombre_modelo}.joblib"
                joblib.dump(modelo, ruta)
                mlflow.log_artifact(str(ruta), artifact_path="modelo")
        return corrida.info.run_id
