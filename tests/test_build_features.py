# tests/test_build_features.py
import sys
sys.path.append('.')
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from src.features.build_features import (
    clusterizar_productos, top_palabras_por_cluster,
    top_palabras_por_subcluster, asignar_categorias, TOKEN_PATTERN
)


def catalogo_chico(n=20):
    """Catálogo sintético con descripciones variadas, suficiente para
    probar K-Means con pocos clusters (no los 15 reales de producción)."""
    temas = ['red glass vase', 'blue ceramic mug', 'christmas tree light',
             'vintage paper card', 'wooden photo frame']
    descripciones = [f"{temas[i % len(temas)]} set of {i}" for i in range(n)]
    return pd.DataFrame({'stock_code': [f'P{i}' for i in range(n)],
                          'description': descripciones,
                          'precio': [1.0] * n})


def test_clusteriza_sin_romper_con_pocos_productos(monkeypatch):
    """clusterizar_productos debe funcionar con K chico, no solo con el
    K_PRINCIPAL=15 de producción (si no, ningún test podría usar un
    catálogo sintético pequeño)."""
    import src.features.build_features as bf
    monkeypatch.setattr(bf, 'K_PRINCIPAL', 2)
    monkeypatch.setattr(bf, 'K_SUBCLUSTER', 2)

    productos, vectorizer, matriz, vectorizer_bi, matriz_bi, mask, modelo, modelo_sub, cluster_generico = bf.clusterizar_productos(catalogo_chico())

    assert 'cluster' in productos.columns
    assert productos['cluster'].nunique() <= 2
    assert mask.sum() > 0  # el cluster genérico (el más grande) existe


def test_token_pattern_excluye_numeros_sueltos():
    """Bug real encontrado en el notebook: 'SET OF 12' generaba '12' como
    palabra de categoría. El patrón debe exigir letras, nunca dígitos solos."""
    vectorizer = TfidfVectorizer(token_pattern=TOKEN_PATTERN)
    vectorizer.fit(['set of 12 candles', 'pack of 10 cards'])
    vocabulario = vectorizer.get_feature_names_out()
    assert '12' not in vocabulario
    assert '10' not in vocabulario
    assert 'candles' in vocabulario


def test_top_palabras_devuelve_n_palabras():
    """top_palabras_por_cluster debe respetar el parámetro n y no romper
    con un vocabulario chico."""
    productos = pd.DataFrame({'description': ['red glass vase', 'blue glass jar'],
                               'cluster': [0, 0]})
    vectorizer = TfidfVectorizer()
    matriz = vectorizer.fit_transform(productos['description'])

    resultado = top_palabras_por_cluster(productos, vectorizer, matriz, n=3)
    assert len(resultado) == 1  # 1 solo cluster
    assert len(resultado.iloc[0]['palabras_top']) <= 3


def test_asignar_categorias_usa_el_nombre_correcto():
    """Un cluster con nombre asignado debe quedar con ese nombre exacto."""
    productos = pd.DataFrame({'cluster': [0, 1], 'sub_cluster': [np.nan, np.nan]})
    resultado = asignar_categorias(productos, {0: 'Cocina', 1: 'Jardín'}, {})
    assert list(resultado['categoria']) == ['Cocina', 'Jardín']


def test_cluster_sin_nombre_cae_en_categoria_generica():
    """El cluster genérico (sin entrada en el diccionario de nombres) debe
    caer en 'Variedad / Sorpresa' — así se resolvió el caso real donde el
    29,8% del catálogo no tenía vocabulario distintivo."""
    productos = pd.DataFrame({'cluster': [0, 4], 'sub_cluster': [np.nan, np.nan]})
    resultado = asignar_categorias(productos, {0: 'Cocina'}, {})  # cluster 4 sin nombre
    assert resultado['categoria'].iloc[1] == 'Variedad / Sorpresa'


def test_subcluster_tiene_prioridad_sobre_cluster():
    """Si un producto tiene sub_cluster asignado (viene del cluster
    genérico dividido), su categoría final debe salir del nombre del
    sub-cluster, no del cluster genérico original."""
    productos = pd.DataFrame({'cluster': [4], 'sub_cluster': [2.0]})
    resultado = asignar_categorias(productos, {}, {2: 'Velas aromáticas'})
    assert resultado['categoria'].iloc[0] == 'Velas aromáticas'


def test_sub_cluster_sin_nombre_tambien_cae_en_generica():
    """Un sub_cluster sin entrada en el diccionario (como el sub_cluster 5
    real, con 1.412 productos) también debe caer en la categoría residual."""
    productos = pd.DataFrame({'cluster': [4], 'sub_cluster': [5.0]})
    resultado = asignar_categorias(productos, {}, {2: 'Velas aromáticas'})
    assert resultado['categoria'].iloc[0] == 'Variedad / Sorpresa'

def test_re_entrenar_y_categorizar_productos_nuevos_no_rompe(tmp_path, monkeypatch):
    """Simula el ciclo completo: entrenar de cero, guardar, y usar eso para
    categorizar un producto que no existía al entrenar — ninguna de las
    2 funciones debe romperse, y categorizar_productos_nuevos no debe
    re-entrenar nada (nombres y categoria_generica se le pasan de afuera,
    no se recalculan)."""
    import src.features.build_features as bf
    monkeypatch.setattr(bf, 'K_PRINCIPAL', 2)
    monkeypatch.setattr(bf, 'K_SUBCLUSTER', 2)

    productos, vectorizer, matriz, vectorizer_bi, matriz_bi, mask, modelo, modelo_sub, cluster_generico = bf.clusterizar_productos(catalogo_chico())

    nombres_cluster = {c: f'Categoria {c}' for c in productos['cluster'].unique()}
    nombres_subcluster = {}

    path = tmp_path / "modelos.pkl"
    bf.guardar_modelos(path, vectorizer, modelo, vectorizer_bi, modelo_sub,
                        cluster_generico, nombres_cluster, nombres_subcluster)

    paquete = bf.cargar_modelos(path)

    producto_nuevo = pd.DataFrame({'stock_code': ['99999'], 'description': ['NUEVO PRODUCTO DE PRUEBA']})
    resultado = bf.categorizar_productos_nuevos(producto_nuevo, paquete)

    assert 'categoria' in resultado.columns
    assert len(resultado) == 1