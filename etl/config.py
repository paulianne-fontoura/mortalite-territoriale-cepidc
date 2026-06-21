"""Configuration de la chaîne de traitement — mortalité territoriale.

Deux sources ouvertes et agrégées :

- CépiDc (Inserm), portail open data des causes médicales de décès. API publique
  du portail https://opendata-cepidc.inserm.fr. Effectifs de décès et taux
  (bruts, standardisés sur l'âge) par département, sexe et classe d'âge décennale,
  toutes causes. Anonymisation et licence décrites sur le site du CépiDc.
- INSEE, estimations de population par département, sexe et âge (fichier
  estim-pop-dep-sexe-aq, séries 1975-2023), utilisées comme dénominateur.

Aucune donnée individuelle n'est mobilisée (celles-ci relèvent d'une autorisation
CNIL). Toutes les données téléchargées ici sont publiques et agrégées.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW, PROCESSED = DATA / "raw", DATA / "processed"
for d in (RAW, PROCESSED):
    d.mkdir(parents=True, exist_ok=True)

ANNEE = 2023

# --- CépiDc : API du portail open data -------------------------------------
CEPIDC_API = "https://opendata-cepidc.inserm.fr/bcmd/r/"
GEO_CLASS = "depdom"                              # échelle départementale
STANDPOP = "european_standard_population_2013"    # population de référence du CépiDc
# Sexe : code de l'API -> libellé harmonisé
SEXES = {"1": "Hommes", "2": "Femmes", "12": "Tous sexes"}

RAW_DECES = RAW / "cepidc_deces_dep_age_sexe_2023.json"
RAW_TAUX = RAW / "cepidc_taux_publies_2023.json"
RAW_DEPTS = RAW / "cepidc_departements.json"

# --- INSEE : population par département, sexe, âge --------------------------
INSEE_URL = ("https://www.insee.fr/fr/statistiques/fichier/1893198/"
             "estim-pop-dep-sexe-aq-1975-2023.xls")
RAW_INSEE = RAW / "insee_pop_dep_sexe_age_2023.xls"

# --- Sorties mises en forme -------------------------------------------------
DECES_POP_PARQUET = PROCESSED / "deces_pop_dep_age_sexe.parquet"
DECES_POP_CSV = PROCESSED / "deces_pop_dep_age_sexe.csv"
TAUX_PUBLIES_CSV = PROCESSED / "taux_cepidc_publies.csv"
QUALITE_JSON = PROCESSED / "rapport_qualite.json"

# --- Harmonisation des classes d'âge ---------------------------------------
# Le CépiDc diffuse des classes décennales en distinguant « < 1 » et « 1-4 ».
# L'INSEE diffuse des classes quinquennales dont la première est « 0-4 ».
# On ramène les deux sources à 11 classes communes, en regroupant « < 1 » et
# « 1-4 » en « 0-4 », puis en cumulant les tranches quinquennales par paires.
CLASSES_AGE = ["0-4", "5-14", "15-24", "25-34", "35-44", "45-54",
               "55-64", "65-74", "75-84", "85-94", "95+"]

# classes du CépiDc -> classe harmonisée
AGE_CEPIDC = {
    "< 1": "0-4", "1-4": "0-4", "5-14": "5-14", "15-24": "15-24",
    "25-34": "25-34", "35-44": "35-44", "45-54": "45-54", "55-64": "55-64",
    "65-74": "65-74", "75-84": "75-84", "85-94": "85-94", "95p": "95+",
}

# tranches quinquennales de l'INSEE -> classe harmonisée
AGE_INSEE = {
    "0 à 4 ans": "0-4", "5 à 9 ans": "5-14", "10 à 14 ans": "5-14",
    "15 à 19 ans": "15-24", "20 à 24 ans": "15-24",
    "25 à 29 ans": "25-34", "30 à 34 ans": "25-34",
    "35 à 39 ans": "35-44", "40 à 44 ans": "35-44",
    "45 à 49 ans": "45-54", "50 à 54 ans": "45-54",
    "55 à 59 ans": "55-64", "60 à 64 ans": "55-64",
    "65 à 69 ans": "65-74", "70 à 74 ans": "65-74",
    "75 à 79 ans": "75-84", "80 à 84 ans": "75-84",
    "85 à 89 ans": "85-94", "90 à 94 ans": "85-94",
    "95 ans et plus": "95+",
}
