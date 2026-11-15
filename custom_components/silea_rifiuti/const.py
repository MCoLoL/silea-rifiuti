"""Costanti dell'integrazione Silea Raccolta Rifiuti."""

from datetime import timedelta

DOMAIN = "silea_rifiuti"
VERSION = "0.3.1"
REPO_URL = "https://github.com/MCoLoL/silea-rifiuti"

# Si presenta in modo riconoscibile, così Silea sa chi fa le richieste e dove trovare il progetto.
USER_AGENT = f"HomeAssistant-SileaRifiuti/{VERSION} (+{REPO_URL})"

CARD_FILE = "silea-rifiuti-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"

CONF_COMUNE = "comune"
CONF_COMUNE_NOME = "comune_nome"
CONF_VIA = "via"
CONF_VIA_NOME = "via_nome"
CONF_MESI = "mesi"
CONF_UTENZA = "utenza"

DEFAULT_MESI = 4
UPDATE_INTERVAL = timedelta(hours=12)
# Ogni installazione aggiorna con uno scarto fisso tra 0 e 59 minuti, per non arrivare tutte insieme.
MAX_OFFSET_MINUTES = 60
# Gli orari dei centri di raccolta cambiano di rado: basta una volta al giorno, per tutte le vie configurate.
CENTRI_INTERVAL = timedelta(hours=24)
CENTRI_RETRY = timedelta(minutes=30)
CENTRI_URL = "https://www.sileaspa.it/giorni-e-orari-centri-di-raccolta-comunali/"

AJAX_URL = "https://www.sileaspa.it/wp-admin/admin-ajax.php"
REFERER = "https://www.sileaspa.it/calendario-raccolta-rifiuti/"

DEFAULT_START = "05:30"
DEFAULT_END = "13:30"

# Tipi di raccolta: chiave stabile, nome mostrato, icona.
# L'ordine è quello in cui compaiono nei sensori.
TIPI: dict[str, tuple[str, str]] = {
    "umido": ("Umido", "mdi:food-apple-outline"),
    "carta": ("Carta e cartone", "mdi:newspaper-variant-outline"),
    "vetro": ("Vetro", "mdi:bottle-wine-outline"),
    "plastica": ("Plastica, lattine e tetrapak", "mdi:recycle"),
    "indifferenziato": ("Indifferenziato", "mdi:trash-can-outline"),
}


def tipo_da_servizio(servizio: str) -> str:
    """Riconduce il nome del servizio Silea a una chiave di TIPI (o a uno slug se nuovo)."""
    s = servizio.upper()
    if "UMIDO" in s or "ORGANIC" in s:
        return "umido"
    if "CARTA" in s:
        return "carta"
    if "VETRO" in s:
        return "vetro"
    if "PLASTICA" in s or "LATTINE" in s:
        return "plastica"
    if "INDIFF" in s or "SECCO" in s:
        return "indifferenziato"
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_") or "altro"
