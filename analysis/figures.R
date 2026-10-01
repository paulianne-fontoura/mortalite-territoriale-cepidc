# Figures de la note.
#
# Figure 1 - comparaison brut vs standardisé par département (noir et blanc).
# Pour chaque département (toutes causes, tous sexes), on relie le taux brut
# (cercle vide) au taux standardisé sur l'âge (cercle plein), entouré de son
# intervalle de confiance à 95 %. Les départements sont ordonnés par taux
# standardisé. L'écart entre les deux points mesure l'effet de la structure
# d'âge : il est important là où la population est âgée (le taux brut
# surestime) ou très jeune (il sous-estime).
#
# Figure 2 - décomposition de l'écart à la France par grand chapitre de causes.
# Chaque case donne la contribution d'un chapitre à l'écart entre le taux
# standardisé du département et celui de la France entière (pour 100 000).
# Rouge au-dessus de la France, bleu en dessous, gris neutre au milieu.
suppressMessages({library(readr); library(dplyr); library(tidyr); library(ggplot2)})
dir.create("report/figures", showWarnings = FALSE, recursive = TRUE)

lire <- function(fichier) {
  read_csv(fichier, show_col_types = FALSE,
           col_types = cols(.default = "?", dep_code = "c", chapitre = "c")) |>
    suppressWarnings()
}
taux <- lire("data/processed/taux_standardises.csv") |> filter(sexe == "Tous sexes")
ordre <- taux |> arrange(taux_standardise) |> pull(departement)
taux$departement <- factor(taux$departement, levels = ordre)

# --- Figure 1 ----------------------------------------------------------------
pts <- taux |>
  select(departement, taux_brut, taux_standardise) |>
  pivot_longer(c(taux_brut, taux_standardise), names_to = "type", values_to = "taux") |>
  mutate(type = recode(type,
                       taux_brut = "Taux brut",
                       taux_standardise = "Taux standardisé sur l'âge (IC 95 %)"))

p1 <- ggplot(taux) +
  geom_segment(aes(y = departement, yend = departement,
                   x = taux_brut, xend = taux_standardise),
               colour = "grey65", linewidth = 0.3) +
  geom_errorbarh(aes(y = departement, xmin = ic_bas, xmax = ic_haut),
                 height = 0.55, colour = "black", linewidth = 0.3) +
  geom_point(data = pts, aes(x = taux, y = departement, shape = type),
             colour = "black", size = 1.5) +
  scale_shape_manual(values = c("Taux brut" = 1,
                                "Taux standardisé sur l'âge (IC 95 %)" = 19)) +
  scale_x_continuous(breaks = seq(0, 1800, 300)) +
  labs(
    x = "Taux de mortalité pour 100 000 habitants",
    y = NULL, shape = NULL,
    title = "Mortalité toutes causes par département, France, 2023",
    subtitle = "Taux brut et taux standardisé sur l'âge (population de référence : Europe 2013)",
    caption = paste("Sources : CépiDc-Inserm (open data) et INSEE (estimations de population).",
                    "Calcul : standardisation directe, IC de Dobson.")
  ) +
  theme_classic(base_size = 9) +
  theme(
    axis.text.y = element_text(size = 5),
    legend.position = "top",
    plot.title = element_text(face = "bold", size = 11),
    plot.caption = element_text(size = 6, colour = "grey30"),
    panel.grid.major.x = element_line(colour = "grey92", linewidth = 0.3)
  )
ggsave("report/figures/fig1_brut_vs_standardise.png", p1,
       width = 7, height = 11, dpi = 200, bg = "white")
cat("[R] figure -> report/figures/fig1_brut_vs_standardise.png\n")

# --- Figure 2 ----------------------------------------------------------------
# Les huit chapitres qui varient le plus d'un département à l'autre gardent leur
# colonne, les dix autres sont regroupés ; la dernière colonne donne l'écart total.
decomp <- lire("data/processed/decomposition_ecart_france.csv")
glossaire <- lire("data/processed/glossaire_cim10.csv")
principaux <- decomp |>
  group_by(chapitre) |>
  summarise(dispersion = sd(contribution), .groups = "drop") |>
  slice_max(dispersion, n = 8) |>
  pull(chapitre)
court <- c("02" = "Tumeurs", "07" = "Circula-\ntoire", "08" = "Respira-\ntoire",
           "04" = "Endocrin.,\nmétabol.", "16" = "Causes\nmal\ndéfinies",
           "17" = "Causes\nexternes", "01" = "Infec-\ntieux", "05" = "Troubles\nmentaux",
           "09" = "Digestif", "06" = "Système\nnerveux", "12" = "Génito-\nurinaire")
colonnes <- decomp |>
  mutate(groupe = if_else(chapitre %in% principaux, chapitre, "autres")) |>
  group_by(departement, groupe) |>
  summarise(contribution = sum(contribution), .groups = "drop")
total <- decomp |>
  group_by(departement) |>
  summarise(contribution = sum(contribution), .groups = "drop") |>
  mutate(groupe = "total")
ordre_col <- decomp |>
  filter(chapitre %in% principaux) |>
  group_by(chapitre) |>
  summarise(d = sd(contribution)) |>
  arrange(desc(d)) |>
  pull(chapitre)
etiquettes <- c(court[ordre_col], autres = "Autres\nchapitres", total = "Écart\ntotal")
grille <- bind_rows(colonnes, total) |>
  mutate(
    groupe = factor(groupe, levels = c(ordre_col, "autres", "total"),
                    labels = etiquettes[c(ordre_col, "autres", "total")]),
    departement = factor(departement, levels = ordre)
  )
borne <- 60  # au-delà, la couleur sature (Mayotte, Guyane)

# l'écart total s'écrit en chiffres, sa couleur saturerait presque partout
cases <- grille |> filter(groupe != etiquettes[["total"]])
totaux <- grille |> filter(groupe == etiquettes[["total"]])

p2 <- ggplot(cases, aes(x = groupe, y = departement, fill = contribution)) +
  geom_tile(colour = "white", linewidth = 0.4) +
  geom_text(data = totaux, aes(label = sprintf("%+.0f", contribution)),
            size = 1.7, colour = "grey15", hjust = 1, nudge_x = 0.3) +
  scale_fill_gradient2(
    low = "#2a78d6", mid = "#f0efec", high = "#e34948", midpoint = 0,
    limits = c(-borne, borne), oob = scales::squish,
    breaks = c(-borne, -30, 0, 30, borne),
    labels = c(paste0("≤ -", borne), "-30", "0", "+30", paste0("≥ +", borne)),
    name = "Écart à la France\npour 100 000"
  ) +
  scale_x_discrete(position = "top", drop = FALSE) +
  labs(
    x = NULL, y = NULL,
    title = "D'où vient l'écart de chaque département à la France ?",
    subtitle = "Contribution de chaque grand chapitre de causes, taux standardisés, tous sexes, 2023",
    caption = paste("Lecture : une case rouge signale un chapitre qui pèse plus qu'en moyenne nationale.",
                    "Départements classés par taux standardisé.\nSources : CépiDc-Inserm et INSEE.",
                    "Chapitres de la liste européenne abrégée, voir GLOSSAIRE_CIM10.md.")
  ) +
  theme_minimal(base_size = 9) +
  theme(
    axis.text.y = element_text(size = 5),
    axis.text.x.top = element_text(size = 7, lineheight = 0.9),
    panel.grid = element_blank(),
    plot.title = element_text(face = "bold", size = 11),
    plot.caption = element_text(size = 6, colour = "grey30", hjust = 0),
    legend.title = element_text(size = 7),
    legend.text = element_text(size = 6)
  )
ggsave("report/figures/fig2_decomposition_causes.png", p2,
       width = 7.5, height = 11, dpi = 200, bg = "white")
cat("[R] figure -> report/figures/fig2_decomposition_causes.png\n")
