"""Nettoyage, harmonisation et appariement des deux sources.

On ramène les effectifs de décès du CépiDc et la population INSEE à un jeu commun
de 11 classes d'âge (voir ``config``), on les apparie par département, sexe et
classe d'âge, puis on exporte la table en Parquet et en CSV. La même opération
produit une seconde table ventilée par grand chapitre de causes. Les taux déjà
publiés par le CépiDc sont mis de côté dans un fichier distinct, qui sert de
référence de contrôle à l'étape de standardisation. Enfin le glossaire des
chapitres (libellés français et anglais, plages CIM-10) est régénéré depuis les
libellés diffusés par l'API.
"""
from __future__ import annotations
import json
import re

import pandas as pd

from etl import config as C


def _depts_label_to_code() -> dict:
    ref = json.loads(C.RAW_DEPTS.read_text(encoding="utf-8"))
    return {v["label"]: v["code"] for v in ref.values()}


def _deces() -> pd.DataFrame:
    """Effectifs de décès -> dép. x sexe x classe d'âge harmonisée."""
    lab2code = _depts_label_to_code()
    df = pd.DataFrame(json.loads(C.RAW_DECES.read_text(encoding="utf-8")))
    df = df.rename(columns={"depdom": "departement", "sexe": "sexe",
                            "cl_age10": "age_cepidc", "sum_dc": "deces"})
    df["dep_code"] = df["departement"].map(lab2code)
    df["classe_age"] = df["age_cepidc"].map(C.AGE_CEPIDC)
    df["deces"] = pd.to_numeric(df["deces"], errors="coerce")
    g = (df.groupby(["dep_code", "sexe", "classe_age"], as_index=False)["deces"].sum())
    return g


def _chapitre(libelle: str) -> str:
    """« 7. Maladies de l'appareil circulatoire » -> « 07 »."""
    m = re.match(r"^(\d+)\. ", libelle)
    if m is None:
        raise ValueError(f"libellé de chapitre inattendu : {libelle!r}")
    return m.group(1).zfill(2)


def _deces_causes() -> pd.DataFrame:
    """Effectifs par chapitre de causes -> dép. x sexe x classe d'âge x chapitre."""
    lab2code = _depts_label_to_code()
    df = pd.DataFrame(json.loads(C.RAW_DECES_CAUSES.read_text(encoding="utf-8")))
    df["dep_code"] = df["depdom"].map(lab2code)
    df["classe_age"] = df["cl_age10"].map(C.AGE_CEPIDC)
    df["chapitre"] = df["cause_of_death"].map(_chapitre)
    df["deces"] = pd.to_numeric(df["sum_dc"], errors="coerce")
    return (df.groupby(["dep_code", "sexe", "classe_age", "chapitre"], as_index=False)
              ["deces"].sum())


def glossaire() -> pd.DataFrame:
    """Chapitres de niveau 1 : code, libellés français et anglais, plage CIM-10."""
    tables = {}
    for langue, chemin in C.RAW_CODES.items():
        codes = json.loads(chemin.read_text(encoding="utf-8")).values()
        # le libellé du chapitre 18 répète ses codes (« Covid-19 : U071-U072,... »)
        lignes = [(_chapitre(c["label"]),
                   re.sub(r"\s*:\s*U[\dU,\s-]+$", "", c["label"].split(". ", 1)[1]),
                   c["icd_10_code"])
                  for c in codes if re.match(r"^\d+\. ", c["label"])]
        tables[langue] = pd.DataFrame(lignes, columns=["chapitre", f"libelle_{langue}", "cim10"])
    g = tables["fr"].merge(tables["en"].drop(columns="cim10"), on="chapitre", how="outer")
    g = g.sort_values("chapitre").reset_index(drop=True)[
        ["chapitre", "cim10", "libelle_fr", "libelle_en"]]
    if len(g) != len(C.CHAPITRES) or g.isna().any().any():
        raise ValueError("glossaire incomplet : chapitres ou libellés manquants")
    return g


def _ecrire_glossaire(g: pd.DataFrame) -> None:
    g.to_csv(C.GLOSSAIRE_CSV, index=False)
    lignes = [
        "# Glossaire des causes de décès (CIM-10)",
        "",
        "Les 18 grands chapitres de la liste européenne abrégée utilisée par le",
        "CépiDc, avec la plage de codes de la Classification internationale des",
        "maladies (CIM-10) que chacun regroupe. Fichier généré par",
        "`python -m etl.transform` depuis les libellés diffusés par l'API du",
        "CépiDc - ne pas modifier à la main.",
        "",
        "| Chapitre | CIM-10 | Libellé | English label |",
        "|---|---|---|---|",
    ]
    lignes += [f"| {r.chapitre} | {r.cim10} | {r.libelle_fr} | {r.libelle_en} |"
               for r in g.itertuples()]
    C.GLOSSAIRE_MD.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def _population() -> pd.DataFrame:
    """Population INSEE 2023 -> dép. x sexe x classe d'âge harmonisée."""
    valides = set(_depts_label_to_code().values())
    raw = pd.read_excel(C.RAW_INSEE, sheet_name=str(C.ANNEE), header=None, dtype=object)

    section, entete = raw.iloc[3], raw.iloc[4]                # libellés sexe / âge
    sexe_par_section = {"Ensemble": "Tous sexes", "Hommes": "Hommes", "Femmes": "Femmes"}
    blocs = {}                                                # colonne de début -> sexe
    for col in range(2, raw.shape[1]):
        lab = section[col]
        if isinstance(lab, str) and lab.strip() in sexe_par_section:
            blocs[col] = sexe_par_section[lab.strip()]

    lignes = []
    for i in range(5, raw.shape[0]):
        code = raw.iat[i, 0]
        if code is None or (isinstance(code, float) and pd.isna(code)):
            continue
        code = str(code).strip()                              # « 01 » texte, 971 entier
        if code not in valides:
            continue
        nom = str(raw.iat[i, 1]).strip()
        for start, sexe in blocs.items():
            for col in range(start, start + 20):              # 20 tranches quinquennales
                age_lab = entete[col]
                cls = C.AGE_INSEE.get(str(age_lab).strip())
                if cls is None:
                    continue
                pop = pd.to_numeric(raw.iat[i, col], errors="coerce")
                lignes.append((code, nom, sexe, cls, pop))

    pop = pd.DataFrame(lignes, columns=["dep_code", "departement", "sexe", "classe_age", "population"])
    return (pop.groupby(["dep_code", "departement", "sexe", "classe_age"], as_index=False)["population"]
               .sum())


def _taux_publies() -> pd.DataFrame:
    lab2code = _depts_label_to_code()
    df = pd.DataFrame(json.loads(C.RAW_TAUX.read_text(encoding="utf-8")))
    df["dep_code"] = df["depdom"].map(lab2code)
    brut = (df[df["tx_100000"].notna()][["dep_code", "depdom", "sexe", "tx_100000"]]
            .rename(columns={"depdom": "departement", "tx_100000": "taux_brut_cepidc"}))
    std = (df[df["tx_stand_age"].notna()][["dep_code", "sexe", "tx_stand_age"]]
           .rename(columns={"tx_stand_age": "taux_standardise_cepidc"}))
    out = brut.merge(std, on=["dep_code", "sexe"], how="outer")
    return out.sort_values(["sexe", "dep_code"]).reset_index(drop=True)


def run() -> pd.DataFrame:
    deces, pop = _deces(), _population()
    df = pop.merge(deces, on=["dep_code", "sexe", "classe_age"], how="left")
    df["deces"] = df["deces"].fillna(0).astype(int)
    df["population"] = df["population"].astype(int)
    df["classe_age"] = pd.Categorical(df["classe_age"], categories=C.CLASSES_AGE, ordered=True)
    df = df.sort_values(["sexe", "dep_code", "classe_age"]).reset_index(drop=True)
    df["annee"] = C.ANNEE

    cols = ["annee", "dep_code", "departement", "sexe", "classe_age", "deces", "population"]
    out = df[cols]
    out.to_parquet(C.DECES_POP_PARQUET, index=False)
    out.to_csv(C.DECES_POP_CSV, index=False)
    _taux_publies().to_csv(C.TAUX_PUBLIES_CSV, index=False)
    nat = pd.DataFrame(json.loads(C.RAW_TAUX_FRANCE.read_text(encoding="utf-8")))
    (nat[["sexe", "tx_stand_age"]]
        .rename(columns={"tx_stand_age": "taux_standardise_cepidc"})
        .to_csv(C.TAUX_FRANCE_PUBLIES_CSV, index=False))

    # Même appariement, ventilé par chapitre de causes
    causes = pop.merge(_deces_causes(), on=["dep_code", "sexe", "classe_age"], how="left")
    causes["deces"] = causes["deces"].fillna(0).astype(int)
    causes["population"] = causes["population"].astype(int)
    causes["classe_age"] = pd.Categorical(causes["classe_age"], categories=C.CLASSES_AGE,
                                          ordered=True)
    causes["annee"] = C.ANNEE
    causes = causes.sort_values(["sexe", "dep_code", "chapitre", "classe_age"])
    causes[["annee", "dep_code", "departement", "sexe", "chapitre", "classe_age",
            "deces", "population"]].to_csv(C.DECES_CAUSES_CSV, index=False)
    _ecrire_glossaire(glossaire())

    print(f"[transform] {len(out)} cellules (dép. x sexe x âge) -> {C.DECES_POP_CSV.name}")
    print(f"[transform] {out['dep_code'].nunique()} départements, "
          f"{out['classe_age'].nunique()} classes d'âge, {out['sexe'].nunique()} modalités de sexe")
    print(f"[transform] {len(causes)} cellules par cause -> {C.DECES_CAUSES_CSV.name}, "
          f"glossaire -> {C.GLOSSAIRE_MD.name}")
    return out


if __name__ == "__main__":
    run()
