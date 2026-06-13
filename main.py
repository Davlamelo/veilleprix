# -*- coding: utf-8 -*-
"""
main.py — VeillePrix
Pipeline complet : scrape → compare → sauvegarde → rapport → email.

Usage : python main.py [--source URL_ou_fichier] [--concurrent "Nom"]
"""
import argparse
from datetime import date

from comparateur import comparer, n_evenements, sauvegarder_releve
from rapport import envoyer_email, generer_html, sauvegarder
from scraper import scraper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="site_demo/index.html",
                    help="URL ou fichier HTML du catalogue concurrent")
    ap.add_argument("--concurrent", default="Grossimarket")
    args = ap.parse_args()

    date_jour = date.today()
    print(f"=== VeillePrix — relevé du {date_jour:%d/%m/%Y} ===")

    # 1. Scraping
    df = scraper(args.source)
    print(f"1. Scraping : {len(df)} produits extraits "
          f"({df['en_promo'].sum()} promos, {df['en_rupture'].sum()} ruptures)")

    # 2. Comparaison avec le relevé précédent
    comp = comparer(df)
    if comp["premier_releve"]:
        print("2. Comparaison : premier relevé — historique initialisé")
    else:
        print(f"2. Comparaison vs {comp['date_precedente']:%d/%m/%Y} : "
              f"{n_evenements(comp)} événements "
              f"({len(comp['baisses'])} baisses, {len(comp['hausses'])} hausses, "
              f"{len(comp['nouvelles_promos'])} promos, {len(comp['ruptures'])} ruptures)")

    # 3. Sauvegarde du relevé dans l'historique
    sauvegarder_releve(df, date_jour)
    print("3. Historique mis à jour")

    # 4. Rapport
    html = generer_html(comp, args.concurrent, date_jour)
    fichier = sauvegarder(html, date_jour)
    print(f"4. Rapport généré : {fichier}")

    # 5. Email (si configuré)
    sujet = f"Veille tarifaire {args.concurrent} — {date_jour:%d/%m/%Y}"
    if not comp["premier_releve"] and n_evenements(comp) > 0:
        sujet = f"⚠ {n_evenements(comp)} mouvements concurrent — {date_jour:%d/%m/%Y}"
    envoyer_email(html, sujet)


if __name__ == "__main__":
    main()
