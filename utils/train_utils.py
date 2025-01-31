import torch
import numpy as np
from tqdm import tqdm
from .test_utils import test_predictor, test_classifier, test_hybrid, test_contrastive
from .label_utils import convert_label, get_one_hot_label, get_extreme_label_pairs
from .contrastive_utils import compute_inner_product, compute_contrastive_loss


def process_instance(ins, ins_idx, data_len_dict, feature_dim_dict, file_idx=0):
    for key in ins.keys():
        ins[key] = np.array(ins[key]).reshape(len(ins[key]),-1)
        if file_idx == 0 and ins_idx == 0:
            print(f'Each {key} shape: {ins[key].shape}')
            data_len_dict[key] = ins[key].shape[0]
            feature_dim_dict[key] = ins[key].shape[1]


def train_predictor(model, optimizer, scheduler, loss_function,
                    train_loader, test_loader, test_bs,
                    data_len, pred_len, tgt_clip_value,
                    value_threshold, strong_threshold, data_amplifier,
                    epoch, device, save_dir):
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_predictor(model, loss_function,
                           test_loader, test_bs,
                           data_len, pred_len, tgt_clip_value,
                           value_threshold, strong_threshold, data_amplifier,
                           device, save_dir)

        model.train()
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt'],
                              min=-tgt_clip_value,
                              max=tgt_clip_value).to(torch.float32).to(device)
            
            for step in range(pred_len):
                out = model(ob, tr, volume, tgt[:,:data_len+step,:])
                label = tgt[:,1:data_len+step+1,:].squeeze(dim=2)
                loss = loss_function(out,label)
                loss.backward()

                optimizer.step()
                optimizer.zero_grad()
            
            epoch_loss += loss.detach().cpu().item()        
        print(f'Epoch {epoch} Average Loss: {np.sqrt(epoch_loss/(idx+1))/data_amplifier}')
        scheduler.step()
    
    test_predictor(model, loss_function,
                   test_loader, test_bs,
                   data_len, pred_len, tgt_clip_value,
                   value_threshold, strong_threshold, data_amplifier,
                   device, save_dir)


def train_classifier(result_dim, model, optimizer, scheduler, loss_function,
                     train_loader, test_loader, test_bs,
                     data_len, pred_len, tgt_clip_value,
                     value_threshold, strong_threshold,
                     epoch, device, save_dir):

    if pred_len > 1:
        raise NotImplementedError("Classifier has not yet been implemented for pred_len bigger than 1")
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_classifier(result_dim, model, loss_function,
                            test_loader, test_bs,
                            data_len, pred_len, tgt_clip_value,
                            value_threshold, strong_threshold,
                            device, save_dir)

        model.train()
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt'],
                              min=-tgt_clip_value,
                              max=tgt_clip_value).to(torch.float32).to(device)
            
            out = model(ob, tr, volume, tgt[:,:data_len,:])                
            label = tgt[:,1:,:].squeeze(dim=2)
            label = convert_label(label, result_dim, value_threshold)
            
            loss = loss_function(out[:,-1,:],label[:,-1])
            loss.backward()

            optimizer.step()
            optimizer.zero_grad()
            
            epoch_loss += loss.detach().cpu().item()        
        print(f'Epoch {epoch} Average Loss: {epoch_loss/(idx+1)}')
        scheduler.step()
    
    test_classifier(result_dim, model, loss_function,
                    test_loader, test_bs,
                    data_len, pred_len, tgt_clip_value,
                    value_threshold, strong_threshold,
                    device, save_dir)


def train_hybrid(result_dim, model, optimizer, scheduler,
                 loss_function1, loss_function2, loss_weight,
                 train_loader, test_loader, test_bs,
                 data_len, pred_len, tgt_clip_value,
                 value_threshold, strong_threshold,
                 epoch, device, save_dir):

    if pred_len > 1:
        raise NotImplementedError("Classifier has not yet been implemented for pred_len bigger than 1")
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_hybrid(result_dim, model,
                        loss_function1, loss_function2, loss_weight,
                        test_loader, test_bs,
                        data_len, pred_len, tgt_clip_value,
                        value_threshold, strong_threshold,
                        device, save_dir)

        model.train()
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt'],
                              min=-tgt_clip_value,
                              max=tgt_clip_value).to(torch.float32).to(device)
            
            out = model(ob, tr, volume, tgt[:,:data_len,:])                
            label = tgt[:,1:,:].squeeze(dim=2)
            
            loss = loss_weight * loss_function1(out,label) + (1-loss_weight) * loss_function2(get_one_hot_label(out[:,-1], result_dim, value_threshold),
                                                                                              convert_label(label[:,-1], result_dim, value_threshold))
            loss.backward()

            optimizer.step()
            optimizer.zero_grad()
            
            epoch_loss += loss.detach().cpu().item()        
        print(f'Epoch {epoch} Average Loss: {epoch_loss/(idx+1)}')
        scheduler.step()
    
    test_hybrid(result_dim, model,
                loss_function1, loss_function2, loss_weight,
                test_loader, test_bs,
                data_len, pred_len, tgt_clip_value,
                value_threshold, strong_threshold,
                device, save_dir)


def train_contrastive(result_dim, contrastive_side, model, optimizer, scheduler,
                      train_loader, test_loader,
                      data_len, pred_len, tgt_clip_value, value_threshold,
                      epoch, device, save_dir):

    if pred_len > 1:
        raise NotImplementedError("Classifier has not yet been implemented for pred_len bigger than 1")
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_contrastive(result_dim, contrastive_side, model, 
                             test_loader, data_len, pred_len, tgt_clip_value, value_threshold,
                             device, save_dir)

        model.train()
        epoch_loss, update_num = 0, 0
        for batch in tqdm(train_loader):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt'],
                              min=-tgt_clip_value,
                              max=tgt_clip_value).to(torch.float32).to(device)

            out = model(ob, tr, volume, tgt[:,:data_len,:])[:,-1]
            out = compute_inner_product(out)
            
            label = tgt[:,-1,:].squeeze(dim=1)
            label = convert_label(label, result_dim, value_threshold)
            leftmost_label_idx, rightmost_label_idx = get_extreme_label_pairs(label, result_dim)

            loss = compute_contrastive_loss(out, leftmost_label_idx, rightmost_label_idx, contrastive_side)

            if loss is not None:
                loss.backward()

                optimizer.step()
                optimizer.zero_grad()
            
                epoch_loss += loss.detach().cpu().item()  
                update_num += 1
        
        print(f'Epoch {epoch} Average Loss: {epoch_loss/update_num}')
        scheduler.step()
    
    test_contrastive(result_dim, contrastive_side, model, 
                     test_loader, data_len, pred_len, tgt_clip_value, value_threshold,
                     device, save_dir)