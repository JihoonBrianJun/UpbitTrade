import os
import numpy as np
from tqdm import tqdm
from argparse import ArgumentParser

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import StepLR
from model.vanilla import TEncoderVanilla


def main(args):
    with open(os.path.join(args.data_dir, 'src.npy'), 'rb') as f:
        src = np.load(f)
    with open(os.path.join(args.data_dir, 'tgt.npy'), 'rb') as f:
        tgt = np.load(f)
    
    print(f'src shape: {src.shape}')
    print(f'tgt shape: {tgt.shape}')
    
    data = np.array([{'src': src[i], 'tgt': tgt[i]} for i in range(src.shape[0])])
    train_idx = np.random.choice(np.arange(src.shape[0]), size=int(src.shape[0]*args.train_ratio), replace=False)
    test_idx = np.array(list(set(np.arange(src.shape[0]).tolist()).difference(set(train_idx.tolist()))))
    
    train_loader = DataLoader(data[train_idx], batch_size=args.bs, shuffle=True)
    test_loader = DataLoader(data[test_idx], batch_size=args.bs, shuffle=True)
    
    if args.gpu:
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        
    model = TEncoderVanilla(model_dim=args.model_dim,
                            n_head=args.n_head,
                            num_layers=args.num_layers,
                            src_dim=src.shape[-1],
                            tgt_dim=tgt.shape[-1],
                            src_len=src.shape[-2],
                            tgt_len=tgt.shape[-2]).to(device)
    num_param = 0
    for _, param in model.named_parameters():
        num_param += param.numel()
    print(f'model param size: {num_param}')
    
    loss_function = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0)
    scheduler = StepLR(optimizer, step_size=1, gamma=args.gamma)
    
    for epoch in tqdm(range(args.epoch)):
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            src = batch['src'].to(torch.float32).to(device)
            out = model(src)

            tgt = batch['tgt'].to(torch.float32).to(device)
            tgt = tgt.view(tgt.shape[0],-1)
            loss = loss_function(out.mean(dim=1), tgt.mean(dim=1))
            epoch_loss += loss.detach().cpu().item()
            loss.backward()
                    
            optimizer.step()
            optimizer.zero_grad()
        
        print(f'Epoch {epoch} Average Loss: {epoch_loss/(idx+1)}')
        scheduler.step()
    
    test_loss = 0
    correct = 0
    for idx, batch in tqdm(enumerate(test_loader)):
        model.eval()
        src = batch['src'].to(torch.float32).to(device)
        out = model(src)
        
        tgt = batch['tgt'].to(torch.float32).to(device)
        tgt = tgt.view(tgt.shape[0],-1)
        loss = loss_function(out.mean(dim=1), tgt.mean(dim=1))
        test_loss += loss.detach().cpu().item()
        correct += ((out.mean(dim=1) * tgt.mean(dim=1))>0).sum().item()
    print(f'Test Average Loss: {test_loss / (idx+1)}')
    print(f'Test Correct: {correct} out of {args.bs*(idx+1)}')
    
    torch.save(model.state_dict(), args.save_dir)
    
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--data_dir', type=str, default='/home/jay/UpbitTrade/analysis/data/train')
    parser.add_argument('--save_dir', type=str, default='/home/jay/UpbitTrade/analysis/vanilla.pt')
    parser.add_argument('--model_dim', type=int, default=64)
    parser.add_argument('--n_head', type=int, default=2)
    parser.add_argument('--num_layers', type=int, default=2)
    parser.add_argument('--gpu', type=bool, default=False)
    parser.add_argument('--epoch', type=int, default=1)
    parser.add_argument('--bs', type=int, default=16)
    parser.add_argument('--lr', type=int, default=0.001)
    parser.add_argument('--gamma', type=int, default=0.1)
    parser.add_argument('--train_ratio', type=float, default=0.9)
    args = parser.parse_args()
    main(args)