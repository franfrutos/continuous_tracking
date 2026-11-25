## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Fits of the three models (continuous, discrete and hybrid) to the slider and TET
# responses of each participant in the peripheral trials. The summaries of each cell
# (participant x method) are appended to output/models as soon as it ends, so an
# interrupted run resumes where it stopped: parameters, PSIS-LOO ELPD, differences in
# ELPD and posterior predictive quantities

# Loading packages----
source("scripts/functions.R")
source("scripts/load_data.R")

if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(dplyr, # Data wrangling
       purrr,
       readr, # Summaries of the fits
       loo, # PSIS-LOO
       posterior # Summaries of the draws
)

setup_cmdstan()
ensure_project_dirs()

config <- list(
  participants = levels(samples$participant_id),
  methods = c("slider", "tet"),
  trial_type = "peripheral",
  models = c("continuous", "discrete", "hybrid"),
  target_hz = 25,
  chains = 4,
  iter_warmup = 1000,
  iter_sampling = 1000,
  adapt_delta = .95,
  max_treedepth = 12,
  seed = 20260627
)

out_dir <- "output/models"
params_path <- file.path(out_dir, "params.csv")
elpd_path <- file.path(out_dir, "elpd_table.csv")
compare_path <- file.path(out_dir, "elpd_compare.csv")
density_path <- file.path(out_dir, "ppc_density.csv")
trial_path <- file.path(out_dir, "ppc_trial.csv")

density_breaks <- seq(0, 1, by = .05)
time_bin <- .5

param_vars <- list(
  continuous = c("attractor", "rho", "phi", "logit_attractor", "logit_rho", "log_phi"),
  discrete = c("state_mean", "theta", "init_dist", "phi", "state_logit", "logit_theta11", "logit_theta22", "log_phi"),
  hybrid = c("attractor_mean", "rho", "phi", "theta", "init_dist", "attractor_logit", "logit_rho", "logit_theta11",
             "logit_theta22", "log_phi")
)

contrasts_elpd <- list(c("hybrid", "continuous"), c("hybrid", "discrete"), c("continuous", "discrete"))

models <-
  set_names(config$models) %>%
  map(~ cmdstanr::cmdstan_model(paste0("models/", .x, ".stan"), cpp_options = list(PRECOMPILED_HEADERS = FALSE)))

d_models <-
  samples %>%
  mutate(across(c(participant_id, method, trial_type), as.character)) %>%
  filter(trial_type == config$trial_type, method %in% config$methods)

# Cells already in the summaries
done <- character(0)

if (file.exists(compare_path)) {
  done <- unique(do.call(paste, read_csv(compare_path, show_col_types = FALSE)[c("participant_id", "method", "trial_type")]))
}

# Fits ----
for (pid in config$participants) {
  for (method in config$methods) {
    if (paste(pid, method, config$trial_type) %in% done) next

    d_cell <-
      d_models %>%
      filter(participant_id == pid, method == !!method) %>%
      downsample_track(config$target_hz)

    prep <- build_stan_data(d_cell)
    d_stan <- prep$stan_data
    trial_cols <- split(seq_len(d_stan$N), prep$trial_id)
    bins <- round(prep$df$time_s / time_bin) * time_bin
    trial_groups <- split(seq_len(d_stan$N), list(prep$df$trial_in_block, bins), drop = TRUE)
    trial_keys <- stringr::str_split_fixed(names(trial_groups), "\\.", 2)

    elpd <- list()
    pointwise <- list()
    ppc_dens <- list()
    ppc_trial <- list()
    params <- list()

    for (model in config$models) {
      message(sprintf("p%s | %s | %s | %s | N = %d", pid, method, config$trial_type, model, d_stan$N))

      fit <-
        models[[model]]$sample(
          data = d_stan,
          init = function() init_values(model),
          seed = config$seed,
          chains = config$chains,
          parallel_chains = config$chains,
          iter_warmup = config$iter_warmup,
          iter_sampling = config$iter_sampling,
          adapt_delta = config$adapt_delta,
          max_treedepth = config$max_treedepth,
          refresh = 0,
          show_messages = FALSE
        )

      diagnostics <- fit$diagnostic_summary()
      divergences <- sum(diagnostics$num_divergent)
      max_treedepth_hit <- sum(diagnostics$num_max_treedepth)

      # ELPD: pointwise (the main result) and leaving out whole trials
      log_lik <- array(as.numeric(fit$draws("log_lik")), dim = dim(fit$draws("log_lik")))
      log_lik_trial <- array(0, dim = c(dim(log_lik)[1:2], length(trial_cols)))
      for (j in seq_along(trial_cols)) {
        log_lik_trial[, , j] <- apply(log_lik[, , trial_cols[[j]], drop = FALSE], 1:2, sum)
      }
      pointwise[[model]] <- psis_loo(log_lik)

      elpd[[model]] <-
        bind_rows(
          loo_row(pointwise[[model]], "pointwise") %>% mutate(loo_method = "psis"),
          loo_row(psis_loo(log_lik_trial), "trial") %>% mutate(loo_method = "psis")
        ) %>%
        mutate(
          participant_id = pid,
          method = method,
          trial_type = config$trial_type,
          model = model,
          n_obs = d_stan$N,
          n_trials = d_stan$J,
          divergences = divergences,
          max_treedepth_hit = max_treedepth_hit,
          .before = 1
        )

      # Parameters
      params[[model]] <-
        fit$summary(
          param_vars[[model]],
          "median",
          "sd",
          ~ posterior::quantile2(.x, probs = c(.05, .95)),
          posterior::default_convergence_measures()
        ) %>%
        mutate(
          participant_id = pid,
          method = method,
          trial_type = config$trial_type,
          model = model,
          divergences = divergences,
          max_treedepth_hit = max_treedepth_hit,
          .before = 1
        )

      # Posterior predictive quantities
      tag <- tibble(participant_id = pid, method = method, trial_type = config$trial_type, model = model)
      expected <- draws_by_obs(fit, "expected_response")
      y_rep <- draws_by_obs(fit, "y_rep_generative")

      ppc_dens[[model]] <- bind_cols(tag, ppc_density(y_rep, density_breaks))
      ppc_trial[[model]] <-
        bind_cols(
          tag,
          tibble(trial_in_block = as.integer(trial_keys[, 1]), time_bin = as.numeric(trial_keys[, 2])),
          ppc_by_group(expected, trial_groups)
        )

      rm(fit)
      gc()
    }

    # Differences in ELPD, the same as loo::loo_compare()
    compare <-
      map_dfr(contrasts_elpd, function(p) {
        d <- pointwise[[p[1]]]$pointwise[, "elpd_loo"] - pointwise[[p[2]]]$pointwise[, "elpd_loo"]
        se <- sqrt(length(d)) * sd(d)
        tibble(
          participant_id = pid,
          method = method,
          trial_type = config$trial_type,
          contrast = paste(p[1], "-", p[2]),
          elpd_diff = sum(d),
          se_diff = se,
          z = sum(d) / se
        )
      })

    append_csv(bind_rows(params), params_path)
    append_csv(bind_rows(elpd), elpd_path)
    append_csv(compare, compare_path)
    append_csv(bind_rows(ppc_dens), density_path)
    append_csv(bind_rows(ppc_trial), trial_path)
  }
}
