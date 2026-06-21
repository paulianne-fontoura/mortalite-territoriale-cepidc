"""Téléchargement des données réelles : API open data du CépiDc et fichier INSEE.

Le portail du CépiDc expose une API JSON. Les filtres « sexe » sont transmis sous
forme de tableau (clé ``sex[]``), comme le fait l'interface du portail. On
récupère, pour l'année retenue et toutes causes confondues, les effectifs de
décès par département et classe d'âge, ainsi que les taux bruts et standardisés
déjà publiés par le CépiDc (pour contrôle).
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

from etl import config as C

UA = {"User-Agent": "mortalite-territoriale-cepidc/1.0", "Accept": "application/json"}


def _api(path: str, params: list[tuple[str, str]]) -> object:
    url = C.CEPIDC_API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def _query(measures: str, sexe_code: str, par_age: bool) -> list[dict]:
    """Une interrogation de l'API mortalityQuery pour un sexe donné."""
    params = [
        ("measures", measures),
        ("standpop", C.STANDPOP),
        ("from", str(C.ANNEE)), ("to", str(C.ANNEE)), ("year_info", "true"),
        ("sex[]", sexe_code),
        ("code", "0"),                       # toutes causes
        ("age_info", "true" if par_age else "false"),
        ("age_class", "10_years_age_group"), ("age_filter", "false"),
        ("agregration_1_24", ""),
        ("geo_class", C.GEO_CLASS),
        ("lang", "fr"),
    ]
    return _api("mortalityQuery", params)


def download() -> None:
    # Référentiel des départements (code <-> libellé)
    depts = _api("codes_geo", [("scale", C.GEO_CLASS)])
    C.RAW_DEPTS.write_text(json.dumps(depts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[download] {C.RAW_DEPTS.name} — {len(depts)} départements")

    # Effectifs de décès par département x classe d'âge x sexe
    deces = []
    for code in C.SEXES:
        deces += _query("raw_number_of_death", code, par_age=True)
    C.RAW_DECES.write_text(json.dumps(deces, ensure_ascii=False), encoding="utf-8")
    print(f"[download] {C.RAW_DECES.name} — {len(deces)} lignes (effectifs CépiDc)")

    # Taux bruts et standardisés déjà publiés par le CépiDc (par dép. x sexe)
    taux = []
    for code in C.SEXES:
        for mesure in ("crude_mortality_rate", "standardised_mortality_rate_by_age"):
            taux += _query(mesure, code, par_age=False)
    C.RAW_TAUX.write_text(json.dumps(taux, ensure_ascii=False), encoding="utf-8")
    print(f"[download] {C.RAW_TAUX.name} — {len(taux)} lignes (taux CépiDc publiés)")

    # Population INSEE par département, sexe et âge
    req = urllib.request.Request(C.INSEE_URL, headers={"User-Agent": UA["User-Agent"]})
    data = urllib.request.urlopen(req, timeout=120).read()
    C.RAW_INSEE.write_bytes(data)
    print(f"[download] {C.RAW_INSEE.name} — {len(data)} octets (population INSEE)")


if __name__ == "__main__":
    download()
