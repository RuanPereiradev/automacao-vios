"""Log do Jarvis: tela e logs/bot.log da pasta jarvis/ (antes vinha do main.py do Sam)."""
import logging
from pathlib import Path

PASTA_LOGS = Path("logs")


def configurar_log():
    PASTA_LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(PASTA_LOGS / "bot.log", encoding="utf-8"),
        ],
    )
