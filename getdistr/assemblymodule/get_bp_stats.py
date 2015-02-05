
from itertools import ifilter
import math
import lib_est
import pysam
import sys

from mathstats.normaldist.normal import MaxObsDistr

import heapq

class Scanner(object):
	"""docstring for Scanner"""
	def __init__(self,name,outfile):
		super(Scanner, self).__init__()
		self.ref_name = name
		self.position = 0
		self.mu = 0
		self.var = 0
		self.o = 0
		self.o_sq = 0
		self.n_obs = 0.0
		self.outfile = outfile

	def write_bp_stats_to_file(self,bp_index):
		#print  '{0}\t{1}\t{2}\t{3}\t{4}'.format(self.ref_name, bp_index, self.n_obs, self.mu, self.var)
		print >> self.outfile, '{0}\t{1}\t{2}\t{3}\t{4}'.format(self.ref_name, bp_index, self.n_obs, self.mu, math.sqrt(self.var))

	def add_obs(self, isize):
		self.o += isize
		self.o_sq += isize**2
		self.n_obs += 1 
		if self.n_obs < 2:
			self.mu = 0
			self.var = 0
			return
		self.mu = self.o / self.n_obs  #(self.n_obs * self.mu + isize)/ float(self.n_obs+1)
		#print self.mu,self.o,self.o_sq
		self.var = 1/(self.n_obs -1)* (self.o_sq - 2*self.mu*self.o + self.n_obs*self.mu**2) #(self.n_obs * self.var + isize**2)/ float(self.n_obs+1)

	def remove_obs(self, neg_isize):
		self.o += neg_isize
		self.o_sq -= neg_isize**2
		self.n_obs -= 1 
		if self.n_obs < 2:
			self.mu = 0
			self.var = 0
			return		
		self.mu = self.o / self.n_obs  #(self.n_obs * self.mu + isize)/ float(self.n_obs+1)
		self.var = 1/(self.n_obs -1)* (self.o_sq - 2*self.mu*self.o + self.n_obs*self.mu**2) #(self.n_obs * self.var + isize**2)/ float(self.n_obs+1)

	def update_pos(self,pos):
		if self.position < pos:
			for bp_index in range(self.position,pos):
				self.write_bp_stats_to_file(bp_index)
		self.position = pos

def read_pair_generator(bam,libstats):
	read_pairs = {}
	read_pair_heap = []
	#visited = set()
	prev_read_ref = None
	bam_filtered = ifilter(lambda r: r.flag <= 255, bam)
	for read in bam_filtered:
		if read.tid != prev_read_ref  and prev_read_ref != None:
			print read.tid, prev_read_ref
			while True:
				try:
					min_pos,r1,mate_pos = heapq.heappop(read_pair_heap)
					yield r1, mate_pos
				except IndexError:
					break
		prev_read_ref = read.tid


		if lib_est.is_proper_aligned_unique_innie(read) and 0 <= read.tlen <= libstats.max_isize and not read.is_reverse:
			if (read.qname, read.is_reverse) in read_pairs:
				print 'bug, multiple alignments', read.qname
				# if '361218' == read.qname:
				# 	print 'lollong here'
				del read_pairs[(read.qname, read.is_reverse)]
				continue
			else:
				read_pairs[(read.qname, read.is_reverse)] = read
				# if '361218' == read.qname:
				# 	print 'pushing here'

		elif lib_est.is_proper_aligned_unique_innie(read) and  -libstats.max_isize <= read.tlen < 0 and read.is_reverse:
			if (read.qname, read.is_reverse) in read_pairs :
				print 'bug, multiple reverse alignments',read.qname
				del read_pairs[(read.qname, read.is_reverse)]
				continue

			elif (read.qname, not read.is_reverse) in read_pairs:
				read_pairs[(read.qname, read.is_reverse)] = read
				#print 'gg',read.qname
				#if '361218' in read_pairs:
				#	print 'lollzzz'
				#visited.add(read.qname)
				read1 = read_pairs[(read.qname, not read.is_reverse)]	
				if read.tid != read1.tid:
					del read_pairs[(read.qname, not read.is_reverse)]
					del read_pairs[(read.qname, read.is_reverse)]
					continue
				assert read.mpos == read1.pos
				assert read.pos == read1.mpos
				# print 'Read has another forward alignment'
				# print read.pos, read.is_secondary, read.is_reverse
				# print read1.pos, read1.is_secondary, read1.is_reverse
				heapq.heappush(read_pair_heap, (read1.pos, read1, read.pos))
				heapq.heappush(read_pair_heap, (read.pos, read, read1.pos))
				while True:
					try:
						min_pos,r,mate_pos = heapq.heappop(read_pair_heap)
						#print 'index', r1.qname,r2.qname
						# print r1.pos, r2.pos
					except IndexError:
						print 'NOOO'
						break
					if read.pos - libstats.max_isize >= min_pos:
						#print 'p',read1.pos, min_pos
						
						#print 'here!', r1.pos,r1.flag,r1.mpos
						try:
							del read_pairs[(r.qname, r.is_reverse)]
							yield r, mate_pos
						except KeyError:
							pass
							print 'gah',read.is_reverse
							# print r1.qname, r2.qname
							# print r1.pos, r2.pos
							

					else:
						heapq.heappush(read_pair_heap, (min_pos, r, mate_pos))
						break


	# last reads
	while True:
		try:
			min_pos,r1,r2 = heapq.heappop(read_pair_heap)
			yield r1, r2
		except IndexError:
			break


def parse_bam(bam_file,libstats,out_path):
	outfile = open(out_path,'w')

	with pysam.Samfile(bam_file, 'rb') as bam:
		reference_lengths = dict(zip(bam.references, map(lambda x: int(x), bam.lengths)))
		current_scaf = -1
		read_len = int(libstats.read_length)
		counter = 0

		reads_fwd = 0
		reads_rev = 0

		already_sampled = set()
		duplicates = set()

		for i,(read,mpos) in enumerate(read_pair_generator(bam,libstats)):
			#print read.pos, mpos #, read2.pos

			if i %100000 == 0:
				print i

			if abs(read.tlen) <= 2*libstats.read_length:
				continue

			counter += 1

			current_coord = read.pos + read_len
			current_ref = bam.getrname(read.tid)

			if current_ref == -1:
				continue

				
			if reference_lengths[current_ref] < libstats.max_isize:
				continue

			# print out bp stats for base pairs that we have passed
			if current_ref != current_scaf:
				print current_scaf
				#print 'visited to new ref', len(visited)
				print 'reads_fwd on scanned contig:',reads_fwd
				print 'reads_rev on scanned contig:',reads_rev
				reads_fwd = 0
				reads_rev = 0
				already_sampled = set()
				duplicates = set()
				scanner = Scanner(current_ref,outfile)
				scanner.update_pos(current_coord)
				scaf_length = reference_lengths[current_ref]
				current_scaf = current_ref 
			else:
				scanner.update_pos(current_coord)

			if read.is_reverse: #read.qname in visited and read.is_reverse:
				assert read.tlen < 0
				#print 'reads_fwd on scanned contig:',reads_fwd
				#print 'reads_rev on scanned contig:',reads_rev
				if (read.qname,mpos,read.pos) in duplicates:
					continue
				scanner.remove_obs(read.tlen)
				reads_rev +=1
				

			else: #if lib_est.is_proper_aligned_unique_innie(read) and (libstats.min_isize <= read.tlen <= libstats.max_isize):

				if read.aend >= scaf_length or read.aend < 0 or read.mpos +read.rlen > scaf_length or read.pos < 0:
					print 'Read coordinates outside scaffold length for {0}:'.format(current_scaf), read.aend, read.aend, read.mpos +read.rlen, read.pos 
					#continue
				# if read.tlen <0 :
				# 	print 'BUG', read.tlen

				if (read.pos,mpos) in already_sampled:
					duplicates.add((read.qname,read.pos,mpos))
					continue

				already_sampled.add((read.pos,mpos))
				scanner.add_obs(read.tlen)
				reads_fwd += 1
				counter += 1
		print 'Good read pair count: ', counter



		print 'Proper reads:',counter



