## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

required_packages <- c(
  "here", "dplyr", "tidyr", "tibble", "readr", "purrr", "loo", "posterior", "MASS", "stringr"
)

missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing_packages) > 0) {
  stop(
    sprintf(
      "Missing required packages: %s",
      paste(missing_packages, collapse = ", ")
    )
  )
}

# loo, posterior, MASS and stringr are only called with :: (MASS would mask dplyr::select),
# and cmdstanr is loaded by setup_cmdstan()
suppressPackageStartupMessages(
  invisible(lapply(
    setdiff(required_packages, c("here", "loo", "posterior", "MASS", "stringr")),
    library,
    character.only = TRUE
  ))
)

setwd(here::here())

# Data functions ----
# All the session files of a folder, in the format of the task: one row per sample
read_sessions <- function(dir) {
  files <- list.files(dir, pattern = "^mib_.*\\.csv$", full.names = TRUE)
  if (length(files) == 0) {
    stop(sprintf("No session files (mib_*.csv) in '%s'.", dir))
  }
  read_csv(
    files,
    col_types = cols(
      participant_id = "c", age = "d", gender = "c", frame_rate = "d",
      phase = "c", block = "i", method = "c", trial_in_block = "i", trial_type = "c",
      time_s = "d", target_contrast = "d", response = "d"
    ),
    progress = FALSE
  )
}

# Ends of the slider scale: the lowest and highest values that the slider returned in the
# whole experiment. Because of a technical issue, the lowest position returned about 0.003
# instead of 0
slider_scale_range <- function(sessions) {
  range(sessions$response[sessions$method == "slider"], na.rm = TRUE)
}

# Responses normalized between the ends of the scale, so that they correspond to 0 and 1
normalize_scale <- function(x, scale_range) {
  pmin(pmax((x - scale_range[1]) / (scale_range[2] - scale_range[1]), 0), 1)
}

# Visibility (0-1) from the responses with a method, in the experimental trials: the
# button is held down while the target is not seen, the slider is normalized between the
# ends of the scale, and the TET is used as drawn
response_to_visibility <- function(response, method, slider_range) {
  switch(
    method,
    button = round(pmin(pmax(1 - response, 0), 1)),
    slider = normalize_scale(response, slider_range),
    tet = pmin(pmax(response, 0), 1)
  )
}

make_trial_means <- function(samples) {
  samples %>%
    group_by(participant_id, method, trial_type, trial_in_block) %>%
    summarise(mean_visibility = mean(visibility, na.rm = TRUE), .groups = "drop")
}

make_cell_means <- function(trials) {
  trials %>%
    group_by(participant_id, method, trial_type) %>%
    summarise(mean_visibility = mean(mean_visibility, na.rm = TRUE), .groups = "drop")
}

# Means of the method x trial type cells with their within-subject 95% CIs
# (Cousineau-Morey)
within_ci <- function(cells, confidence = .95) {
  n_conditions <- nrow(distinct(cells, method, trial_type))
  correction <- sqrt(n_conditions / (n_conditions - 1))
  grand_mean <- mean(cells$mean_visibility, na.rm = TRUE)

  cells %>%
    filter(is.finite(mean_visibility)) %>%
    group_by(participant_id) %>%
    mutate(norm_visibility = mean_visibility - mean(mean_visibility, na.rm = TRUE) + grand_mean) %>%
    group_by(method, trial_type) %>%
    summarise(
      n = n(),
      mean = mean(mean_visibility, na.rm = TRUE),
      se = sd(norm_visibility, na.rm = TRUE) / sqrt(n),
      ci = qt((1 + confidence) / 2, df = n - 1) * se * correction,
      ci_low = mean - ci,
      ci_high = mean + ci,
      .groups = "drop"
    )
}

rmse <- function(a, b) {
  sqrt(mean((a - b)^2, na.rm = TRUE))
}

# Model functions ----
# cmdstanr and CmdStan, in the paths of the computer where the models were fitted
# unless these environment variables say otherwise
setup_cmdstan <- function() {
  r_lib <- Sys.getenv("MIB_CMDSTANR_R_LIB", unset = "C:/Users/User/OneDrive/Escritorio/Projects/modelling_vsl/.Rlibs")
  cmdstan <- Sys.getenv("MIB_CMDSTAN_PATH", unset = "C:/Users/User/.cmdstan/cmdstan-2.36.0")
  if (dir.exists(r_lib)) {
    .libPaths(c(r_lib, .libPaths()))
  }
  if (!requireNamespace("cmdstanr", quietly = TRUE)) {
    stop("cmdstanr was not found: set MIB_CMDSTANR_R_LIB to its library.")
  }
  if (dir.exists(cmdstan)) {
    cmdstanr::set_cmdstan_path(cmdstan)
  }
}

# Smithson-Verkuilen transformation, to keep the responses inside (0, 1)
smithson_verkuilen <- function(y, n) {
  (y * (n - 1) + .5) / n
}

# Every step-th sample of each trial, for a sampling rate of hz
downsample_track <- function(df, hz) {
  df <- arrange(df, trial_in_block, time_s)
  idx <- ave(seq_len(nrow(df)), df$trial_in_block, FUN = seq_along)
  dt <- median(diff(sort(unique(round(df$time_s, 4)))))
  step <- max(1L, as.integer(round((1 / dt) / hz)))
  df[(idx - 1L) %% step == 0L, ]
}

# Data of the three models: the responses of a participant with a method, with the
# previous response of each sample
build_stan_data <- function(df, compute_ppc = 1L) {
  df <- arrange(df, trial_in_block, time_s)
  trial_ids <- sort(unique(df$trial_in_block))
  track_id <- match(df$trial_in_block, trial_ids)
  starts <- match(seq_along(trial_ids), track_id)
  ends <- as.integer(tapply(seq_len(nrow(df)), track_id, max))

  y <- df$visibility
  lag_y <- numeric(length(y))
  is_first <- integer(length(y))
  for (j in seq_along(trial_ids)) {
    r <- which(track_id == j)
    y[r] <- smithson_verkuilen(df$visibility[r], length(r))
    is_first[r[1]] <- 1L
    lag_y[r[1]] <- .5
    if (length(r) > 1) {
      lag_y[r[-1]] <- y[r[-length(r)]]
    }
  }

  list(
    stan_data = list(
      N = length(y), J = length(trial_ids), track_start = starts, track_end = ends,
      y = y, lag_y = lag_y, is_first = is_first,
      response_epsilon = min(min(y), 1 - max(y)), compute_ppc = compute_ppc
    ),
    trial_id = track_id,
    df = df
  )
}

# Initial values of the three models
init_values <- function(model) {
  switch(
    model,
    continuous = list(attractor = .5, rho = .8, log_phi = log(40)),
    discrete = list(theta = list(c(.9, .1), c(.1, .9)), init_dist = c(.5, .5), state_logit = c(-2, 2),
                    log_phi = log(40)),
    hybrid = list(theta = list(c(.9, .1), c(.1, .9)), init_dist = c(.5, .5), attractor_logit = c(-2, 2),
                  rho = .8, log_phi = log(40))
  )
}

# PSIS-LOO from an array of pointwise log likelihoods (iterations x chains x points)
psis_loo <- function(log_lik) {
  r_eff <- tryCatch(loo::relative_eff(exp(log_lik)), error = function(e) NULL)
  if (is.null(r_eff) || any(!is.finite(r_eff))) {
    r_eff <- rep(1, dim(log_lik)[3])
  }
  suppressWarnings(loo::loo(log_lik, r_eff = r_eff))
}

loo_row <- function(l, scheme) {
  tibble(
    scheme = scheme,
    elpd = l$estimates["elpd_loo", "Estimate"],
    elpd_se = l$estimates["elpd_loo", "SE"],
    p_loo = l$estimates["p_loo", "Estimate"],
    pareto_k_max = max(l$diagnostics$pareto_k),
    prop_k_gt_0.7 = mean(l$diagnostics$pareto_k > .7)
  )
}

# Draws of a vector quantity, one column per observation in their order
draws_by_obs <- function(fit, var) {
  m <- posterior::as_draws_matrix(fit$draws(var))
  m[, order(as.integer(sub(paste0("^", var, "\\[([0-9]+)\\]$"), "\\1", colnames(m)))), drop = FALSE]
}

# Posterior mean and 90% interval
ppc_quantiles <- function(x) {
  x <- x[is.finite(x)]
  if (length(x) == 0) {
    return(c(pred_mean = NA, pred_lo = NA, pred_hi = NA))
  }
  c(pred_mean = mean(x), pred_lo = quantile(x, .05, names = FALSE), pred_hi = quantile(x, .95, names = FALSE))
}

# Posterior predictive density of the responses, in bins
ppc_density <- function(y_rep, breaks) {
  dens <- t(apply(y_rep, 1, function(r) {
    r <- r[is.finite(r)]
    if (length(r) == 0) {
      return(rep(NA_real_, length(breaks) - 1L))
    }
    hist(r, breaks = breaks, include.lowest = TRUE, plot = FALSE)$density
  }))
  tibble(
    bin_mid = (head(breaks, -1) + tail(breaks, -1)) / 2,
    pred_mean = colMeans(dens, na.rm = TRUE),
    pred_lo = apply(dens, 2, quantile, .05, na.rm = TRUE),
    pred_hi = apply(dens, 2, quantile, .95, na.rm = TRUE)
  )
}

# Expected response in groups of observations (time bins)
ppc_by_group <- function(expected, groups) {
  as_tibble(t(vapply(groups, function(cols) ppc_quantiles(rowMeans(expected[, cols, drop = FALSE])), numeric(3))))
}

append_csv <- function(df, path) {
  write_csv(df, path, append = file.exists(path))
}

# Reporting functions (inline statistics of the manuscript) ----
fmt <- function(x, digits = 2) sub("^-", "−", formatC(x, format = "f", digits = digits)) # Typographic minus
nz <- function(x, digits = 2) sub("^(−?)0\\.", "\\1.", fmt(x, digits)) # No leading zero
big0 <- function(x) sub("^-", "−", formatC(x, format = "f", digits = 0, big.mark = ",")) # -2781 -> −2,781

p_txt <- function(p, label = "p") {
  if (p < .001) sprintf("$%s$ < .001", label) else sprintf("$%s$ = %s", label, nz(p, 3))
}
p_holm <- function(p) p_txt(p, "p_\\text{Holm}")

# Degrees of freedom: F(1, 17), F(1.62, 27.53)
df_txt <- function(x) if (abs(x - round(x)) < 1e-8) sprintf("%d", round(x)) else fmt(x, 2)

# t statistic with the degrees of freedom as a subscript: t_17 = 7.83, p < .001
t_txt <- function(t, df, p, p_fun = p_txt) sprintf("$t_{%s}$ = %s, %s", df_txt(df), fmt(t, 2), p_fun(p))
t_head <- function(df) sprintf("$t_{%s}$", df_txt(unique(df))) # Column of a table

# One term of an afex ANOVA table
f_row <- function(tab, term) {
  sprintf(
    "$F$(%s, %s) = %s, %s, $\\eta^2_p$ = %s",
    df_txt(tab[term, "num Df"]), df_txt(tab[term, "den Df"]), fmt(tab[term, "F"], 2),
    p_txt(tab[term, "Pr(>F)"]), nz(tab[term, "pes"])
  )
}

# Parameters of the hybrid model
par_labels <- c(
  rho = "Persistence ($\\rho$)",
  phi = "Precision ($\\phi$)",
  `attractor_mean[1]` = "Low-state level",
  `attractor_mean[2]` = "High-state level",
  `theta[1,1]` = "Stay in low state",
  `theta[2,2]` = "Stay in high state"
)

# Disattenuated correlation between the slider and TET, with its credible interval
par_r <- function(v, p) {
  me <- p$params_me[p$params_me$variable == v, ]
  sprintf("%s [%s, %s]", nz(me$rho_me), nz(me$lo), nz(me$hi))
}

# Saving and loading the results ----
analysis_results_path <- function(name, dir = "output/analysis") {
  file.path(dir, paste0(name, ".rds"))
}

ensure_project_dirs <- function() {
  dirs <- c("output/analysis", "output/figures", "output/manuscript", "output/models")
  invisible(lapply(dirs, function(dir) {
    if (!dir.exists(dir)) {
      dir.create(dir, recursive = TRUE)
    }
  }))
}

save_analysis_objects <- function(name, ..., dir = "output/analysis") {
  objects <- list(...)
  if (is.null(names(objects)) || any(names(objects) == "")) {
    stop("All objects passed to save_analysis_objects() must be named.")
  }
  if (!dir.exists(dir)) {
    dir.create(dir, recursive = TRUE)
  }
  saveRDS(objects, analysis_results_path(name, dir = dir))
  invisible(objects)
}

load_analysis_objects <- function(name, dir = "output/analysis") {
  path <- analysis_results_path(name, dir = dir)
  if (!file.exists(path)) {
    stop(sprintf("Could not find saved analysis objects at '%s'.", path))
  }
  readRDS(path)
}
