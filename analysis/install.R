pkgs <- c("readr", "dplyr", "tidyr", "ggplot2", "scales")
new <- pkgs[!pkgs %in% rownames(installed.packages())]
if (length(new)) install.packages(new, repos = "https://cloud.r-project.org")
