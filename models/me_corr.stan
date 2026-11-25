// Measurement-error model of the correlation of a parameter between the slider and TET. Each
// participant has a latent pair of values (bivariate normal), and the posterior median of each
// method is observed with its posterior SD as measurement error. The medians are standardized by
// parameter in parameter_convergence.R, so that the same priors apply to all the parameters

data {
  int<lower=1> N;
  vector[N] x;
  vector<lower=0>[N] xse;
  vector[N] y;
  vector<lower=0>[N] yse;
}

parameters {
  vector[2] mu;
  vector<lower=0>[2] tau;
  real<lower=-1, upper=1> rho;
  array[N] vector[2] z;
}

model {
  matrix[2, 2] S;
  S[1, 1] = square(tau[1]);
  S[2, 2] = square(tau[2]);
  S[1, 2] = rho * tau[1] * tau[2];
  S[2, 1] = S[1, 2];

  mu ~ normal(0, 2);
  tau ~ student_t(3, 0, 2);
  for (n in 1:N) {
    z[n] ~ multi_normal(mu, S);
    x[n] ~ normal(z[n][1], xse[n]);
    y[n] ~ normal(z[n][2], yse[n]);
  }
}
