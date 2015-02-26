#!/bin/bash -l
#SBATCH -A b2013169
#SBATCH -p core -n 1
#SBATCH -t 3-10:00:00
#SBATCH -J plasm-pe


#####
#Module dependencies
#none
#####

#########
#TO SPECIFY
INBASE='/proj/b2013169/private/data/genomes/plasm/'
OUTBASE='/home/kris/Work/GetDistr/two_bias/plasm_pe/'

#######

#######
if [ ! -d $OUTBASE ]; then
    mkdir -p $OUTBASE
else
        rm -r $OUTBASE
        mkdir -p $OUTBASE
fi


/usr/bin/time -v python /home/kris/git_repos/GetDistr/getdistr/assemblymodule/main.py pipeline \
       "$INBASE"aligned/ref/pe.bam \
        "$INBASE"/ref/genome.fasta \
        "$OUTBASE" \
        --plots 1> "$OUTBASE"run.stdout 2> "$OUTBASE"run.stderr





