## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

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
       emmeans, # Post-hoc contrasts
       broom, # Tidy tests
       rapidsplithalf, # Split-half reliability
       lme4, # Model of the tracking in the calibration trials
       pwr # Sensitivity of the design
)

ensure_project_dirs()

afex_options(type = 3)

# Sample ----
sample_description <-
  sessions %>%
  distinct(participant_id, age, gender, frame_rate) %>%
  summarise(
    n = n(),
    age_mean = mean(age),
    age_sd = sd(age),
    age_min = min(age),
    age_max = max(age),
    n_women = sum(gender == "Mujer"), # Gender is coded in Spanish in the session files
    n_men = sum(gender == "Hombre"),
    frame_rate_min = min(frame_rate),
    frame_rate_max = max(frame_rate)
  )

sample_description

# Sensitivity of the design ----
# Smallest effects detected with a power of .80 (alpha = .05, two-tailed): the paired
# difference between two conditions (Cohen's dz) and a correlation
sensitivity <-
  tibble(
    dz = power.t.test(n = sample_description$n, power = .80, sig.level = .05, type = "paired")$delta,
    r = pwr.r.test(n = sample_description$n, power = .80, sig.level = .05)$r
  )

sensitivity

# Exclusions ----
# Participants who show evidence of not understanding how to use the slider during
# the calibration are excluded, by visual inspection of the sinusoidal calibration
# trials (figure of the calibration) and the RMSE between the intensity of the
# stimulus and the reported visibility. The thresholds below only flag candidates
corr_flag <- .30   # Weak tracking
rmse_flag_mad <- 3 # RMSE above the median + 3 MADs

# The response is normalized between the ends of the slider scale, as in the experimental trials
calibration <-
  sessions %>%
  filter(phase == "calibration") %>%
  transmute(
    participant_id,
    trial_in_block,
    trial_type,
    time_s,
    stimulus = target_contrast,
    response_raw = response
  ) %>%
  filter(is.finite(time_s), is.finite(stimulus), is.finite(response_raw)) %>%
  mutate(response_norm = normalize_scale(response_raw, slider_range)) %>%
  filter(trial_type == "calibration_sinusoidal")

calibration_metrics <-
  calibration %>%
  group_by(participant_id) %>%
  summarise(
    n_samples = n(),
    rmse_raw = rmse(response_raw, stimulus),
    rmse_norm = rmse(response_norm, stimulus),
    cor_r = cor(stimulus, response_raw),
    response_sd = sd(response_raw),
    response_range = diff(range(response_raw)),
    .groups = "drop"
  ) %>%
  mutate(
    rmse_z = (rmse_norm - median(rmse_norm, na.rm = TRUE)) / mad(rmse_norm, na.rm = TRUE),
    flag_low_corr = coalesce(cor_r < corr_flag, TRUE),
    flag_high_rmse = coalesce(rmse_z > rmse_flag_mad, TRUE),
    exclusion_candidate = flag_low_corr | flag_high_rmse
  ) %>%
  arrange(desc(rmse_z))

calibration_metrics

# H1: MIB with the button, peripheral vs near-fixation trials ----
h1_data <-
  cells %>%
  filter(method == "button") %>%
  dplyr::select(participant_id, trial_type, mean_visibility) %>%
  pivot_wider(names_from = trial_type, values_from = mean_visibility)

h1 <- t.test(h1_data$peripheral, h1_data$near_fixation, paired = TRUE)

h1

# H2: Method x Trial type ----
f.h2 <-
  aov_ez(
    id = "participant_id",
    dv = "mean_visibility",
    data = cells,
    within = c("method", "trial_type"),
    anova_table = list(correction = "GG", es = "pes")
  )

h2 <- f.h2$anova_table

h2

h2_method <- summary(pairs(emmeans(f.h2, ~ method), adjust = "holm"))
h2_trial_type <- summary(pairs(emmeans(f.h2, ~ trial_type)))
h2_method_by_trial_type <- summary(pairs(emmeans(f.h2, ~ method | trial_type), adjust = "holm"))

h2_method
h2_trial_type
h2_method_by_trial_type

# MIB with each method: peripheral vs near-fixation trials
mib_by_method <-
  cells %>%
  pivot_wider(names_from = trial_type, values_from = mean_visibility) %>%
  group_by(method) %>%
  reframe(dplyr::select(tidy(t.test(near_fixation, peripheral, paired = TRUE)), -method)) %>%
  rename(t = statistic, df = parameter, p = p.value, ci_low = conf.low, ci_high = conf.high)

mib_by_method

# H3: Convergence between methods ----
method_pairs <-
  tibble(
    method_a = c("button", "button", "slider"),
    method_b = c("slider", "tet", "tet")
  ) %>%
  mutate(contrast = paste(method_a, "vs", method_b))

method_means <- pivot_wider(cells, names_from = method, values_from = mean_visibility)

convergence <-
  method_pairs %>%
  pmap_dfr(function(method_a, method_b, contrast) {
    method_means %>%
      transmute(
        participant_id,
        trial_type,
        method_a = method_a,
        method_b = method_b,
        contrast = contrast,
        x = .data[[method_a]],
        y = .data[[method_b]]
      )
  }) %>%
  filter(is.finite(x), is.finite(y)) %>%
  mutate(
    trial_type = factor(trial_type, levels = trial_levels),
    trial_type_dummy = as.integer(trial_type == "peripheral")
  )

# Correlations between methods, Holm-corrected within each trial type
h3_correlations <-
  convergence %>%
  group_by(trial_type, method_a, method_b, contrast) %>%
  reframe(tidy(cor.test(x, y))) %>%
  rename(r = estimate, ci_low = conf.low, ci_high = conf.high, p_value = p.value) %>%
  group_by(trial_type) %>%
  mutate(p_holm = pmin(p.adjust(p_value, "holm"), 1)) %>%
  ungroup()

h3_correlations

# Slope between methods and its change across trial types
h3_terms <-
  convergence %>%
  group_by(method_a, method_b, contrast) %>%
  reframe(tidy(lm(y ~ x * trial_type_dummy))) %>%
  mutate(
    h3_family = case_when(
      term == "x" ~ "method_slope",
      term == "x:trial_type_dummy" ~ "slope_change_by_trial_type",
      TRUE ~ NA_character_
    )
  ) %>%
  group_by(h3_family) %>%
  mutate(p_holm = if_else(is.na(h3_family), NA_real_, pmin(p.adjust(p.value, "holm"), 1))) %>%
  ungroup()

h3_terms

h3_fit <-
  convergence %>%
  group_by(method_a, method_b, contrast) %>%
  reframe(glance(lm(y ~ x * trial_type_dummy)))

h3_fit

# Split-half reliability per method and trial type
set.seed(20260627)

reliability <-
  trials %>%
  mutate(across(c(participant_id, method, trial_type, trial_in_block), as.character)) %>%
  group_by(method, trial_type) %>%
  group_modify(~ {
    fit <-
      rapidsplit(
        data = as.data.frame(.x),
        subjvar = "participant_id",
        stratvars = "trial_in_block",
        aggvar = "mean_visibility",
        splits = 5000,
        aggfunc = "means",
        include.scores = FALSE,
        verbose = FALSE,
        check = FALSE
      )
    tibble(reliability = fit$r, ci_low = fit$ci[1], ci_high = fit$ci[2])
  }) %>%
  ungroup()

reliability

# How the continuous responses move ----
# On the time grid of the models: share of steps without any change, share of samples at
# the ends of the scale and at intermediate levels, and share of the steps without any
# change that were at intermediate levels, in the trials used to fit the models
response_shape <-
  samples %>%
  filter(method != "button", trial_type == "peripheral") %>%
  group_by(participant_id, method) %>%
  group_modify(~ downsample_track(.x, hz = 25)) %>%
  group_by(trial_in_block, .add = TRUE) %>%
  mutate(step = visibility - lag(visibility)) %>%
  group_by(participant_id, method) %>%
  summarise(
    still = mean(abs(step) < 1e-6, na.rm = TRUE),
    ends = mean(visibility < .01 | visibility > .99),
    middle = mean(visibility > .1 & visibility < .9),
    still_middle = mean((visibility > .1 & visibility < .9)[which(abs(step) < 1e-6)]),
    .groups = "drop"
  )

response_shape

# Tracking of a known change in intensity (exploratory) ----
# A mixed model of the responses in the sinusoidal calibration trials, at 10 Hz, with the cosine
# and sine of the frequency of the stimulus, which give the amplitude of the response and its lag
stimulus_w <- 2 * pi * .2 # The stimulus is .5 + .5 cos(wt)

add_wave <- function(d) mutate(d, c1 = cos(stimulus_w * time_s), s1 = sin(stimulus_w * time_s))

amplitude_of <- function(b) sqrt(b[["c1"]]^2 + b[["s1"]]^2) / .5
lag_of <- function(b) atan2(b[["s1"]], b[["c1"]]) / stimulus_w

tracking_data <-
  calibration %>%
  filter(round(time_s * 50) %% 5 == 0) %>%
  mutate(participant_id = as.character(participant_id)) %>%
  add_wave()

tracking_model <-
  lmer(
    response_norm ~ c1 + s1 + (c1 + s1 || participant_id),
    tracking_data,
    control = lmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 1e5))
  )

summary(tracking_model)

tracking_beta <- fixef(tracking_model)
tracking_vcov <- as.matrix(vcov(tracking_model))

# Estimates of the group, with intervals from simulating the fixed effects
set.seed(20260627)
tracking_draws <- MASS::mvrnorm(20000, tracking_beta, tracking_vcov)

interval_of <- function(f) {
  x <- apply(tracking_draws, 1, f)
  tibble(estimate = f(tracking_beta), ci_low = quantile(x, .025, names = FALSE), ci_high = quantile(x, .975, names = FALSE))
}

calibration_estimates <-
  bind_rows(
    lag = interval_of(lag_of),
    amplitude = interval_of(amplitude_of),
    mean_level = interval_of(function(b) b[["(Intercept)"]]),
    .id = "measure"
  )

calibration_estimates

# Curve of the group, with its 95% CI over participants
calibration_curve <-
  tibble(time_s = seq(0, 30, by = .02)) %>%
  add_wave() %>%
  mutate(stimulus = .5 + .5 * c1)

tracking_x <- model.matrix(~ c1 + s1, calibration_curve)
tracking_se <- sqrt(rowSums((tracking_x %*% tracking_vcov) * tracking_x))
tracking_t <- qt(.975, n_distinct(tracking_data$participant_id) - 1)

calibration_curve <-
  calibration_curve %>%
  mutate(
    fit = as.numeric(tracking_x %*% tracking_beta),
    ci_low = fit - tracking_t * tracking_se,
    ci_high = fit + tracking_t * tracking_se
  ) %>%
  dplyr::select(time_s, stimulus, fit, ci_low, ci_high)

# Each participant, from the same model
tracking_coefs <- coef(tracking_model)$participant_id

calibration_tracking <-
  tibble(
    participant_id = rownames(tracking_coefs),
    lag = map_dbl(seq_len(nrow(tracking_coefs)), ~ lag_of(tracking_coefs[.x, ])),
    amplitude = map_dbl(seq_len(nrow(tracking_coefs)), ~ amplitude_of(tracking_coefs[.x, ])),
    mean_level = tracking_coefs[["(Intercept)"]]
  )

calibration_tracking

# Stability of the lag and the amplitude between the two trials
calibration_stability <-
  tracking_data %>%
  group_by(participant_id, trial_in_block) %>%
  group_modify(function(d, key) {
    b <- coef(lm(response_norm ~ c1 + s1, d))
    tibble(lag = lag_of(b), amplitude = amplitude_of(b))
  }) %>%
  group_by(participant_id) %>%
  mutate(trial = row_number()) %>%
  ungroup() %>%
  dplyr::select(participant_id, trial, lag, amplitude) %>%
  pivot_longer(c(lag, amplitude), names_to = "measure") %>%
  pivot_wider(names_from = trial, names_prefix = "trial_") %>%
  group_by(measure) %>%
  summarise(r = cor(trial_1, trial_2), .groups = "drop")

calibration_stability

# Tracking against the reports with the slider in peripheral trials
calibration_vs_mib <-
  calibration_tracking %>%
  inner_join(
    response_shape %>%
      filter(method == "slider") %>%
      transmute(participant_id = as.character(participant_id), middle),
    by = "participant_id"
  ) %>%
  inner_join(
    cells %>%
      filter(method == "slider", trial_type == "peripheral") %>%
      transmute(participant_id = as.character(participant_id), visibility = mean_visibility),
    by = "participant_id"
  ) %>%
  pivot_longer(c(lag, amplitude), names_to = "tracking", values_to = "x") %>%
  pivot_longer(c(middle, visibility), names_to = "report", values_to = "y") %>%
  group_by(tracking, report) %>%
  group_modify(function(d, key) {
    test <- cor.test(d$x, d$y)
    tibble(r = test$estimate[[1]], ci_low = test$conf.int[1], ci_high = test$conf.int[2])
  }) %>%
  ungroup()

calibration_vs_mib

# Data of the figures ----
# Example trials for the figure of the procedure: a participant who illustrates how the
# three methods differ, with the peripheral trial of each method whose mean visibility is
# the closest to the mean of that participant with that method
fig_task_traces <-
  samples %>%
  filter(participant_id == "1015", trial_type == "peripheral") %>%
  group_by(method, trial_in_block) %>%
  mutate(trial_mean = mean(visibility)) %>%
  group_by(method) %>%
  filter(abs(trial_mean - mean(trial_mean)) == min(abs(trial_mean - mean(trial_mean)))) %>%
  ungroup() %>%
  dplyr::select(method, trial_in_block, time_s, visibility)

# Means of each cell with their within-subject 95% CIs
fig_means <- within_ci(cells)

fig_means

# Effect of each participant: central - peripheral visibility
fig_effects <-
  cells %>%
  pivot_wider(names_from = trial_type, values_from = mean_visibility) %>%
  filter(is.finite(near_fixation), is.finite(peripheral)) %>%
  mutate(effect = near_fixation - peripheral) %>%
  group_by(method) %>%
  arrange(effect, .by_group = TRUE) %>%
  mutate(rank = row_number()) %>%
  ungroup()

save_analysis_objects(
  "analysis",
  sample_description = sample_description,
  sensitivity = sensitivity,
  calibration_metrics = calibration_metrics,
  calibration_estimates = calibration_estimates,
  calibration_curve = calibration_curve,
  calibration_tracking = calibration_tracking,
  calibration_stability = calibration_stability,
  calibration_vs_mib = calibration_vs_mib,
  h1 = h1,
  h2 = h2,
  h2_method = h2_method,
  h2_trial_type = h2_trial_type,
  h2_method_by_trial_type = h2_method_by_trial_type,
  mib_by_method = mib_by_method,
  h3_correlations = h3_correlations,
  h3_terms = h3_terms,
  h3_fit = h3_fit,
  reliability = reliability,
  response_shape = response_shape,
  fig_task_traces = fig_task_traces,
  fig_cells = cells,
  fig_means = fig_means,
  fig_effects = fig_effects,
  fig_convergence = convergence,
  fig_calibration = calibration
)
