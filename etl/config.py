"""Configuration de la chaîne de traitement - mortalité territoriale.

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

RAW_DECES = RAW / f"cepidc_deces_dep_age_sexe_{ANNEE}.json"
RAW_TAUX = RAW / f"cepidc_taux_publies_{ANNEE}.json"
RAW_TAUX_FRANCE = RAW / f"cepidc_taux_publies_france_{ANNEE}.json"
RAW_DEPTS = RAW / "cepidc_departements.json"

# --- Causes de décès : les 18 grands chapitres -------------------------------
# Le portail classe les causes selon la liste européenne abrégée (Eurostat),
# dont les 18 chapitres de niveau 1 sont codés « 1. » à « 18. » ; « 0 » désigne
# toutes causes confondues. Chaque chapitre couvre une plage de codes CIM-10,
# que l'API fournit avec ses libellés (codes_details) et dont on tire le
# glossaire du dépôt.
CHAPITRES = [f"{i}." for i in range(1, 19)]
RAW_DECES_CAUSES = RAW / f"cepidc_deces_dep_age_sexe_causes_{ANNEE}.json"
RAW_CODES = {"fr": RAW / "cepidc_codes_details_fr.json",
             "en": RAW / "cepidc_codes_details_en.json"}

# --- INSEE : population par département, sexe, âge --------------------------
INSEE_URL = ("https://www.insee.fr/fr/statistiques/fichier/1893198/"
             "estim-pop-dep-sexe-aq-1975-2023.xls")
RAW_INSEE = RAW / "insee_pop_dep_sexe_age_2023.xls"

# --- Sorties mises en forme -------------------------------------------------
DECES_POP_PARQUET = PROCESSED / "deces_pop_dep_age_sexe.parquet"
DECES_POP_CSV = PROCESSED / "deces_pop_dep_age_sexe.csv"
TAUX_PUBLIES_CSV = PROCESSED / "taux_cepidc_publies.csv"
TAUX_FRANCE_PUBLIES_CSV = PROCESSED / "taux_cepidc_publies_france.csv"
DECES_CAUSES_CSV = PROCESSED / "deces_pop_dep_age_sexe_cause.csv"
GLOSSAIRE_CSV = PROCESSED / "glossaire_cim10.csv"
QUALITE_JSON = PROCESSED / "rapport_qualite.json"
# Empreinte et date de chaque fichier source, pour savoir quelle version des
# données a produit les chiffres (les taux 2023 du CépiDc sont provisoires et
# l'INSEE révise ses estimations de population).
PROVENANCE_JSON = PROCESSED / "provenance.json"
# Glossaire versionné, régénéré depuis l'API à chaque exécution
GLOSSAIRE_MD = ROOT / "GLOSSAIRE_CIM10.md"

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
