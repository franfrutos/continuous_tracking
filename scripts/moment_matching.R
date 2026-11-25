## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Moment matching for the fits of models.R, only in the cells with a Pareto k above .7. The saved
# fits (output/models) keep their parameters and predictive checks, and only the ELPD changes. In
# the cells (participant x method) with a Pareto k above .7 in any model, the three models are
# fitted again, because the differences between them need their pointwise ELPD, which was not
# saved, and moment matching is applied in the points with a Pareto k above .7. Each cell is saved
# in output/models/moment_matching/parts as soon as it ends, and the ELPD summaries are written in
# output/models/moment_matching, with the same format as output/models, when all the cells are there
#
# It can run in several processes at the same time, each with its own part of the cells:
# Rscript scripts/moment_matching.R <worker> <number of workers>. Without arguments, it runs them all

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
       loo, # PSIS-LOO and moment matching
       posterior # Summaries of the draws
)

setup_cmdstan()
ensure_project_dirs()

args <- as.integer(commandArgs(TRUE))
worker <- if (length(args) == 2) args[1] else 1L
n_workers <- if (length(args) == 2) args[2] else 1L

config <- list(
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

saved_dir <- "output/models"
out_dir <- "output/models/moment_matching"
parts_dir <- file.path(out_dir, "parts")
exe_dir <- file.path(out_dir, "exe", worker) # Each process compiles its own copy
dir.create(parts_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(exe_dir, recursive = TRUE, showWarnings = FALSE)

contrasts_elpd <- list(c("hybrid", "continuous"), c("hybrid", "discrete"), c("continuous", "discrete"))

saved_elpd <- read_csv(file.path(saved_dir, "elpd_table.csv"), show_col_types = FALSE)
saved_compare <- read_csv(file.path(saved_dir, "elpd_compare.csv"), show_col_types = FALSE)

# The cells with a problem
all_cells <-
  saved_elpd %>%
  filter(scheme == "pointwise", pareto_k_max > .7) %>%
  distinct(participant_id, method) %>%
  arrange(participant_id, method)

message(nrow(all_cells), " cells with a Pareto k above .7")

cells <- all_cells[(seq_len(nrow(all_cells)) - 1L) %% n_workers == worker - 1L, ]

models <-
  set_names(config$models) %>%
  map(~ cmdstanr::cmdstan_model(
    paste0("models/", .x, ".stan"),
    dir = exe_dir,
    compile_model_methods = TRUE,
    cpp_options = list(PRECOMPILED_HEADERS = FALSE)
  ))

d_models <-
  samples %>%
  mutate(across(c(participant_id, method, trial_type), as.character)) %>%
  filter(trial_type == config$trial_type)

# Fits ----
for (i in seq_len(nrow(cells))) {
  pid <- as.character(cells$participant_id[i])
  method <- cells$method[i]
  part_path <- file.path(parts_dir, sprintf("%s_%s.rds", pid, method))
  if (file.exists(part_path)) next

  d_stan <-
    d_models %>%
    filter(participant_id == pid, method == !!method) %>%
    downsample_track(config$target_hz) %>%
    build_stan_data(compute_ppc = 0L) %>%
    pluck("stan_data")

  pointwise <- list()
  rows <- list()

  for (model in config$models) {
    message(sprintf("p%s | %s | %s", pid, method, model))

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
        sig_figs = 18, # Needed for moment matching
        refresh = 0,
        show_messages = FALSE
      )

    psis <- fit$loo(r_eff = TRUE)
    k_psis <- psis$diagnostics$pareto_k
    pointwise[[model]] <- psis
    loo_method <- "psis"

    if (any(k_psis > .7)) {
      matched <-
        tryCatch(
          fit$loo(r_eff = TRUE, moment_match = TRUE),
          error = function(e) {
            message("Moment matching failed: ", conditionMessage(e))
            NULL
          }
        )

      if (!is.null(matched)) {
        pointwise[[model]] <- matched
        loo_method <- "psis+moment_match"
      }
    }

    rows[[model]] <-
      loo_row(pointwise[[model]], "pointwise") %>%
      mutate(
        participant_id = as.numeric(pid),
        method = method,
        trial_type = config$trial_type,
        model = model,
        loo_method = loo_method,
        n_high_k_psis = sum(k_psis > .7),
        k_max_psis = max(k_psis)
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
        participant_id = as.numeric(pid),
        method = method,
        trial_type = config$trial_type,
        contrast = paste(p[1], "-", p[2]),
        elpd_diff = sum(d),
        se_diff = se,
        z = sum(d) / se
      )
    })

  saveRDS(list(elpd_table = bind_rows(rows), elpd_compare = compare), part_path)
}

# Summaries, when all the cells are there ----
part_files <- list.files(parts_dir, full.names = TRUE)

if (length(part_files) == nrow(all_cells)) {
  parts <- map(part_files, readRDS)
  new_elpd <- map_dfr(parts, "elpd_table")
  new_compare <- map_dfr(parts, "elpd_compare")
  redone <- distinct(new_elpd, participant_id, method)

  # The ELPD of the cells without problems stays as it was saved
  kept <-
    saved_elpd %>%
    anti_join(mutate(redone, scheme = "pointwise"), by = c("participant_id", "method", "scheme")) %>%
    mutate(
      n_high_k_psis = ifelse(scheme == "pointwise", round(prop_k_gt_0.7 * n_obs), NA),
      k_max_psis = ifelse(scheme == "pointwise", pareto_k_max, NA)
    )

  counts <- distinct(saved_elpd, participant_id, method, model, n_obs, n_trials, divergences, max_treedepth_hit)

  bind_rows(kept, left_join(new_elpd, counts, by = c("participant_id", "method", "model"))) %>%
    write_csv(file.path(out_dir, "elpd_table.csv"))

  saved_compare %>%
    anti_join(redone, by = c("participant_id", "method")) %>%
    bind_rows(new_compare) %>%
    write_csv(file.path(out_dir, "elpd_compare.csv"))

  # The parameters and the predictive checks do not change, so they stay in output/models
  message("All the cells are done.")
}
