# Dictionnaire des données

## Sources réelles

- **CépiDc-Inserm**, portail open data des causes médicales de décès
  (`https://opendata-cepidc.inserm.fr`). Effectifs de décès et taux de mortalité
  (bruts, standardisés sur l'âge) par département, sexe et classe d'âge décennale,
  toutes causes, année 2023. Interrogés via l'API du portail. Données agrégées et
  anonymisées ; les données individuelles ne sont pas utilisées (autorisation CNIL).
- **INSEE**, estimations de population par département, sexe et âge, fichier
  `estim-pop-dep-sexe-aq` (séries 1975-2023), effectif au 1ᵉʳ janvier 2023.

## Table appariée `data/processed/deces_pop_dep_age_sexe.csv`
| Variable | Description |
|---|---|
| annee | Année (2023) |
| dep_code | Code département INSEE (`01`…`95`, `2A`, `2B`, `971`…`976`) |
| departement | Libellé du département |
| sexe | `Hommes`, `Femmes` ou `Tous sexes` |
| classe_age | Classe d'âge harmonisée (11 classes, de `0-4` à `95+`) |
| deces | Effectif de décès toutes causes (CépiDc) |
| population | Population au 1ᵉʳ janvier 2023 (INSEE) |

## Taux publiés par le CépiDc `data/processed/taux_cepidc_publies.csv`
| Variable | Description |
|---|---|
| dep_code, departement, sexe | Identifiants |
| taux_brut_cepidc | Taux brut publié par le CépiDc (pour 100 000) |
| taux_standardise_cepidc | Taux standardisé sur l'âge publié par le CépiDc (réf. Europe 2013) |

## Taux recalculés `data/processed/taux_standardises.csv`
Ajoute, par département et sexe, `taux_brut` et `taux_standardise` obtenus par
standardisation directe (référence : population européenne 2013), ainsi que les
totaux `deces` et `population`.

## Contrôle `data/processed/controle_vs_cepidc.csv`
Rapproche les taux recalculés des taux publiés ; colonnes `ecart_std` et
`ecart_rel_std` (écart absolu et relatif sur le taux standardisé).

## Qualité `data/processed/rapport_qualite.json`
Couverture (départements, classes d'âge, sexes, cellules), absence de valeurs
manquantes ou négatives, cohérence des décès entre sexes, totaux nationaux.
