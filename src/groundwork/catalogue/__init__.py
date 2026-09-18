"""Source catalogue: model, controlled vocabularies and rules.

Checked by the `catcheck` command. Not to be confused with `check`, which
validates data files against expectations — a different job on a different
kind of input.
"""

from groundwork.catalogue.model import Catalogue, CatalogueLoadError, Entry, load
from groundwork.catalogue.rules import REGISTRY, run

__all__ = ["REGISTRY", "Catalogue", "CatalogueLoadError", "Entry", "load", "run"]
