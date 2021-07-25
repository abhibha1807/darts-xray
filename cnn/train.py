import os
import sys
import time
import glob
import numpy as np
import torch
import utils
import logging
import argparse
import torch.nn as nn
import genotypes
import torch.utils
import torchvision.datasets as dset
import torch.backends.cudnn as cudnn
from tqdm import tqdm
from torch.autograd import Variable
from model import NetworkCIFAR as Network
from torchvision import transforms, datasets, models
from skimage.transform import rotate
from skimage.util import random_noise
from skimage.filters import gaussian
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

parser = argparse.ArgumentParser("cifar")
parser.add_argument('--data', type=str, default='./data', help='location of the data corpus')
parser.add_argument('--batch_size', type=int, default=1, help='batch size')
parser.add_argument('--learning_rate', type=float, default=0.025, help='init learning rate')
parser.add_argument('--momentum', type=float, default=0.9, help='momentum')
parser.add_argument('--weight_decay', type=float, default=3e-4, help='weight decay')
parser.add_argument('--report_freq', type=float, default=50, help='report frequency')
parser.add_argument('--gpu', type=int, default=0, help='gpu device id')
parser.add_argument('--epochs', type=int, default=600, help='num of training epochs')
parser.add_argument('--init_channels', type=int, default=36, help='num of init channels')
parser.add_argument('--layers', type=int, default=20, help='total number of layers')
parser.add_argument('--model_path', type=str, default='saved_models', help='path to save the model')
parser.add_argument('--auxiliary', action='store_true', default=False, help='use auxiliary tower')
parser.add_argument('--auxiliary_weight', type=float, default=0.4, help='weight for auxiliary loss')
parser.add_argument('--cutout', action='store_true', default=False, help='use cutout')
parser.add_argument('--cutout_length', type=int, default=16, help='cutout length')
parser.add_argument('--drop_path_prob', type=float, default=0.2, help='drop path probability')
parser.add_argument('--save', type=str, default='EXP', help='experiment name')
parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--arch', type=str, default='DARTS', help='which architecture to use')
parser.add_argument('--grad_clip', type=float, default=5, help='gradient clipping')
args = parser.parse_args()

args.save = 'try2eval-{}-{}'.format(args.save, time.strftime("%Y%m%d-%H%M%S"))
utils.create_exp_dir(args.save, scripts_to_save=glob.glob('*.py'))

log_format = '%(asctime)s %(message)s'
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format=log_format, datefmt='%m/%d %I:%M:%S %p')
fh = logging.FileHandler(os.path.join(args.save, 'log.txt'))
fh.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(fh)

CIFAR_CLASSES = 2


def main():
  if not torch.cuda.is_available():
    logging.info('no gpu device available')
    sys.exit(1)

  np.random.seed(args.seed)
  torch.cuda.set_device(args.gpu)
  cudnn.benchmark = True
  torch.manual_seed(args.seed)
  cudnn.enabled=True
  torch.cuda.manual_seed(args.seed)
  logging.info('gpu device = %d' % args.gpu)
  logging.info("args = %s", args)

  genotype = eval("genotypes.%s" % args.arch)
  model = Network(args.init_channels, CIFAR_CLASSES, args.layers, args.auxiliary, genotype)
  model = model.cuda()

  logging.info("param size = %fMB", utils.count_parameters_in_MB(model))

  criterion = nn.CrossEntropyLoss()
  criterion = criterion.cuda()
  optimizer = torch.optim.SGD(
      model.parameters(),
      args.learning_rate,
      momentum=args.momentum,
      weight_decay=args.weight_decay
      )

  train_transform, valid_transform = utils._data_transforms_cifar10(args)
  # train_data = dset.CIFAR10(root=args.data, train=True, download=True, transform=train_transform)
  # valid_data = dset.CIFAR10(root=args.data, train=False, download=True, transform=valid_transform)

  datadir=args.data
  print(datadir)
  traindir = datadir + '/train/'
  validdir = datadir + '/val/'
  testdir = datadir + '/test/'
  data = {
  'train':
  datasets.ImageFolder(root=traindir, transform=train_transform),
  'val':
  datasets.ImageFolder(root=validdir, transform=train_transform),
  'test':
  datasets.ImageFolder(root=testdir, transform=train_transform)
}

  train_data=data['train']
  valid_data=data['val']
  num_train = len(train_data)
  num_val=len(valid_data)
  

  final_train_data=[]
  print(dir(train_data))
  # print((train_data[0]))
  train_data=train_data[0:10]
  print(len(train_data.imgs))
  for i in tqdm(range(len(train_data.imgs))):
    final_train_data.append(train_data[i])
    final_train_data.append((rotate(train_data[i][0], angle=45, mode = 'wrap'), train_data[i][1]))
    final_train_data.append((np.fliplr(train_data[i][0]), train_data[i][1]))
    final_train_data.append((np.flipud(train_data[i][0]), train_data[i][1]))
    final_train_data.append((random_noise(train_data[i][0],var=0.2**2), train_data[i][1]))
  print(len(final_train_data))

  

  final_val_data=[]
  valid_data=valid_data[0:4]
  print(len(valid_data.imgs))
  for i in tqdm(range(len(valid_data.imgs))):
    final_val_data.append(valid_data[i])
    final_val_data.append((rotate(valid_data[i][0], angle=45, mode = 'wrap'), valid_data[i][1]))
    final_val_data.append((np.fliplr(valid_data[i][0]), valid_data[i][1]))
    final_val_data.append((np.flipud(valid_data[i][0]), valid_data[i][1]))
    final_val_data.append((random_noise(valid_data[i][0],var=0.2**2), valid_data[i][1]))
  print(len(final_val_data))

  # final_val_data=final_val_data[0:1]

  indices = list(range(len(final_train_data)))
  indices_val=list(range(len(final_val_data)))

  # train_queue = torch.utils.data.DataLoader(train_data, batch_size=args.batch_size,
  #         sampler=torch.utils.data.sampler.SubsetRandomSampler(indices[:split]),
  #         pin_memory=True, num_workers=2)

  #   valid_queue = torch.utils.data.DataLoader(train_data, batch_size=args.batch_size,
  #         sampler=torch.utils.data.sampler.SubsetRandomSampler(indices[split:num_train]),
  #         pin_memory=True, num_workers=2)
  #   #  sampler=torch.utils.data.sampler.SubsetRandomSampler(indices[:]),
  #   unlabeled_queue = torch.utils.data.DataLoader(u_data, batch_size=args.batch_size,
  #         pin_memory=True, num_workers=0)

  # train_queue = torch.utils.data.DataLoader(
  #     final_train_data, batch_size=args.batch_size, shuffle=True, pin_memory=True, num_workers=2)

  # valid_queue = torch.utils.data.DataLoader(
  #     valid_data, batch_size=args.batch_size, shuffle=False, pin_memory=True, num_workers=2)
  
  print('final train len:', len(final_train_data))
  print('final val len:', len(final_val_data))
  
  train_queue = torch.utils.data.DataLoader(final_train_data, batch_size=args.batch_size,
          sampler=torch.utils.data.sampler.SubsetRandomSampler(indices[:]),
          pin_memory=True, num_workers=2)
  valid_queue = torch.utils.data.DataLoader(final_val_data, batch_size=args.batch_size,
        sampler=torch.utils.data.sampler.SubsetRandomSampler(indices_val[:]),
        pin_memory=True, num_workers=2)


  scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, float(args.epochs))

  for epoch in range(args.epochs):
    scheduler.step()
    logging.info('epoch %d lr %e', epoch, scheduler.get_lr()[0])
    model.drop_path_prob = args.drop_path_prob * epoch / args.epochs

    train_acc, train_obj = train(train_queue, model, criterion, optimizer)
    logging.info('train_acc %f', train_acc)

    valid_acc, valid_obj = infer(valid_queue, model, criterion)
    logging.info('valid_acc %f', valid_acc)

    utils.save(model, os.path.join(args.save, 'weights.pt'))


def train(train_queue, model, criterion, optimizer):
  objs = utils.AvgrageMeter()
  top1 = utils.AvgrageMeter()
  top5 = utils.AvgrageMeter()
  model.train()

  for step, (input, target) in enumerate(train_queue):
    input.to(device='cuda', dtype=torch.float)
    #input = Variable(input).cuda()
    target = Variable(target).cuda(async=True)

    optimizer.zero_grad()
    logits, logits_aux = model(input)
    loss = criterion(logits, target)
    print('train loss:', loss)
    if args.auxiliary:
      loss_aux = criterion(logits_aux, target)
      loss += args.auxiliary_weight*loss_aux
    loss.backward()
    nn.utils.clip_grad_norm(model.parameters(), args.grad_clip)
    optimizer.step()

    prec1, prec5 = utils.accuracy(logits, target, topk=(1, 1))
    n = input.size(0)
    objs.update(loss.data[0], n)
    top1.update(prec1.data[0], n)
    top5.update(prec5.data[0], n)

    if step % args.report_freq == 0:
      logging.info('train %03d %e %f %f', step, objs.avg, top1.avg, top5.avg)

  return top1.avg, objs.avg


def infer(valid_queue, model, criterion):
  objs = utils.AvgrageMeter()
  top1 = utils.AvgrageMeter()
  top5 = utils.AvgrageMeter()
  model.eval()

  for step, (input, target) in enumerate(valid_queue):
    input.to(device='cuda', dtype=torch.float)
    #input = Variable(input, volatile=True).cuda()
    target = Variable(target, volatile=True).cuda(async=True)

    logits, _ = model(input)
    loss = criterion(logits, target)
    print('val loss:', loss)
    prec1, prec5 = utils.accuracy(logits, target, topk=(1, 1))
    n = input.size(0)
    objs.update(loss.data[0], n)
    top1.update(prec1.data[0], n)
    top5.update(prec5.data[0], n)

    if step % args.report_freq == 0:
      logging.info('valid %03d %e %f %f', step, objs.avg, top1.avg, top5.avg)

  return top1.avg, objs.avg


if __name__ == '__main__':
  main() 

