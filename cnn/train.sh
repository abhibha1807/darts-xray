#!/usr/bin/env bash
#/abhibha-volume/rbt/bin python 
#
nvidia-smi
pwd
ls
source activate /abhibha-volume/darts
conda info
which python
python /abhibha-volume/darts-xray/cnn/train.py 
#python train_search.py --unrolled
#python visualize.py DARTS
# python test.py 


