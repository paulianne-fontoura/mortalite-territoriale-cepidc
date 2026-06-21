# Figure 1 — comparaison brut vs standardisé par département (noir et blanc).
#
# Pour chaque département (toutes causes, tous sexes), on relie le taux brut
# (cercle vide) au taux standardisé sur l'âge (cercle plein). Les départements
# sont ordonnés par taux standardisé. L'écart entre les deux points mesure
# l'effet de la structure d'âge : il est important là où la population est âgée
# (le taux brut surestime) ou très jeune (il sous-estime).
suppressMessages({library(readr); library(dplyr); library(tidyr); library(ggplot2)})
dir.create("report/figures", showWarnings = FALSE, recursive = TRUE)

taux <- read_csv("data/processed/taux_standardises.csv", show_col_types = FALSE) |>
  filter(sexe == "Tous sexes")
nat <- read_csv("data/processed/deces_pop_dep_age_sexe.csv", show_col_types = FALSE) |>
  filter(sexe == "Tous sexes") |>
  summarise(t = 1e5 * sum(deces) / sum(population)) |>  # taux brut national (repère)
  pull(t)

ordre <- taux |> arrange(taux_standardise) |> pull(departement)
taux$departement <- factor(taux$departement, levels = ordre)

pts <- taux |>
  select(departement, taux_brut, taux_standardise) |>
  pivot_longer(c(taux_brut, taux_standardise), names_to = "type", values_to = "taux") |>
  mutate(type = recode(type,
                       taux_brut = "Taux brut",
                       taux_standardise = "Taux standardisé sur l'âge"))

p <- ggplot(taux) +
  geom_segment(aes(y = departement, yend = departement,
                   x = taux_brut, xend = taux_standardise),
               colour = "grey55", linewidth = 0.3) +
  geom_point(data = pts, aes(x = taux, y = departement, shape = type),
             colour = "black", size = 1.5) +
  scale_shape_manual(values = c("Taux brut" = 1, "Taux standardisé sur l'âge" = 19)) +
  scale_x_continuous(breaks = seq(0, 1800, 300)) +
  labs(
    x = "Taux de mortalité pour 100 000 habitants",
    y = NULL, shape = NULL,
    title = "Mortalité toutes causes par département, France, 2023",
    subtitle = "Taux brut et taux standardisé sur l'âge (population de référence : Europe 2013)",
    caption = "Sources : CépiDc-Inserm (open data) et INSEE (estimations de population). Calcul : standardisation directe."
  ) +
  theme_classic(base_size = 9) +
  theme(
    axis.text.y = element_text(size = 5),
    legend.position = "top",
    plot.title = element_text(face = "bold", size = 11),
    plot.caption = element_text(size = 6, colour = "grey30"),
    panel.grid.major.x = element_line(colour = "grey92", linewidth = 0.3)
  )

ggsave("report/figures/fig1_brut_vs_standardise.png", p,
       width = 7, height = 11, dpi = 200, bg = "white")
cat("[R] figure -> report/figures/fig1_brut_vs_standardise.png\n")
