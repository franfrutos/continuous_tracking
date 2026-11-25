// Continuous model: first-order autoregressive model with one attractor and a Beta
// likelihood. Generated quantities: the pointwise log likelihood, the posterior predictive
// quantities and the parameters on the unbounded scale (logit of rho and of the attractor),
// whose posterior SD is read directly from Stan. log_phi is already a parameter

data {
  int<lower=1> N;
  int<lower=1> J;
  array[J] int<lower=1, upper=N> track_start;
  array[J] int<lower=1, upper=N> track_end;
  vector<lower=0, upper=1>[N] y;
  vector<lower=0, upper=1>[N] lag_y;
  array[N] int<lower=0, upper=1> is_first;
  real<lower=0, upper=0.5> response_epsilon;
  int<lower=0, upper=1> compute_ppc;
}

parameters {
  real<lower=response_epsilon, upper=1 - response_epsilon> attractor;
  real<lower=0, upper=1> rho;
  real log_phi;
}

transformed parameters {
  real<lower=0> phi = exp(log_phi);
}

model {
  vector[N] mu;

  attractor ~ beta(1, 1);          // uniform within bounds
  rho ~ beta(1, 1);                // uniform
  log_phi ~ student_t(3, 0, 2.5);  // brms default for the precision (log scale)

  for (n in 1:N) {
    mu[n] = is_first[n] == 1 ? attractor : attractor + rho * (lag_y[n] - attractor);
  }
  y ~ beta(mu * phi, (1 - mu) * phi);
}

generated quantities {
  vector[N] log_lik;
  vector[compute_ppc ? N : 0] expected_response;
  vector[compute_ppc ? N : 0] y_rep_generative;
  // On the unbounded scale, so that their posterior SD is exact (no delta method)
  real logit_rho       = logit(rho);        // AR coefficient on logit scale (rho in (0,1))
  real logit_attractor = logit(attractor);  // attractor mean on logit scale

  {
    vector[N] mu;
    for (n in 1:N) {
      mu[n] = is_first[n] == 1 ? attractor : attractor + rho * (lag_y[n] - attractor);
      log_lik[n] = beta_lpdf(y[n] | mu[n] * phi, (1 - mu[n]) * phi);
    }

    if (compute_ppc) {
      expected_response = mu;
      for (j in 1:J) {
        int n0 = track_start[j];
        y_rep_generative[n0] = beta_rng(attractor * phi, (1 - attractor) * phi);
        for (t in (track_start[j] + 1):track_end[j]) {
          real mu_g = attractor + rho * (y_rep_generative[t - 1] - attractor);
          y_rep_generative[t] = beta_rng(mu_g * phi, (1 - mu_g) * phi);
        }
      }
    }
  }
}
