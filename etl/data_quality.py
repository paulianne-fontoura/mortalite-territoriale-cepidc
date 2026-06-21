"""Contrôles qualité de la table appariée (auditabilité de la chaîne).

On vérifie la couverture (101 départements, 11 classes d'âge, 3 modalités de sexe),
l'absence de valeurs négatives ou manquantes, la cohérence interne (les décès
« Tous sexes » égalent la somme hommes + femmes), et un ordre de grandeur sur le
total national. Le bilan est exporté en JSON.
"""
from __future__ import annotations
import json

import pandas as pd

from etl import config as C


def run() -> dict:
    df = pd.read_csv(C.DECES_POP_CSV)
    ts = df[df["sexe"] == "Tous sexes"]
    hf = df[df["sexe"].isin(["Hommes", "Femmes"])]
    somme_hf = hf.groupby(["dep_code", "classe_age"])["deces"].sum().reset_index()
    cmp = ts.merge(somme_hf, on=["dep_code", "classe_age"], suffixes=("_ts", "_hf"))
    ecart_sexe = int((cmp["deces_ts"] != cmp["deces_hf"]).sum())

    cellules_attendues = 101 * len(C.CLASSES_AGE) * 3
    rep = {
        "annee": int(C.ANNEE),
        "departements": int(df["dep_code"].nunique()),
        "classes_age": int(df["classe_age"].nunique()),
        "modalites_sexe": int(df["sexe"].nunique()),
        "cellules": int(len(df)),
        "controles": {
            "cellules_attendues": cellules_attendues,
            "deces_negatifs": int((df["deces"] < 0).sum()),
            "population_nulle_ou_negative": int((df["population"] <= 0).sum()),
            "valeurs_manquantes": int(df[["deces", "population"]].isna().sum().sum()),
            "incoherences_tous_sexes_vs_h_f": ecart_sexe,
            "deces_total_tous_sexes": int(ts["deces"].sum()),
            "population_totale_tous_sexes": int(ts["population"].sum()),
        },
    }
    c = rep["controles"]
    rep["statut"] = "OK" if (c["deces_negatifs"] == 0 and c["population_nulle_ou_negative"] == 0
                             and c["valeurs_manquantes"] == 0 and c["incoherences_tous_sexes_vs_h_f"] == 0
                             and c["cellules_attendues"] == rep["cellules"]) else "ALERTE"

    C.QUALITE_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[qualité] statut={rep['statut']} — {rep['departements']} départements, "
          f"{rep['cellules']} cellules -> {C.QUALITE_JSON.name}")
    print(f"[qualité] décès toutes causes France entière {C.ANNEE} : "
          f"{c['deces_total_tous_sexes']:,}".replace(",", " "))
    return rep


if __name__ == "__main__":
    run()
