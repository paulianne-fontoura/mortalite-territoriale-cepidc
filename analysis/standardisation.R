# Standardisation directe sur l'âge des taux de mortalité départementaux.
#
# Pour chaque département et chaque sexe, on calcule le taux brut et le taux
# standardisé sur l'âge par la méthode directe, en pondérant les taux par classe
# d'âge avec une population de référence explicite : la population standard
# européenne 2013 (Eurostat), ramenée aux 11 classes d'âge communes aux deux
# sources. Le taux standardisé répond à la question « quelle serait la mortalité
# de ce département si sa structure par âge était celle de la référence ? », ce
# qui rend les départements comparables.
#
# Le calcul passe par PHEindicatormethods::calculate_dsr, qui donne aussi
# l'intervalle de confiance à 95 % (méthode de Dobson). La formule directe,
# écrite à la main, sert de contrôle : les deux doivent coïncider. Les taux
# obtenus sont ensuite confrontés à ceux déjà publiés par le CépiDc (même
# référence).
#
# Par cause, les 18 chapitres réunis redonnent exactement les décès toutes
# causes (contrôle qualité de l'ETL). Comme la population et les poids sont
# les mêmes, le taux standardisé toutes causes est la somme des taux par
# chapitre, et l'écart d'un département à la France se décompose exactement en
# contributions par chapitre.
suppressMessages({
  library(readr); library(dplyr); library(tidyr); library(PHEindicatormethods)
})

lire <- function(fichier) {
  # codes département (« 01 », « 2A ») et chapitres (« 07 ») lus comme texte
  read_csv(fichier, show_col_types = FALSE,
           col_types = cols(.default = "?", dep_code = "c", chapitre = "c")) |>
    suppressWarnings()
}
df <- lire("data/processed/deces_pop_dep_age_sexe.csv")
causes <- lire("data/processed/deces_pop_dep_age_sexe_cause.csv")
glossaire <- lire("data/processed/glossaire_cim10.csv")

# Population standard européenne 2013, par classe d'âge (pour 100 000).
# Source : Eurostat, « Revision of the European Standard Population » (2013).
# Les tranches quinquennales d'origine sont cumulées sur les 11 classes communes.
ref <- tibble::tibble(
  classe_age = c("0-4", "5-14", "15-24", "25-34", "35-44", "45-54",
                 "55-64", "65-74", "75-84", "85-94", "95+"),
  poids = c(5000, 11000, 11500, 12500, 14000, 14000,
            12500, 10500, 6500, 2300, 200)
)
stopifnot(sum(ref$poids) == 100000)

# Formule directe, appliquée aux vecteurs par âge avant toute agrégation
dsr_formule <- function(deces, population, poids) {
  1e5 * sum(poids * deces / population) / sum(poids)
}

# DSR et intervalle de confiance par groupe, avec le contrôle de la formule
dsr <- function(data, ...) {
  data <- data |> left_join(ref, by = "classe_age")
  phe <- data |>
    group_by(...) |>
    calculate_dsr(x = deces, n = population, stdpop = poids) |>
    select(..., ic_bas = lowercl, ic_haut = uppercl, dsr_phe = value)
  data |>
    group_by(...) |>
    summarise(
      # le taux standardisé d'abord, sur les vecteurs par âge du groupe
      taux_standardise = dsr_formule(deces, population, poids),
      taux_brut = 1e5 * sum(deces) / sum(population),
      deces = sum(deces),
      population = sum(population),
      .groups = "drop"
    ) |>
    left_join(phe, by = join_by(...))
}

# --- Toutes causes, par département et sexe ---------------------------------
taux <- dsr(df, dep_code, departement, sexe)
ecart_phe <- with(taux, max(abs(taux_standardise - dsr_phe)))
stopifnot(ecart_phe < 1e-8)  # PHEindicatormethods et formule directe coïncident

# France entière : décès et population sommés par sexe et âge
france_age <- df |>
  group_by(sexe, classe_age) |>
  summarise(deces = sum(deces), population = sum(population), .groups = "drop")
france <- dsr(france_age, sexe)

taux <- taux |>
  left_join(france |> select(sexe, taux_france = taux_standardise), by = "sexe") |>
  mutate(
    vs_france = case_when(
      ic_bas > taux_france ~ "au-dessus",
      ic_haut < taux_france ~ "en dessous",
      TRUE ~ "non distinct"
    )
  ) |>
  select(dep_code, departement, sexe, deces, population, taux_brut,
         taux_standardise, ic_bas, ic_haut, vs_france)

# --- Par grand chapitre de causes -------------------------------------------
# Le DSR de PHEindicatormethods n'est pas calculé sous 10 décès (valeur NA) ;
# la formule directe, toujours définie, sert à la décomposition additive.
par_cause <- dsr(causes, dep_code, departement, sexe, chapitre) |>
  select(dep_code, departement, sexe, chapitre, deces, taux_standardise,
         ic_bas, ic_haut)
france_cause <- causes |>
  group_by(sexe, chapitre, classe_age) |>
  summarise(deces = sum(deces), population = sum(population), .groups = "drop") |>
  dsr(sexe, chapitre) |>
  select(sexe, chapitre, taux_france = taux_standardise)

# Additivité : la somme des chapitres redonne le taux toutes causes
somme_chap <- par_cause |>
  group_by(dep_code, sexe) |>
  summarise(somme = sum(taux_standardise), .groups = "drop") |>
  left_join(taux |> select(dep_code, sexe, taux_standardise), by = c("dep_code", "sexe"))
stopifnot(max(abs(somme_chap$somme - somme_chap$taux_standardise)) < 1e-8)

decomposition <- par_cause |>
  filter(sexe == "Tous sexes") |>
  left_join(france_cause, by = c("sexe", "chapitre")) |>
  mutate(contribution = taux_standardise - taux_france) |>
  left_join(glossaire |> select(chapitre, libelle_fr), by = "chapitre") |>
  select(dep_code, departement, chapitre, libelle_fr, taux_standardise,
         taux_france, contribution)

# --- Contrôle : comparaison aux taux publiés par le CépiDc -------------------
pub <- lire("data/processed/taux_cepidc_publies.csv")
ctrl <- taux |>
  left_join(pub, by = c("dep_code", "departement", "sexe")) |>
  mutate(
    ecart_std = taux_standardise - taux_standardise_cepidc,
    ecart_rel_std = 100 * ecart_std / taux_standardise_cepidc
  )

# Au niveau national, même confrontation au taux publié pour la France entière
france <- france |>
  left_join(lire("data/processed/taux_cepidc_publies_france.csv"), by = "sexe") |>
  mutate(ecart_rel_cepidc = 100 * (taux_standardise / taux_standardise_cepidc - 1))

arrondi <- function(t) mutate(t, across(where(is.double), \(x) round(x, 2)))
write_csv(arrondi(taux), "data/processed/taux_standardises.csv")
write_csv(arrondi(france), "data/processed/taux_france.csv")
write_csv(arrondi(par_cause), "data/processed/taux_par_cause.csv")
write_csv(arrondi(decomposition), "data/processed/decomposition_ecart_france.csv")
write_csv(arrondi(ctrl), "data/processed/controle_vs_cepidc.csv")

# --- Résumés imprimés -------------------------------------------------------
fr <- france |> filter(sexe == "Tous sexes")
cat(sprintf("[R] France entière (Tous sexes) : brut %.1f, standardisé %.1f [%.1f ; %.1f] /100 000, publié par le CépiDc %.1f (%+.1f %%)\n",
            fr$taux_brut, fr$taux_standardise, fr$ic_bas, fr$ic_haut,
            fr$taux_standardise_cepidc, fr$ecart_rel_cepidc))
ts <- taux |> filter(sexe == "Tous sexes") |> arrange(desc(taux_standardise))
cat("[R] 5 taux standardisés les plus élevés (Tous sexes) :\n")
print(ts |> select(departement, taux_brut, taux_standardise, ic_bas, ic_haut) |> head(5))
cat("[R] 5 taux standardisés les plus faibles (Tous sexes) :\n")
print(ts |> select(departement, taux_brut, taux_standardise, ic_bas, ic_haut) |> tail(5))
cat(sprintf("[R] rapport des extrêmes : %.2f (%s / %s)\n",
            max(ts$taux_standardise) / min(ts$taux_standardise),
            ts$departement[1], ts$departement[nrow(ts)]))
cat("[R] position par rapport à la France (IC 95 %) :\n")
print(table(ts$vs_france))
val <- ctrl |> filter(sexe == "Tous sexes")
cat(sprintf("[R] contrôle vs CépiDc (Tous sexes) : écart absolu moyen %.2f /100 000, écart relatif max %.2f %%, corrélation %.4f\n",
            mean(abs(val$ecart_std)), max(abs(val$ecart_rel_std)),
            cor(val$taux_standardise, val$taux_standardise_cepidc)))
cat(sprintf("[R] PHEindicatormethods vs formule directe : écart max %.1e\n", ecart_phe))
