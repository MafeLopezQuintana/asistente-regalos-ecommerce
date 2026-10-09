"""
Utilidades para registrar experimentos en MLflow de forma consistente
entre los distintos modelos del equipo (KNN item-item, SVD, etc.).

Por qué existe este archivo: sin esto, cada quien registraría sus
corridas de MLflow a su manera (otro nombre de experimento, otras
claves de parámetros) y después no se podrían comparar los modelos
lado a lado — que es justo lo que pide el hueco #5 del roadmap
(justificar los hiperparámetros del SVD) y lo que después va a usar
el script de monitoreo (hueco #9).

Uso típico dentro del notebook o script de cada modelo:

    from src.utils.mlflow_utils import registrar_corrida

    registrar_corrida(
        nombre_modelo="knn_item_item",
        parametros={"n_neighbors": 20, "metric": "cosine"},
        metricas={"precision_at_10": 0.34, "recall_at_10": 0.21},
    )
"""
import mlflow

# Un solo nombre de experimento para todo el equipo — así todas las
# corridas (KNN, SVD, lo que venga) quedan agrupadas y comparables
# en la misma pantalla de MLflow, en vez de dispersas.
EXPERIMENTO = "asistente-regalos-ecommerce"


def registrar_corrida(nombre_modelo, parametros, metricas, modelo=None, tags=None):
    """Registra una corrida de entrenamiento o evaluación en MLflow.

    nombre_modelo : str
        Nombre corto del modelo (ej. "knn_item_item", "svd_k15").
    parametros : dict
        Hiperparámetros usados en esta corrida (ej. {"n_components": 15}).
    metricas : dict
        Métricas de evaluación de esta corrida (ej. {"precision_at_10": 0.34}).
    modelo : objeto entrenado, opcional
        Si se pasa, se guarda junto con la corrida para poder recuperarlo
        después sin tener que reentrenar.
    tags : dict, opcional
        Etiquetas libres para filtrar corridas más tarde
        (ej. {"sprint": "1", "autor": "franco"}).
    """
    mlflow.set_experiment(EXPERIMENTO)
    with mlflow.start_run(run_name=nombre_modelo):
        mlflow.log_params(parametros)
        mlflow.log_metrics(metricas)
        if tags:
            mlflow.set_tags(tags)
        if modelo is not None:
            mlflow.sklearn.log_model(modelo, artifact_path=nombre_modelo)
