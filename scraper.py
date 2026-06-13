# -*- coding: utf-8 -*-
"""
scraper.py — VeillePrix
Scrape le catalogue du concurrent et retourne un DataFrame normalisé.
Fonctionne sur une URL (requests) ou un fichier HTML local.
"""
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ENTETES = {
    "User-Agent": "Mozilla/5.0 (VeillePrix; veille tarifaire; contact: tass.u.david@gmail.com)"
}


def charger_html(source: str) -> str:
    """Charge le HTML depuis une URL ou un fichier local."""
    if source.startswith(("http://", "https://")):
        r = requests.get(source, headers=ENTETES, timeout=30)
        r.raise_for_status()
        return r.text
    return Path(source).read_text(encoding="utf-8")


def extraire_prix(texte: str) -> float | None:
    """Extrait un montant suivi d'une devise.
    '12,50 €' → 12.5 | '1 234,56 €' → 1234.56 | '358.00 MAD' → 358.0"""
    m = re.search(r"([\d\s\u00a0\u202f]+[.,]?\d*)\s*(?:€|EUR|MAD|DH|Dhs?)", texte)
    if not m:
        return None
    brut = re.sub(r"[\s\u00a0\u202f]", "", m.group(1))
    return float(brut.replace(",", "."))


def scraper(source: str) -> pd.DataFrame:
    """Extrait les produits du catalogue concurrent.
    Retourne : ref, nom, categorie, prix, prix_avant_promo, en_promo, en_rupture."""
    html = charger_html(source)
    soup = BeautifulSoup(html, "html.parser")

    lignes = []
    for carte in soup.select(".produit"):
        ref = carte.get("data-ref", "")
        nom = carte.select_one(".nom")
        categorie = carte.select_one(".categorie")
        bloc_prix = carte.select_one(".prix")
        rupture = carte.select_one(".rupture") is not None
        promo = carte.select_one(".badge-promo") is not None
        prix_barre = carte.select_one(".prix-barre")

        prix = None
        prix_avant = None
        if bloc_prix:
            if promo and prix_barre:
                prix_avant = extraire_prix(prix_barre.get_text())
                # prix actuel = texte du bloc sans la partie barrée
                texte_promo = bloc_prix.get_text().replace(prix_barre.get_text(), "")
                prix = extraire_prix(texte_promo)
            else:
                prix = extraire_prix(bloc_prix.get_text())

        lignes.append({
            "ref": ref,
            "nom": nom.get_text(strip=True) if nom else "",
            "categorie": categorie.get_text(strip=True) if categorie else "",
            "prix": prix,
            "prix_avant_promo": prix_avant,
            "en_promo": promo,
            "en_rupture": rupture,
        })

    df = pd.DataFrame(lignes)
    if df.empty:
        raise ValueError("Aucun produit extrait — la structure du site a peut-être changé.")
    return df


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "site_demo/index.html"
    df = scraper(source)
    print(f"{len(df)} produits extraits")
    print(df.head(8).to_string(index=False))
