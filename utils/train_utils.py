import torch
from tqdm import tqdm
from .test_utils import test_predictor, test_classifier
from .label_utils import convert_label


def train_predictor(model, optimizer, scheduler, loss_function,
                    train_loader, test_loader, test_bs,
                    data_len, pred_len, tgt_amplifier, tgt_clip_value,
                    value_threshold, strong_threshold,
                    epoch, device, save_dir):
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_predictor(model, loss_function,
                           test_loader, test_bs,
                           data_len, pred_len, tgt_amplifier, tgt_clip_value,
                           value_threshold, strong_threshold,
                           device, save_dir)

        model.train()
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt']*tgt_amplifier,
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
        print(f'Epoch {epoch} Average Loss: {epoch_loss/(idx+1)}')
        scheduler.step()
    
    test_predictor(model, loss_function,
                   test_loader, test_bs,
                   data_len, pred_len, tgt_amplifier, tgt_clip_value,
                   value_threshold, strong_threshold,
                   device, save_dir)


def train_classifier(result_dim, model, optimizer, scheduler, loss_function,
                     train_loader, test_loader, test_bs,
                     data_len, pred_len, tgt_amplifier, tgt_clip_value,
                     value_threshold, strong_threshold,
                     epoch, device, save_dir):
    
    for epoch in tqdm(range(epoch)):
        if epoch % 10 == 0:
            test_classifier(result_dim, model, loss_function,
                            test_loader, test_bs,
                            data_len, pred_len, tgt_amplifier, tgt_clip_value,
                            value_threshold, strong_threshold,
                            device, save_dir)

        model.train()
        epoch_loss = 0
        for idx, batch in tqdm(enumerate(train_loader)):
            ob = batch['ob'].to(torch.float32).to(device)
            tr = batch['tr'].to(torch.float32).to(device)
            volume = batch['volume'].to(torch.float32).to(device)
            tgt = torch.clamp(batch['tgt']*tgt_amplifier,
                                min=-tgt_clip_value,
                                max=tgt_clip_value).to(torch.float32).to(device)
            
            for step in range(pred_len):
                out = model(ob, tr, volume, tgt[:,:data_len+step,:])
                label = tgt[:,1:data_len+step+1,:].squeeze(dim=2)
                label = convert_label(label, result_dim, value_threshold)
                
                loss = loss_function(out.view(-1,result_dim),label.view(-1))
                loss.backward()

                optimizer.step()
                optimizer.zero_grad()
            
            epoch_loss += loss.detach().cpu().item()        
        print(f'Epoch {epoch} Average Loss: {epoch_loss/(idx+1)}')
        scheduler.step()
    
    test_classifier(result_dim, model, loss_function,
                    test_loader, test_bs,
                    data_len, pred_len, tgt_amplifier, tgt_clip_value,
                    value_threshold, strong_threshold,
                    device, save_dir)