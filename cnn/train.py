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
import torchvision
from PIL import Image
from torch.autograd import Variable
from model import NetworkCIFAR as Network
from torchvision import transforms, datasets, models

from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

parser = argparse.ArgumentParser("cifar")
parser.add_argument('--data', type=str, default='./data', help='location of the data corpus')
parser.add_argument('--batch_size', type=int, default=96, help='batch size')
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

args.save = 'try3eval-{}-{}'.format(args.save, time.strftime("%Y%m%d-%H%M%S"))
utils.create_exp_dir(args.save, scripts_to_save=glob.glob('*.py'))

log_format = '%(asctime)s %(message)s'
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
    format=log_format, datefmt='%m/%d %I:%M:%S %p')
fh = logging.FileHandler(os.path.join(args.save, 'log.txt'))
fh.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(fh)

CIFAR_CLASSES = 2


def main():
  print(os.listdir())
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
  #model = Network(args.init_channels, CIFAR_CLASSES, args.layers, args.auxiliary, genotype)
  #utils.load(model, '/Users/abhibhagupta/Desktop/weights.pt', map_location=torch.device('cpu'))
  # model.load_state_dict(torch.load('/Users/abhibhagupta/Desktop/weights.pt', map_location=torch.device('cpu')))
  # model = torch.jit.load('/Users/abhibhagupta/Desktop/weights.pt')
  model=torch.load('/abhibha-volume/darts-xray/cnn/try3eval-EXP-20210730-134151/weights.pt')
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
  # valid_data_cifar = dset.CIFAR10(root=args.data, train=False, download=True, transform=valid_transform)
  # valid_data_cifar=valid_data_cifar[0]
  # print(dir(valid_data_cifar))
  # print(valid_data_cifar.data[0])
  # print(valid_data_cifar.targets[0])
  # valid_data_cifar=valid_data_cifar.data[0:10]
  #len(valid_data_cifar)
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
  valid_data=data['test']

 
  scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, float(args.epochs))

  #print(dir(train_data))

  center_crop = torchvision.transforms.CenterCrop(size=(32,32))
  color_jitter = torchvision.transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5, hue=0.5)
  gray = torchvision.transforms.Grayscale(num_output_channels=1)
  horizontal_flip = torchvision.transforms.RandomHorizontalFlip()
  transform = torchvision.transforms.Compose([
    # you can add other transformations in this list
    transforms.ToTensor()
])
  final_train_data=[]
  final_cifar_data=[]
  c=0
  #cifar: [1,32,32,3]
  # train: [1,3,32,32]
  for i in range(len(train_data)):
    c=c+1
    # print(train_data.imgs[i][0])
    img = Image.open(train_data.imgs[i][0])
    # img = Image.open(train_data.imgs[i][0]).convert('RGB')
    # img1 = Image.open(valid_data_cifar.filename).convert('RGB')
    # img=transform(center_crop(img))
    # img=torch.reshape(img, (32, 32, 3))
    # print(torch.tensor([3,1,2]).shape)
    # img=img.permute(2,1,0)
    # print(img.shape)
    # img=torch.gather(img, 0, torch.tensor([3,1,2]))
    final_train_data.append((transform(img), train_data.imgs[i][1]))

    # print(img1)
    # final_cifar_data.append((transform(center_crop(img1))))
    if c==10:
      break
    # final_train_data.append(center_crop(img))
    # final_train_data.append(gray(img))
    # final_train_data.append(horizontal_flip(img))

  final_valid_data=[]
  c=0
  for i in range(len(valid_data)):
    c=c+1
    # print(valid_data.imgs[i][0])
    img = Image.open(valid_data.imgs[i][0])
    # img = Image.open(valid_data.imgs[i][0]).convert('RGB')
    # img=transform(center_crop(img))
    # img=torch.reshape(img, (32, 32, 3))
    # img=img.permute(2,1,0)
    final_valid_data.append((transform(img), valid_data.imgs[i][1]))
    if c==10:
      break
    # final_valid_data.append(center_crop(img))
    # final_valid_data.append(gray(img))
    # final_valid_data.append(horizontal_flip(img))

  # final_cifar_data.append((torch.tensor(valid_data_cifar.data[0]), 1))
  #num_workers=2,
  train_queue = torch.utils.data.DataLoader(
      train_data, batch_size=args.batch_size, shuffle=True, pin_memory=True,  drop_last=True, num_workers=2,)

  valid_queue = torch.utils.data.DataLoader(
      valid_data, batch_size=args.batch_size, shuffle=False, pin_memory=True, drop_last=True, num_workers=2,)
 
  # cifar_queue=torch.utils.data.DataLoader(
  #     final_cifar_data, batch_size=args.batch_size, shuffle=True, pin_memory=True, drop_last=True)

  
  
  for epoch in range(args.epochs):
    scheduler.step()
    logging.info('epoch %d lr %e', epoch, scheduler.get_lr()[0])
    model.drop_path_prob = args.drop_path_prob * epoch / args.epochs
    # print('called cifar')
    #train_acc, train_obj = 
    # train(cifar_queue, model, criterion, optimizer)
    print('called train')
   
    # train_acc, train_obj = train(train_queue, model, criterion, optimizer)

    # logging.info('train_acc %f', train_acc)

    valid_acc, valid_obj = infer(valid_queue, model, criterion)
    logging.info('valid_acc %f', valid_acc)

    print('inference complete')
    #print('saving model')
    #utils.save(model, os.path.join(args.save, 'weights.pt'))
    #torch.save(model, os.path.join(args.save, 'weights.pt'))


def train(train_queue, model, criterion, optimizer):
  objs = utils.AvgrageMeter()
  top1 = utils.AvgrageMeter()
  top5 = utils.AvgrageMeter()
  model.train()

  for step, (input, target) in enumerate(train_queue):
    input = Variable(input).cuda()
    # input = Variable(input)
    target = Variable(target).cuda(async=True)
    # target = Variable(target)

    # print('shape:', input.shape)
    # print((input[0].shape))
    # break

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
    # break
  return top1.avg, objs.avg


def infer(valid_queue, model, criterion):
  objs = utils.AvgrageMeter()
  top1 = utils.AvgrageMeter()
  top5 = utils.AvgrageMeter()
  model.eval()

  for step, (input, target) in enumerate(valid_queue):
    input = Variable(input, volatile=True).cuda()
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
    # break
  return top1.avg, objs.avg


if __name__ == '__main__':
  main() 

