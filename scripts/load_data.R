## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Installing (if needed) and loading the packages ----
if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(here, dplyr)

setwd(here::here())

# Session files ----
# One CSV per session, in the format of the task: one row per sample of the response
sessions <- read_sessions("Input/sessions")

# Ends of the slider scale, the same for all participants
slider_range <- slider_scale_range(sessions)

# Visibility in the experimental trials ----
method_levels <- c("button", "slider", "tet")
trial_levels <- c("near_fixation", "peripheral")

samples <-
  sessions %>%
  filter(phase == "experimental", method %in% method_levels, trial_type %in% trial_levels) %>%
  group_by(participant_id, method) %>%
  mutate(visibility = response_to_visibility(response, cur_group()$method, slider_range)) %>%
  ungroup() %>%
  filter(is.finite(visibility), is.finite(time_s)) %>%
  transmute(
    participant_id = factor(participant_id),
    method = factor(method, levels = method_levels),
    trial_type = factor(trial_type, levels = trial_levels),
    trial_in_block,
    time_s,
    visibility
  )

# Only participants with data in every method x trial type cell
complete_participants <-
  samples %>%
  distinct(participant_id, method, trial_type) %>%
  count(participant_id) %>%
  filter(n == length(method_levels) * length(trial_levels)) %>%
  pull(participant_id)

samples <-
  samples %>%
  filter(participant_id %in% complete_participants) %>%
  mutate(participant_id = droplevels(participant_id))

# Mean visibility per trial and per participant, method and trial type
trials <- make_trial_means(samples)
cells <- make_cell_means(trials)
