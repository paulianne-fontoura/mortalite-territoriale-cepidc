# Chiffres de la note, lus dans les tables produites par la chaîne.
#
# Écrit report/chiffres.tex (une macro LaTeX par chiffre cité dans la note) et
# report/tableau_extremes.tex (les lignes du tableau 1). La note ne contient
# ainsi aucun nombre tapé à la main : relancer la chaîne sur des données
# révisées met le texte à jour.
suppressMessages({library(readr); library(dplyr)})

lire <- function(fichier) {
  read_csv(file.path("data/processed", fichier), show_col_types = FALSE,
           col_types = cols(.default = "?", dep_code = "c", chapitre = "c")) |>
    suppressWarnings()
}
qualite <- jsonlite::fromJSON("data/processed/rapport_qualite.json")
taux <- lire("taux_standardises.csv") |> filter(sexe == "Tous sexes") |>
  arrange(desc(taux_standardise))
france <- lire("taux_france.csv") |> filter(sexe == "Tous sexes")
ctrl <- lire("controle_vs_cepidc.csv") |> filter(sexe == "Tous sexes")
decomp <- lire("decomposition_ecart_france.csv")
par_cause <- lire("taux_par_cause.csv") |> filter(sexe == "Tous sexes")

# Nombres à la française : espace fine des milliers, virgule décimale, vrai signe moins
nb <- function(x, d = 0) {
  s <- formatC(abs(x), format = "f", digits = d, big.mark = " ", decimal.mark = ",")
  s <- gsub(" ", "\\\\,", s)
  ifelse(x < 0, paste0("$-$", s), s)
}
signe <- function(x) ifelse(x > 0, paste0("+", nb(x)), nb(x))

dep <- function(code) taux |> filter(dep_code == code)
contrib <- function(code, chap) {
  decomp |> filter(dep_code == code, chapitre == chap) |> pull(contribution)
}
ecart <- function(code) sum(decomp$contribution[decomp$dep_code == code])
haut <- taux[1, ]
bas <- taux[nrow(taux), ]
positions <- table(factor(taux$vs_france, levels = c("au-dessus", "en dessous", "non distinct")))
mal_def <- sum(par_cause$deces[par_cause$chapitre == "16"])
md_outremer <- decomp |> filter(dep_code %in% c("971", "972", "973"), chapitre == "16")
telecharge <- as.Date(substr(min(qualite$provenance$telecharge_le), 1, 10))

macros <- c(
  annee = qualite$annee,
  dateDonnees = format(telecharge, "%d/%m/%Y"),
  nDep = qualite$departements,
  nCellules = nb(qualite$cellules),
  nCellulesCauses = nb(qualite$controles$cellules_par_cause),
  ecartChapitres = qualite$controles$cellules_ou_chapitres_different_du_total,
  decesTotal = nb(qualite$controles$deces_total_tous_sexes),
  popTotal = nb(qualite$controles$population_totale_tous_sexes / 1e6, 1),
  frBrut = nb(france$taux_brut),
  frStd = nb(france$taux_standardise),
  frIcBas = nb(france$ic_bas),
  frIcHaut = nb(france$ic_haut),
  frCepidc = nb(france$taux_standardise_cepidc, 1),
  frEcartCepidc = nb(france$ecart_rel_cepidc, 1),
  hautNom = haut$departement,
  hautStd = nb(haut$taux_standardise),
  hautIcBas = nb(haut$ic_bas),
  hautIcHaut = nb(haut$ic_haut),
  basNom = bas$departement,
  basStd = nb(bas$taux_standardise),
  rapportExtremes = nb(haut$taux_standardise / bas$taux_standardise, 1),
  creuseBrut = nb(dep("23")$taux_brut),
  creuseStd = nb(dep("23")$taux_standardise),
  seineBrut = nb(dep("93")$taux_brut),
  seineStd = nb(dep("93")$taux_standardise),
  guyaneBrut = nb(dep("973")$taux_brut),
  guyaneStd = nb(dep("973")$taux_standardise),
  nAuDessus = positions[["au-dessus"]],
  nEnDessous = positions[["en dessous"]],
  nNonDistinct = positions[["non distinct"]],
  ctrlCor = nb(cor(ctrl$taux_standardise, ctrl$taux_standardise_cepidc), 3),
  ctrlEcartMoyen = nb(mean(abs(ctrl$ecart_std)), 1),
  pdcEcart = signe(ecart("62")),
  pdcTumeurs = signe(contrib("62", "02")),
  pdcCirc = signe(contrib("62", "07")),
  pdcDigestif = signe(contrib("62", "09")),
  parisEcart = signe(ecart("75")),
  parisCirc = signe(contrib("75", "07")),
  parisTumeurs = signe(contrib("75", "02")),
  outremerMdMin = signe(min(md_outremer$contribution)),
  outremerMdMax = signe(max(md_outremer$contribution)),
  mayotteMd = signe(contrib("976", "16")),
  malDefinies = nb(mal_def),
  malDefiniesPct = nb(100 * mal_def / qualite$controles$deces_total_tous_sexes, 1)
)
lignes <- c(
  "% Fichier généré par analysis/chiffres.R - ne pas modifier à la main.",
  sprintf("\\newcommand{\\%s}{%s}", names(macros), macros)
)
writeLines(lignes, "report/chiffres.tex", useBytes = TRUE)

# Tableau 1 : France, cinq taux les plus élevés, cinq plus faibles
ligne <- function(nom, t) {
  sprintf("%s & %s & %s & %s -- %s \\\\", nom, nb(t$taux_brut), nb(t$taux_standardise),
          nb(t$ic_bas), nb(t$ic_haut))
}
tableau <- c(
  "% Fichier généré par analysis/chiffres.R - ne pas modifier à la main.",
  "\\begin{tabular}{lrrr}",
  "\\toprule",
  "Département & Taux brut & Taux standardisé & IC 95\\,\\% \\\\",
  "\\midrule",
  sprintf("\\textit{France entière} & \\textit{%s} & \\textit{%s} & \\textit{%s -- %s} \\\\",
          nb(france$taux_brut), nb(france$taux_standardise), nb(france$ic_bas),
          nb(france$ic_haut)),
  "\\addlinespace",
  vapply(1:5, \(i) ligne(taux$departement[i], taux[i, ]), ""),
  "\\addlinespace",
  vapply((nrow(taux) - 4):nrow(taux), \(i) ligne(taux$departement[i], taux[i, ]), ""),
  "\\bottomrule",
  "\\end{tabular}"
)
writeLines(tableau, "report/tableau_extremes.tex", useBytes = TRUE)
cat(sprintf("[R] %d chiffres -> report/chiffres.tex, tableau -> report/tableau_extremes.tex\n",
            length(macros)))
