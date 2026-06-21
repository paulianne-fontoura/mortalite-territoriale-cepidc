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
# Les taux obtenus sont confrontés à ceux déjà publiés par le CépiDc (même
# référence), comme contrôle de la chaîne.
suppressMessages({library(readr); library(dplyr); library(tidyr)})

df <- read_csv("data/processed/deces_pop_dep_age_sexe.csv", show_col_types = FALSE)

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

taux <- df |>
  left_join(ref, by = "classe_age") |>
  group_by(dep_code, departement, sexe) |>
  summarise(
    # rates computed on the per-âge vectors, AVANT toute agrégation des totaux
    taux_brut = 1e5 * sum(deces) / sum(population),
    # taux standardisé direct : moyenne des taux par âge pondérée par la référence
    taux_standardise = 1e5 * sum(poids * deces / population) / sum(poids),
    deces = sum(deces),
    population = sum(population),
    .groups = "drop"
  ) |>
  mutate(across(c(taux_brut, taux_standardise), \(x) round(x, 1)))

# Contrôle : comparaison aux taux publiés par le CépiDc
pub <- read_csv("data/processed/taux_cepidc_publies.csv", show_col_types = FALSE) |>
  mutate(dep_code = as.character(dep_code))
ctrl <- taux |>
  mutate(dep_code = as.character(dep_code)) |>
  left_join(pub, by = c("dep_code", "departement", "sexe")) |>
  mutate(
    ecart_std = taux_standardise - taux_standardise_cepidc,
    ecart_rel_std = 100 * ecart_std / taux_standardise_cepidc
  )

write_csv(taux, "data/processed/taux_standardises.csv")
write_csv(ctrl, "data/processed/controle_vs_cepidc.csv")

# --- Résumés imprimés -------------------------------------------------------
ts <- taux |> filter(sexe == "Tous sexes") |> arrange(desc(taux_standardise))
nat <- df |> filter(sexe == "Tous sexes") |>
  left_join(ref, by = "classe_age") |>
  summarise(brut = 1e5 * sum(deces) / sum(population),
            std = 1e5 * sum(poids * deces / population) / sum(poids))

cat(sprintf("[R] France entière (Tous sexes) : brut %.1f, standardisé %.1f /100 000\n",
            nat$brut, nat$std))
cat("[R] 5 taux standardisés les plus élevés (Tous sexes) :\n")
print(ts |> select(departement, taux_brut, taux_standardise) |> head(5))
cat("[R] 5 taux standardisés les plus faibles (Tous sexes) :\n")
print(ts |> select(departement, taux_brut, taux_standardise) |> tail(5))

ecart <- ts$taux_standardise
cat(sprintf("[R] écart extrêmes (standardisé) : %.1f (%s) vs %.1f (%s) ; rapport %.2f\n",
            max(ecart), ts$departement[which.max(ecart)],
            min(ecart), ts$departement[which.min(ecart)],
            max(ecart) / min(ecart)))

val <- ctrl |> filter(sexe == "Tous sexes")
cat(sprintf("[R] contrôle vs CépiDc (standardisé, Tous sexes) : écart absolu moyen %.2f /100 000, écart relatif max %.2f %%, corrélation %.4f\n",
            mean(abs(val$ecart_std)), max(abs(val$ecart_rel_std)),
            cor(val$taux_standardise, val$taux_standardise_cepidc)))
