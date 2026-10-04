# src/features/build_features.py
"""Genera la columna `categoria` para el catálogo de productos.

Receta validada en notebooks/02b_categorias.ipynb: TF-IDF (unigramas) +
K-Means(15) sobre el catálogo completo separa la mayoría de los productos
en grupos con tema reconocible. El grupo más grande no tiene vocabulario
distintivo (confirmado con 4 métodos: Elbow, Silhouette, Gap Statistic,
Tibshirani) — se vuelve a vectorizar con bigramas + K-Means(15) para
rescatar sub-temas, y lo que sigue sin tema se etiqueta "Variedad / Sorpresa".
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd

TOKEN_PATTERN = r'\b[a-zA-Z]{2,}\b'  # sin dígitos sueltos (ej. "SET OF 12")
K_PRINCIPAL = 15
K_SUBCLUSTER = 15


def _top_palabras(matriz, vectorizer, indices, n=8):
    """Las n palabras/bigramas con mayor TF-IDF promedio en un grupo de filas."""
    palabras = vectorizer.get_feature_names_out()
    promedio = matriz[indices].mean(axis=0).A1
    top = promedio.argsort()[-n:][::-1]
    return [palabras[i] for i in top]


def clusterizar_productos(productos: pd.DataFrame):
    """Agrupa productos por descripción. Devuelve el catálogo con 'cluster'
    (0-14) y, solo para el cluster más grande (el genérico, sin vocabulario
    distintivo), un 'sub_cluster' (0-14) adicional vía bigramas.
    """
    vectorizer = TfidfVectorizer(stop_words='english', min_df=2, token_pattern=TOKEN_PATTERN)
    matriz = vectorizer.fit_transform(productos['description'])

    modelo = KMeans(n_clusters=K_PRINCIPAL, random_state=42, n_init=10)
    productos = productos.copy()
    productos['cluster'] = modelo.fit_predict(matriz)

    # El cluster genérico es el más grande — confirmado en la exploración,
    # no es un número fijo: puede cambiar si el catálogo cambia.
    cluster_generico = productos['cluster'].value_counts().idxmax()
    mask = productos['cluster'] == cluster_generico

    vectorizer_bi = TfidfVectorizer(stop_words='english', min_df=3,
                                      token_pattern=TOKEN_PATTERN, ngram_range=(1, 2))
    matriz_bi = vectorizer_bi.fit_transform(productos.loc[mask, 'description'])

    modelo_sub = KMeans(n_clusters=K_SUBCLUSTER, random_state=42, n_init=10)
    productos.loc[mask, 'sub_cluster'] = modelo_sub.fit_predict(matriz_bi)

    return productos, vectorizer, matriz, vectorizer_bi, matriz_bi, mask


def top_palabras_por_cluster(productos, vectorizer, matriz, n=8):
    """Una fila por cluster principal, con sus palabras top — para nombrarlos."""
    filas = []
    for c in sorted(productos['cluster'].unique()):
        indices = productos.index[productos['cluster'] == c]
        filas.append({'cluster': c, 'n_productos': len(indices),
                       'palabras_top': _top_palabras(matriz, vectorizer, indices, n)})
    return pd.DataFrame(filas)


def top_palabras_por_subcluster(productos, vectorizer_bi, matriz_bi, mask, n=8):
    """Una fila por sub-cluster del grupo genérico, con sus palabras top."""
    sub = productos.loc[mask].reset_index(drop=True)
    filas = []
    for sc in sorted(sub['sub_cluster'].dropna().unique()):
        indices = sub.index[sub['sub_cluster'] == sc]
        filas.append({'sub_cluster': int(sc), 'n_productos': len(indices),
                       'palabras_top': _top_palabras(matriz_bi, vectorizer_bi, indices, n)})
    return pd.DataFrame(filas)


def asignar_categorias(productos, nombres_cluster: dict, nombres_subcluster: dict,
                        categoria_generica: str = 'Variedad / Sorpresa'):
    """Aplica los nombres elegidos a mano (mirando top_palabras_por_*).
    Un sub_cluster sin nombre asignado queda en categoria_generica.
    """
    productos = productos.copy()
    productos['categoria'] = productos['cluster'].map(nombres_cluster).astype(object)
    tiene_sub = productos['sub_cluster'].notna()
    productos.loc[tiene_sub, 'categoria'] = productos.loc[tiene_sub, 'sub_cluster'].map(nombres_subcluster).astype(object)
    productos['categoria'] = productos['categoria'].fillna(categoria_generica)
    return productos