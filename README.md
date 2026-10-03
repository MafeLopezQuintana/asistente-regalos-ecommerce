![Recomendador de regalos: ¿Qué le regalo?](portada-regalos.png)

# Asistente de regalos para e-commerce
Proyecto Final Henry · Presente Analytics

Asistente que, a partir de un cuestionario de 5 preguntas, sugiere regalos individuales y combos dentro del presupuesto, usando modelos de recomendación entrenados con compras reales (Online Retail II).

## Equipo y roles

Marco Scrum y metodología CRISP-DM. Los roles son formales, para la documentación del PF: todos programamos y aportamos por igual a todo el proyecto.

| Integrante | Rol formal | Aporte adicional | Frente técnico |
|---|---|---|---|
| Franco | Product Owner | Visualización y dashboards | Modelado |
| Mafe | Scrum Master | Visualización y dashboards | Demo en Streamlit y README |
| Cristian | Liderazgo técnico (Data Team) | Visualización | EDA y Power BI |
| Ezequiel | Liderazgo técnico (Data Team) | Documentación y Git | Modelado |
| Mauricio | Liderazgo técnico (Data Team) | Documentación y Git | Ingeniería de datos |

## Cómo correr el proyecto
( versión de Python, instalación de requirements.txt, cómo abrir la demo)

## 1. Calidad de datos (Mauricio)
Qué limpieza se hizo, qué archivos se generan (Parquet), para qué sirve cada uno y cómo cargarlo.

## 2. Categorías e intereses (Mauricio)
Cómo se derivaron las categorías a partir de la descripción del producto.

## 3. EDA y visualizaciones (Cristian)
Hallazgos principales del análisis exploratorio y del dashboard.

## 4. Modelos (Ezequiel y Franco)
Baseline, KNN item-item y SVD: métricas (Hit Rate@5, NDCG@5) y tabla comparativa.

## 5. Justificación del modelo y plan de validación (Franco)
Por qué se eligió el modelo final y cómo se valida.

## 6. Demo en Streamlit (Mafe)
Qué hace cada pantalla, cómo se usa y el link público.

## 7. Pipeline reproducible y monitoreo (Mauricio)
GitHub Actions, MLflow y cómo se reevalúa el modelo.

## Limitaciones
Qué no cubre este prototipo.
