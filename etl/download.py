"""Téléchargement des données réelles : API open data du CépiDc et fichier INSEE.

Le portail du CépiDc expose une API JSON. Les filtres « sexe » et « cause » sont
transmis sous forme de tableau (clés ``sex[]`` et ``code[]``), comme le fait
l'interface du portail. On récupère, pour l'année retenue :

- les effectifs de décès toutes causes par département et classe d'âge ;
- les mêmes effectifs pour chacun des 18 grands chapitres de causes ;
- les taux bruts et standardisés déjà publiés par le CépiDc (pour contrôle) ;
- les libellés et plages CIM-10 des chapitres, en français et en anglais.

Chaque fichier écrit est consigné dans ``provenance.json`` avec sa taille, son
empreinte SHA-256 et sa date de téléchargement : une révision des sources se
voit à l'empreinte, et les chiffres publiés restent rattachés à leur version.
"""
from __future__ import annotations
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from etl import config as C

UA = {"User-Agent": "mortalite-territoriale-cepidc/1.1", "Accept": "application/json"}

_provenance: list[dict] = []


def _api(path: str, params: list[tuple[str, str]]) -> object:
    url = C.CEPIDC_API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def _query(measures: str, sexe_code: str, par_age: bool,
           causes: list[str] | None = None, geo_class: str = C.GEO_CLASS) -> list[dict]:
    """Une interrogation de l'API mortalityQuery pour un sexe donné."""
    params = [
        ("measures", measures),
        ("standpop", C.STANDPOP),
        ("from", str(C.ANNEE)), ("to", str(C.ANNEE)), ("year_info", "true"),
        ("sex[]", sexe_code),
    ]
    # « 0 » = toutes causes ; sinon un code[] par chapitre demandé
    params += [("code[]", c) for c in causes] if causes else [("code", "0")]
    params += [
        ("age_info", "true" if par_age else "false"),
        ("age_class", "10_years_age_group"), ("age_filter", "false"),
        ("agregration_1_24", ""),
        ("geo_class", geo_class),
        ("lang", "fr"),
    ]
    return _api("mortalityQuery", params)


def _ecrire(path: Path, contenu: bytes, source: str) -> None:
    """Écrit un fichier brut et consigne sa provenance."""
    path.write_bytes(contenu)
    _provenance.append({
        "fichier": path.name,
        "source": source,
        "octets": len(contenu),
        "sha256": hashlib.sha256(contenu).hexdigest(),
        "telecharge_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def _json(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def download() -> None:
    # Référentiel des départements (code <-> libellé)
    depts = _api("codes_geo", [("scale", C.GEO_CLASS)])
    _ecrire(C.RAW_DEPTS, _json(depts), "CépiDc API codes_geo")
    print(f"[download] {C.RAW_DEPTS.name} - {len(depts)} départements")

    # Effectifs de décès toutes causes par département x classe d'âge x sexe
    deces = []
    for code in C.SEXES:
        deces += _query("raw_number_of_death", code, par_age=True)
    _ecrire(C.RAW_DECES, _json(deces), "CépiDc API mortalityQuery, toutes causes")
    print(f"[download] {C.RAW_DECES.name} - {len(deces)} lignes (effectifs CépiDc)")

    # Mêmes effectifs, ventilés par grand chapitre de causes
    causes = []
    for code in C.SEXES:
        causes += _query("raw_number_of_death", code, par_age=True, causes=C.CHAPITRES)
    _ecrire(C.RAW_DECES_CAUSES, _json(causes), "CépiDc API mortalityQuery, 18 chapitres")
    print(f"[download] {C.RAW_DECES_CAUSES.name} - {len(causes)} lignes (effectifs par cause)")

    # Taux bruts et standardisés déjà publiés par le CépiDc (par dép. x sexe)
    taux = []
    for code in C.SEXES:
        for mesure in ("crude_mortality_rate", "standardised_mortality_rate_by_age"):
            taux += _query(mesure, code, par_age=False)
    _ecrire(C.RAW_TAUX, _json(taux), "CépiDc API mortalityQuery, taux publiés")
    print(f"[download] {C.RAW_TAUX.name} - {len(taux)} lignes (taux CépiDc publiés)")

    # Taux standardisé publié pour la France entière (geo_class vide), par sexe
    national = []
    for code in C.SEXES:
        national += _query("standardised_mortality_rate_by_age", code, par_age=False,
                           geo_class="")
    _ecrire(C.RAW_TAUX_FRANCE, _json(national), "CépiDc API mortalityQuery, France entière")
    print(f"[download] {C.RAW_TAUX_FRANCE.name} - {len(national)} lignes (taux France publiés)")

    # Libellés et plages CIM-10 des chapitres, pour le glossaire
    for langue, chemin in C.RAW_CODES.items():
        codes = _api("codes_details", [("lang", langue)])
        _ecrire(chemin, _json(codes), f"CépiDc API codes_details ({langue})")
    print(f"[download] libellés CIM-10 en {len(C.RAW_CODES)} langues")

    # Population INSEE par département, sexe et âge
    req = urllib.request.Request(C.INSEE_URL, headers={"User-Agent": UA["User-Agent"]})
    data = urllib.request.urlopen(req, timeout=300).read()
    _ecrire(C.RAW_INSEE, data, C.INSEE_URL)
    print(f"[download] {C.RAW_INSEE.name} - {len(data)} octets (population INSEE)")

    C.PROVENANCE_JSON.write_text(
        json.dumps(_provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[download] provenance de {len(_provenance)} fichiers -> {C.PROVENANCE_JSON.name}")


if __name__ == "__main__":
    download()
