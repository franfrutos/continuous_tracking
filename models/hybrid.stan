// Hybrid model: two-state hidden Markov model with autoregressive dynamics within each state
// and a Beta likelihood. The prior on the state means is mildly directional (low state around
// .1, high state around .9), the same as in the discrete model; with priors that only order
// the means, chains could get stuck when the two states separate poorly. Generated quantities:
// the pointwise log likelihood (forward algorithm), the posterior predictive quantities and
// the parameters on the unbounded scale (logit of rho and of the probabilities of staying in
// each state), whose posterior SD is read directly from Stan. attractor_logit and log_phi are
// already parameters

functions {
  vector forward_pointwise(matrix log_omega, matrix Gamma, vector init_dist) {
    int K = rows(log_omega);
    int T = cols(log_omega);
    vector[T] ll;
    vector[K] log_alpha;
    real prev_norm;
    real cur_norm;
    matrix[K, K] log_Gamma = log(Gamma);

    log_alpha = log(init_dist) + log_omega[, 1];
    cur_norm = log_sum_exp(log_alpha);
    ll[1] = cur_norm;

    for (t in 2:T) {
      vector[K] log_alpha_new;
      prev_norm = cur_norm;
      for (k in 1:K) {
        log_alpha_new[k] = log_omega[k, t] + log_sum_exp(log_alpha + log_Gamma[, k]);
      }
      log_alpha = log_alpha_new;
      cur_norm = log_sum_exp(log_alpha);
      ll[t] = cur_norm - prev_norm;
    }
    return ll;
  }

  // Predicted state probabilities P(state_t = k | y_{1:t-1}), from the forward algorithm: the
  // state expected at each step given only the previous responses. softmax keeps every column a
  // finite simplex
  matrix hmm_predict(matrix log_omega, matrix Gamma, vector init_dist) {
    int K = rows(log_omega);
    int T = cols(log_omega);
    matrix[K, T] log_pred;
    matrix[K, T] p;
    matrix[K, K] log_Gamma = log(Gamma);

    log_pred[, 1] = log(init_dist);
    for (t in 2:T) {
      vector[K] log_filter = log_pred[, t - 1] + log_omega[, t - 1];
      for (k in 1:K) {
        log_pred[k, t] = log_sum_exp(log_filter + log_Gamma[, k]);
      }
    }

    for (t in 1:T) {
      p[, t] = softmax(log_pred[, t]);
    }
    return p;
  }
}

data {
  int<lower=1> N;
  int<lower=1> J;
  array[J] int<lower=1, upper=N> track_start;
  array[J] int<lower=1, upper=N> track_end;
  vector<lower=0, upper=1>[N] y;
  vector<lower=0, upper=1>[N] lag_y;
  array[N] int<lower=0, upper=1> is_first;
  real<lower=0, upper=0.5> response_epsilon;  // Not used: the three models take the same data
  int<lower=0, upper=1> compute_ppc;
}

parameters {
  array[2] simplex[2] theta;
  simplex[2] init_dist;
  ordered[2] attractor_logit;        // State means on the logit scale
  real<lower=0, upper=1> rho;
  real log_phi;
}

transformed parameters {
  matrix[2, 2] Gamma;
  vector[2] attractor_mean = inv_logit(attractor_logit);  // mean[1] < mean[2]
  real<lower=0> phi = exp(log_phi);

  for (k in 1:2) {
    Gamma[k, ] = theta[k]';
  }
}

model {
  matrix[2, N] log_omega;

  theta[1] ~ dirichlet([1, 1]');
  theta[2] ~ dirichlet([1, 1]');
  init_dist ~ dirichlet([1, 1]');
  attractor_logit[1] ~ normal(logit(0.1), 1);   // Low state around .1 (mildly directional)
  attractor_logit[2] ~ normal(logit(0.9), 1);   // High state around .9 (mildly directional)
  rho ~ beta(1, 1);                             // uniform
  log_phi ~ student_t(3, 0, 2.5);               // brms default for the precision (log scale)

  for (n in 1:N) {
    for (k in 1:2) {
      real mu_nk = is_first[n] == 1
        ? attractor_mean[k]
        : attractor_mean[k] + rho * (lag_y[n] - attractor_mean[k]);
      log_omega[k, n] = beta_lpdf(y[n] | mu_nk * phi, (1 - mu_nk) * phi);
    }
  }

  for (j in 1:J) {
    int Tj = track_end[j] - track_start[j] + 1;
    target += hmm_marginal(block(log_omega, 1, track_start[j], 2, Tj), Gamma, init_dist);
  }
}

generated quantities {
  vector[N] log_lik;
  vector[compute_ppc ? N : 0] expected_response;   // expected one step ahead
  vector[compute_ppc ? N : 0] y_rep_generative;    // posterior predictive draw
  // On the unbounded scale, so that their posterior SD is exact (no delta method)
  real logit_rho     = logit(rho);            // AR coefficient on logit scale (rho in (0,1))
  real logit_theta11 = logit(theta[1, 1]);    // P(stay LOW)  on logit scale
  real logit_theta22 = logit(theta[2, 2]);    // P(stay HIGH) on logit scale

  {
    matrix[2, N] log_omega;
    matrix[2, N] mu_emit;

    for (n in 1:N) {
      for (k in 1:2) {
        mu_emit[k, n] = is_first[n] == 1
          ? attractor_mean[k]
          : attractor_mean[k] + rho * (lag_y[n] - attractor_mean[k]);
        log_omega[k, n] = beta_lpdf(y[n] | mu_emit[k, n] * phi, (1 - mu_emit[k, n]) * phi);
      }
    }

    for (j in 1:J) {
      int Tj = track_end[j] - track_start[j] + 1;
      matrix[2, Tj] log_omega_j = block(log_omega, 1, track_start[j], 2, Tj);
      vector[Tj] ll_j = forward_pointwise(log_omega_j, Gamma, init_dist);

      for (t in 1:Tj) {
        log_lik[track_start[j] + t - 1] = ll_j[t];
      }

      if (compute_ppc) {
        matrix[2, Tj] state_prob_j = hmm_predict(log_omega_j, Gamma, init_dist);
        for (t in 1:Tj) {
          int n = track_start[j] + t - 1;
          expected_response[n] = state_prob_j[1, t] * mu_emit[1, n]
            + state_prob_j[2, t] * mu_emit[2, n];
        }

        {
          int n0 = track_start[j];
          int s = categorical_rng(init_dist);
          y_rep_generative[n0] = beta_rng(attractor_mean[s] * phi, (1 - attractor_mean[s]) * phi);
          for (t in 2:Tj) {
            int n = track_start[j] + t - 1;
            real mu_g;
            s = categorical_rng(Gamma[s, ]');
            mu_g = attractor_mean[s] + rho * (y_rep_generative[n - 1] - attractor_mean[s]);
            y_rep_generative[n] = beta_rng(mu_g * phi, (1 - mu_g) * phi);
          }
        }
      }
    }
  }
}
