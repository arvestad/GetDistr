
import argparse

import calc_pvalues
import lib_est
import get_bp_stats
import get_gap_coordinates
import cluster_p_vals

import os,sys

class Parameters(object):
	"""docstring for Parameters"""
	def __init__(self):
		super(Parameters, self).__init__()
		self.mu = None
		self.sigma = None
		self.adjusted_mu = None
		self.adjusted_sigma = None
		self.min_isize = None
		self.max_isize = None
		self.read_length = None
		self.pval = None
		self.total_basepairs = None

		self.outfolder = None
		self.plots = None

def collect_libstats(args,infile):
	info_file = open(infile,'r')
	param = Parameters()
	param.outfolder = args.outfolder
	vals = filter( lambda line: line[0] != '#', info_file.readlines())[0:]
	print vals
	[mean,stddev] =  vals[0].strip().split()
	[min_lib_isize,max_lib_isize] = vals[1].strip().split()
	[read_length] = vals[2].strip().split()
	[adjusted_mean, adjusted_stddev] = vals[3].strip().split()
	param.mu, param.sigma, param.adjusted_mu,param.adjusted_sigma = float(mean), float(stddev), float(adjusted_mean), float(adjusted_stddev)
	param.min_isize, param.max_isize = int(min_lib_isize), int(max_lib_isize)
	param.read_length = float(read_length)
	print param.mu, param.sigma, param.adjusted_mu, param.adjusted_sigma, param.min_isize, param.max_isize, param.read_length
	param.max_window_size = int(param.mu) if param.mu <= 1000 else int(param.mu)/2
	param.total_basepairs = int(vals[4].strip().split()[0])
	param.pval = 0.05/ param.total_basepairs # bonferroni correction

	param.scaf_lengths = {}
	for line in vals[5:]:
		ref,length = line.strip().split('|')
		length = int(length)
		param.scaf_lengths[ref] = length

	return param

def get_lib_est(args):
	lib_out = os.path.join(args.outfolder,'library_info.txt')
	lib_est.LibrarySampler(args.bampath,lib_out)

def bp_stats(args):
	lib_out = os.path.join(args.outfolder,'library_info.txt')
	param = collect_libstats(args,lib_out)
	get_bp_stats.parse_bam(args.bampath, param)

def gap_coordinates(args):
	gaps_out = os.path.join(args.outfolder,'gap_coordinates.txt')
	get_gap_coordinates.get_gap_coordinates(args.assembly_file, gaps_out)

def p_value_cluster(args):
	bp_file = os.path.join(args.outfolder,'bp_stats.txt')
	gap_file = os.path.join(args.outfolder,'gap_coordinates.txt')
	lib_out = os.path.join(args.outfolder,'library_info.txt')
	param = collect_libstats(args,lib_out)
	param.plots = args.plots
	cluster_p_vals.main(bp_file, gap_file,param)

def main_pipline(args):
	"""
		Algorithm a follows:
			1 Estimate library parameters (lib_est) and print to library_info.txt.
			2 Parse bamfile and get mean and stddev over each position in assembly (get_bp_stats)
				Print to bp_stats.csv
			3 Get gap coordinates in assembly (get_gap_coordinates)
				print to gap_coordinates.csv
			4 Calculate pvalues based on expected span mean and stddev (calc_pvalues)
				print ctg_accesion, pos, pvalues to p_values.csv
			5 Cluster p-values into significant cliques and print significant
				locations on GFF format.


	"""

	if not os.path.exists(args.outfolder):
		os.makedirs(args.outfolder)

	# 1
	lib_out = os.path.join(args.outfolder,'library_info.txt')
	lib_est.LibrarySampler(args.bampath,lib_out)
 
 	# 2
	param = collect_libstats(args,lib_out)
	get_bp_stats.parse_bam(args.bampath, param)

	# 3
	#get_gap_coordinates.
	gap_coordinates(args)

	# 4 
	p_value_cluster(args)
	#cluster_pvals(args.outfolder, args.assembly_file, args.pval, args.window_size)



if __name__ == '__main__':

	# create the top-level parser
	parser = argparse.ArgumentParser()#prog="Infer variants with simple p-value test using theory of GetDistr - proof of concept.")
	#parser.add_argument('--foo', action='store_true', help='help for foo arg.')
	subparsers = parser.add_subparsers(help='help for subcommand')

	# create the parser for the "pipeline" command
	pipeline = subparsers.add_parser('pipeline', help='Run the entire pipeline')
	pipeline.add_argument('bampath', type=str, help='bam file with mapped reads. ')
	pipeline.add_argument('assembly_file', type=str, help='Fasta file with assembly/genome. ')
	pipeline.add_argument('outfolder', type=str, help='Outfolder. ')
	pipeline.add_argument('--plots', dest="plots", action='store_true', help='Plot pval distribution.')
	pipeline.set_defaults(which='pipeline')


	# create the parser for the "lib_est" command	
	lib_est_parser = subparsers.add_parser('lib_est', help='Estimate library parameters')
	lib_est_parser.add_argument('bampath', type=str, help='bam file with mapped reads. ')
	lib_est_parser.add_argument('outfolder', type=str, help='Outfolder. ')
	lib_est_parser.set_defaults(which='lib_est')
	
	# create the parser for the "get_bp_stats" command
	get_bp_stats_parser = subparsers.add_parser('get_bp_stats', help='Scan bam file and calculate pvalues for each base pair')
	get_bp_stats_parser.add_argument('bampath', type=str, help='bam file with mapped reads. ')
	get_bp_stats_parser.add_argument('outfolder', type=str, help='Outfolder. ')
	get_bp_stats_parser.set_defaults(which='get_bp_stats')

	# create the parser for the "get_gaps" command
	get_bp_stats_parser = subparsers.add_parser('get_gaps', help='Contig assembly file for gap positions')
	get_bp_stats_parser.add_argument('assembly_file', type=str, help='Fasta file with assembly/genome. ')
	get_bp_stats_parser.add_argument('outfolder', type=str, help='Outfolder. ')
	get_bp_stats_parser.set_defaults(which='get_gaps')

	# create the parser for the "pvalue_cluster" command
	pvalue_cluster_parser = subparsers.add_parser('cluster_pvals', help='Takes a pvalue file and clusters them into significan regions')
	pvalue_cluster_parser.add_argument('bp_file', type=str, help='bp_stats.txt file generated by "get_bp_stats" command. ')	
	pvalue_cluster_parser.add_argument('gap_file', type=str, help='gap_coordinates.txt file generated by "get_bp_stats" command. ')	
	pvalue_cluster_parser.add_argument('outfolder', type=str, help='Folder with p-value fila and "info.txt" file contianing parameters "scan_bam" output. ')
	pvalue_cluster_parser.add_argument('--plots', dest="plots", action='store_true', help='Plot pval distribution.')
	pvalue_cluster_parser.set_defaults(which='cluster_pvals')

	# parser.add_argument('mean', type=int, help='mean insert size. ')
	# parser.add_argument('stddev', type=int, help='Standard deviation of insert size ')

	
	args = parser.parse_args()

	if args.which == 'pipeline' or args.which == 'get_bp_stats' or args.which == 'lib_est':
		try:
		    open(args.bampath)
		except IOError as e:
		    sys.exit("couldn't find BAM file: " + args.bampath + " check that the path is correct and that the file exists")
		try:
		    open(args.bampath + '.bai')
		except IOError as e:
		    print "couldn't find index file: ", args.bampath + '.bai', " check that the path is correct and that the bam file is sorted and indexed"
		    sys.exit(0)
	#print args

	if args.which == 'pipeline':
		main_pipline(args)
	elif args.which == 'lib_est':
		get_lib_est(args)
	elif args.which == 'get_bp_stats':
		bp_stats(args)
	elif args.which == 'get_gaps':
		gap_coordinates(args)
	elif args.which == 'cluster_pvals':
		p_value_cluster(args)
	else:
		print 'invalid call'


