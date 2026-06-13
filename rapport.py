# -*- coding: utf-8 -*-
"""
rapport.py — VeillePrix
Génère le rapport HTML (format email) et l'envoie si SMTP configuré.
"""
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

ROUGE, ORANGE, VERT, GRIS = "#D32F2F", "#E65100", "#2E7D32", "#666"


def _ligne_prix(e: dict, couleur: str) -> str:
    return f"""<tr>
      <td style="padding:8px 12px;border-bottom:1px solid #eee">{e['nom']}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right">{e['prix_avant']:.2f} MAD</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;font-weight:bold">{e['prix_apres']:.2f} MAD</td>
      <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;color:{couleur};font-weight:bold">{e['variation_pct']:+.1f}%</td>
    </tr>"""


def _section_table(titre: str, lignes: list, couleur: str) -> str:
    if not lignes:
        return ""
    corps = "".join(_ligne_prix(e, couleur) for e in lignes)
    return f"""
    <h2 style="font-size:15px;color:{couleur};margin:24px 0 8px">{titre}</h2>
    <table style="width:100%;border-collapse:collapse;background:#fff;font-size:13px">
      <tr style="background:#f5f5f5">
        <th style="padding:8px 12px;text-align:left">Produit</th>
        <th style="padding:8px 12px;text-align:right">Avant</th>
        <th style="padding:8px 12px;text-align:right">Maintenant</th>
        <th style="padding:8px 12px;text-align:right">Variation</th>
      </tr>
      {corps}
    </table>"""


def _section_liste(titre: str, items: list, couleur: str, champ="nom") -> str:
    if not items:
        return ""
    lis = "".join(f'<li style="padding:3px 0">{i[champ]}</li>' for i in items)
    return f"""
    <h2 style="font-size:15px;color:{couleur};margin:24px 0 8px">{titre}</h2>
    <ul style="margin:0;padding-left:20px;font-size:13px;background:#fff;
               border-radius:6px;padding:12px 12px 12px 30px">{lis}</ul>"""


def generer_html(comp: dict, concurrent: str, date_jour: date) -> str:
    if comp["premier_releve"]:
        synthese = "Premier relevé enregistré — les comparaisons commenceront au prochain relevé."
        corps = ""
    else:
        n_baisses = len(comp["baisses"])
        n_actions = n_baisses + len(comp["nouvelles_promos"]) + len(comp["ruptures"])
        synthese = (f"<b>{n_actions} mouvements nécessitent votre attention</b> "
                    f"depuis le {comp['date_precedente']:%d/%m/%Y} : "
                    f"{n_baisses} baisse(s) de prix · "
                    f"{len(comp['nouvelles_promos'])} nouvelle(s) promo(s) · "
                    f"{len(comp['ruptures'])} rupture(s) chez le concurrent.")
        corps = (
            _section_table("▼ Baisses de prix — risque concurrentiel", comp["baisses"], ROUGE)
            + _section_liste("🏷 Nouvelles promotions", comp["nouvelles_promos"], ORANGE)
            + _section_table("▲ Hausses de prix — opportunité de marge", comp["hausses"], VERT)
            + _section_liste("✕ Ruptures chez le concurrent — opportunité commerciale",
                             comp["ruptures"], VERT)
            + _section_liste("Fins de promotion", comp["fins_promo"], GRIS)
            + _section_liste("Retours en stock", comp["retours_stock"], GRIS)
        )
        if not corps.strip():
            corps = '<p style="font-size:13px;color:#666">Aucun mouvement significatif cette semaine.</p>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;background:#f0f0f0;font-family:Arial,sans-serif">
<div style="max-width:640px;margin:0 auto;padding:24px 16px">
  <div style="background:#16161D;border-radius:10px 10px 0 0;padding:20px 24px">
    <div style="color:#fff;font-size:18px;font-weight:bold">Veille tarifaire — {concurrent}</div>
    <div style="color:#999;font-size:12px;margin-top:4px">Relevé du {date_jour:%d/%m/%Y} · généré automatiquement</div>
  </div>
  <div style="background:#fafafa;padding:20px 24px;border-radius:0 0 10px 10px">
    <p style="font-size:13.5px;line-height:1.6;background:#FFF3E0;border-left:4px solid {ORANGE};
              padding:12px 16px;border-radius:6px">{synthese}</p>
    {corps}
    <p style="font-size:11px;color:#999;margin-top:28px;border-top:1px solid #ddd;padding-top:12px">
      VeillePrix — veille concurrentielle automatisée · T. Ulrich David — Data Science & IA<br>
      Démonstration sur catalogue concurrent simulé.
    </p>
  </div>
</div>
</body></html>"""


def envoyer_email(html: str, sujet: str) -> bool:
    hote = os.getenv("SMTP_HOST")
    dest = os.getenv("RAPPORT_DESTINATAIRE")
    if not (hote and dest):
        print("Email non configuré — envoi ignoré (rapport sauvegardé localement).")
        return False
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = dest
    msg.set_content("Votre client mail ne supporte pas le HTML.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(hote, int(os.getenv("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        s.send_message(msg)
    print(f"Rapport envoyé à {dest}.")
    return True


def sauvegarder(html: str, date_jour: date) -> Path:
    out = Path("rapports")
    out.mkdir(exist_ok=True)
    fichier = out / f"veille_{date_jour:%Y-%m-%d}.html"
    fichier.write_text(html, encoding="utf-8")
    return fichier
