## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Exploratory: the parameters of the hybrid model expressed in seconds. The time of each
# participant comes from the posterior medians of the parameters: a stay in a state lasts on
# average 0.04 / (1 - theta) s, where theta is the probability of staying in that state, and the
# response covers half of the distance to the level of its state in 0.04 log(.5) / log(rho) s.
# The group value is the median across participants, with a bootstrap 95% CI

# Loading packages----
source("scripts/functions.R")

if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(dplyr, # Data wrangling
       tidyr,
       readr # Summaries of the fits
)

ensure_project_dirs()
set.seed(2026)

target_hz <- 25
step_s <- 1 / target_hz
n_boot <- 5000

hybrid_params <-
  read_csv("output/models/params.csv", show_col_types = FALSE) %>%
  filter(model == "hybrid") %>%
  mutate(participant_id = as.character(participant_id))

# Times of each participant and method ----
times_participant <-
  hybrid_params %>%
  filter(variable %in% c("rho", "theta[1,1]", "theta[2,2]")) %>%
  select(participant_id, method, variable, median) %>%
  pivot_wider(names_from = variable, values_from = median) %>%
  transmute(
    participant_id, method,
    stay_low = step_s / (1 - `theta[1,1]`),
    stay_high = step_s / (1 - `theta[2,2]`),
    half = step_s * log(.5) / log(rho)
  )

# Median across participants with its bootstrap 95% CI
boot_median <- function(x) {
  b <- replicate(n_boot, median(sample(x, replace = TRUE)))
  tibble(median = median(x), ci_low = quantile(b, .025), ci_high = quantile(b, .975))
}

times_summary <-
  times_participant %>%
  pivot_longer(c(stay_low, stay_high, half), names_to = "measure") %>%
  group_by(method, measure) %>%
  reframe(boot_median(value))

save_analysis_objects(
  "states",
  settings = list(target_hz = target_hz, n_boot = n_boot),
  times_participant = times_participant,
  times_summary = times_summary
)
