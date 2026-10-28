"""Exporta las tablas del dashboard de Power BI a un único Excel.

Por qué Excel y no CSV: el Excel guarda los números y las fechas ya tipados, así que
Power BI los lee bien aunque la computadora use coma decimal (es-AR) y no hay que
corregir tipos a mano.

Entradas (generadas por el ETL y por build_features.py, en data/processed/):
  online_retail_modelo.parquet, online_retail_rfm.parquet, catalogo_categorizado.parquet
Salida:
  reports/powerbi/datos_dashboard.xlsx   (una hoja por tabla)

Uso, desde la raíz del repo y con el entorno activo:
  python reports/powerbi/exportar_datos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path("data/processed")
SALIDA = Path("reports/powerbi/datos_dashboard.xlsx")

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
PAISES_STD = {
    "EIRE": "Ireland",
    "RSA": "South Africa",
    "Unspecified": "Desconocido",
    "European Community": "Desconocido",
}
# Colores de la guía de estilo (los usa la hoja "modelos" para colorear por modelo)
COLOR_MODELO = {"Popularidad": "#8A94B8", "Item-item": "#0739D9", "SVD": "#7F9CFF"}


def cargar():
    df = pd.read_parquet(PROC / "online_retail_modelo.parquet")
    rfm = pd.read_parquet(PROC / "online_retail_rfm.parquet")
    cat = pd.read_parquet(PROC / "catalogo_categorizado.parquet")
    for d in (df, rfm):
        d["ventas"] = d["quantity"] * d["unit_price"]
        d["country_std"] = d["country"].replace(PAISES_STD)
    return df, rfm, cat


def tabla_ventas_mes(df):
    mes = df["invoice_date"].dt.to_period("M")
    g = (df.groupby(mes)
           .agg(unidades=("quantity", "sum"), ingresos=("ventas", "sum"), facturas=("invoice_no", "nunique"))
           .reset_index().rename(columns={"invoice_date": "mes"}))
    g["ticket_promedio"] = g["ingresos"] / g["facturas"]
    # el último mes del dataset (dic-2011) solo tiene 9 días: se marca como incompleto
    ult = df["invoice_date"].max()
    ultimo_mes = ult.to_period("M")
    incompleto = ult.day < ult.days_in_month - 2
    g["mes_completo"] = np.where((g["mes"] == ultimo_mes) & incompleto, "No", "Sí")
    g["temporada"] = np.where(g["mes"].dt.month.isin([9, 10, 11]), "Sep–Nov", "Resto del año")
    g["mes"] = g["mes"].dt.to_timestamp()
    return g[["mes", "unidades", "ingresos", "facturas", "ticket_promedio", "mes_completo", "temporada"]]


def tabla_ventas_dia(df):
    g = (df.groupby(df["invoice_date"].dt.dayofweek)
           .agg(unidades=("quantity", "sum"), ingresos=("ventas", "sum"), facturas=("invoice_no", "nunique"))
           .reindex(range(7), fill_value=0))
    g.insert(0, "dia_semana", DIAS)
    g.insert(1, "orden", range(1, 8))
    return g.reset_index(drop=True)


def tabla_ventas_hora(df):
    g = (df.groupby(df["invoice_date"].dt.hour)
           .agg(unidades=("quantity", "sum"), ingresos=("ventas", "sum"))
           .reset_index().rename(columns={"invoice_date": "hora"}))
    return g


def tabla_productos(df, cat):
    desc = (df.groupby(["stock_code", "description"]).size().reset_index(name="n")
              .sort_values(["n", "description"], ascending=[False, True])
              .drop_duplicates("stock_code").set_index("stock_code")["description"])
    prod = df.groupby("stock_code").agg(
        unidades=("quantity", "sum"), ingresos=("ventas", "sum"),
        facturas=("invoice_no", "nunique"), precio_mediano=("unit_price", "median"))
    minoristas = (df[df["segmento"] == "minorista"].groupby("stock_code")["customer_id"].nunique()
                    .rename("clientes_minoristas"))
    prod = prod.join(minoristas).fillna({"clientes_minoristas": 0})
    prod["clientes_minoristas"] = prod["clientes_minoristas"].astype(int)
    prod["descripcion"] = desc
    prod["categoria"] = cat.set_index("stock_code")["categoria"].reindex(prod.index).fillna("Sin categoría")
    for col in ("unidades", "ingresos", "facturas"):
        prod[f"ranking_{col}"] = prod[col].rank(ascending=False, method="min").astype(int)
    prod = prod.reset_index()
    return prod[["stock_code", "descripcion", "categoria", "precio_mediano", "unidades", "ingresos", "facturas",
                 "clientes_minoristas", "ranking_unidades", "ranking_ingresos", "ranking_facturas"]]


def tabla_categorias(prod):
    g = (prod.groupby("categoria")
             .agg(productos=("stock_code", "count"), precio_mediano=("precio_mediano", "median"),
                  unidades=("unidades", "sum"), ingresos=("ingresos", "sum"))
             .reset_index())
    g["pct_catalogo"] = g["productos"] / g["productos"].sum()
    return g.sort_values("productos", ascending=False).reset_index(drop=True)


def tabla_categoria_mes(df, cat):
    m = df[["stock_code", "invoice_date", "quantity"]].merge(cat[["stock_code", "categoria"]], on="stock_code", how="left")
    m["categoria"] = m["categoria"].fillna("Sin categoría")
    g = (m.groupby(["categoria", m["invoice_date"].dt.month])["quantity"].sum()
           .reset_index().rename(columns={"invoice_date": "mes_numero", "quantity": "unidades"}))
    return g


def tabla_paises(df):
    g = (df.groupby("country_std")
           .agg(ingresos=("ventas", "sum"), unidades=("quantity", "sum"), lineas=("invoice_no", "size"))
           .reset_index().rename(columns={"country_std": "pais"}))
    g["pct_ingresos"] = g["ingresos"] / g["ingresos"].sum()
    return g.sort_values("ingresos", ascending=False).reset_index(drop=True)


def tabla_segmentos(rfm):
    g = (rfm.groupby("segmento")
            .agg(clientes=("customer_id", "nunique"), unidades=("quantity", "sum"),
                 ingresos=("ventas", "sum"), facturas=("invoice_no", "nunique"))
            .reset_index())
    g["pct_clientes"] = g["clientes"] / g["clientes"].sum()
    g["pct_unidades"] = g["unidades"] / g["unidades"].sum()
    g["pct_ingresos"] = g["ingresos"] / g["ingresos"].sum()
    return g


def tabla_pareto(rfm):
    ing = rfm.groupby("customer_id")["ventas"].sum().sort_values(ascending=False).to_numpy()
    acum = np.cumsum(ing) / ing.sum()
    filas = [{"pct_clientes": 0.0, "pct_ingresos_acumulado": 0.0}]
    for p in range(1, 101):
        n = max(int(np.ceil(len(ing) * p / 100)), 1)
        filas.append({"pct_clientes": p / 100, "pct_ingresos_acumulado": float(acum[n - 1])})
    return pd.DataFrame(filas)


def tabla_kpis(df, rfm, ventas_mes, prod):
    ing_factura = df.groupby("invoice_no")["ventas"].sum()
    completos = ventas_mes[ventas_mes["mes_completo"] == "Sí"]
    pct = completos.loc[completos["temporada"] == "Sep–Nov", "ingresos"].sum() / completos["ingresos"].sum()
    fila = {
        "desde": df["invoice_date"].min().normalize(),
        "hasta": df["invoice_date"].max().normalize(),
        "ingresos_totales": df["ventas"].sum(),
        "facturas": df["invoice_no"].nunique(),
        "productos": df["stock_code"].nunique(),
        "clientes": rfm["customer_id"].nunique(),
        "ticket_promedio": ing_factura.mean(),
        "ticket_mediano": ing_factura.median(),
        "productos_por_factura_mediana": df.groupby("invoice_no")["stock_code"].nunique().median(),
        "precio_mediano_producto": prod["precio_mediano"].median(),
        "pct_ingresos_sep_nov": pct,
    }
    return pd.DataFrame([fila])


def tabla_modelos():
    """Métricas de los modelos, tomadas de la Demo 1 (diapositivas 18 y 19).
    Fuente original: reports/comparacion_modelos.csv, rama modelos-demo1. Si el equipo
    actualiza las métricas, hay que actualizar esta tabla (o cargar ese CSV directamente)."""
    ancla = [("Item-item", 0.0842837274, 0.059, 0.616),
             ("SVD", 0.0695410292, 0.048, 0.535),
             ("Popularidad", 0.0182197497, 0.011, 0.001)]
    carrito = [("Item-item", 0.199, np.nan, np.nan),
               ("SVD", 0.070, np.nan, np.nan),
               ("Popularidad", 0.023, np.nan, np.nan)]
    filas = [{"modo": "Una ancla", "modelo": m, "hit_rate_5": h, "ndcg_5": n, "cobertura": c} for m, h, n, c in ancla]
    filas += [{"modo": "Carrito", "modelo": m, "hit_rate_5": h, "ndcg_5": n, "cobertura": c} for m, h, n, c in carrito]
    t = pd.DataFrame(filas)
    base = t.groupby("modo")["hit_rate_5"].transform(lambda s: s[t.loc[s.index, "modelo"] == "Popularidad"].iloc[0])
    t["veces_baseline"] = t["hit_rate_5"] / base
    t["color_hex"] = t["modelo"].map(COLOR_MODELO)
    return t


def main():
    df, rfm, cat = cargar()
    ventas_mes = tabla_ventas_mes(df)
    prod = tabla_productos(df, cat)
    hojas = {
        "kpis": tabla_kpis(df, rfm, ventas_mes, prod),
        "ventas_mes": ventas_mes,
        "ventas_dia": tabla_ventas_dia(df),
        "ventas_hora": tabla_ventas_hora(df),
        "productos": prod,
        "categorias": tabla_categorias(prod),
        "categoria_mes": tabla_categoria_mes(df, cat),
        "paises": tabla_paises(df),
        "segmentos": tabla_segmentos(rfm),
        "pareto_clientes": tabla_pareto(rfm),
        "modelos": tabla_modelos(),
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(SALIDA, engine="openpyxl") as w:
        for nombre, t in hojas.items():
            t.to_excel(w, sheet_name=nombre, index=False)
    print(f"Guardado: {SALIDA}")
    for nombre, t in hojas.items():
        print(f"  {nombre:16s} {t.shape[0]:>6,} filas x {t.shape[1]} columnas")


if __name__ == "__main__":
    main()
