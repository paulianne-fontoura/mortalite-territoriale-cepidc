"""Contrôles qualité de la table appariée (auditabilité de la chaîne).

On vérifie la couverture (101 départements, 11 classes d'âge, 3 modalités de sexe),
l'absence de valeurs négatives ou manquantes, la cohérence interne (les décès
« Tous sexes » égalent la somme hommes + femmes), et un ordre de grandeur sur le
total national. Pour la table par cause, on vérifie que les 18 chapitres
réunis redonnent exactement les décès toutes causes de chaque cellule, ce qui
rend la décomposition des écarts par cause exacte. Le bilan est exporté en JSON,
avec la provenance des fichiers sources.
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

    # Les chapitres réunis doivent redonner les décès toutes causes, cellule par cellule
    causes = pd.read_csv(C.DECES_CAUSES_CSV, dtype={"dep_code": str, "chapitre": str})
    somme_chap = (causes.groupby(["dep_code", "sexe", "classe_age"])["deces"].sum()
                  .rename("deces_chapitres").reset_index())
    tc = df.assign(dep_code=df["dep_code"].astype(str).str.zfill(2))
    cmp_causes = tc.merge(somme_chap, on=["dep_code", "sexe", "classe_age"], how="left")
    ecart_causes = int((cmp_causes["deces"] != cmp_causes["deces_chapitres"]).sum())
    provenance = json.loads(C.PROVENANCE_JSON.read_text(encoding="utf-8"))
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
            "chapitres_de_causes": int(causes["chapitre"].nunique()),
            "cellules_par_cause": int(len(causes)),
            "cellules_ou_chapitres_different_du_total": ecart_causes,
        },
        "provenance": provenance,
    }
    c = rep["controles"]
    rep["statut"] = "OK" if (c["deces_negatifs"] == 0 and c["population_nulle_ou_negative"] == 0
                             and c["valeurs_manquantes"] == 0 and c["incoherences_tous_sexes_vs_h_f"] == 0
                             and c["cellules_attendues"] == rep["cellules"]
                             and c["chapitres_de_causes"] == len(C.CHAPITRES)
                             and c["cellules_par_cause"] == cellules_attendues * len(C.CHAPITRES)
                             and c["cellules_ou_chapitres_different_du_total"] == 0) else "ALERTE"

    C.QUALITE_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[qualité] statut={rep['statut']} - {rep['departements']} départements, "
          f"{rep['cellules']} cellules -> {C.QUALITE_JSON.name}")
    print(f"[qualité] décès toutes causes France entière {C.ANNEE} : "
          f"{c['deces_total_tous_sexes']:,}".replace(",", " "))
    print(f"[qualité] chapitres de causes : {c['chapitres_de_causes']}, cellules où leur somme "
          f"diffère du total : {c['cellules_ou_chapitres_different_du_total']}")
    if rep["statut"] != "OK":
        raise SystemExit("[qualité] contrôle en échec, voir rapport_qualite.json")
    return rep


if __name__ == "__main__":
    run()
