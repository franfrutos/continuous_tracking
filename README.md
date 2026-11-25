# Continuous tracking of subjective visibility

This project is the repository for the data, scripts, and materials used for the manuscript entitled: "***Continuous Tracking of Subjective Visibility***".

### Project Structure ###

The project is organized into the following main sections:

- **Input**: Data used in the analyses.
    - *sessions*: Data of the 18 participants, one CSV per session (`mib_<participant>_<date>.csv`), with one row per sample of the response, in the format that the current program of the task writes (its columns are described in the [README of the task](Materials/psychopy_task/README.md#data)). The sessions were run with the original program, which saved the data in five files per participant; they were reformatted without changing the responses. Settings common to all participants, summaries that can be computed from the samples, and the times of the button events, which were not relative to the start of the trial, were left out.
    - `apaquarto_reference.docx`: Word template used to render the manuscript.
- **Output**: Results generated from **scripts**.
    - *analysis*: R objects of the analyses, used by the manuscript and the supplementary material.
    - *models*: Summaries of the fits of the three models, per participant and method: parameters (`params.csv`), PSIS-LOO ELPD (`elpd_table.csv`), differences in ELPD between the models (`elpd_compare.csv`), and posterior predictive checks (`ppc_*.csv`).
        - *moment_matching*: The same ELPD summaries, with moment matching in the responses with a Pareto *k* above .7.
    - *figures*: Figures of the manuscript and the supplementary material, and every trial of every participant with the predictions of the models (`fig-supp-ppc-trials.pdf`, one page per participant and method).
    - *manuscript*: Rendered manuscript and supplementary material.
    - `session_info.txt`: Versions of R and of the packages used to generate the results.
- **Scripts**: Includes the scripts used to load and preprocess the data and to run the analyses.
- **Models**: The three preregistered models in Stan: first-order autoregressive (*continuous.stan*), two-state hidden Markov (*discrete.stan*), and two-state hidden Markov with autoregressive dynamics (*hybrid.stan*), and the measurement-error model of the correlations between methods (*me_corr.stan*).
- **Materials**: The task, in PsychoPy.
    - *psychopy_task*: The current program of the task, with its own README. Start here to see or run the task.
    - *original_task*: The program that collected the data (PsychoPy 2022.2.5), unchanged, with its documentation.
- **Manuscript**: Quarto source files of the manuscript (`continuous_tracking_manuscript.qmd`) and the supplementary material (`continuous_tracking_supplementary.qmd`), and their references (`refs.bib`).
- **_extensions**: Quarto extension used to render both documents in APA style (`apaquarto`).
- **filters**: Lua filters that write references such as "Figure 1A" (`fig.lua`) and the title of the supplementary material (`supplement-title.lua`).

##### Scripts Folder Structure #####

- *analysis.R*: Description of the sample, sensitivity of the design, calibration-based exclusion criterion, and preregistered analyses of mean visibility (**Sensitivity and Convergence of the Methods**): MIB with the button (H1), differences between methods and locations (H2), and convergence and split-half reliability of the methods (H3). It also describes how the continuous responses move and how closely the slider followed the sinusoidal calibration trials (**Continuous Tracking of Objective Changes in Visibility**).
- *models.R*: Fits of the three models to the slider and TET responses of each participant in peripheral trials (25 Hz). It takes many hours, and it continues from the cells already written in `output/models`.
- *moment_matching.R*: Fits the three models again in the combinations of participant and method with a Pareto *k* above .7, and applies moment matching to those responses (**Supplementary Material**). It can run in several processes at the same time (usage at the top of the script), and it continues from the cells already saved.
- *model_comparison.R*: Comparison of the models on ELPD, before and after moment matching (and without the participant whose responses keep a Pareto *k* above .7), and data of the posterior predictive checks (**Modeling Subjective Changes in Visibility**).
- *parameter_convergence.R*: Comparison and correlations of the parameters of the hybrid model between the slider and TET (with the probability of direction of each correlation), and the times that these parameters imply (**Dynamics of Visibility With the Slider and TET**).
- *states.R*: The parameters of the hybrid model expressed in seconds (the mean stay in each state and the time to cover half of the distance to its level), with the bootstrap 95% CI of the median across participants (**Dynamics of Visibility With the Slider and TET**).
- *figures.R*: All the figures, from the results in `output/analysis`.

All the above .R files call `source(...)` to run *functions.R*, where helper functions are loaded into the workspace, and those that use the data also run *load_data.R*, where the session files are loaded and preprocessed. `run_all.R` runs all the scripts (cached results in **Output** are used when available).

### How to Reproduce ###

The scripts need **R** (version 4.3.1), **CmdStan** (version 2.36.0) with `cmdstanr`, and **Quarto** (version 1.7) with a LaTeX distribution. Each script installs and loads its packages with `pacman`, except `functions.R`, which stops with the list of the packages that are missing. If `cmdstanr` and CmdStan are not in the paths of `setup_cmdstan()` in `scripts/functions.R`, set the environment variables `MIB_CMDSTANR_R_LIB` and `MIB_CMDSTAN_PATH`.

1. Download or clone the repository and open `continuous_tracking.Rproj`.
2. Run `run_all.R`. The results of every script are cached in `output/analysis`; set `force_main <- TRUE` to run the analyses again. The summaries of the models in `output/models` and `output/models/moment_matching` are reused while they are complete; to fit the models again, remove those files.
3. Render the manuscript with `quarto render continuous_tracking_manuscript.qmd --to apaquarto-pdf` (or `--to apaquarto-docx`), and the supplementary material with `quarto render continuous_tracking_supplementary.qmd --to apaquarto-pdf`.

On Windows, run the scripts as files (`Rscript run_all.R`), not with `Rscript -e`, which crashed when drawing the figures on the computer used for the analyses.

### License ###

Data, code, and materials are released under a [CC BY 4.0](LICENSE.md) license. Third-party files keep the licenses of their authors: the Quarto extension in `_extensions` and the Word template `Input/apaquarto_reference.docx` (`apaquarto`).

### Links ###

- Preregistration: <https://osf.io/r8h4q>
- Preprint: [to be added]
- Zenodo repository: <https://doi.org/10.5281/zenodo.24543404>
