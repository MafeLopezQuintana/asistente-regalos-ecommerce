# src/data/catalogo_app.py
"""Catálogo liviano para la app de Streamlit.

Toma el catálogo categorizado (data/processed/catalogo_categorizado.parquet)
y le agrega el interés del cuestionario de cada producto.

Por qué reglas y no los clusters: al leer los 4.725 productos uno por uno
vimos que K-Means agrupa por palabras repetidas (colores, "SET", "DESIGN")
y no por tipo de producto. "Sets y combos" mezcla vajilla, velas y tarjetas,
y "Variedad / Sorpresa" tiene juguetes, papelería y jardín. Para el
cuestionario usamos palabras clave explícitas: cada interés tiene su lista,
se evalúan en orden y gana la primera que coincide. Lo que no coincide con
ninguna va a "¡Sorprendeme!".

Uso:
    python -m src.data.catalogo_app
"""
import re
from pathlib import Path

import pandas as pd

RUTA_ENTRADA = Path("data/processed/catalogo_categorizado.parquet")
RUTA_CATALOGO = Path("models/catalogo_app.parquet")
RUTA_INTERESES = Path("models/intereses.csv")

INTERES_DEFECTO = "¡Sorprendeme!"
EXCLUIDO = "EXCLUIDO"
CATEGORIA_GENERICA = "Variedad / Sorpresa"

# Productos que no van en un asistente de regalos: vales, ítems que no son
# producto (imagen, relleno de almohadón) y artículos de drogas o para adultos.
PALABRAS_EXCLUIR = [
    "GIFT VOUCHER", "HIGH RESOLUTION IMAGE", "PADS TO MATCH", "FILLER PAD",
    "MARIJUANA", "CANNABIS", "SPLIFF", "ASHTRAY", "SEX BOMB", "DROP YOUR PANTS",
    "KISS MY", "CAB ELECTRONIC METER", "TALKING BREATH",
]

# El orden importa: gana la primera regla que coincide.
# Ej.: "SET OF 6 T-LIGHTS SANTA" es Fiestas (va antes que Velas).
REGLAS = {
    "Fiestas y celebraciones": [
        "CHRISTMAS", "XMAS", "SANTA", "REINDEER", "SNOWMAN", "SNOWMEN", "SNOWFLAKE",
        "ADVENT", "BAUBLE", "BAUBLES", "TINSEL", "NATIVITY", "YULETIDE", "NOEL",
        "HOLLY", "MISTLETOE", "SLEIGH", "EASTER", "HALLOWEEN", "PARTY", "BUNTING",
        "CRACKER", "CRACKERS", "STOCKING", "WREATH", "BIRTHDAY", "CELEBRATION",
        "CONFETTI", "BALLOON", "BALLOONS", "HONEYCOMB", "PAPER CHAIN",
    ],
    "Niños y juegos": [
        "TOY", "TOYS", "GAME", "GAMES", "DOLL", "DOLLS", "JIGSAW", "JIGSAWS",
        "PUZZLE", "PUZZLES", "SKITTLES", "PLAYING CARDS", "TOP TRUMPS", "TEDDY",
        "PUPPET", "CHILDREN", "CHILDRENS", "CHILDREN'S", "CHILDS", "CHILD'S", "KIDS", "KID'S",
        "BABY", "HELICOPTER", "DOMINOES", "SNAP CARDS", "LUDO", "HARMONICA",
        "PAINT SET", "DRAWING SLATE", "SPINNING TOPS", "SKIPPING ROPE",
        "KNITTING NANCY", "MODELLING CLAY", "PICK UP STICKS", "FLYING DISC",
        "TATTOOS", "LOLLY MAKERS", "INFLATABLE", "PLAYHOUSE", "STENCIL", "CRAYONS",
        "FELTCRAFT", "RACING CAR", "CREEPY CRAWLIES", "SOFT TOY", "NURSERY",
    ],
    "Velas y aromas": [
        "CANDLE", "CANDLES", "T-LIGHT", "T-LIGHTS", "TLIGHT", "TEALIGHT", "TEALIGHTS",
        "INCENSE", "VOTIVE", "CANDLEHOLDER", "CANDLESTICK", "CANDLEPOT",
        "CANDELABRA", "LANTERN", "LANTERNS", "OIL BURNER", "SCENTED", "SCENT",
        "POTPOURRI", "FRAGRANCE",
    ],
    "Accesorios": [
        "NECKLACE", "NECKLAC", "NECKL", "BRACELET", "BRACLET", "EARRINGS", "EARRING",
        "BROOCH", "RING", "BANGLE", "CHOKER", "CHARM", "CHARMS", "KEY RING",
        "KEYRING", "KEYRINGS", "KEY-CHAINS", "KEY FOB", "PENDANT", "LARIAT", "HAIR", "HAIRCLIP",
        "HAIRCLIPS", "HAIRSLIDE", "HAIRBAND", "PURSE", "HANDBAG", "UMBRELLA",
        "SCARF", "SUNGLASSES", "BAG", "BACKPACK", "RUCKSACK", "WASHBAG", "COSMETIC",
        "LUGGAGE TAG", "PASSPORT COVER", "GLASSES CASE", "LIP GLOSS", "EAR MUFF",
        "HAND WARMER", "PONCHO", "RAIN HAT", "SLIPPER", "JEWELLERY", "JEWEL STAND",
        "PERFUME", "TIARAS",
    ],
    "Papelería y manualidades": [
        "CARD", "CARDS", "POSTCARD", "POSTCARDS", "NOTEBOOK", "NOTEBOOKS", "JOURNAL",
        "SKETCHBOOK", "SCRAP BOOK", "SCRAPBOOK", "POCKET BOOK", "ADDRESS BOOK",
        "WRITING SET", "PENCIL", "PENCILS", "PEN", "PENS", "STICKER", "STICKERS",
        "BADGE", "BADGES", "WRAP", "WRAPPING", "GIFT TAGS", "TISSUES", "STATIONERY",
        "NOTELETS", "ALBUM", "NOTEPAD", "MEMO PAD", "ENVELOPE", "ENVELOPES",
        "INVITES", "RIBBON", "RIBBONS", "SHARPENER", "SHARPNER", "ERASER", "ERASERS",
        "RUBBER", "RUBBERS", "HIGHLIGHTER", "RULER", "EXERCISE BOOKS", "BOOK MARK",
        "BOOKCOVER", "TAPE", "CHALK", "STAMP", "STAMPS", "CALENDAR", "GIFT BOXES",
        "PAPER BOXES", "SEWING", "SEW ON", "IRON ON PATCHES", "MAKE YOUR OWN",
        "PAINT YOUR OWN",
    ],
    "Cocina y repostería": [
        "MUG", "MUGS", "CUP", "CUPS", "SAUCER", "TEAPOT", "TEA", "COFFEE", "CAKE",
        "CAKES", "CAKESTAND", "BAKING", "TIN", "TINS", "JAR", "JARS", "BOWL", "BOWLS",
        "PLATE", "PLATES", "PLATTER", "TRAY", "TRAYS", "CUTLERY", "SPOON", "SPOONS",
        "KITCHEN", "PANTRY", "APRON", "OVEN GLOVE", "OVEN MITT", "TEA TOWEL",
        "TEA TOWELS", "TEATOWELS", "NAPKINS", "NAPKIN", "CHOPPING", "LUNCH BOX",
        "LUNCHBOX", "JUG", "PAN", "EGG CUP", "EGG CUPS", "EGG WARMER", "EGG HOLDER",
        "COSY", "BREAD BIN", "BUTTER DISH", "STRAWS", "DOILIES", "COASTER",
        "COASTERS", "PLACEMAT", "PLACEMATS", "FOOD COVER", "CHOPSTICKS", "TOASTRACK",
        "SCALES", "ROLLING PIN", "COOKIE CUTTER", "COOKIE CUTTERS", "BEAKER",
        "BEAKERS", "TUMBLER", "GOBLET", "GLASS", "GLASSES", "RAMEKINS", "CADDY",
        "CONTAINER", "CANISTER", "CANNISTER", "TABLECLOTH", "TABLE CLOTH",
        "PETIT FOUR", "COLANDER", "BISCUIT", "SQUEEZER", "BOTTLE OPENER",
        "SALAD SERVERS", "SUGAR TONGS", "POPCORN", "WASHING UP GLOVES", "DRINKS",
        "JAM MAKING", "COOKING SET",
    ],
    "Jardín y flores": [
        "GARDEN", "GARDENING", "PLANTER", "PLANTERS", "PLANT", "WATERING CAN",
        "BIRD HOUSE", "BIRDHOUSE", "BIRD BOX", "BIRD FEEDER", "BIRDFEEDER",
        "BIRD TABLE", "DOVECOTE", "PICNIC", "PARASOL", "HAMMOCK", "WINDMILL",
        "WINDCHIME", "WINDSOCK", "BEACH", "FLOWER POT", "BIRD BATH", "GNOME",
        "THERMOMETER", "HERB MARKER", "SEED", "KNEELING PAD", "SECATEURS", "PAIL",
        "SANDCASTLE", "BARBECUE", "GROW YOUR OWN", "POTTING SHED",
    ],
    "Decoración y hogar": [
        "FRAME", "PHOTOFRAME", "MIRROR", "CLOCK", "CUSHION", "WALL ART", "CANVAS",
        "PICTURE", "PLAQUE", "SIGN", "LAMP", "LAMPSHADE", "LIGHTS", "LIGHT",
        "NIGHTLIGHT", "CHANDELIER", "GARLAND", "HANGING", "DECORATION",
        "DECORATIONS", "HEART", "HEARTS", "STAR", "VASE", "ARTIFICIAL FLOWER",
        "ART FLOWER", "DOORMAT", "DOOR MAT", "DOORSTOP", "HOOK", "HOOKS", "SHELF",
        "CABINET", "DRAWER", "DRAWERS", "BASKET", "BASKETS", "STORAGE", "BOX",
        "BOXES", "CHEST", "QUILT", "THROW", "BLANKET", "RUG", "CURTAIN",
        "HOT WATER BOTTLE", "MAGNET", "MAGNETS", "TABLE", "CHAIR", "STOOL", "WICKER",
        "ORGANISER", "LETTERS", "BLOCK WORD", "COAT RACK", "MAGAZINE RACK",
        "LETTER RACK", "KEY HOLDER", "PHOTO CLIP", "SOAP DISH", "SOAP HOLDER",
        "BATHROOM", "TOILET", "FLANNEL", "TOWEL", "BATH SPONGE", "IRONING BOARD",
        "LAUNDRY", "PEGS", "PAPERWEIGHT", "CHALKBOARD", "BLACKBOARD", "MEMO BOARD", "MEMOBOARD",
        "DOOR HANGER", "MONEY BOX", "PIGGY BANK", "MONEY BANK", "TRINKET", "POUFFE",
        "DRESSER", "SIDEBOARD", "WALL TIDY", "COVER", "MOBILE", "MATCHES",
        "SCISSOR", "SCISSORS", "TORCH", "SCREWDRIVER", "SPIRIT LEVEL",
        "TAPE MEASURE", "RADIO", "DISCO BALL", "SHELL", "SHELLS", "TOADSTOOL",
        "MUSHROOM", "FARM ANIMAL", "HEN HOUSE", "DOG", "CAT", "COLLAR", "BIN",
    ],
}


def _patron(palabras: list[str]) -> re.Pattern:
    """Une las palabras en una regex con límite de palabra (\\b).

    El límite evita falsos positivos: RING no matchea STRING y PAN no
    matchea PANTRY. re.escape protege guiones y apóstrofes (T-LIGHT, KID'S).
    """
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in palabras) + r")\b")


_PATRON_EXCLUIR = _patron(PALABRAS_EXCLUIR)
_PATRONES = [(interes, _patron(palabras)) for interes, palabras in REGLAS.items()]


def asignar_interes(descripcion) -> str:
    """Devuelve el interés del cuestionario para una descripción de producto."""
    texto = str(descripcion).upper()
    if _PATRON_EXCLUIR.search(texto):
        return EXCLUIDO
    for interes, patron in _PATRONES:
        if patron.search(texto):
            return interes
    return INTERES_DEFECTO


def construir_catalogo_app(catalogo: pd.DataFrame) -> pd.DataFrame:
    """Arma el catálogo para la app a partir del catálogo categorizado.

    Espera las columnas stock_code, description, precio y categoria.
    Devuelve stock_code, description, price, category e interes, sin
    productos excluidos y sin precio o categoría faltantes.
    """
    app = catalogo.rename(columns={"precio": "price", "categoria": "category"})
    app = app[["stock_code", "description", "price", "category"]].copy()
    app["description"] = app["description"].astype(str).str.strip()
    app["interes"] = app["description"].apply(asignar_interes)

    app = app[app["interes"] != EXCLUIDO]
    app = app[app["price"].notna() & (app["price"] > 0) & app["category"].notna()]
    return app.sort_values("stock_code").reset_index(drop=True)


def tabla_intereses(catalogo_app: pd.DataFrame, top: int = 3) -> pd.DataFrame:
    """Tabla interés → categorías: cuántos productos tiene cada interés,
    su precio mediano y las categorías del catálogo donde más aparece.

    No listamos la categoría genérica del clustering porque aporta productos
    a todos los intereses y no describe a ninguno.
    """
    filas = []
    for interes, grupo in catalogo_app.groupby("interes"):
        especificas = grupo.loc[grupo["category"] != CATEGORIA_GENERICA, "category"]
        principales = especificas.value_counts().head(top).index
        filas.append({
            "interes": interes,
            "n_productos": len(grupo),
            "precio_mediano": round(grupo["price"].median(), 2),
            "categorias_principales": "; ".join(principales),
        })
    return pd.DataFrame(filas).sort_values("n_productos", ascending=False).reset_index(drop=True)


def main():
    catalogo = pd.read_parquet(RUTA_ENTRADA)
    app = construir_catalogo_app(catalogo)
    intereses = tabla_intereses(app)

    RUTA_CATALOGO.parent.mkdir(parents=True, exist_ok=True)
    app.to_parquet(RUTA_CATALOGO, index=False)
    intereses.to_csv(RUTA_INTERESES, index=False, encoding="utf-8")

    excluidos = len(catalogo) - len(app)
    tamano_kb = RUTA_CATALOGO.stat().st_size / 1024
    print(f"Catálogo de entrada: {len(catalogo):,} productos")
    print(f"Catálogo app:        {len(app):,} productos ({excluidos} excluidos) → {RUTA_CATALOGO} ({tamano_kb:.0f} KB)")
    print(f"Tabla de intereses:  {RUTA_INTERESES}\n")
    print(intereses.to_string(index=False))


if __name__ == "__main__":
    main()
