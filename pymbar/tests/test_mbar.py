"""Test MBAR by performing statistical tests on a set of model systems
for which the true free energy differences can be computed analytically.
"""

import numpy as np
import pytest
from pymbar import MBAR
from pymbar.testsystems import harmonic_oscillators, exponential_distributions
from pymbar.utils_for_testing import assert_equal, assert_almost_equal

precision = 8  # the precision for systems that do have analytical results that should be matched.
# Scales the z_scores so that we can reject things that differ at the ones decimal place.  TEMPORARY HACK
z_scale_factor = 12.0
# 0.5 is rounded to 1, so this says they must be within 3.0 sigma
N_k = np.array([1000, 500, 0, 800])


def generate_ho(O_k = np.array([1.0, 2.0, 3.0, 4.0]), K_k = np.array([0.5, 1.0, 1.5, 2.0])):
    return "Harmonic Oscillators", harmonic_oscillators.HarmonicOscillatorsTestCase(O_k, K_k)


def generate_exp(rates=np.array([1.0, 2.0, 3.0, 4.0])):  # Rates, e.g. Lambda
    return "Exponentials", exponential_distributions.ExponentialTestCase(rates)


def convert_to_differences(x_ij, dx_ij, xa):
    xa_ij = xa - np.vstack(xa)

    # add ones to the diagonal of the uncertainties, because they are zero
    for i in range(len(N_k)):
        dx_ij[i, i] += 1
    z = (x_ij - xa_ij) / dx_ij
    for i in range(len(N_k)):
        z[i, i] = x_ij[i, i]-xa_ij[i, i]  # these terms should be zero; so we only throw an error if they aren't
    return z


system_generators = [generate_ho, generate_exp]
observables = ['position', 'position^2', 'RMS deviation', 'potential energy']


@pytest.fixture(scope="module", params=system_generators)
def mbar_and_test(request):
    name, test = request.param()
    x_n, u_kn, N_k_output, s_n = test.sample(N_k, mode='u_kn')
    assert_equal(N_k, N_k_output)
    mbar = MBAR(u_kn, N_k)
    yield_bundle = {
        'mbar': mbar,
        'test': test,
        'x_n': x_n,
        'u_kn': u_kn,
    }
    yield yield_bundle


@pytest.mark.parametrize("system_generator", system_generators)
def test_analytical(system_generator):
    """Generate test objects and calculate analytical results."""
    name, test = system_generator()
    mu = test.analytical_means()
    variance = test.analytical_variances()
    f_k = test.analytical_free_energies()
    for observable in observables:
        A_k = test.analytical_observable(observable=observable)
    s_k = test.analytical_entropies()


@pytest.mark.parametrize("system_generator", system_generators)
def test_sample(system_generator):
    """Draw samples via test object."""

    name, test = system_generator()
    print(name)

    x_n, u_kn, N_k, s_n = test.sample([5, 6, 7, 8], mode='u_kn')
    x_n, u_kn, N_k, s_n = test.sample([5, 5, 5, 5], mode='u_kn')
    x_n, u_kn, N_k, s_n = test.sample([1, 1, 1, 1], mode='u_kn')
    x_n, u_kn, N_k, s_n = test.sample([10, 0, 8, 0], mode='u_kn')

    x_kn, u_kln, N_k = test.sample([5, 6, 7, 8], mode='u_kln')
    x_kn, u_kln, N_k = test.sample([5, 5, 5, 5], mode='u_kln')
    x_kn, u_kln, N_k = test.sample([1, 1, 1, 1], mode='u_kln')
    x_kn, u_kln, N_k = test.sample([10, 0, 8, 0], mode='u_kln')


def test_mbar_free_energies(mbar_and_test):

    """Can MBAR calculate moderately correct free energy differences?"""
    mbar, test = mbar_and_test['mbar'], mbar_and_test['test']
    results = mbar.getFreeEnergyDifferences()
    fe = results['Delta_f']
    fe_sigma = results['dDelta_f']

    fe, fe_sigma = fe[0, 1:], fe_sigma[0, 1:]

    fe0 = test.analytical_free_energies()
    fe0 = fe0[1:] - fe0[0]

    z = (fe - fe0) / fe_sigma
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computeExpectations_position_averages(mbar_and_test):

    """Can MBAR calculate E(x_n)??"""

    mbar, test, x_n = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n']
    results = mbar.computeExpectations(x_n)
    mu = results['mu']
    sigma = results['sigma']

    mu0 = test.analytical_observable(observable='position')

    z = (mu0 - mu) / sigma
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computeExpectations_position_differences(mbar_and_test):

    """Can MBAR calculate E(x_n)??"""

    mbar, test, x_n = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n']
    results = mbar.computeExpectations(x_n, output='differences')
    mu_ij = results['mu']
    sigma_ij = results['sigma']

    mu0 = test.analytical_observable(observable='position')
    z = convert_to_differences(mu_ij, sigma_ij, mu0)
    assert_almost_equal(z / z_scale_factor, np.zeros(np.shape(z)), decimal=0)


def test_mbar_computeExpectations_position2(mbar_and_test):

    """Can MBAR calculate E(x_n^2)??"""

    mbar, test, x_n = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n']
    results = mbar.computeExpectations(x_n ** 2)
    mu = results['mu']
    sigma = results['sigma']
    mu0 = test.analytical_observable(observable='position^2')

    z = (mu0 - mu) / sigma
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computeExpectations_potential(mbar_and_test):

    """Can MBAR calculate E(u_kn)??"""

    mbar, test, u_kn = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['u_kn']
    results = mbar.computeExpectations(u_kn, state_dependent = True)
    mu = results['mu']
    sigma = results['sigma']
    mu0 = test.analytical_observable(observable='potential energy')
    print(mu)
    print(mu0)
    z = (mu0 - mu) / sigma
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computeMultipleExpectations(mbar_and_test):

    """Can MBAR calculate E(u_kn)??"""

    mbar, test, x_n, u_kn = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n'], mbar_and_test['u_kn']
    A = np.zeros([2, len(x_n)])
    A[0, :] = x_n
    A[1, :] = x_n**2
    state = 1
    results = mbar.computeMultipleExpectations(A, u_kn[state,:])
    mu = results['mu']
    sigma = results['sigma']

    mu0 = test.analytical_observable(observable='position')[state]
    mu1 = test.analytical_observable(observable='position^2')[state]
    z = (mu0 - mu[0]) / sigma[0]
    assert_almost_equal(z / z_scale_factor, 0*z, decimal=0)
    z = (mu1 - mu[1]) / sigma[1]
    assert_almost_equal(z / z_scale_factor, 0*z, decimal=0)


def test_mbar_computeEntropyAndEnthalpy(mbar_and_test):

    """Can MBAR calculate f_k, <u_k> and s_k ??"""

    mbar, test, x_n, u_kn = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n'], mbar_and_test['u_kn']
    results = mbar.computeEntropyAndEnthalpy(u_kn)
    f_ij = results['Delta_f']
    df_ij = results['dDelta_f']
    u_ij = results['Delta_u']
    du_ij = results['dDelta_u']
    s_ij = results['Delta_s']
    ds_ij = results['dDelta_s']

    fa = test.analytical_free_energies()
    ua = test.analytical_observable('potential energy')
    sa = test.analytical_entropies()

    fa_ij = fa-fa.T
    ua_ij = ua-ua.T
    sa_ij = sa-sa.T

    z = convert_to_differences(f_ij, df_ij, fa)
    assert_almost_equal(z / z_scale_factor, np.zeros(np.shape(z)), decimal=0)
    z = convert_to_differences(u_ij, du_ij, ua)
    assert_almost_equal(z / z_scale_factor, np.zeros(np.shape(z)), decimal=0)
    z = convert_to_differences(s_ij, ds_ij, sa)
    assert_almost_equal(z / z_scale_factor, np.zeros(np.shape(z)), decimal=0)


def test_mbar_computeEffectiveSampleNumber(mbar_and_test):
    """ testing computeEffectiveSampleNumber """

    mbar = mbar_and_test['mbar']
    # one mathematical effective sample numbers should be between N_k and sum_k N_k
    N_eff = mbar.computeEffectiveSampleNumber()
    sumN = np.sum(N_k)
    assert all(N_eff > N_k)
    assert all(N_eff < sumN)


def test_mbar_computeOverlap_analytical():
    """Tests Overlap with identical states, which gives analytical results."""

    d = len(N_k)
    even_O_k = 2.0*np.ones(d)
    even_K_k = 0.5*np.ones(d)
    even_N_k = 100*np.ones(d)
    name, test = generate_ho(O_k=even_O_k, K_k=even_K_k)
    x_n, u_kn, N_k_output, s_n = test.sample(even_N_k, mode='u_kn')
    mbar = MBAR(u_kn, even_N_k)

    results = mbar.computeOverlap()
    overlap_scalar = results['scalar']
    eigenval = results['eigenvalues']
    O = results['matrix']

    reference_matrix = (1.0/d)*np.ones([d,d])
    reference_eigenvalues = np.zeros(d)
    reference_eigenvalues[0] = 1.0
    reference_scalar = np.float64(1.0)

    assert_almost_equal(O, reference_matrix, decimal=precision)
    assert_almost_equal(eigenval, reference_eigenvalues, decimal=precision)
    assert_almost_equal(overlap_scalar, reference_scalar, decimal=precision)


def test_mbar_computeOverlap_nonanalytical(mbar_and_test):
    """Tests Overlap with stochastic tests"""
    mbar = mbar_and_test['mbar']
    results = mbar.computeOverlap()
    overlap_scalar = results['scalar']
    eigenval = results['eigenvalues']
    O = results['matrix']

    assert isinstance(overlap_scalar, (float, int))
    # rows of matrix should sum to one
    sumrows = np.array(np.sum(O, axis=1))
    assert_almost_equal(sumrows, np.ones(np.shape(sumrows)), decimal=precision)
    assert_almost_equal(eigenval[0], np.float64(1.0), decimal=precision)


def test_mbar_getWeights(mbar_and_test):

    """ testing getWeights """

    mbar = mbar_and_test['mbar']
    W = mbar.getWeights()
    sumrows = np.sum(W, axis=0)
    assert_almost_equal(sumrows, np.ones(len(sumrows)), decimal=precision)


@pytest.mark.parametrize("system_generator", system_generators)
def test_mbar_computePerturbedFreeEnergeies(system_generator):

    """ testing computePerturbedFreeEnergies """

    # only do MBAR with the first and last set

    name, test = system_generator()
    x_n, u_kn, N_k_output, s_n = test.sample(N_k, mode='u_kn')
    numN = np.sum(N_k[:2])
    mbar = MBAR(u_kn[:2, :numN], N_k[:2])
    results = mbar.computePerturbedFreeEnergies(u_kn[2:, :numN])
    fe = results['Delta_f']
    fe_sigma = results['dDelta_f']

    fe, fe_sigma = fe[0,1:], fe_sigma[0,1:]

    print(fe, fe_sigma)
    fe0 = test.analytical_free_energies()[2:]
    fe0 = fe0[1:] - fe0[0]

    z = (fe - fe0) / fe_sigma
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computePMF():

    """ testing computePMF """

    # Does not work with the Exponential Test Case

    name, test = generate_ho()
    x_n, u_kn, N_k_output, s_n = test.sample(N_k, mode='u_kn')
    mbar = MBAR(u_kn, N_k)
    #do a 1d PMF of the potential in the 3rd state:
    refstate = 2
    dx = 0.25
    xmin = test.O_k[refstate] - 1
    xmax = test.O_k[refstate] + 1
    within_bounds = (x_n >= xmin) & (x_n < xmax)
    bin_centers = dx*np.arange(np.int(xmin/dx), np.int(xmax/dx)) + dx/2
    bin_n = np.zeros(len(x_n), int)
    bin_n[within_bounds] = 1 + np.floor((x_n[within_bounds]-xmin)/dx)
    # 0 is reserved for samples outside the domain.  We will ignore this state
    range = np.max(bin_n)+1
    results = mbar.computePMF(u_kn[refstate, :], bin_n, range, uncertainties='from-specified', pmf_reference=1)
    f_i = results['f_i']
    df_i = results['df_i']

    f0_i = 0.5*test.K_k[refstate]*(bin_centers-test.O_k[refstate])**2
    f_i, df_i = f_i[2:], df_i[2:]  # first state is ignored, second is zero, with zero uncertainty
    normf0_i = f0_i[1:] - f0_i[0]  # normalize to first state
    z = (f_i - normf0_i) / df_i
    assert_almost_equal(z / z_scale_factor, np.zeros(len(z)), decimal=0)


def test_mbar_computeExpectationsInner(mbar_and_test):

    """Can MBAR calculate general expectations inner code (note: this just tests completion)"""
    mbar, test, x_n, u_kn = mbar_and_test['mbar'], mbar_and_test['test'], mbar_and_test['x_n'], mbar_and_test['u_kn']
    A_in = np.array([x_n, x_n ** 2, x_n ** 3])
    u_n = u_kn[:2, :]
    state_map = np.array([[0, 0], [1, 0], [2, 0], [2, 1]], int)
    _ = mbar.computeExpectationsInner(A_in, u_n, state_map)
