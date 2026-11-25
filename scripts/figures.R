## -----------------------------------------------------------------------------
## Author: Francisco Garre-Frutos
## -----------------------------------------------------------------------------

# Figures of the manuscript and the supplementary material, drawn at the text width (16 cm)
# and saved as PNG (600 dpi), with the supplementary trial-level figure as a PDF with one
# page per participant and method. They only use the results saved in output/analysis

# Loading packages----
source("scripts/functions.R")

if (!require(pacman)) {
  install.packages("pacman")
  library(pacman)
}

p_load(dplyr, # Data wrangling
       tidyr,
       ggplot2, # Plotting
       cowplot, # Panels
       ggdist # Distributions
)

ensure_project_dirs()

an <- load_analysis_objects("analysis")
mc <- load_analysis_objects("model_comparison_mm")
pc <- load_analysis_objects("parameter_convergence")

# Theme of all the figures ----
ink <- "grey20"
label_size <- 6.5 / .pt
fig_width <- 16 # cm, text width

theme_results <- function() {
  theme_minimal(base_size = 7.5) +
    theme(
      text = element_text(color = ink),
      axis.text = element_text(size = 6.5, color = "grey35"),
      axis.title = element_text(size = 7.5, color = ink),
      axis.line = element_line(color = "grey55", linewidth = .3),
      axis.ticks = element_line(color = "grey55", linewidth = .3),
      axis.ticks.length = unit(1.5, "pt"),
      panel.grid = element_blank(),
      plot.title = element_text(size = 7.5, face = "bold", color = ink, hjust = .5, margin = margin(0, 0, 3, 0)),
      plot.title.position = "panel",
      strip.text = element_text(size = 7.5, face = "bold", color = ink),
      strip.placement = "outside",
      legend.position = "none",
      plot.margin = margin(4, 6, 3, 3)
    )
}

# Small multiples: a hairline around each panel, because inner panels have no axes
theme_panels <- function() {
  theme_results() +
    theme(
      axis.line = element_blank(),
      panel.border = element_rect(color = "grey80", fill = NA, linewidth = .25),
      panel.spacing = unit(2.5, "pt"),
      strip.text = element_text(size = 6.5, face = "plain", color = ink, margin = margin(1.5, 1.5, 1.5, 1.5))
    )
}

minus <- function(x) gsub("-", "−", x) # typographic minus sign
apa_r <- function(x) minus(sub("^(-?)0\\.", "\\1.", sprintf("%.2f", x))) # correlation without the leading zero

# Grey for the control trials and purple for the MIB trials (the two are also named on
# the axis or next to the marks). The colours of the models can be told apart with
# colour-vision deficiencies, and shape is a second encoding
effect_color <- "#762A83"
trial_labels <- c(near_fixation = "Central", peripheral = "Peripheral")
trial_colors <- c(near_fixation = "grey40", peripheral = effect_color)
method_labels <- c(button = "Button", slider = "Slider", tet = "TET")
model_labels <- c(hybrid = "Hybrid", continuous = "Continuous", discrete = "Discrete")
model_colors <- c(hybrid = effect_color, continuous = "#1B9E77", discrete = "#D95F02")
model_shapes <- c(hybrid = 16, continuous = 15, discrete = 17)

# Mean with its interval: a white halo keeps it readable over the individual data
mean_layers <- function(data, ymin, ymax, y) {
  list(
    geom_linerange(data = data, aes(y = {{ y }}, ymin = {{ ymin }}, ymax = {{ ymax }}), color = "white", linewidth = 1.5,
                   lineend = "round"),
    geom_linerange(data = data, aes(y = {{ y }}, ymin = {{ ymin }}, ymax = {{ ymax }}), color = ink, linewidth = .6,
                   lineend = "round"),
    geom_point(data = data, aes(y = {{ y }}), shape = 21, size = 1.5, color = "white", fill = ink, stroke = .35)
  )
}

# Figure of the procedure ----
# Drawn on a canvas in mm. The display has the real geometry of the task (1 cm = 1 degree),
# with the target in colour for illustration, and the traces are real trials of one participant
canvas <- new.env()
canvas$n <- 0
canvas$polys <- list()
canvas$texts <- list()
canvas$arrows <- list()
canvas$lines <- list()
canvas$paths <- list()

annot <- "grey40"

add_poly <- function(x, y, fill, colour = NA, lw = 0) {
  canvas$n <- canvas$n + 1
  canvas$polys[[length(canvas$polys) + 1]] <- tibble(group = canvas$n, x = x, y = y, fill = fill, colour = colour, lw = lw)
}

add_line <- function(x, y, xend, yend, colour = "grey55", lw = .25) {
  canvas$lines[[length(canvas$lines) + 1]] <- tibble(x = x, y = y, xend = xend, yend = yend, colour = colour, lw = lw)
}

add_path <- function(x, y, colour = effect_color, lw = .4) {
  canvas$n <- canvas$n + 1
  canvas$paths[[length(canvas$paths) + 1]] <- tibble(group = canvas$n, x = x, y = y, colour = colour, lw = lw)
}

add_text <- function(x, y, label, size = 6.5, colour = ink, face = "plain", hjust = .5, vjust = .5, angle = 0) {
  canvas$texts[[length(canvas$texts) + 1]] <- tibble(x = x, y = y, label = label, size = size / .pt, colour = colour, face = face,
                                                     hjust = hjust, vjust = vjust, angle = angle)
}

add_arrow <- function(x, y, xend, yend, colour = "grey45") {
  canvas$arrows[[length(canvas$arrows) + 1]] <- tibble(x = x, y = y, xend = xend, yend = yend, colour = colour)
}

disc <- function(cx, cy, r, fill, ...) {
  th <- seq(0, 2 * pi, length.out = 61)
  add_poly(cx + r * cos(th), cy + r * sin(th), fill, ...)
}

rounded_rect <- function(x0, y0, w, h, r, fill, ...) {
  arc <- function(cx, cy, a0) {
    th <- seq(a0, a0 + pi / 2, length.out = 10)
    cbind(cx + r * cos(th), cy + r * sin(th))
  }
  p <- rbind(arc(x0 + w - r, y0 + h - r, 0), arc(x0 + r, y0 + h - r, pi / 2), arc(x0 + r, y0 + r, pi), arc(x0 + w - r, y0 + r, 3 * pi / 2))
  add_poly(p[, 1], p[, 2], fill, ...)
}

# A screen: rounded white rectangle with a soft shadow
draw_screen <- function(x0, y0, w, h, r = .9) {
  rounded_rect(x0 + .45, y0 - .45, w, h, r, "grey86")
  rounded_rect(x0, y0, w, h, r, "white", colour = "grey55", lw = .25)
}

keycap <- function(cx, cy, w, h, label) {
  rounded_rect(cx - w / 2 + .25, cy - h / 2 - .25, w, h, .6, "grey75")
  rounded_rect(cx - w / 2, cy - h / 2, w, h, .6, "grey95", colour = "grey55", lw = .2)
  add_text(cx, cy, label, size = 5.5, face = "bold")
}

# The target: a Gaussian (SD = 0.3 degrees) that fades into the background
draw_target <- function(cx, cy, s, color) {
  rgb_color <- col2rgb(color)[, 1]
  for (r in seq(.9, .02, length.out = 40)) {
    w <- exp(-r^2 / (2 * .3^2))
    disc(cx, cy, s * r, rgb(rgb_color[1] * w + 255 * (1 - w), rgb_color[2] * w + 255 * (1 - w), rgb_color[3] * w + 255 * (1 - w), maxColorValue = 255))
  }
}

# The display at (cx, cy), with s mm per degree, the target at ecc degrees from fixation and
# the mask rotated by angle degrees. Returns the position of the target
draw_display <- function(cx, cy, s, ecc, color, angle = 22) {
  a <- angle * pi / 180
  coords <- (seq_len(11) - 6) * 1.2
  grid <- expand.grid(x = coords, y = coords)
  rx <- cos(a) * grid$x - sin(a) * grid$y
  ry <- sin(a) * grid$x + cos(a) * grid$y
  target <- ecc * c(cos(135 * pi / 180), sin(135 * pi / 180))
  keep <- sqrt(rx^2 + ry^2) >= 1.35 & sqrt((rx - target[1])^2 + (ry - target[2])^2) >= 1.35
  # A cross: 0.8 degrees wide, with arms of 0.08 degrees. As in the task, each cross turns the
  # opposite way to the grid (the orientation in PsychoPy is clockwise)
  w <- .4
  t <- .04
  vx <- c(-t, t, t, w, w, t, t, -t, -t, -w, -w, -t)
  vy <- c(w, w, t, t, -t, -t, -w, -w, -t, -t, t, t)
  for (i in which(keep)) {
    add_poly(cx + s * (rx[i] + cos(a) * vx + sin(a) * vy), cy + s * (ry[i] - sin(a) * vx + cos(a) * vy), "grey50")
  }
  disc(cx, cy, s * .135, "black")
  draw_target(cx + s * target[1], cy + s * target[2], s, color)
  c(cx + s * target[1], cy + s * target[2])
}

# A. The display in the two types of trials ----
w_a <- 38
h_a <- 25
s_a <- h_a / 19
x_a <- 4
y_a <- c(34.5, 5.5)
ecc <- c(5.45, 1)
screen_titles <- c("Peripheral (5.45°)", "Central (1°)")
screen_colors <- c(trial_colors[["peripheral"]], trial_colors[["near_fixation"]])

for (k in 1:2) {
  draw_screen(x_a, y_a[k], w_a, h_a)
  draw_display(x_a + w_a / 2, y_a[k] + h_a / 2, s_a, ecc[k], screen_colors[k])
  add_text(x_a + w_a / 2, y_a[k] + h_a + 2.1, screen_titles[k], size = 7, face = "bold")
}

# Label of the target, with a leader line
centre <- c(x_a + w_a / 2, y_a[1] + h_a / 2)
target <- centre + 5.45 * s_a * c(cos(135 * pi / 180), sin(135 * pi / 180))
add_line(target[1] - .9, target[2] + .6, x_a + 7.2, y_a[1] + h_a - 3.4)
add_text(x_a + 7, y_a[1] + h_a - 3.2, "Target", colour = annot, hjust = 1)

# The rotation of the mask
th <- seq(0, 46, length.out = 30) * pi / 180 # counterclockwise, as in the task
r_arc <- 14
cx_arc <- x_a + w_a / 2
cy_arc <- y_a[2] + h_a / 2
n_arc <- length(th)
add_path(cx_arc + r_arc * cos(th), cy_arc + r_arc * sin(th), colour = "grey45", lw = .3)
add_arrow(cx_arc + r_arc * cos(th[n_arc - 2]), cy_arc + r_arc * sin(th[n_arc - 2]),
          cx_arc + r_arc * cos(th[n_arc]), cy_arc + r_arc * sin(th[n_arc]))

# Duration of the trials
x_bracket <- x_a + w_a + 2
add_line(x_bracket, y_a[2], x_bracket, y_a[1] + h_a)
add_line(x_bracket - .6, c(y_a[2], y_a[1] + h_a), x_bracket, c(y_a[2], y_a[1] + h_a))
add_text(x_bracket + 2, mean(c(y_a[2], y_a[1] + h_a)), "30 s", colour = annot, angle = 90)

# B. One trial with each method ----
row_y <- c(button = 44.5, slider = 25, tet = 5.5)
row_h <- 18
x_cell <- 57
w_cell <- 102.5
x_trace <- x_cell + 18.5
w_trace <- 81
trace_x <- function(t) x_trace + t / 30 * w_trace
trace_y <- function(v, y) y + 1.6 + v * (row_h - 3.2)

for (this_method in names(row_y)) {
  y <- row_y[[this_method]]
  # The row: its name along a spine
  rounded_rect(x_cell - 2.3, y, .55, row_h, .25, ink)
  add_text(x_cell - 4, y + row_h / 2, method_labels[[this_method]], size = 7, face = "bold", angle = 90)
  rounded_rect(x_cell, y, w_cell, row_h, .8, "grey96")
  # The trial
  d <- filter(an$fig_task_traces, method == this_method)
  add_line(trace_x(0), trace_y(.5, y), trace_x(30), trace_y(.5, y), colour = "grey85", lw = .2)
  add_path(trace_x(d$time_s), trace_y(d$visibility, y), lw = .45)
  add_text(trace_x(0) - 1, trace_y(c(0, 1), y), c("0", "1"), size = 5.5, colour = annot, hjust = 1)
}

# Scale of time
add_line(trace_x(0), 3.4, trace_x(5), 3.4, colour = annot, lw = .45)
add_text(trace_x(5) + .8, 3.4, "5 s", size = 5.5, colour = annot, hjust = 0)

# How each method is used
x_icon <- x_cell + 7.8
keycap(x_icon, row_y[["button"]] + row_h / 2, 11, 3.8, "Space")

ys <- row_y[["slider"]]
add_poly(x_icon + c(-.28, .28, .28, -.28), ys + c(3, 3, row_h - 3, row_h - 3), "grey70")
rounded_rect(x_icon - 1.6, ys + row_h / 2 + 1, 3.2, 1.5, .4, "grey95", colour = "grey45", lw = .2)

# A mouse
yt <- row_y[["tet"]]
rounded_rect(x_icon - 2.3, yt + 5.5, 4.6, 7, 2.1, "grey95", colour = "grey45", lw = .25)
add_line(x_icon - 2.3, yt + 9.5, x_icon + 2.3, yt + 9.5, colour = "grey45", lw = .25)
add_line(x_icon, yt + 9.5, x_icon, yt + 12.5, colour = "grey45", lw = .25)

# Letters of the panels
add_text(0, 64.5, "A", size = 10, face = "bold", hjust = 0, vjust = 1)
add_text(50.5, 64.5, "B", size = 10, face = "bold", hjust = 0, vjust = 1)

fig_task <-
  ggplot() +
  geom_polygon(data = bind_rows(canvas$polys), aes(x, y, group = group, fill = fill, colour = colour, linewidth = lw)) +
  geom_segment(data = bind_rows(canvas$lines), aes(x, y, xend = xend, yend = yend, colour = colour, linewidth = lw)) +
  geom_path(data = bind_rows(canvas$paths), aes(x, y, group = group, colour = colour, linewidth = lw), linejoin = "round") +
  geom_segment(data = bind_rows(canvas$arrows), aes(x, y, xend = xend, yend = yend, colour = colour), linewidth = .3,
               arrow = arrow(length = unit(.9, "mm"), type = "closed")) +
  geom_text(data = bind_rows(canvas$texts), aes(x, y, label = label, size = size, colour = colour, fontface = face, hjust = hjust,
                                                vjust = vjust, angle = angle), lineheight = .9) +
  scale_fill_identity() +
  scale_colour_identity() +
  scale_linewidth_identity() +
  scale_size_identity() +
  coord_fixed(xlim = c(0, 160), ylim = c(2, 65), expand = FALSE, clip = "off") +
  theme_void() +
  theme(plot.background = element_rect(fill = "white", colour = NA), plot.margin = margin(0, 0, 0, 0))

ggsave("output/figures/fig-task.png", fig_task, width = fig_width, height = 6.3, units = "cm", dpi = 600, bg = "white")

# Figure of the visibility ----
# The colour is always the type of trial, as in the figure of the procedure
set.seed(20260627)

# Mean visibility in each type of trial with each method: the participants, the mean with
# its within-subject 95% CI and the density, with the means connected
means_ind <-
  an$fig_cells %>%
  mutate(x = as.numeric(trial_type), x_dot = x - .24 + runif(n(), -.09, .09))

means_group <- mutate(an$fig_means, x = as.numeric(trial_type))

plot_means <-
  ggplot(means_ind, aes(x = x, y = mean_visibility, color = trial_type, fill = trial_type)) +
  ggdist::stat_slab(aes(group = trial_type, x = x + .09), side = "right", scale = .42, density = ggdist::density_bounded(bounds = c(0, 1), adjust = .9), trim = FALSE,
                    normalize = "groups", color = NA, alpha = .28) +
  geom_point(aes(x = x_dot), shape = 16, size = .6, alpha = .7) +
  geom_line(data = means_group, aes(y = mean, group = method), color = ink, linewidth = .4) +
  mean_layers(means_group, ci_low, pmin(ci_high, 1), mean) +
  facet_wrap(~ method, strip.position = "bottom", labeller = as_labeller(method_labels)) +
  coord_cartesian(xlim = c(.55, 2.6), ylim = c(0, 1), expand = FALSE, clip = "off") +
  scale_x_continuous(breaks = 1:2, labels = trial_labels) +
  scale_y_continuous(breaks = seq(0, 1, .25), labels = c("0", ".25", ".50", ".75", "1")) +
  scale_color_manual(values = trial_colors) +
  scale_fill_manual(values = trial_colors) +
  labs(x = NULL, y = "Mean visibility") +
  theme_results() +
  theme(panel.spacing.x = unit(6, "pt"), plot.margin = margin(10, 6, 3, 3))

# Effect of each participant, sorted within each method, and the mean effect of the method
# as one more line, after the participants
effects_mean <- mutate(an$mib_by_method, rank = 20.5, effect = estimate)

plot_effects <-
  ggplot(an$fig_effects, aes(x = rank, y = effect, color = effect > 0)) +
  annotate("segment", x = -Inf, xend = Inf, y = 0, yend = 0, color = "grey55", linewidth = .3) +
  geom_segment(aes(xend = rank, yend = 0), linewidth = .35) +
  geom_point(shape = 16, size = .8) +
  mean_layers(effects_mean, 0, effect, effect) +
  facet_wrap(~ method, strip.position = "bottom", labeller = as_labeller(method_labels)) +
  scale_x_continuous(breaks = NULL) +
  scale_y_continuous(breaks = seq(0, .75, .25), labels = c("0", ".25", ".50", ".75")) +
  scale_color_manual(values = c(`TRUE` = effect_color, `FALSE` = "grey40")) +
  labs(x = "Participants, sorted by effect", y = "Central − peripheral visibility") +
  theme_results() +
  theme(axis.line.x = element_blank(), panel.spacing.x = unit(6, "pt"), plot.margin = margin(10, 6, 3, 3))

# Convergence between methods: each participant and the regression within each type of
# trial, with the identity dashed. The correlations name the types of trial
convergence_panel <- function(a, b) {
  d <- filter(an$fig_convergence, method_a == a, method_b == b)
  rs <-
    an$h3_correlations %>%
    filter(method_a == a, method_b == b) %>%
    mutate(
      trial_type = as.character(trial_type),
      y = ifelse(trial_type == "near_fixation", .13, .05),
      label = sprintf("'%s:' ~ italic(r) == '%s' ~ '[%s, %s]'", trial_labels[trial_type], apa_r(r), apa_r(ci_low), apa_r(ci_high))
    )

  ggplot(d, aes(x, y, color = trial_type, fill = trial_type)) +
    annotate("segment", x = 0, xend = 1, y = 0, yend = 1, color = "grey60", linewidth = .3, linetype = "22") +
    geom_smooth(method = "lm", formula = y ~ x, se = TRUE, linewidth = .5, alpha = .15) +
    geom_point(shape = 16, size = .9, alpha = .65) +
    geom_point(data = rs, aes(x = .29, y = y), shape = 16, size = 1.1, inherit.aes = FALSE, color = trial_colors[rs$trial_type]) +
    geom_text(data = rs, aes(x = .325, y = y, label = label), hjust = 0, size = label_size - .15, color = ink, parse = TRUE, inherit.aes = FALSE) +
    coord_equal(xlim = c(0, 1), ylim = c(0, 1), expand = FALSE, clip = "off") +
    scale_x_continuous(breaks = seq(0, 1, .25), labels = c("0", ".25", ".50", ".75", "1")) +
    scale_y_continuous(breaks = seq(0, 1, .25), labels = c("0", ".25", ".50", ".75", "1")) +
    scale_color_manual(values = trial_colors) +
    scale_fill_manual(values = trial_colors) +
    labs(x = paste(method_labels[[a]], "visibility"), y = paste(method_labels[[b]], "visibility")) +
    theme_results() +
    theme(plot.margin = margin(10, 6, 3, 3))
}

fig_visibility <-
  plot_grid(
    plot_grid(plot_means, plot_effects, nrow = 1, rel_widths = c(1.08, 1), labels = c("A", "B"), label_size = 10),
    plot_grid(
      convergence_panel("button", "slider"),
      convergence_panel("button", "tet"),
      convergence_panel("slider", "tet"),
      nrow = 1,
      align = "h",
      axis = "tb",
      labels = c("C", "D", "E"),
      label_size = 10
    ),
    ncol = 1,
    rel_heights = c(1.12, 1)
  )

ggsave("output/figures/fig-visibility.png", fig_visibility, width = fig_width, height = 12.4, units = "cm", dpi = 600, bg = "white")

# Figure of the model comparison ----
# ELPD of each model: each participant across models, and the mean of each model with
# its within-subject SE. There are no bars: ELPD has no meaningful zero
model_comparison_figure <- function(m) {
  elpd_means <- mutate(m$fig_elpd_means, x = as.numeric(model))

  plot_elpd <-
    ggplot(mutate(m$fig_elpd, x = as.numeric(model)), aes(x = x, y = elpd)) +
    geom_line(aes(group = participant_id), color = "grey85", linewidth = .25) +
    geom_point(aes(color = model, shape = model), size = .75, alpha = .8) +
    geom_line(data = elpd_means, aes(y = mean, group = method), color = ink, linewidth = .45) +
    mean_layers(elpd_means, mean - se, mean + se, mean) +
    facet_wrap(~ method, strip.position = "bottom", labeller = as_labeller(method_labels)) +
    coord_cartesian(xlim = c(.6, 3.4), expand = TRUE) +
    scale_x_continuous(breaks = 1:3, labels = model_labels) +
    scale_y_continuous(breaks = seq(-5000, 30000, 5000), labels = function(x) minus(as.character(x / 1000))) +
    scale_color_manual(values = model_colors) +
    scale_shape_manual(values = model_shapes) +
    labs(x = NULL, y = "ELPD (thousands)") +
    theme_results() +
    theme(
      axis.text.x = element_text(size = 5.5, color = "grey35"),
      panel.spacing.x = unit(6, "pt"),
      plot.margin = margin(16, 6, 3, 3)
    )

  # Centred ELPD of each participant, ordered by the advantage of the hybrid, which is
  # drawn last
  elpd_range <-
    m$fig_elpd_centred %>%
    group_by(participant_id, method) %>%
    summarise(lo = min(elpd_c), hi = max(elpd_c), .groups = "drop")

  plot_elpd_participants <-
    ggplot(arrange(m$fig_elpd_centred, desc(model)), aes(x = elpd_c, y = participant_id)) +
    annotate("segment", x = 0, xend = 0, y = -Inf, yend = Inf, color = "grey70", linewidth = .3) +
    geom_segment(data = elpd_range, aes(x = lo, xend = hi, yend = participant_id), color = "grey85", linewidth = .3) +
    geom_point(aes(color = model, shape = model), size = 1) +
    facet_wrap(~ method, strip.position = "bottom", labeller = as_labeller(method_labels)) +
    scale_x_continuous(breaks = seq(-15000, 10000, 5000), labels = function(x) minus(as.character(x / 1000))) +
    scale_color_manual(NULL, values = model_colors, labels = model_labels) +
    scale_shape_manual(NULL, values = model_shapes, labels = model_labels) +
    labs(x = "Centered ELPD (thousands)", y = "Participant") +
    theme_results() +
    theme(
      axis.title.x = element_text(margin = margin(1, 0, 0, 0)),
      axis.text.y = element_text(size = 5.5),
      panel.spacing.x = unit(8, "pt"),
      legend.position = "top",
      legend.margin = margin(0, 0, 0, 0),
      legend.box.margin = margin(0, 0, -6, 0),
      legend.key.size = unit(.3, "cm"),
      legend.text = element_text(size = 6.5, color = ink)
    )

  plot_grid(plot_elpd, plot_elpd_participants, nrow = 1, rel_widths = c(1, 1), labels = c("A", "B"), label_size = 10)
}

ggsave("output/figures/fig-model-comparison.png", model_comparison_figure(mc), width = fig_width, height = 9, units = "cm", dpi = 600, bg = "white")

# Figures of the posterior predictive checks: trajectories ----
# One panel per model, so that their bands do not hide each other: the observed mean and
# its 95% CI (grey), and the same for the responses expected by the model

# The whole sample, as one more row: the mean of the participants with its 95% CI, and
# each participant as a thin line
ppc_all_obs <-
  mc$ppc_trajectory_obs %>%
  group_by(method, tb) %>%
  summarise(mean_obs = mean(obs), se = sd(obs) / sqrt(n()), n = n(), .groups = "drop") %>%
  transmute(participant_id = "All", method, tb, obs = mean_obs, lo = mean_obs - qt(.975, n - 1) * se, hi = mean_obs + qt(.975, n - 1) * se)

ppc_all_models <-
  mc$ppc_trajectory_models %>%
  group_by(method, model, time_bin) %>%
  summarise(m = mean(pred_mean), se = sd(pred_mean) / sqrt(n()), n = n(), .groups = "drop") %>%
  transmute(participant_id = "All", method, model, time_bin, pred_mean = m, pred_lo = m - qt(.975, n - 1) * se, pred_hi = m + qt(.975, n - 1) * se)

ppc_all_lines <-
  mc$ppc_trajectory_obs %>%
  transmute(trial_in_block = as.integer(factor(participant_id)), participant_id = "All", method, tb, obs)

# ids sets the participants and their order
trajectory_method <- function(this_method, ids, individual = FALSE, first = TRUE) {
  models <- factor(names(model_labels), levels = names(model_labels))
  by_id <- function(d) {
    d %>%
      filter(participant_id %in% ids, method == this_method) %>%
      mutate(participant_id = factor(participant_id, levels = ids))
  }
  obs <- crossing(by_id(bind_rows(ppc_all_obs, mc$ppc_trajectory_obs)), model = models)
  pred <- by_id(bind_rows(ppc_all_models, mc$ppc_trajectory_models))

  p <- ggplot()

  if (individual) {
    p <- p +
      geom_line(data = crossing(by_id(bind_rows(ppc_all_lines, mc$ppc_trial_obs)), model = models), aes(tb, obs, group = trial_in_block),
                color = "grey60", alpha = .3, linewidth = .12)
  }

  p +
    geom_ribbon(data = obs, aes(tb, ymin = lo, ymax = hi), fill = "grey50", alpha = .3) +
    geom_line(data = obs, aes(tb, obs), color = ink, linewidth = .3) +
    geom_ribbon(data = pred, aes(time_bin, ymin = pred_lo, ymax = pred_hi, fill = model), alpha = .22) +
    geom_line(data = pred, aes(time_bin, pred_mean, color = model), linewidth = .35) +
    facet_grid(participant_id ~ model, labeller = labeller(model = model_labels)) +
    coord_cartesian(xlim = c(0, 30), ylim = c(-.04, 1.04), expand = FALSE) +
    scale_x_continuous(breaks = c(0, 10, 20)) +
    scale_y_continuous(breaks = c(0, .5, 1), labels = c("0", ".5", "1")) +
    scale_color_manual(values = model_colors) +
    scale_fill_manual(values = model_colors) +
    labs(title = method_labels[[this_method]], x = "Time (s)", y = if (first) "Visibility" else NULL) +
    theme_panels() +
    theme(
      panel.spacing.x = unit(2, "pt"),
      panel.spacing.y = unit(3, "pt"),
      axis.text.y = if (first) element_text(size = 5.5, color = "grey35") else element_blank(),
      axis.ticks.y = if (first) element_line(color = "grey55", linewidth = .3) else element_blank(),
      axis.text.x = element_text(size = 5.5, color = "grey35"),
      strip.text.y = if (first) element_blank() else element_text(size = 6, angle = -90, margin = margin(0, 0, 0, 2)),
      plot.margin = if (first) margin(3, 2, 2, 2) else margin(3, 2, 2, 4)
    )
}

trajectory_figure <- function(ids, individual = FALSE) {
  plot_grid(
    trajectory_method("slider", ids, individual, first = TRUE),
    trajectory_method("tet", ids, individual, first = FALSE),
    nrow = 1,
    rel_widths = c(1.03, 1),
    align = "h",
    axis = "tb"
  )
}

# The whole sample and six participants, from dichotomous to graded responses
ggsave("output/figures/fig-ppc-trajectories.png", trajectory_figure(c("All", as.character(mc$ppc_representative)), individual = TRUE),
       width = fig_width, height = 13.2, units = "cm", dpi = 600, bg = "white")

# All the participants (supplementary)
all_ids <- sort(unique(mc$ppc_trajectory_obs$participant_id))

ggsave("output/figures/fig-supp-ppc-trajectories.png", trajectory_figure(all_ids), width = fig_width, height = 23,
       units = "cm", dpi = 600, bg = "white")

# Figure of the posterior predictive checks: distributions (supplementary) ----
# Observed distribution of the responses (grey) and the one predicted by each model. The
# square-root axis keeps visible the middle of the scale next to the peaks at the ends
density_method <- function(this_method) {
  ggplot() +
    geom_col(data = filter(mc$ppc_density_obs, method == this_method), aes(bin_mid, dens), fill = "grey80", width = .045) +
    geom_ribbon(data = filter(mc$ppc_density_models, method == this_method),
                aes(bin_mid, ymin = pred_lo, ymax = pred_hi, fill = model), alpha = .2) +
    geom_line(data = filter(mc$ppc_density_models, method == this_method), aes(bin_mid, pred_mean, color = model), linewidth = .35) +
    facet_wrap(~ participant_id, ncol = 6) +
    coord_cartesian(xlim = c(0, 1), expand = FALSE) +
    scale_x_continuous(breaks = c(0, .5, 1), labels = c("0", ".5", "1")) +
    scale_y_sqrt(breaks = c(1, 5, 10, 20), expand = expansion(mult = c(0, .04))) +
    scale_color_manual(NULL, values = model_colors, labels = model_labels) +
    scale_fill_manual(NULL, values = model_colors, labels = model_labels) +
    labs(title = method_labels[[this_method]], x = "Visibility", y = "Density") +
    theme_panels() +
    theme(axis.text = element_text(size = 5.5, color = "grey35"), panel.spacing.x = unit(7, "pt"))
}

density_legend <-
  get_plot_component(
    density_method("slider") +
      theme(legend.position = "top", legend.key.size = unit(.3, "cm"), legend.text = element_text(size = 6.5, color = ink),
            legend.margin = margin(0, 0, 0, 0)),
    "guide-box-top"
  )

fig_density <-
  plot_grid(density_legend, density_method("slider"), density_method("tet"), ncol = 1, rel_heights = c(.04, 1, 1))

ggsave("output/figures/fig-supp-ppc-distributions.png", fig_density, width = fig_width, height = 20, units = "cm", dpi = 600, bg = "white")

# Figure of the posterior predictive checks: trials (supplementary) ----
# One page per participant and method, with the observed response in each trial and the
# predictions of the three models
cells_ppc <-
  mc$ppc_trial_models %>%
  distinct(participant_id, method) %>%
  arrange(participant_id, method)

pdf("output/figures/fig-supp-ppc-trials.pdf", width = fig_width / 2.54, height = 9.5 / 2.54)

for (i in seq_len(nrow(cells_ppc))) {
  pid <- cells_ppc$participant_id[i]
  this_method <- as.character(cells_ppc$method[i])
  obs <- filter(mc$ppc_trial_obs, participant_id == pid, method == this_method)
  pred <- filter(mc$ppc_trial_models, participant_id == pid, method == this_method)

  page <-
    ggplot() +
    geom_line(data = obs, aes(tb, obs), color = ink, linewidth = .3) +
    geom_ribbon(data = pred, aes(time_bin, ymin = pred_lo, ymax = pred_hi, fill = model), alpha = .15) +
    geom_line(data = pred, aes(time_bin, pred_mean, color = model), linewidth = .35) +
    facet_wrap(~ trial_in_block, ncol = 4, labeller = as_labeller(function(x) paste("Trial", x))) +
    coord_cartesian(ylim = c(0, 1), expand = FALSE) +
    scale_x_continuous(breaks = c(0, 15, 30)) +
    scale_y_continuous(breaks = c(0, .5, 1), labels = c("0", ".5", "1")) +
    scale_color_manual(NULL, values = model_colors, labels = model_labels) +
    scale_fill_manual(NULL, values = model_colors, labels = model_labels) +
    labs(title = paste0(pid, " · ", method_labels[[this_method]]), x = "Time (s)", y = "Visibility") +
    theme_panels() +
    theme(legend.position = "top", legend.key.size = unit(.3, "cm"), legend.text = element_text(size = 6.5, color = ink),
          legend.margin = margin(0, 0, 0, 0))

  print(page)
}

invisible(dev.off())

# Figure of the convergence of the parameters ----
# Each participant with the posterior median and SD of each parameter in each method, the group mean,
# the regression and the identity (dashed), on equal axes: the correlation is read in the
# spread around the slope, and a difference between methods in the distance of the group
# mean to the identity
param_labels <- c(
  rho = "logit ρ (persistence)",
  phi = "log φ (precision)",
  `attractor_mean[1]` = "logit low-state level",
  `attractor_mean[2]` = "logit high-state level",
  `theta[1,1]` = "logit P(stay in low state)",
  `theta[2,2]` = "logit P(stay in high state)"
)

param_limits <-
  pc$fig_params %>%
  group_by(variable) %>%
  summarise(
    lo = min(tm_slider - ts_slider, tm_tet - ts_tet),
    hi = max(tm_slider + ts_slider, tm_tet + ts_tet),
    .groups = "drop"
  ) %>%
  mutate(pad = .06 * (hi - lo), lo = lo - pad, hi = hi + 3 * pad) # Room for the correlation

param_blank <-
  bind_rows(
    transmute(param_limits, variable, tm_slider = lo, tm_tet = lo),
    transmute(param_limits, variable, tm_slider = hi, tm_tet = hi)
  )

param_text <-
  pc$params_naive %>%
  left_join(param_limits, by = "variable") %>%
  mutate(
    x = lo + .03 * (hi - lo),
    y = hi - .03 * (hi - lo),
    label = sprintf("italic(r) == '%s' ~ '[%s, %s]'", apa_r(r_pearson), apa_r(ci_lo), apa_r(ci_hi))
  )

# Group mean of each method, with the 95% CI of the mean on each axis
param_means <-
  pc$fig_params %>%
  group_by(variable) %>%
  summarise(
    across(c(tm_slider, tm_tet), list(m = mean, ci = ~ qt(.975, n() - 1) * sd(.x) / sqrt(n()))),
    .groups = "drop"
  )

fig_parameters <-
  ggplot(pc$fig_params, aes(tm_slider, tm_tet)) +
  geom_blank(data = param_blank) +
  geom_abline(slope = 1, intercept = 0, color = "grey60", linewidth = .3, linetype = "22") +
  geom_linerange(aes(ymin = tm_tet - ts_tet, ymax = tm_tet + ts_tet), color = "grey75", linewidth = .25) +
  geom_linerange(aes(xmin = tm_slider - ts_slider, xmax = tm_slider + ts_slider), orientation = "y", color = "grey75", linewidth = .25) +
  geom_smooth(method = "lm", formula = y ~ x, se = TRUE, color = effect_color, fill = effect_color, alpha = .15, linewidth = .5) +
  geom_point(shape = 21, size = 1, color = "white", fill = ink, stroke = .2) +
  geom_linerange(data = param_means, aes(x = tm_slider_m, ymin = tm_tet_m - tm_tet_ci, ymax = tm_tet_m + tm_tet_ci),
                 inherit.aes = FALSE, color = ink, linewidth = .45) +
  geom_linerange(data = param_means, aes(y = tm_tet_m, xmin = tm_slider_m - tm_slider_ci, xmax = tm_slider_m + tm_slider_ci),
                 orientation = "y", inherit.aes = FALSE, color = ink, linewidth = .45) +
  geom_point(data = param_means, aes(tm_slider_m, tm_tet_m), inherit.aes = FALSE, shape = 23, size = 2.2, color = ink,
             fill = "white", stroke = .5) +
  geom_text(data = param_text, aes(x, y, label = label), hjust = 0, vjust = 1, size = label_size, color = ink, parse = TRUE) +
  facet_wrap(~ variable, scales = "free", ncol = 3, labeller = as_labeller(param_labels)) +
  scale_x_continuous(labels = function(x) minus(format(x, trim = TRUE))) +
  scale_y_continuous(labels = function(x) minus(format(x, trim = TRUE))) +
  coord_cartesian(expand = FALSE) +
  labs(x = "Slider (posterior median and SD)", y = "TET (posterior median and SD)") +
  theme_results() +
  theme(aspect.ratio = 1, panel.spacing = unit(8, "pt"))

ggsave("output/figures/fig-parameters.png", fig_parameters, width = fig_width, height = 11, units = "cm", dpi = 600, bg = "white")

# Figure of the tracking of a known change in intensity ----
# The wave of the stimulus in black, the curve of the group from the model with its 95% CI, and
# the mean response of each participant in the background
tracking_participants <-
  an$fig_calibration %>%
  group_by(participant_id, time_s) %>%
  summarise(response = mean(response_norm), .groups = "drop")

fig_tracking <-
  ggplot(an$calibration_curve, aes(x = time_s)) +
  geom_line(data = tracking_participants, aes(y = response, group = participant_id), color = "grey75", linewidth = .2, alpha = .55) +
  geom_ribbon(aes(ymin = ci_low, ymax = ci_high), fill = effect_color, alpha = .28) +
  geom_line(aes(y = fit), color = effect_color, linewidth = .7) +
  geom_line(aes(y = stimulus), color = "black", linewidth = .55) +
  coord_cartesian(xlim = c(0, 30), ylim = c(-.02, 1.02), expand = FALSE) +
  scale_x_continuous(breaks = seq(0, 30, 5)) +
  scale_y_continuous(breaks = seq(0, 1, .25), labels = c("0", ".25", ".50", ".75", "1")) +
  labs(x = "Time (s)", y = "Contrast and response") +
  theme_results()

ggsave("output/figures/fig-tracking.png", fig_tracking, width = fig_width, height = 6, units = "cm", dpi = 600, bg = "white")

# Figure of the calibration (supplementary) ----
# Sinusoidal calibration trials: stimulus and response, for the visual inspection of the
# exclusion criterion, and the RMSE of each participant relative to the median
calibration_labels <-
  an$calibration_metrics %>%
  transmute(
    participant_id,
    label = sprintf("p%s%s\nr = %s, RMSE = %s", participant_id, ifelse(exclusion_candidate, " (flagged)", ""), apa_r(cor_r), apa_r(rmse_norm))
  )

calibration_data <- left_join(an$fig_calibration, calibration_labels, by = "participant_id")

plot_calibration <-
  ggplot(calibration_data, aes(x = time_s)) +
  geom_line(data = filter(calibration_data, trial_in_block == min(trial_in_block)), aes(y = stimulus), color = "grey60", linewidth = .35) +
  geom_line(aes(y = response_norm, group = trial_in_block), color = effect_color, linewidth = .25, alpha = .85) +
  facet_wrap(~ label, ncol = 6) +
  coord_cartesian(xlim = c(0, 30), ylim = c(-.04, 1.04), expand = FALSE) +
  scale_x_continuous(breaks = c(0, 10, 20)) +
  scale_y_continuous(breaks = c(0, .5, 1), labels = c("0", ".5", "1")) +
  labs(x = "Time (s)", y = "Stimulus (grey) and response (purple)") +
  theme_panels() +
  theme(
    axis.text = element_text(size = 5.5, color = "grey35"),
    strip.text = element_text(size = 5.5, lineheight = .95),
    plot.margin = margin(4, 6, 3, 12)
  )

plot_deviation <-
  an$calibration_metrics %>%
  arrange(rmse_z) %>%
  mutate(rank = row_number()) %>%
  ggplot(aes(x = rank, y = rmse_z, color = exclusion_candidate)) +
  annotate("segment", x = -Inf, xend = Inf, y = 0, yend = 0, color = "grey55", linewidth = .3) +
  annotate("segment", x = -Inf, xend = Inf, y = 3, yend = 3, color = "grey40", linewidth = .3, linetype = "22") +
  annotate("text", x = .6, y = 3.08, label = "Flag: median + 3 MADs", hjust = 0, vjust = 0, size = label_size, color = "grey35") +
  geom_segment(aes(xend = rank, yend = 0), linewidth = .35) +
  geom_point(shape = 16, size = 1) +
  scale_x_continuous(breaks = seq_len(nrow(an$calibration_metrics)),
                     labels = paste0("p", arrange(an$calibration_metrics, rmse_z)$participant_id)) +
  scale_y_continuous(labels = function(x) minus(format(x, trim = TRUE))) +
  scale_color_manual(values = c(`FALSE` = "grey40", `TRUE` = effect_color)) +
  labs(x = NULL, y = "RMSE deviation (MADs)") +
  theme_results() +
  theme(axis.text.x = element_text(size = 5.5, angle = 45, hjust = 1), plot.margin = margin(6, 6, 3, 12))

fig_calibration <-
  plot_grid(plot_calibration, plot_deviation, ncol = 1, rel_heights = c(2.4, 1), labels = c("A", "B"), label_size = 10)

ggsave("output/figures/fig-supp-calibration.png", fig_calibration, width = fig_width, height = 15, units = "cm", dpi = 600, bg = "white")
