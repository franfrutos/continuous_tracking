## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Comparison of the models on ELPD and posterior predictive checks: the summaries of models.R
# and those of moment_matching.R, which has the same fits with moment matching in the points
# with a Pareto k above .7

# Loading packages----
source("scripts/functions.R")
source("scripts/load_data.R")

if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(dplyr, # Data wrangling
       tidyr,
       purrr,
       afex, # RM-ANOVA
       emmeans # Post-hoc contrasts
)

ensure_project_dirs()

afex_options(type = 3)

model_levels <- c("hybrid", "continuous", "discrete")
ppc_methods <- c("slider", "tet")
ppc_trial_type <- "peripheral"
time_bin <- .5
density_breaks <- seq(0, 1, by = .05)
density_mids <- (head(density_breaks, -1) + tail(density_breaks, -1)) / 2

# Observed responses ----
add_labels <- function(d) {
  mutate(d, participant_id = paste0("p", participant_id), method = factor(method, levels = ppc_methods))
}

# On the scale of the models: the Smithson-Verkuilen transformation of each trial, as in
# build_stan_data(), which moves the responses less than .001
ppc_obs <-
  samples %>%
  mutate(across(c(participant_id, method, trial_type), as.character)) %>%
  filter(trial_type == ppc_trial_type, method %in% ppc_methods, is.finite(visibility), is.finite(time_s)) %>%
  add_labels() %>%
  mutate(tb = round(time_s / time_bin) * time_bin) %>%
  group_by(participant_id, method, trial_in_block) %>%
  mutate(visibility = smithson_verkuilen(visibility, n())) %>%
  ungroup()

ppc_density_obs <-
  ppc_obs %>%
  group_by(participant_id, method) %>%
  reframe(
    bin_mid = density_mids,
    dens = hist(visibility, breaks = density_breaks, include.lowest = TRUE, plot = FALSE)$density
  )

# Observed responses per trial and time bin
ppc_trial_obs <-
  ppc_obs %>%
  group_by(participant_id, method, trial_in_block, tb) %>%
  summarise(obs = mean(visibility), .groups = "drop")

# Trajectories: both bands are between-trial 95% CIs, the mean of each trial in a time
# bin and the CI of that mean across trials, so that they are comparable
ppc_trajectory_obs <-
  ppc_trial_obs %>%
  group_by(participant_id, method, tb) %>%
  summarise(mean_obs = mean(obs), se = sd(obs) / sqrt(n()), n = n(), .groups = "drop") %>%
  mutate(
    lo = mean_obs - qt(.975, pmax(n - 1, 1)) * se,
    hi = mean_obs + qt(.975, pmax(n - 1, 1)) * se
  ) %>%
  rename(obs = mean_obs)

# Six participants that span from dichotomous to graded responses, ranked by the
# proportion of intermediate visibility (.15-.85), picked evenly
ppc_ranking <-
  ppc_obs %>%
  group_by(participant_id) %>%
  summarise(mid = mean(visibility > .15 & visibility < .85), .groups = "drop") %>%
  arrange(mid)

ppc_representative <-
  ppc_ranking %>%
  slice(round(seq(1, nrow(ppc_ranking), length.out = 6))) %>%
  pull(participant_id)

ppc_representative

# Comparison of the models with the ELPD of one folder ----
# The parameters and the posterior predictive checks are always those of output/models. The
# participants in exclude are left out of the comparison of ELPD
compare_models <- function(elpd_dir, models_dir = "output/models", exclude = NULL) {
  d_elpd <-
    read_csv(file.path(elpd_dir, "elpd_table.csv"), show_col_types = FALSE) %>%
    filter(trial_type == ppc_trial_type, !participant_id %in% exclude) %>%
    mutate(
      participant_id = factor(participant_id),
      method = factor(method, levels = ppc_methods),
      model = factor(model, levels = model_levels)
    )

  # Preregistered: RM-ANOVA on ELPD with model and method as within-subject factors and, if
  # the model factor is significant, post-hoc comparisons of the models within each method,
  # Holm-corrected. The pointwise PSIS-LOO is the main analysis, and leaving out whole trials
  # is a robustness check, to interpret with care because with 8 trials per fit, leaving out a
  # whole trial gives high Pareto k
  compare_scheme <- function(s) {
    d <- filter(d_elpd, scheme == s)

    complete_ids <-
      d %>%
      distinct(participant_id, method, model) %>%
      count(participant_id) %>%
      filter(n == length(model_levels) * length(ppc_methods)) %>%
      pull(participant_id)

    d <-
      d %>%
      filter(participant_id %in% complete_ids) %>%
      droplevels()

    wins <-
      d %>%
      group_by(method, participant_id) %>%
      slice_max(elpd, n = 1) %>%
      ungroup() %>%
      count(method, model, .drop = FALSE, name = "n_best")

    fit <-
      aov_ez(
        id = "participant_id",
        dv = "elpd",
        data = d,
        within = c("model", "method"),
        anova_table = list(correction = "GG", es = "pes")
      )

    list(
      n = nlevels(d$participant_id),
      wins = wins,
      anova = fit$anova_table,
      posthoc = summary(pairs(emmeans(fit, ~ model | method), adjust = "holm"))
    )
  }

  elpd_pointwise <- compare_scheme("pointwise")
  elpd_trial <- compare_scheme("trial")

  # Each model relative to the hybrid: elpd_diff < 0 is worse than the hybrid, and z < -2
  # reliably worse
  vs_hybrid <-
    read_csv(file.path(elpd_dir, "elpd_compare.csv"), show_col_types = FALSE) %>%
    filter(
      trial_type == ppc_trial_type, contrast %in% c("hybrid - continuous", "hybrid - discrete"),
      !participant_id %in% exclude
    ) %>%
    mutate(
      method = factor(method, levels = ppc_methods),
      model = factor(sub("hybrid - ", "", contrast), levels = model_levels),
      elpd_diff = -elpd_diff,
      z = elpd_diff / se_diff
    )

  vs_hybrid_summary <-
    vs_hybrid %>%
    group_by(method, model) %>%
    summarise(
      n = n(),
      mean_elpd_diff = mean(elpd_diff),
      mean_z = mean(z),
      n_reliably_worse = sum(z < -2),
      p = t.test(elpd_diff)$p.value,
      .groups = "drop"
    ) %>%
    group_by(method) %>%
    mutate(p_holm = pmin(p.adjust(p, "holm"), 1)) %>%
    ungroup()

  # Data of the figures: ELPD
  fig_elpd <-
    d_elpd %>%
    filter(scheme == "pointwise") %>%
    droplevels()

  # Mean of each model with its within-subject SE (Cousineau-Morey), within each method.
  # It is descriptive: the differences between models are in the paired contrasts
  fig_elpd_means <-
    fig_elpd %>%
    group_by(method) %>%
    group_modify(~ {
      grand_mean <- mean(.x$elpd)
      n_models <- n_distinct(.x$model)
      .x %>%
        group_by(participant_id) %>%
        mutate(elpd_norm = elpd - mean(elpd) + grand_mean) %>%
        ungroup() %>%
        group_by(model) %>%
        summarise(mean = mean(elpd), se = sd(elpd_norm) / sqrt(n()) * sqrt(n_models / (n_models - 1)), .groups = "drop")
    }) %>%
    ungroup()

  # ELPD centred within participant x method, with the participants ordered by the
  # advantage of the hybrid
  fig_elpd_centred <-
    fig_elpd %>%
    group_by(participant_id, method) %>%
    mutate(elpd_c = elpd - mean(elpd)) %>%
    ungroup()

  participant_order <-
    fig_elpd_centred %>%
    filter(model == "hybrid") %>%
    group_by(participant_id) %>%
    summarise(h = mean(elpd_c), .groups = "drop") %>%
    arrange(h) %>%
    pull(participant_id)

  fig_elpd_centred <- mutate(fig_elpd_centred, participant_id = factor(participant_id, levels = participant_order))

  # Largest R-hat of all the parameters of the three models
  rhat_max <- max(read_csv(file.path(models_dir, "params.csv"), show_col_types = FALSE)$rhat, na.rm = TRUE)

  # Posterior predictive checks
  read_ppc <- function(file) {
    read_csv(file.path(models_dir, file), show_col_types = FALSE) %>%
      filter(trial_type == ppc_trial_type) %>%
      add_labels() %>%
      mutate(model = factor(model, levels = model_levels))
  }

  ppc_density_models <- read_ppc("ppc_density.csv")
  ppc_trial_models <- read_ppc("ppc_trial.csv")

  ppc_trajectory_models <-
    ppc_trial_models %>%
    group_by(participant_id, method, model, time_bin) %>%
    summarise(m = mean(pred_mean), se = sd(pred_mean) / sqrt(n()), n = n(), .groups = "drop") %>%
    mutate(
      pred_mean = m,
      pred_lo = m - qt(.975, pmax(n - 1, 1)) * se,
      pred_hi = m + qt(.975, pmax(n - 1, 1)) * se
    )

  list(
    elpd_pointwise = elpd_pointwise,
    elpd_trial = elpd_trial,
    vs_hybrid = vs_hybrid,
    vs_hybrid_summary = vs_hybrid_summary,
    rhat_max = rhat_max,
    fig_elpd = fig_elpd,
    fig_elpd_means = fig_elpd_means,
    fig_elpd_centred = fig_elpd_centred,
    ppc_density_obs = ppc_density_obs,
    ppc_density_models = ppc_density_models,
    ppc_trial_obs = ppc_trial_obs,
    ppc_trial_models = ppc_trial_models,
    ppc_trajectory_obs = ppc_trajectory_obs,
    ppc_trajectory_models = ppc_trajectory_models,
    ppc_representative = ppc_representative
  )
}

# Preregistered models ----
preregistered <- compare_models("output/models")

preregistered$elpd_pointwise
preregistered$elpd_trial
preregistered$vs_hybrid_summary

do.call(save_analysis_objects, c(list("model_comparison"), preregistered))

# Preregistered models with moment matching in the points with a Pareto k above .7 ----
matched <- compare_models("output/models/moment_matching")

matched$elpd_pointwise
matched$elpd_trial
matched$vs_hybrid_summary

# The same comparison without the participants with responses whose Pareto k is still above .7
# after moment matching
high_k_ids <-
  matched$fig_elpd %>%
  filter(pareto_k_max > .7) %>%
  distinct(participant_id, method)

without_high_k <-
  compare_models("output/models/moment_matching", exclude = as.character(unique(high_k_ids$participant_id)))

matched$high_k_ids <- high_k_ids
matched$elpd_without_high_k <- without_high_k$elpd_pointwise
matched$vs_hybrid_without_high_k <- without_high_k$vs_hybrid_summary

matched$elpd_without_high_k
matched$vs_hybrid_without_high_k

do.call(save_analysis_objects, c(list("model_comparison_mm"), matched))
