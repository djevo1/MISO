import os
import sys
import time

import numpy as np

import scipy
import scipy.misc 
from scipy.special import gammaln

import misopy
import misopy.internal_tests
import misopy.internal_tests.py_scores as py_scores

import misopy.pyx.miso_scores_single as scores_single
import misopy.pyx.miso_scores_paired as scores_paired
import misopy.pyx.stat_helpers as stat_helpers
import misopy.pyx.sampling_utils as sampling_utils

# Global data
num_inc = 3245
num_exc = 22
num_com = 39874
reads = [[1,0]] * num_inc + \
        [[0,1]] * num_exc + \
        [[1,1]] * num_com
reads = np.array(reads, dtype=np.dtype("i"))
isoform_nums = []
read_len = 40
overhang_len = 4
num_parts_per_isoform = np.array([3, 2], dtype=np.dtype("i"))
iso_lens = np.array([1253, 1172], dtype=np.dtype("i"))
# Assignment of reads to isoforms: assign half of
# the common reads to isoform 0, half to isoform 1
isoform_nums = [0]*3245 + [1]*22 + [0]*19937 + [1]*19937
isoform_nums = np.array(isoform_nums, dtype=np.dtype("i"))
num_reads = len(reads)
total_reads = num_reads
num_calls = 2000


def get_reads(num_reads):
    return reads[0:num_reads]


def get_iso_nums(num_reads):
    return isoform_nums[0:num_reads]


def profile_lndirichlet():
    psi_vector = np.array([0.5, 0.5])
    test_array = np.array([1,2,3,4], dtype=np.float)
    scaled_lens = iso_lens - read_len + 1
    num_calls = 350
    # Get reads and isoform assignments
    num_reads = 500
    reads = get_reads(num_reads)
    iso_nums = get_iso_nums(num_reads)
    # Score dirichlet
    print "Benchmarking lndirichlet functions..."
    print stat_helpers.dirichlet_lnpdf(np.array([1, 1], dtype=np.float),
                                       np.array([0.5, 0.5]))
    print py_scores.dirichlet_lnpdf(np.array([1, 1]), np.array([0.5, 0.5]))


def profile_cumsum():
    psi_vector = np.array([0.5, 0.5])
    test_array = np.array([1,2,3,4], dtype=np.float)
    scaled_lens = iso_lens - read_len + 1
    num_calls = 350
    # Get reads and isoform assignments
    num_reads = 500
    print "Profiling numpy cumsum"
    t1 = time.time()
    np_result = None
    for n in np.arange(num_calls):
        np_result = np.cumsum(test_array)
    t2 = time.time()
    print "Took %.2f seconds" %(t2 - t1)
    print "np result -> ", np_result
    print "Profiling CYTHON cumsum"
    t1 = time.time()
    cy_result = None
    for n in np.arange(num_calls):
        cy_result = stat_helpers.my_cumsum(test_array)
    t2 = time.time()
    print "cy result -> ", cy_result
    for n in range(len(np_result)):
        assert np_result[n] == cy_result[n], \
          "Cumsum does not work."
    print "CYTHON took %.2f seconds" %(t2 - t1)


def profile_init_assignments():
    print "-" * 20
    print "Profiling init assignments..."
    psi_vector = np.array([0.5, 0.5])
    test_array = np.array([1,2,3,4], dtype=float)
    scaled_lens = iso_lens - read_len + 1
    num_calls = 10000
    # Get reads and isoform assignments
    #num_reads = 2
    #reads = np.array([[1, 0], [0, 1]]) 
    #iso_nums = np.array([0, 1])
    num_reads = 2000
    reads = get_reads(num_reads)
    iso_nums = get_iso_nums(num_reads)
    num_isoforms = 2
    t1 = time.time()
    print "Calling init assignments for %d calls, %d reads" \
          %(num_calls,
            num_reads)
    for n in range(num_calls):
        assignments = scores_single.init_assignments(reads,
                                                     num_reads,
                                                     num_isoforms)
    t2 = time.time()
    print "Init assignments took %.2f seconds" %(t2 - t1)
        

def profile_sample_reassignments():
    print "-" * 20
    print "Profiling sample assignments..."
    psi_vector = np.array([0.5, 0.5])
    test_array = np.array([1,2,3,4], dtype=np.float)
    scaled_lens = iso_lens - read_len + 1
    num_calls = 350
    # Get reads and isoform assignments
    #num_reads = 2
    #reads = np.array([[1, 0], [0, 1]]) 
    #iso_nums = np.array([0, 1])
    num_reads = 400
    reads = get_reads(num_reads)
    iso_nums = get_iso_nums(num_reads)
    # Score dirichlet
    print "Benchmarking lndirichlet functions..."
    print stat_helpers.dirichlet_lnpdf(np.array([1, 1], dtype=np.float),
                                          np.array([0.5, 0.5]))
    print py_scores.dirichlet_lnpdf(np.array([1, 1]), np.array([0.5, 0.5]))
    samples = np.zeros(100, dtype=np.dtype("i"))
    scores_single.sample_from_multinomial(np.array([0.1, 0.3, 0.6]),
                                                   100,
                                                   samples)
    log_psi_frag = np.log(psi_vector) + np.log(scaled_lens)
    log_psi_frag = log_psi_frag - scipy.misc.logsumexp(log_psi_frag)
    log_num_reads_possible_per_iso = np.log(scaled_lens)
    print "Calling sample reassignments %d times " \
          "with %d reads" %(num_calls, num_reads)
    new_assignments = np.empty(num_reads, dtype=np.dtype("i"))
    t1 = time.time()
    for n in xrange(num_calls):
        scores_single.sample_reassignments(reads,
                                           psi_vector,
                                           log_psi_frag,
                                           log_num_reads_possible_per_iso,
                                           scaled_lens,
                                           iso_lens,
                                           num_parts_per_isoform,
                                           iso_nums,
                                           num_reads,
                                           read_len,
                                           overhang_len,
                                           new_assignments)
    t2 = time.time()
    print "Sampling reassignments took %.2f seconds" %(t2 - t1)


def profile_sample_from_multinomial():
    """
    Multinomial sampling. This is the major bottleneck
    of the sampling functions.
    """
    print "-" * 20
    p = np.array([0.2, 0.1, 0.5])
    N = len(p)
    num_calls = 1000
    num_reads = 1000
    print "Sampling from multinomial for %d x %d times" %(num_reads,
                                                          num_calls)
    results = np.zeros(N, dtype=np.dtype("i"))
    t1 = time.time()
    for n in range(num_reads):
        for x in range(num_calls):
            scores_single.sample_from_multinomial(p, N, results)
    t2 = time.time()
    print "Sampling from multinomial took %.2f seconds" %(t2 - t1)


def profile_sample_from_normal():
    print "Profiling sampling from multivariate normal"
    mu = np.array([2.05, 0.55], dtype=float)
    sigma = np.matrix(np.array([[0.05, 0],
                                [0, 0.05]], dtype=float))
    # Get Cholesky decomposition L of Sigma covar matrix
    L = np.linalg.cholesky(sigma)
    k = mu.shape[0]
    all_numpy_samples = []
    all_pyx_samples = []
    # Compile a list of all the samples
    num_iter = 10000
    t1 = time.time()
    for n in range(num_iter):
        npy_samples = np.random.multivariate_normal(mu, sigma)
    t2 = time.time()
    print "Numpy sampling took %.2f seconds" %(t2 - t1)
    # Cython interface expects mu as a *column* vector
    mu_col = np.matrix(mu).T
    t1 = time.time()
    for n in range(num_iter):
        pyx_samples = sampling_utils.sample_multivar_normal(mu_col, L, k)
    t2 = time.time()
    print "Cython sampling took %.2f seconds" %(t2 - t1)
    

def profile_log_score_reads():
    print "-" * 20
    t1 = time.time()
    psi_vector = np.array([0.5, 0.5])
    scaled_lens = iso_lens - read_len + 1
    num_calls = 3000
    print "Profiling log_score_reads for %d calls..." %(num_calls)
    log_num_reads_possible_per_iso = np.log(scaled_lens)
    log_psi_frag = np.log(psi_vector) + np.log(scaled_lens)
    log_psi_frag = log_psi_frag - scipy.misc.logsumexp(log_psi_frag)
    results = np.empty(num_reads, dtype=float)
    for n in xrange(num_calls):
        v = scores_single.log_score_reads(reads,
                                          isoform_nums,
                                          num_parts_per_isoform,
                                          iso_lens,
                                          log_num_reads_possible_per_iso,
                                          num_reads,
                                          read_len,
                                          overhang_len,
                                          results)
    t2 = time.time()
    print "log_score_reads took %.2f seconds per %d calls." %(t2 - t1,
                                                              num_calls)


    
def profile_sum_log_score_reads():
    print "-" * 20
    t1 = time.time()
    psi_vector = np.array([0.5, 0.5])
    scaled_lens = iso_lens - read_len + 1
    num_calls = 3000
    print "Profiling SUM log score reads (%d reads)" %(num_reads)
    print "Profiling SUM log_score_reads for %d calls..." %(num_calls)
    log_num_reads_possible_per_iso = np.log(scaled_lens)
    log_psi_frag = np.log(psi_vector) + np.log(scaled_lens)
    log_psi_frag = log_psi_frag - scipy.misc.logsumexp(log_psi_frag)
    for n in xrange(num_calls):
        v = scores_single.sum_log_score_reads(reads,
                                              isoform_nums,
                                              num_parts_per_isoform,
                                              iso_lens,
                                              log_num_reads_possible_per_iso,
                                              num_reads,
                                              read_len,
                                              overhang_len)
    t2 = time.time()
    print "SUM log_score_reads took %.2f seconds per %d calls." %(t2 - t1,
                                                                  num_calls)
    

def log_score_assignments(isoform_nums, psi_vector, scaled_lens, num_reads):
    """
    Score an assignment of a set of reads given psi
    and a gene (i.e. a set of isoforms).
    """
    psi_frag = np.log(psi_vector) + np.log(scaled_lens)
    psi_frag = psi_frag - scipy.misc.logsumexp(psi_frag)
    psi_frags = np.tile(psi_frag, [num_reads, 1])
    return psi_frags[np.arange(num_reads), isoform_nums]


def profile_log_score_assignments():
    print "-" * 20
    psi_vector = np.array([0.5, 0.5])
    scaled_lens = iso_lens - read_len + 1
    num_calls = 1000
    print "Profiling log score assignments (%d reads)" %(num_reads)
    print "Profiling log score assignments in PYTHON..."
    t1 = time.time()
    for n in range(num_calls):
        v1 = log_score_assignments(isoform_nums,
                                   psi_vector,
                                   scaled_lens,
                                   num_reads)
    t2 = time.time()
    print "Python took %.2f seconds" %(t2 - t1)
    print "Profiling log score assignments in cython..."
    log_psi_frag = np.log(psi_vector) + np.log(scaled_lens)
    log_psi_frag = log_psi_frag - scipy.misc.logsumexp(log_psi_frag)
    t1 = time.time()
    results = np.empty(num_reads, dtype=float)
    for n in range(num_calls):
        v2 = scores_single.log_score_assignments(isoform_nums,
                                                 log_psi_frag,
                                                 num_reads,
                                                 results)
    t2 = time.time()
    print "Cython took %.2f seconds" %(t2 - t1)
    print "RESULTS"
    print "-" * 4
    print "Python: "
    print v1
    print "Cython: "
    print v2


def profile_logistic_normal_log_pdf():
    theta = np.array([0.5, 0.5])
    mu = np.array([0.8])
    num_isoforms = 2
    proposal_diag = 0.05
    sigma = py_scores.set_diag(np.zeros((num_isoforms-1, num_isoforms-1)),
                               proposal_diag)
    num_calls = 5000
    t1 = time.time()
    for n in range(num_calls):
        result_numpy = \
          py_scores.original_logistic_normal_log_pdf(theta, mu, sigma)
    t2 = time.time()
    print "Python logistic normal took %.2f seconds" %(t2 - t1)
    t1 = time.time()
    for n in range(num_calls):
        result_pyx = stat_helpers.logistic_normal_log_pdf(theta[:-1],
                                                          mu,
                                                          proposal_diag)
    t2 = time.time()
    print "Cython logistic normal took %.2f seconds" %(t2 - t1)


def profile_rand_normals():
    num_calls = 25000
    print "Calling numpy rand normals for %d calls" %(num_calls)
    t1 = time.time()
    npy_vals = []
    for n in xrange(num_calls):
        npy_vals.append(np.random.normal([0],[1]))
    t2 = time.time()
    print "Numpy rand normals took %.2f seconds." %(t2 - t1)
    print "Calling Cython rand normals for %d calls" %(num_calls)
    t1 = time.time()
    cython_vals = []
    for n in xrange(num_calls):
        cython_vals.append(sampling_utils.rand_normal_boxmuller())
    t2 = time.time()
    mean_npy = np.mean(npy_vals)
    sd_npy = np.std(npy_vals)
    mean_cython = np.mean(cython_vals)
    sd_cython = np.std(cython_vals)
    print "Cython rand normals took %.2f seconds" %(t2 - t1)
    print "Mean npy values: %.2f" %(mean_npy)
    print "Sd npy values: %.2f" %(sd_npy)
    print "--" * 10
    print "Mean cython values: %.2f" %(mean_cython)
    print "Sd cython values: %.2f" %(sd_cython)


def main():
    profile_sample_from_normal()
    profile_rand_normals()
    profile_sample_reassignments()
    
    profile_init_assignments()
    profile_sample_from_multinomial()
    # read scoring
    profile_log_score_reads()
    profile_sum_log_score_reads()

    # assignment scoring
    profile_log_score_assignments()
    profile_logistic_normal_log_pdf()
    

if __name__ == "__main__":
    main()
