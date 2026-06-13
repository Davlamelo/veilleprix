# -*- coding: utf-8 -*-
"""
comparateur.py — VeillePrix
Compare le relevé du jour avec le précédent et détecte les changements
qui méritent une action commerciale.
"""
from datetime import date
from pathlib import Path

import pandas as pd

SEUIL_VARIATION = 0.03   # 3% : en-dessous, on considère le prix stable
HISTORIQUE = Path("data/historique.csv")


def charger_historique() -> pd.DataFrame:
    if HISTORIQUE.exists():
        return pd.read_csv(HISTORIQUE, parse_dates=["date_releve"])
    return pd.DataFrame()


def sauvegarder_releve(df: pd.DataFrame, date_releve: date):
    df = df.copy()
    df["date_releve"] = pd.Timestamp(date_releve)
    histo = charger_historique()
    if not histo.empty:
        # un nouveau relevé le même jour remplace le précédent
        histo = histo[histo["date_releve"] != pd.Timestamp(date_releve)]
    histo = pd.concat([histo, df], ignore_index=True)
    HISTORIQUE.parent.mkdir(parents=True, exist_ok=True)
    histo.to_csv(HISTORIQUE, index=False)


def comparer(df_jour: pd.DataFrame) -> dict:
    """Compare avec le dernier relevé en historique.
    Retourne un dict d'événements : baisses, hausses, promos, ruptures, nouveautés."""
    histo = charger_historique()
    resultat = {
        "premier_releve": histo.empty,
        "baisses": [], "hausses": [], "nouvelles_promos": [],
        "fins_promo": [], "ruptures": [], "retours_stock": [],
        "nouveaux_produits": [], "produits_disparus": [],
        "date_precedente": None,
    }
    if histo.empty:
        return resultat

    derniere_date = histo["date_releve"].max()
    resultat["date_precedente"] = derniere_date.date()
    prec = histo[histo["date_releve"] == derniere_date].set_index("ref")
    jour = df_jour.set_index("ref")

    refs_communes = jour.index.intersection(prec.index)
    resultat["nouveaux_produits"] = [
        dict(jour.loc[r]) | {"ref": r} for r in jour.index.difference(prec.index)
    ]
    resultat["produits_disparus"] = [
        dict(prec.loc[r]) | {"ref": r} for r in prec.index.difference(jour.index)
    ]

    for ref in refs_communes:
        avant, apres = prec.loc[ref], jour.loc[ref]
        p_avant, p_apres = avant["prix"], apres["prix"]

        # variations de prix (hors promo pour comparer le fond)
        if pd.notna(p_avant) and pd.notna(p_apres) and p_avant > 0:
            variation = (p_apres - p_avant) / p_avant
            evt = {
                "ref": ref, "nom": apres["nom"], "categorie": apres["categorie"],
                "prix_avant": round(float(p_avant), 2),
                "prix_apres": round(float(p_apres), 2),
                "variation_pct": round(variation * 100, 1),
            }
            if variation <= -SEUIL_VARIATION:
                resultat["baisses"].append(evt)
            elif variation >= SEUIL_VARIATION:
                resultat["hausses"].append(evt)

        # promos
        if apres["en_promo"] and not avant["en_promo"]:
            resultat["nouvelles_promos"].append({
                "ref": ref, "nom": apres["nom"],
                "prix": round(float(p_apres), 2) if pd.notna(p_apres) else None,
                "prix_avant_promo": apres.get("prix_avant_promo"),
            })
        elif avant["en_promo"] and not apres["en_promo"]:
            resultat["fins_promo"].append({"ref": ref, "nom": apres["nom"]})

        # stock
        if apres["en_rupture"] and not avant["en_rupture"]:
            resultat["ruptures"].append({"ref": ref, "nom": apres["nom"]})
        elif avant["en_rupture"] and not apres["en_rupture"]:
            resultat["retours_stock"].append({"ref": ref, "nom": apres["nom"]})

    # tri par ampleur
    resultat["baisses"].sort(key=lambda e: e["variation_pct"])
    resultat["hausses"].sort(key=lambda e: -e["variation_pct"])
    return resultat


def n_evenements(comp: dict) -> int:
    return sum(len(comp[k]) for k in
               ["baisses", "hausses", "nouvelles_promos", "fins_promo",
                "ruptures", "retours_stock", "nouveaux_produits", "produits_disparus"])
