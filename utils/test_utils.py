import torch
from tqdm import tqdm
from .label_utils import convert_label, get_one_hot_label
from .metric_utils import compute_predictor_metrics, compute_classifier_metrics

def test_predictor(model, loss_function,
                   dataloader, test_bs,
                   data_len, pred_len, tgt_amplifier, tgt_clip_value,
                   value_threshold, strong_threshold,
                   device, save_dir, save_ckpt=True, load_ckpt=False):
    
    if save_ckpt:
        torch.save(model.state_dict(), save_dir)
    if load_ckpt:
        model.load_state_dict(torch.load(save_dir))

    model.eval()
    test_loss = 0
    metric_list = ["correct", "rec_correct", "rec_tgt", "strong_prec_correct", "strong_prec_tgt"]
    metric_dict = dict((metric, 0) for metric in metric_list)
    
    for idx, batch in tqdm(enumerate(dataloader)):
        ob = batch['ob'].to(torch.float32).to(device)
        tr = batch['tr'].to(torch.float32).to(device)
        volume = batch['volume'].to(torch.float32).to(device)
        tgt = torch.clamp(batch['tgt']*tgt_amplifier,
                          min=-tgt_clip_value,
                          max=tgt_clip_value).to(torch.float32).to(device)
        
        for step in range(pred_len):
            if step == 0:
                out = model(ob, tr, volume, tgt[:,:data_len,:])
            else:
                out = model(ob, tr, volume, torch.cat((tgt[:,:data_len,:], out[:,-step:].unsqueeze(dim=2)),dim=1))

        label = tgt[:,1:,:].squeeze(dim=2)                    
        loss = loss_function(out,label)
        test_loss += loss.detach().cpu().item()

        metrics = compute_predictor_metrics(out[:,-1], label[:,-1], value_threshold, strong_threshold)
        for key in metric_dict.keys():
            metric_dict[key] += metrics[key]
        
        if idx == 0:
            print(f'Out: {out[:,-1]}\n Label: {label[:,-1]}')
            
    print(f'Test Average Loss: {test_loss / (idx+1)}')
    print(f'Test Correct: {metric_dict["correct"]} out of {test_bs*(idx+1)}')
    print(f'Test Recall: {metric_dict["rec_correct"]} out of {metric_dict["rec_tgt"]}')
    print(f'Test Precision (Strong): {metric_dict["strong_prec_correct"]} out of {metric_dict["strong_prec_tgt"]}')


def test_classifier(result_dim, model, loss_function,
                    dataloader, test_bs,
                    data_len, pred_len, tgt_amplifier, tgt_clip_value,
                    value_threshold, strong_threshold,
                    device, save_dir, save_ckpt=True, load_ckpt=False):
    
    if pred_len > 1:
        raise NotImplementedError("Classifier has not yet been implemented for pred_len bigger than 1")
    
    if save_ckpt:
        torch.save(model.state_dict(), save_dir)
    if load_ckpt:
        model.load_state_dict(torch.load(save_dir))

    model.eval()
    test_loss = 0
    metric_list = ["correct", "prec_correct", "prec_tgt", 
                   "rec_correct", "rec_tgt", 
                   "strong_prec_correct", "strong_prec_tgt",
                   "prec_close", "strong_prec_close"]
    metric_dict = dict((metric, 0) for metric in metric_list)
    
    for idx, batch in tqdm(enumerate(dataloader)):
        ob = batch['ob'].to(torch.float32).to(device)
        tr = batch['tr'].to(torch.float32).to(device)
        volume = batch['volume'].to(torch.float32).to(device)
        tgt = torch.clamp(batch['tgt']*tgt_amplifier,
                          min=-tgt_clip_value,
                          max=tgt_clip_value).to(torch.float32).to(device)
        
        out = model(ob, tr, volume, tgt[:,:data_len,:])                
        label = tgt[:,1:,:].squeeze(dim=2)
        label = convert_label(label, result_dim, value_threshold)
        
        loss = loss_function(out[:,-1,:],label[:,-1])
        test_loss += loss.detach().cpu().item()
        
        metrics = compute_classifier_metrics(out[:,-1,:], label[:,-1], result_dim, strong_threshold)
        for key in metric_dict.keys():
            metric_dict[key] += metrics[key]

        if idx == 0:
            print(f'Out: {out[:,-1,:]}\n Label: {label[:,-1]}')
            
    print(f'Test Average Loss: {test_loss / (idx+1)}')
    print(f'Test Correct: {metric_dict["correct"]} out of {test_bs*(idx+1)}')
    print(f'Test Recall: {metric_dict["rec_correct"]} out of {metric_dict["rec_tgt"]}')
    print(f'Test Precision: {metric_dict["prec_correct"]} out of {metric_dict["prec_tgt"]}')
    print(f'Test Precision (Strong): {metric_dict["strong_prec_correct"]} out of {metric_dict["strong_prec_tgt"]}')
    print(f'Test Precision_Close: {metric_dict["prec_close"]} out of {metric_dict["prec_tgt"]}')
    print(f'Test Precision_Close (Strong): {metric_dict["strong_prec_close"]} out of {metric_dict["strong_prec_tgt"]}')


def test_hybrid(result_dim, model, 
                loss_function1, loss_function2, loss_weight,
                dataloader, test_bs,
                data_len, pred_len, tgt_amplifier, tgt_clip_value,
                value_threshold, strong_threshold,
                device, save_dir, save_ckpt=True, load_ckpt=False):
    
    if pred_len > 1:
        raise NotImplementedError("Classifier has not yet been implemented for pred_len bigger than 1")
    
    if save_ckpt:
        torch.save(model.state_dict(), save_dir)
    if load_ckpt:
        model.load_state_dict(torch.load(save_dir))

    model.eval()
    test_loss = 0
    metric_list = ["correct", "rec_correct", "rec_tgt", "strong_prec_correct", "strong_prec_tgt"]
    metric_dict = dict((metric, 0) for metric in metric_list)
    
    for idx, batch in tqdm(enumerate(dataloader)):
        ob = batch['ob'].to(torch.float32).to(device)
        tr = batch['tr'].to(torch.float32).to(device)
        volume = batch['volume'].to(torch.float32).to(device)
        tgt = torch.clamp(batch['tgt']*tgt_amplifier,
                          min=-tgt_clip_value,
                          max=tgt_clip_value).to(torch.float32).to(device)
        
        out = model(ob, tr, volume, tgt[:,:data_len,:])                
        label = tgt[:,1:,:].squeeze(dim=2)
        
        loss = loss_weight * loss_function1(out,label) + (1-loss_weight) * loss_function2(get_one_hot_label(out[:,-1], result_dim, value_threshold),
                                                                                          convert_label(label[:,-1], result_dim, value_threshold))
        test_loss += loss.detach().cpu().item()
        
        metrics = compute_predictor_metrics(out[:,-1], label[:,-1], value_threshold, strong_threshold)
        for key in metric_dict.keys():
            metric_dict[key] += metrics[key]

        if idx == 0:
            print(f'Out: {out[:,-1]}\n Label: {label[:,-1]}')
            
    print(f'Test Average Loss: {test_loss / (idx+1)}')
    print(f'Test Correct: {metric_dict["correct"]} out of {test_bs*(idx+1)}')
    print(f'Test Recall: {metric_dict["rec_correct"]} out of {metric_dict["rec_tgt"]}')
    print(f'Test Precision (Strong): {metric_dict["strong_prec_correct"]} out of {metric_dict["strong_prec_tgt"]}')