'''
Created on Sep 20, 2013

@author: ksahlin
'''

# from math import log

from scipy import stats

from mpmath import *
mp.dps = 100 # decimal digits of precision

from scipy.stats import poisson, nbinom,uniform

from coverage import mean_span_coverage, Param
#import math

def normpdf(x, mu, sigma):
    #Get much better approximations with Decimal (simply more decimals)
    #getcontext().prec = 100
    #u = Decimal(str(x - mu)) / Decimal(str(abs(sigma)))
    u = mpf((x - mu)) / mpf(sigma)
    #y = float(str((1 / Decimal(str((math.sqrt(2 * math.pi) * abs(sigma))))) * Decimal(str(-u * u / 2)).exp()))
    y = (1 / mpf((sqrt(2 * pi) * sigma)) * exp(mpf(-u * u / 2)))
    return y

def w(o, r, a, b=None, s=None, infer_lib_mean=False):
    w_fcn = []
    ##
    # Weight function in the case where we want to estimate the original library mean
    # (full original distribution) from alignments of paired reads onto a contig
    if infer_lib_mean:
        return(max(a - (o - 2 * s) + 1, 0))


    ##
    # Weight function in the case where we want to calculate expected or inferred mean of
    # observations coming from our library with truncation and skewness 
    # (e.g. over insertions or scaffold gaps).

    s = s if s != None else r / 2  # if softclipped is not set softclipped to half of read length

    w_fcn.append(max(o - 2 * (r - s) + 1, 0))
    if b:
        w_fcn.append(max(a + b - (o - 2 * s) + 1, 0))
        w_fcn.append(max(min(a, b) - (r - s) + 1, 0))
    else:
        w_fcn.append(max(a - (o - 2 * s) + 1, 0))

    return(min(w_fcn))

def estimate_library_mean(list_of_obs, r, a, soft=None):
    sample_obs_sum = 0
    number_of_obs_sum = 0
    for o in list_of_obs:
        weight = float(w(o, r, a, s=soft, infer_lib_mean=True))
        sample_obs_sum += o / weight
        number_of_obs_sum += 1 / weight
    print sample_obs_sum / number_of_obs_sum
    return(sample_obs_sum / number_of_obs_sum)

def estimate_library_stddev(list_of_obs, r, a, soft=None):
    raise NotImplementedError



# def dw(o, r, a, b=None, s=None):
#     raise NotImplementedError

# def ddw(o, r, a, b=None, s=None):
#     raise NotImplementedError

# def f_general(o, r, a, b=None, s=None):

#     raise NotImplementedError

# def f_normal(x, mu, sigma):
#     stats.norm.pdf(x, mu, sigma)
#     raise NotImplementedError

# def df_normal(o, r, a, b=None, s=None):
#     raise NotImplementedError

# class Weight(object):
#     def __init__(self, o, r, a, b=None, s=None):
#         self.o = o
#         self.r = r
#         self.a = a
#         self.b = b
#         self.s = s if s != None else r / 2
#         return()

#     def w(self):
#         pass


#     def dw(self):
#         raise NotImplementedError


class NormalModel(object):
    def __init__(self, mu, sigma, r, s=None):
        self.mu = mu
        self.sigma = sigma
        self.r = r
        self.s = s if s != None else r / 2

    def expected_mean(self, z, a, b=None):
        E_x_given_z = 0
        norm_const = 0
        for t in range(z + 2 * (self.r - self.s), self.mu + 6 * self.sigma): #iterate over possible fragment sizes   ##range((self.mu - 5 * self.sigma) - y, self.mu + 6 * self.sigma - y): #
            norm_const += w(t - z , self.r, a, b, self.s) * normpdf(t + 0.5, self.mu, self.sigma)  # +0.5 because we approximate a continuous distribution (avg function value of pdf given points i and i+1, just like integration)

        for y in range(2 * (self.r - self.s), self.mu + 6 * self.sigma - z): # iterate over possible observation span
            weight = w(y , self.r, a, b, self.s)
            w_times_f = weight * normpdf(z + y + 0.5, self.mu, self.sigma) # +0.5 because we approximate a continuous distribution (avg function value of pdf given points i and i+1, just like integration)
            E_x_given_z += (y + z) * w_times_f / norm_const
        return(E_x_given_z)

    def expected_standard_deviation(self, z, a, b=None):
        E_x_given_z = self.expected_mean(z, a, b)
        E_x_square_given_z = 0
        norm_const = 0
        for t in range(z + 2 * (self.r - self.s), self.mu + 6 * self.sigma): #iterate over possible fragment sizes   ##range((self.mu - 5 * self.sigma) - y, self.mu + 6 * self.sigma - y): #
            norm_const += w(t - z , self.r, a, b, self.s) * stats.norm.pdf(t + 0.5, self.mu, self.sigma)  # +0.5 because we approximate a continuous distribution (avg function value of pdf given points i and i+1, just like integration)

        for y in range(2 * (self.r - self.s), self.mu + 6 * self.sigma - z): # iterate over possible observation span
            weight = w(y , self.r, a, b, self.s)
            w_times_f = weight * stats.norm.pdf(z + y + 0.5, self.mu, self.sigma) # +0.5 because we approximate a continuous distribution (avg function value of pdf given points i and i+1, just like integration)
            E_x_square_given_z += (y + z) ** 2 * w_times_f / norm_const

        Var_x_given_z = (E_x_square_given_z - E_x_given_z ** 2) ** 0.5
        return(Var_x_given_z)



    def infer_mean(self, list_of_obs, a, precision, b=None, with_covarage = False):
        '''
            Instance method of a NormalModel object. Infers the mean fragment size of a given set of 
            paired read observations.
            
            Keyword arguments:
            @ argument list_of_obs A list of...
            @ argument a Reference sequence length
            @ argument precision Number of base pairs between every point estimate of the ML distribution. 
        '''

        likelihood_curve = self.get_likelihood_function(list_of_obs, a, precision, b, with_covarage)
        ml_gap = max(likelihood_curve, key=lambda x: x[1])
        #print likelihood_curve, ml_gap
        avg_obs = sum(list_of_obs) / len(list_of_obs)  # avg_obs is an integer (rounded to an even bp)
        print avg_obs + ml_gap[0]
        return(avg_obs + ml_gap[0])

    def infer_variance(self):
        raise NotImplementedError

    def get_likelihood_function(self, list_of_obs, a, precision, b=None, coverage = False,n = None):
        '''This function gives back the likelihood values for Z (gap/unknown sequence length)
            parameters
            __________
            @param list_of_obs: A list of observations
            @param a: Reference sequence length
            @param precision: 

        '''

        likelihood_curve = []

        ## For plotting!
        #o_temp =  list_of_obs[0] # <-- Only for plotting
        # range( 3 * self.sigma - o_temp, - o_temp + self.mu + int(5.5 * self.sigma) - (2 * (self.r - self.s)), precision): 
        # range( 3 * self.sigma - o_temp, - o_temp + self.mu + int(5 * self.sigma) - (2 * (self.r - self.s)), precision): 
        # <-- Use the above range for plotting with same intervals, this function gives back likelihood alues of 
        # X instead of Z which is what we want in the MLfcns plots.

        ##
        # This loop iterates over all possible gaps z, we want to see the ML estimation of
        # The interesting range is in general not above  mean + 3*stddev

        for z in range(-3 * self.sigma, self.mu + 3 * self.sigma - (2 * (self.r - self.s)), precision): 
            
            ##
            # calculate the normalization constant for a given gap length z
            norm_const = 0
            for t in range(z + 2 * (self.r - self.s), self.mu + 7 * self.sigma): #iterate over possible fragment sizes   ##range((self.mu - 5 * self.sigma) - y, self.mu + 6 * self.sigma - y): #
                #norm_const += w(t - z , self.r, a, b, self.s) * stats.norm.pdf(t + 0.5, self.mu, self.sigma)  # +0.5 because we approximate a continuous distribution (avg function value of pdf given points i and i+1, just like integration)
                norm_const += w(t - z , self.r, a, b, self.s) * normpdf(t + 0.5, self.mu, self.sigma)
            #print z, norm_const #, norm_const2

            ##
            # calculate the nominator (relative frequency given a gap)
            # in log() format
            log_p_x_given_z = 0
            for o in list_of_obs:
                weight = w(o , self.r, a, b, self.s)
                lib_dist = normpdf(o + z + 0.5, self.mu, self.sigma)
                #print z, weight, lib_dist, norm_const
                log_p_x_given_z += log(weight) + log(lib_dist) - log(norm_const)

            if coverage:
                p_n_given_z = self.coverage_probability(n, a, self.mu, self.sigma, z, coverage, self.r, self.s, b)
                log_p_n_given_z = log(p_n_given_z)/n
                likelihood_curve.append((z, log_p_x_given_z + log_p_n_given_z))
            else:
                likelihood_curve.append((z, log_p_x_given_z))

        return(likelihood_curve)


    def coverage_probability(self,nr_obs, a, mean_lib, stddev_lib,z, coverage_mean, read_len, softclipped, b=None):
        ''' Distribution P(o|c,z) for prior probability over coverage.
            This probability distribution is implemented as an poisson 
            distribution.

            Attributes:

            c       -- coverage
            mean    -- mean value of poisson distribution.

            Returns probability P(c)

        '''
        if not b: 
            # only one reference sequence.
            # We split the reference sequence into two equal 
            # length sequences to fit the model. 
            a = a/2
            b = a/2
        param = Param(mean_lib, stddev_lib, coverage_mean, read_len, softclipped)
        lambda_ = mean_span_coverage(a, b, z, param)

        #print lambda_ , z,uniform.pdf(nr_obs, loc=lambda_- 0.3*lambda_, scale=lambda_ + 0.3*lambda_ ),nr_obs
        #p = 0.01
        #n = (p*lambda_)/(1-p)
        #return uniform.pdf(nr_obs, loc=0, scale=50)
        #return nbinom.pmf(nr_obs, n, p, loc=0) 
        return poisson.pmf(nr_obs, lambda_, loc=0)

         




class GeneralModel(object): 
    def __init__(self, histogram, r, s=None):
        self.histogram = histogram
        self.r = r
        self.s = s if s != None else r / 2

    def expected_mean(self, z, a, b=None):

        return()

