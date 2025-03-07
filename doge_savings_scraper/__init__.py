from importlib.metadata import version
from pathlib import Path

__version__ = version(__package__)


HOME_FOLDER = Path(__file__).resolve().parent
