'''
Created on Sep 25, 2013

@author: ksahlin
'''

import sys
import os

import argparse
import pysam
import subprocess

import model
import bam_file_gen

# model.estimate_library_mean(list_of_obs, r, a, s=None)

class Args(object):
    def __init__(self, in_values, outpath, genomelen):
        self.lib_mean, self.lib_std, self.coverage, self.read_length, self.cont_len, self.nr_trials = in_values
        self.outpath = outpath
        self.genomelen = genomelen


##
# testing the yeild function
def read_input(sim_file):
    for line in sim_file:
        try:
            in_values = map(lambda x: int(x), line.strip().split())
        except:
            continue
        yield in_values

def create_bam(args):
    return(bam_file_gen.main(args))

def print_output():
    pass

def get_bwa_results(bwa_file):
    for line in open(bwa_file, 'r'):
        print line

def get_getdistr_results(bam_path, args):

    list_of_obs = []
    list_of_isize = []
    with pysam.Samfile(bam_path, 'rb') as bam_file:
        for alignedread in bam_file:
            if alignedread.is_read1 and not alignedread.is_unmapped and not alignedread.mate_is_unmapped :  # only count an observation from a read pair once 
                list_of_obs.append(alignedread.tlen)
                #if len(alignedread.cigar) > 1:
                print alignedread.cigarstring

    # Put allowed soft clips to 0, because BWA does not align outside boundaries of the reference.
    # i.e. reeds need to be fully contained (mapped) to the contig in this case.
    mean_est = model.estimate_library_mean(list_of_obs, 100, args.cont_len, soft=0)
    mean_naive = sum(list_of_obs) / float(len(list_of_obs))
    print(mean_est, mean_naive, len(list_of_obs))
    print list_of_obs


def main(args):
    for in_values in read_input(open(args.sim_file, 'r')):
        successful_experiments = 1
        while successful_experiments <= args.experiments: # for exp in xrange(args.experiments):
            args_object = Args(in_values, args.outpath, args.genomelen)
            print 'Processing experiment ' + str(successful_experiments)
            print 'With setting: ', in_values
            try:
                bam_path = create_bam(args_object)
            except subprocess.CalledProcessError:
                continue
            get_bwa_results(os.path.join(args.outpath, 'bwa_out'))
            print bam_path
            get_getdistr_results(bam_path, args_object)
            print_output()
            successful_experiments += 1


if __name__ == '__main__':
    ##
    # Take care of input
    parser = argparse.ArgumentParser(description="Simulate paired end reads with a given mean and standard deviation on mean insert size. A given coverage should also be provided.")
    parser.add_argument('sim_file', type=str, help='Main simulation file. ')
    #parser.add_argument('genome', type=str, help='Name of the reference sequence. ')
    #parser.add_argument('mean', type=int, help='mean insert size. ')
    #parser.add_argument('std_dev', type=int, help='Standard deviation of insert size ')
    #parser.add_argument('read_length', type=int, help='Length of read fragments within a pair. ')
    #parser.add_argument('coverage', type=int, help='Coverage for read library. ')
    parser.add_argument('outpath', type=str, help='Path to output location. ')
    parser.add_argument('experiments', type=int, help='Number of experiment for each line in sim_in.txt file to run. ')
    parser.add_argument('genomelen', type=int, help='Length of the reference sequence. ')
    #parser.add_argument('c_len', type=int, help='Contig length. ')

    args = parser.parse_args()
    main(args)





