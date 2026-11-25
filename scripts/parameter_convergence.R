## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Exploratory: do the parameters of the hybrid model differ between the slider and the TET, and do
# the two methods recover the same parameters within a participant? Each parameter is read on its
# unbounded scale (logit for rho, the state means and the probabilities of staying in each state;
# log for phi), with its posterior median and SD. The difference between methods is a paired t
# test on the medians, Holm-corrected across parameters. The correlation is computed on the
# medians and with a measurement-error model that disattenuates it using the posterior SDs, with
# the probability that it is positive (probability of direction)

# Loading packages----
source("scripts/functions.R")

if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(dplyr, # Data wrangling
       tidyr,
       purrr,
       posterior, # Summaries of the measurement-error model
       effectsize # Interpretation of the probability of direction
)

setup_cmdstan()
ensure_project_dirs()

rhat_max <- 1.05

# Parameter and its name in the summaries
param_names <- c(
  rho = "logit_rho",
  phi = "log_phi",
  `attractor_mean[1]` = "attractor_logit[1]",
  `attractor_mean[2]` = "attractor_logit[2]",
  `theta[1,1]` = "logit_theta11",
  `theta[2,2]` = "logit_theta22"
)

# Measurement-error model ----
# A latent bivariate normal (models/me_corr.stan). The executable is compiled next to the
# model, because a random temporary path can be blocked by Windows Defender
me_model <- cmdstanr::cmdstan_model("models/me_corr.stan", cpp_options = list(PRECOMPILED_HEADERS = FALSE))

# Convergence of the parameters between methods ----
converge_params <- function(models_dir, names_vars) {
  d_params <-
    read_csv(file.path(models_dir, "params.csv"), show_col_types = FALSE) %>%
    filter(model == "hybrid", variable %in% names_vars) %>%
    mutate(variable = names(names_vars)[match(variable, names_vars)])

  # Fits that did not converge are left out
  not_converged <-
    d_params %>%
    filter(rhat > rhat_max) %>%
    distinct(participant_id, method)

  # One row per participant and parameter, with the median and SD in each method
  fig_params <-
    d_params %>%
    anti_join(not_converged, by = c("participant_id", "method")) %>%
    transmute(participant_id, method, variable, tm = median, ts = sd) %>%
    pivot_wider(names_from = method, values_from = c(tm, ts)) %>%
    filter(is.finite(tm_slider), is.finite(tm_tet)) %>%
    mutate(variable = factor(variable, levels = names(names_vars)))

  # Correlation on the medians
  params_naive <-
    fig_params %>%
    group_by(variable) %>%
    summarise(
      n = n(),
      r_pearson = cor(tm_slider, tm_tet),
      ci_lo = cor.test(tm_slider, tm_tet)$conf.int[1],
      ci_hi = cor.test(tm_slider, tm_tet)$conf.int[2],
      .groups = "drop"
    ) %>%
    arrange(variable)

  # Disattenuated correlation
  fit_me <- function(v) {
    d <- filter(fig_params, variable == v)
    values <- c(d$tm_slider, d$tm_tet)

    fit <-
      me_model$sample(
        data = list(
          N = nrow(d),
          x = (d$tm_slider - mean(values)) / sd(values),
          xse = d$ts_slider / sd(values),
          y = (d$tm_tet - mean(values)) / sd(values),
          yse = d$ts_tet / sd(values)
        ),
        seed = 20260627,
        chains = 4,
        parallel_chains = 4,
        iter_warmup = 1000,
        iter_sampling = 1000,
        adapt_delta = .95,
        refresh = 0,
        show_messages = FALSE
      )

    s <- fit$summary("rho", "median", ~ posterior::quantile2(.x, c(.025, .975)))

    # Probability of direction: the posterior probability that the correlation is positive,
    # interpreted with the rules of Makowski et al. (2019)
    pd <- mean(fit$draws("rho", format = "draws_matrix") > 0)

    tibble(
      variable = v, n = nrow(d), rho_me = s$median, lo = s$q2.5, hi = s$q97.5, pd = pd,
      pd_label = as.character(effectsize::interpret_pd(pd, rules = "makowski2019"))
    )
  }

  params_me <-
    names(names_vars) %>%
    map_dfr(fit_me) %>%
    mutate(variable = factor(variable, levels = names(names_vars))) %>%
    arrange(variable)

  # Difference between the methods in each parameter
  params_compare <-
    fig_params %>%
    group_by(variable) %>%
    group_modify(function(d, key) {
      test <- t.test(d$tm_tet, d$tm_slider, paired = TRUE)
      tibble(
        n = nrow(d),
        slider = mean(d$tm_slider),
        tet = mean(d$tm_tet),
        diff = mean(d$tm_tet - d$tm_slider),
        t = unname(test$statistic),
        df = unname(test$parameter),
        ci_low = test$conf.int[1],
        ci_high = test$conf.int[2],
        p = test$p.value
      )
    }) %>%
    ungroup() %>%
    mutate(p_holm = p.adjust(p, "holm"))

  list(
    not_converged = not_converged,
    params_compare = params_compare,
    params_naive = params_naive,
    params_me = params_me,
    fig_params = fig_params
  )
}

# Preregistered models ----
preregistered <- converge_params("output/models", param_names)

preregistered$not_converged
preregistered$params_compare
preregistered$params_naive
preregistered$params_me

# Parameters of the hybrid model in seconds ----
# A step lasts 40 ms (25 Hz) and the state can change at every step: expected stay in each
# state and time to cover half of the distance to the level of the current state, with the
# median across participants
params_hybrid <-
  read_csv("output/models/params.csv", show_col_types = FALSE) %>%
  filter(model == "hybrid") %>%
  select(participant_id, method, variable, median)

par_times <-
  params_hybrid %>%
  filter(variable %in% c("rho", "theta[1,1]", "theta[2,2]")) %>%
  pivot_wider(names_from = variable, values_from = median) %>%
  mutate(
    stay_low = .04 / (1 - `theta[1,1]`),
    stay_high = .04 / (1 - `theta[2,2]`),
    half = .04 * log(.5) / log(rho)
  ) %>%
  group_by(method) %>%
  summarise(across(c(stay_low, stay_high, half), median))

par_times

do.call(
  save_analysis_objects,
  c(list("parameter_convergence"), preregistered, list(params_hybrid = params_hybrid, par_times = par_times))
)
