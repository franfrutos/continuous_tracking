## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Edit to run the analyses again even if cached results exist
force_main <- FALSE

dirs <- c("output/analysis", "output/figures", "output/manuscript", "output/models", "output/models/moment_matching")
for (dir in dirs) {
  if (!dir.exists(dir)) {
    dir.create(dir, recursive = TRUE)
  }
}

run_cached <- function(name, script) {
  if (force_main || !file.exists(file.path("output/analysis", paste0(name, ".rds")))) {
    message("Running ", script, "...")
    source(script, local = new.env())
  } else {
    message("Using cached results: output/analysis/", name, ".rds")
  }
}

# Description of the sample, preregistered analyses (H1-H3) and calibration trials
run_cached("analysis", "scripts/analysis.R")

# Fits of the three models to the slider and TET responses of each participant. They take
# many hours and are resumed where they stopped, so the summaries in output/models are reused
# while they are complete (3 contrasts x 2 methods x 18 participants). To fit the models
# again, remove those files
compare_path <- "output/models/elpd_compare.csv"
n_contrasts <- if (file.exists(compare_path)) nrow(read.csv(compare_path)) else 0

if (n_contrasts < 3 * 2 * 18) {
  message("Running scripts/models.R...")
  source("scripts/models.R", local = new.env())
} else {
  message("Using the model summaries in output/models")
}

# Moment matching in the points of the preregistered models with a Pareto k above .7. It can also
# run in several processes at the same time (see scripts/moment_matching.R)
if (!file.exists("output/models/moment_matching/elpd_compare.csv")) {
  message("Running scripts/moment_matching.R...")
  source("scripts/moment_matching.R", local = new.env())
} else {
  message("Using the model summaries in output/models/moment_matching")
}

# Comparison of the models and posterior predictive checks
run_cached("model_comparison_mm", "scripts/model_comparison.R")

# Convergence of the parameters between the slider and the TET
run_cached("parameter_convergence", "scripts/parameter_convergence.R")

# Parameters of the hybrid model in seconds, with bootstrap CIs
run_cached("states", "scripts/states.R")

# Figures
message("Drawing the figures...")
source("scripts/figures.R", local = new.env())

# Versions of R and packages used to generate the results
writeLines(capture.output(sessionInfo()), "output/session_info.txt")

message("Pipeline completed.")
