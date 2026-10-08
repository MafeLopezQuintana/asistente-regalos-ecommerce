# src/features/build_features.py
"""Genera la columna `categoria` para el catálogo de productos.

Receta validada en notebooks/02b_categorias.ipynb: TF-IDF (unigramas) +
K-Means(15) sobre el catálogo completo separa la mayoría de los productos
en grupos con tema reconocible. El grupo más grande no tiene vocabulario
distintivo (ni Elbow ni Silhouette marcan un K óptimo claro) — se vuelve
a vectorizar con bigramas + K-Means(15) para rescatar sub-temas (aunque
el Silhouette no mejora con bigramas, los sub-temas resultantes sí son
reconocibles con productos reales), y lo que sigue sin tema se etiqueta
"Variedad / Sorpresa".
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd
import pickle

TOKEN_PATTERN = r'\b[a-zA-Z]{2,}\b'  # sin dígitos sueltos (ej. "SET OF 12")
K_PRINCIPAL = 15
K_SUBCLUSTER = 15
NOMBRES_CLUSTER = {
    0: 'Llaveros bling y con letra',
    1: 'Estampado retrospot y lunares',
    2: 'Decoración de árbol navideño',
    3: 'Iluminación y portavelas colgantes',
    5: 'Corazones decorativos',
    6: 'Collares y joyería de vidrio',
    7: 'Dijes y charms (bolso y celular)',
    8: 'Diseños y accesorios variados',
    9: 'Sets y combos (papelería, luces, velas)',
    10: 'Espejos y botellas de agua caliente',
    11: 'Incienso y aromáticos',
    12: 'Velas aromáticas',
    13: 'Bolsas de regalo y contenedores chicos',
    14: 'Cuadernos y cajas vintage',
}
NOMBRES_SUBCLUSTER = {
    0: 'Bandejas y velas de mesa retro',
    1: 'Arte de pared y relojes',
    2: 'Rosas decorativas (inglesa, danesa, clásica)',
    3: 'Cajas y trinket boxes decorativas',
    4: 'Tarjetas de saludo y cumpleaños',
    5: 'Repostería y stands de torta',
    6: 'Vajilla esmaltada estilo sweetheart',
    7: 'Fundas y cobertores de cojín',
    8: 'Tazas de café y flores',
    9: 'Joyería de vidrio y aretes',
    10: 'Carteles metálicos con frases',
    11: 'Decoración colgante y de Pascua',
    12: 'Marcos de fotos',
}


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

    Devuelve también los modelos ya entrenados (vectorizer, matriz,
    vectorizer_bi, matriz_bi, mask, modelo, modelo_sub, cluster_generico)
    para poder guardarlos con guardar_modelos() y reusarlos después sobre
    productos nuevos sin tener que re-entrenar todo el catálogo de nuevo.
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

    return productos, vectorizer, matriz, vectorizer_bi, matriz_bi, mask, modelo, modelo_sub, cluster_generico


def top_palabras_por_cluster(productos, vectorizer, matriz, n=8):
    """Una fila por cluster principal, con sus palabras top — para nombrarlos."""
    productos = productos.reset_index(drop=True)
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

def guardar_modelos(path, vectorizer, modelo, vectorizer_bi, modelo_sub,
                     cluster_generico, nombres_cluster, nombres_subcluster):
    """Guarda todo lo necesario para categorizar productos nuevos sin
    re-entrenar: los 2 vectorizers, los 2 modelos de K-Means, el número
    del cluster genérico, y los 2 diccionarios de nombres ya elegidos.
    """
    paquete = {
        'vectorizer': vectorizer,
        'modelo': modelo,
        'vectorizer_bi': vectorizer_bi,
        'modelo_sub': modelo_sub,
        'cluster_generico': cluster_generico,
        'nombres_cluster': nombres_cluster,
        'nombres_subcluster': nombres_subcluster,
    }
    with open(path, 'wb') as f:
        pickle.dump(paquete, f)

def cargar_modelos(path):
    """Carga lo que guardó guardar_modelos(). Devuelve el mismo diccionario
    con las 7 piezas (vectorizer, modelo, vectorizer_bi, modelo_sub,
    cluster_generico, nombres_cluster, nombres_subcluster).
    """
    with open(path, 'rb') as f:
        return pickle.load(f)

def categorizar_productos_nuevos(productos_nuevos: pd.DataFrame, paquete: dict):
    """Categoriza productos que NO existían al entrenar, sin re-entrenar
    nada — usa los modelos ya guardados (ver guardar_modelos/cargar_modelos).
    Por eso el número de cada cluster no se mueve: siempre son los mismos
    vectorizer y modelos, solo se les aplica .transform()/.predict().
    """
    productos_nuevos = productos_nuevos.copy()

    matriz_nueva = paquete['vectorizer'].transform(productos_nuevos['description'])
    productos_nuevos['cluster'] = paquete['modelo'].predict(matriz_nueva)

    mask = productos_nuevos['cluster'] == paquete['cluster_generico']
    productos_nuevos['sub_cluster'] = pd.NA
    if mask.any():
        matriz_bi_nueva = paquete['vectorizer_bi'].transform(productos_nuevos.loc[mask, 'description'])
        productos_nuevos.loc[mask, 'sub_cluster'] = paquete['modelo_sub'].predict(matriz_bi_nueva)

    return asignar_categorias(productos_nuevos, paquete['nombres_cluster'], paquete['nombres_subcluster'])

if __name__ == '__main__':
    from src.data.clean import catalogo_productos

    df_modelo = pd.read_parquet('data/processed/online_retail_modelo.parquet')
    productos = catalogo_productos(df_modelo)

    productos, vectorizer, matriz, vectorizer_bi, matriz_bi, mask, modelo, modelo_sub, cluster_generico = clusterizar_productos(productos)

    productos_final = asignar_categorias(productos, NOMBRES_CLUSTER, NOMBRES_SUBCLUSTER)
    productos_final.to_parquet('data/processed/catalogo_categorizado.parquet', index=False)

    guardar_modelos('data/processed/modelos_categorias.pkl', vectorizer, modelo, vectorizer_bi, modelo_sub,
                     cluster_generico, nombres_cluster, nombres_subcluster)

    print(f"Guardado: {len(productos_final)} productos, {productos_final['categoria'].nunique()} categorías")
    print("Modelos congelados guardados en data/processed/modelos_categorias.pkl")