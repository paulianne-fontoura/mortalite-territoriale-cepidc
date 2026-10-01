# Dictionnaire des données

## Sources réelles

- **CépiDc-Inserm**, portail open data des causes médicales de décès
  (`https://opendata-cepidc.inserm.fr`). Effectifs de décès par département, sexe
  et classe d'âge décennale, toutes causes et pour chacun des 18 grands chapitres
  de causes, taux publiés (bruts, standardisés sur l'âge) et libellés CIM-10 des
  chapitres, année 2023. Interrogés via l'API du portail. Données agrégées et
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

## Table par cause `data/processed/deces_pop_dep_age_sexe_cause.csv`
Mêmes colonnes que la table appariée, plus `chapitre` (`01` à `18`, voir
[GLOSSAIRE_CIM10.md](GLOSSAIRE_CIM10.md)). Les 18 chapitres réunis redonnent
exactement les décès toutes causes de chaque cellule.

## Taux publiés par le CépiDc `data/processed/taux_cepidc_publies.csv`
| Variable | Description |
|---|---|
| dep_code, departement, sexe | Identifiants |
| taux_brut_cepidc | Taux brut publié par le CépiDc (pour 100 000) |
| taux_standardise_cepidc | Taux standardisé sur l'âge publié par le CépiDc (réf. Europe 2013) |

Le taux standardisé publié pour la France entière, par sexe, est dans
`data/processed/taux_cepidc_publies_france.csv`.

## Taux recalculés `data/processed/taux_standardises.csv`
Par département et sexe, `taux_brut` et `taux_standardise` obtenus par
standardisation directe (référence : population européenne 2013), les totaux
`deces` et `population`, l'intervalle de confiance à 95 % (`ic_bas`, `ic_haut`,
méthode de Dobson) et `vs_france` (`au-dessus`, `en dessous` ou `non distinct`
selon que l'intervalle exclut ou non le taux national).

## Taux France entière `data/processed/taux_france.csv`
Taux brut et standardisé national par sexe, avec intervalle de confiance, calculés
sur les décès et la population de la France entière par classe d'âge, et
confrontés au taux publié par le CépiDc (`ecart_rel_cepidc`, en %).

## Taux par cause `data/processed/taux_par_cause.csv`
Par département, sexe et chapitre, `taux_standardise` et son intervalle de
confiance. L'intervalle n'est pas calculé sous 10 décès (valeur vide).

## Décomposition `data/processed/decomposition_ecart_france.csv`
Tous sexes, par département et chapitre : `taux_standardise` du département,
`taux_france` national pour le même chapitre et `contribution`, leur différence.
La somme des contributions d'un département égale l'écart de son taux
standardisé toutes causes au taux national.

## Contrôle `data/processed/controle_vs_cepidc.csv`
Rapproche les taux recalculés des taux publiés ; colonnes `ecart_std` et
`ecart_rel_std` (écart absolu et relatif sur le taux standardisé).

## Qualité `data/processed/rapport_qualite.json`
Couverture (départements, classes d'âge, sexes, cellules), absence de valeurs
manquantes ou négatives, cohérence des décès entre sexes et entre chapitres de
causes, totaux nationaux, provenance des fichiers sources.

## Provenance `data/processed/provenance.json`
Pour chaque fichier téléchargé, sa source, sa taille, son empreinte SHA-256 et
sa date de téléchargement.
