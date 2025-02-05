import unittest

from gEconpy.exceptions.exceptions import (
    DistributionParsingError,
    InvalidDistributionException,
    MissingParameterValueException,
    RepeatedParameterException,
)
from gEconpy.parser.gEcon_parser import preprocess_gcn
from gEconpy.parser.parse_distributions import (
    create_prior_distribution_dictionary,
    distribution_factory,
    preprocess_distribution_string,
)


class BasicParerFunctionalityTests(unittest.TestCase):
    def setUp(self):
        self.file = """
                Block TEST
                {
                    shocks
                    {
                        epsilon[] ~ norm(mu = 0, sd = 1);
                    };

                    calibration
                    {
                        alpha ~ N(mean = 0, sd = 1) = 0.5;
                    };
                };
        """

    def test_extract_param_dist_simple(self):
        model, prior_dict = preprocess_gcn(self.file)
        self.assertEqual(list(prior_dict.keys()), ["epsilon[]", "alpha"])
        self.assertEqual(list(prior_dict.values()), ["norm(mu = 0, sd = 1)", "N(mean = 0, sd = 1)"])

    def test_catch_no_initial_value(self):
        no_initial_value = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N(mean = 0, sd = 1);
                    };
                };
        """

        self.assertRaises(MissingParameterValueException, preprocess_gcn, no_initial_value)

    def test_catch_typo_in_param_dist_definition(self):
        squiggle_is_equal = """
                Block TEST
                {
                    calibration
                    {
                        alpha = N((mean = 0, sd = 1) = 0.5;
                    };
                };
        """

        self.assertRaises(DistributionParsingError, preprocess_gcn, squiggle_is_equal)

    def test_catch_distribution_typos(self):
        extra_parenthesis_start = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N((mean = 0, sd = 1) = 0.5;
                    };
                };
        """

        extra_parenthesis_end = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N(mean = 0, sd = 1)) = 0.5;
                    };
                };
        """

        extra_equals = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N(mean == 0, sd = 1) = 0.5;
                    };
                };
        """

        missing_common = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N(mean = 0 sd = 1) = 0.5;
                    };
                };
        """

        shock_with_starting_value = """
                Block TEST
                {
                    shocks
                    {
                        epsilon[] ~ N(mean = 0, sd = 1) = 0.5;
                    };
                };
        """

        test_files = [
            extra_parenthesis_start,
            extra_parenthesis_end,
            extra_equals,
            missing_common,
            shock_with_starting_value,
        ]

        for file in test_files:
            model, prior_dict = preprocess_gcn(file)
            for param_name, distribution_string in prior_dict.items():
                self.assertRaises(
                    InvalidDistributionException,
                    preprocess_distribution_string,
                    variable_name=param_name,
                    d_string=distribution_string,
                )

    def test_catch_repeated_parameter_definition(self):
        repeated_parameter = """
                Block TEST
                {
                    calibration
                    {
                        alpha ~ N(mean = 0, mean = 1) = 0.5;
                    };
                };
        """
        model, prior_dict = preprocess_gcn(repeated_parameter)

        for param_name, distribution_string in prior_dict.items():
            self.assertRaises(
                RepeatedParameterException,
                preprocess_distribution_string,
                variable_name=param_name,
                d_string=distribution_string,
            )

    def test_parameter_parsing_simple(self):
        model, prior_dict = preprocess_gcn(self.file)
        dicts = [{"mu": "0", "sd": "1"}, {"mean": "0", "sd": "1"}]

        for i, (param_name, distribution_string) in enumerate(prior_dict.items()):
            dist_name, param_dict = preprocess_distribution_string(param_name, distribution_string)

            self.assertEqual(dist_name, "normal")
            self.assertEqual(param_dict, dicts[i])

    def test_parse_compound_distributions(self):
        compound_distribution = """Block TEST
                {
                    calibration
                    {
                        sigma_alpha ~ inv_gamma(a=20, scale=1) = 0.01;
                        mu_alpha ~ N(mean = 1, scale=1) = 0.01;
                        alpha ~ N(mean = mu_alpha, sd = sigma_alpha) = 0.5;
                    };
                };"""

        model, raw_prior_dict = preprocess_gcn(compound_distribution)
        prior_dict, _ = create_prior_distribution_dictionary(raw_prior_dict)

        d = prior_dict["alpha"]

        self.assertEqual(d.rv_params["loc"].mean(), 1)
        self.assertEqual(d.rv_params["loc"].std(), 1)
        self.assertEqual(d.rv_params["scale"].mean(), 1 / (20 - 1))
        self.assertEqual(d.rv_params["scale"].var(), 1**2 / (20 - 1) ** 2 / (20 - 2))

    def test_multiple_shocks(self):
        compound_distribution = """Block TEST
                {
                    identities
                    {
                        log(A[]) = rho_A * log(A[-1]) + epsilon_A[];
                        log(B[]) = rho_B * log(B[-1]) + epsilon_B[];
                    };

                    shocks
                    {
                        epsilon_A[] ~ N(mean=0, sd=sigma_epsilon_A);
                        epsilon_B[] ~ N(mean=0, sd=sigma_epsilon_B);
                    };

                    calibration
                    {
                        rho_A ~ Beta(mean=0.95, sd=0.04) = 0.95;
                        rho_B ~ Beta(mean=0.95, sd=0.04) = 0.95;

                        sigma_epsilon_A ~ Gamma(alpha=1, beta=0.1) = 0.01;
                        sigma_epsilon_B ~ Gamma(alpha=1, beta=0.1) = 0.01;
                    };
                };"""

        model, raw_prior_dict = preprocess_gcn(compound_distribution)
        prior_dict, _ = create_prior_distribution_dictionary(raw_prior_dict)

        epsilon_A = prior_dict["epsilon_A[]"]
        epsilon_B = prior_dict["epsilon_B[]"]

        self.assertEqual(len(epsilon_A.rv_params), 1)
        self.assertEqual(len(epsilon_B.rv_params), 1)

        # self.assertEqual(d.rv_params['loc'].mean(), 1)
        # self.assertEqual(d.rv_params['loc'].std(), 1)
        # self.assertEqual(d.rv_params['scale'].mean(), 1 / (20 - 1))
        # self.assertEqual(d.rv_params['scale'].var(), 1 ** 2 / (20 - 1) ** 2 / (20 - 2))


class TestDistributionFactory(unittest.TestCase):
    def test_parse_distributions(self):
        file = """
            TEST_BLOCK
            {
                shocks
                {
                    epsilon[] ~ N(mean=0, std=0.1);
                };

                calibration
                {
                    alpha ~ beta(a=1, b=1) = 0.5;
                    rho ~ gamma(mean=0.95, sd=1) = 0.95;
                    sigma ~ inv_gamma(mean=0.01, sd=0.1) = 0.01;
                    tau ~ halfnorm(MEAN=0.5, sd=1) = 1;
                    psi ~ norm(mean=1.5, Sd=1.5, min=0) = 1;
                };
            };
        """

        model, prior_dict = preprocess_gcn(file)
        means = [0, 0.5, 0.95, 0.01, 0.5, 1.5]
        stds = [0.1, 0.28867513459481287, 1, 0.1, 1, 1.5]

        for i, (variable_name, d_string) in enumerate(prior_dict.items()):
            d_name, param_dict = preprocess_distribution_string(variable_name, d_string)
            d = distribution_factory(
                variable_name=variable_name, d_name=d_name, param_dict=param_dict
            )
            self.assertAlmostEqual(d.mean(), means[i], places=3)
            self.assertAlmostEqual(d.std(), stds[i], places=3)


if __name__ == "__main__":
    unittest.main()
