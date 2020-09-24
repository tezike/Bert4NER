# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/utils.engine.ipynb (unless otherwise specified).

__all__ = ['Fitter', 'BertFitter']

# Cell
import os
import time
import timeit
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from abc import ABC
from fastprogress.fastprogress import master_bar, progress_bar

# Cell
class Fitter(ABC):
    def __init__(self):
        pass

    def fit(self):
        pass

    def log(self):
        pass

    def train(self):
        pass

    def validate(self):
        pass

# Cell
class BertFitter(Fitter):
    def __init__(self, model, dataloaders, optimizer, metrics, device, log_file='training_log.txt',scheduler=None, trial=None):
        self.model = model
        self.train_dl, self.valid_dl = dataloaders[0], dataloaders[1]
        self.optimizer = optimizer
        self.scheduler = scheduler
        if not os.path.exists(os.path.join('..', 'outputs')): os.makedirs(os.path.join('..', 'outputs'))
        if os.path.exists(os.path.join('..', 'outputs', f'{log_file}')):
            os.remove(os.path.join('..', 'outputs', f'{log_file}'))
        self.log_file = os.path.join('..', 'outputs', f'{log_file}')
        if not isinstance(metrics, (list, tuple)):
            metrics = list(metrics)
        self.metrics = metrics
        self.device = device
        self.trial = trial #for optuna

    def fit(self, epochs, return_metric=False, monitor='epoch train_loss valid_loss metric1 metric2 time', model_path=os.path.join('..', 'weights', 'model.pth'), show_graph=True):
        self.model_path = model_path
        self.log(f'{time.ctime()}')
        self.log(f'Using device: {self.device}')
        mb = master_bar(range(1, epochs+1)) #MAJOR
        mb.write(monitor.split(),table=True)

        model = self.model.to(self.device)
        optimizer = self.optimizer
        best_metric = -np.inf
        train_loss, valid_loss, valid_metric_0, valid_metric_1 = 0, 0, 0, 0
        train_loss_list, valid_loss_list = [], []

        for i_, epoch in enumerate(mb):
            epoch_start = timeit.default_timer()
            start = time.time()
            self.log('-'*50)
            self.log(f'Running Epoch #{epoch} {"🔥"*epoch}')
            self.log(f'{"-"*50} \n')
            self.log('TRAINING...')
            for ind, batch in enumerate(progress_bar(self.train_dl, parent=mb)):
                train_loss += self.train(batch, model, optimizer, self.device, self.scheduler)
                if ind % 500 == 0:
                    self.log(f'Batch: {ind}, Train loss: {train_loss/ len(self.train_dl)}')
#                 break
                mb.child.comment = f'{train_loss / (ind+1 * self.train_dl.batch_size):.3f}'
            train_loss /= mb.child.total
            train_loss_list.append(train_loss) #for graph
            self.log(f'Training time: {round(time.time()-start, 2)} secs \n')

            start = time.time()
            self.log('EVALUATING...')
            with torch.no_grad():
                for ind, batch in enumerate(progress_bar(self.valid_dl, parent=mb)):
                    valid_loss_, valid_metric_ = self.validate(batch, model, self.device)
                    valid_loss += valid_loss_
                    valid_metric_0 += valid_metric_[0]
                    valid_metric_1 += valid_metric_[1]
                    if ind % 500 == 0:
                        self.log(f'Batch: {ind}, Valid loss: {valid_loss/ len(self.valid_dl)}')
#                     break
                    mb.child.comment = f'{valid_loss / (ind+1 * self.train_dl.batch_size):.3f}'

                valid_loss /= mb.child.total
                valid_metric_0 /= mb.child.total
                valid_metric_1 /= mb.child.total
                valid_loss_list.append(valid_loss) #for graph

            if valid_metric_1 > best_metric: #ie (f1_score > inf)
                #             save model
                if self.model_path is not None:
                    if not os.path.exists(os.path.join('..', 'weights')): os.makedirs(os.path.join('..', 'weights'))
                    self.log(f'Saving model weights at {self.model_path}')
                    torch.save(model.state_dict(), self.model_path)
                best_metric = valid_metric_1

            if self.trial is not None:
                self.trial.report(best_metric, epoch)

                # Handle pruning based on the intermediate value.
                if self.trial.should_prune():
                    raise optuna.exceptions.TrialPruned()

            if show_graph:
                self.plot_loss_update(epoch, epochs, mb, train_loss_list, valid_loss_list) # for graph

            epoch_end = timeit.default_timer()
            total_time = epoch_end - epoch_start
            mins, secs = divmod(total_time, 60)
            hours, mins = divmod(mins, 60)
            ret_time = f'{int(hours)}:{int(mins)}:{int(secs)}'
            mb.write([epoch,f'{train_loss:.6f}',f'{valid_loss:.6f}',f'{valid_metric_0:.6f}', f'{valid_metric_1:.6f}', f'{ret_time}'],table=True)
            self.log(f'Evaluation time: {ret_time}\n')
#             break

        if return_metric: return best_metric

    def train(self, xy, model, opt, device, sched=None):
        model.train()
        y_tag = xy.pop('target_tag')
        y_pos = xy.pop('target_pos')
        x = xy
        inputs, target_tag, target_pos = [x_.to(device) for x_ in x.values()], y_tag.to(device), y_pos.to(device)
        opt.zero_grad()
        out = model(*inputs)
        loss_tag = self.loss_func(out[0], target_tag, x['attention_mask'], model.num_tag)
        loss_pos = self.loss_func(out[1], target_pos, x['attention_mask'], model.num_pos)
        loss = (loss_tag + loss_pos) / 2
        loss.backward()
        opt.step()
        if sched is not None:
            sched.step()
        return loss.item()

    def validate(self, xy, model, device):
        model.eval()
        y_tag = xy.pop('target_tag')
        y_pos = xy.pop('target_pos')
        x = xy
        inputs, target_tag, target_pos = [x_.to(device) for x_ in x.values()], y_tag.to(device), y_pos.to(device)
        out = model(*inputs)
        loss_tag = self.loss_func(out[0], target_tag, x['attention_mask'], model.num_tag)
        loss_pos = self.loss_func(out[1], target_pos, x['attention_mask'], model.num_pos)
        loss = (loss_tag + loss_pos) / 2

#         skelarn metrics to be calculated for every item in batch
        cleaned_out_0 = out[0].cpu().softmax(2).argmax(dim=2) #[bs, seq_len, hidden_dim(num_labels)] -> [bs, seq_len]
        cleaned_out_1 = out[1].cpu().softmax(2).argmax(dim=2) #[bs, seq_len, hidden_dim(num_labels)] -> [bs, seq_len]
        all_metric_0, all_metric_1 = [], []
        for i in range(target_tag.shape[0]):
            metric_0 = self.metrics[0](target_tag.cpu()[i], cleaned_out_0[i])  #sklearn metrics are (targ, inp)
            all_metric_0.append(metric_0)
            metric_1 = self.metrics[1](target_pos.cpu()[i], cleaned_out_1[i])  #sklearn metrics are (targ, inp)
            all_metric_1.append(metric_1)

        metrics = ((sum(all_metric_0) / target_tag.shape[0]),
                   (sum(all_metric_1) / target_tag.shape[1]))
        return loss.item(), metrics

    def log(self, message, verbose=False):
        if verbose: print(message)
        with open(self.log_file, 'a+') as logger_:
            logger_.write(f'{message}\n')

    @staticmethod
    def loss_func(out, target, mask, num_labels, func=nn.CrossEntropyLoss()):
        '''loss func for NER tasks
            out is logit from the model. Shape (bs, seq_len, hidden_dim[num_labels])
            target is target from dataloader. Shape (bs, seq_len)
        '''
        #the mask tell us where non zero tokens are
        #the num_labels is used to tell us how many labels(le.classes_) are in the targ
        non_zero_tokens = mask.view(-1) == 1 # zeroed token_ids have a mask of 1
        ignore_index = func.ignore_index

    #     if the token is not zero, select the corresponding target else set ignore_index
        cleaned_target = torch.where(non_zero_tokens, target.view(-1), torch.tensor(ignore_index)) #[bs*seq_len]

        cleaned_out = out.view(-1, num_labels) #[bs*seq_len, num_labels]

        loss = func(cleaned_out, cleaned_target)

        return loss

    @staticmethod
    def plot_loss_update(epoch, epochs, mb, train_loss, valid_loss):
        """ dynamically print the loss plot during the training/validation loop.
            expects epoch to start from 1.
        """
        x = range(1, epoch+1)
        y = np.concatenate((train_loss, valid_loss))
        graphs = [[x,train_loss], [x,valid_loss]]
        x_margin = 0.2
        y_margin = 0.05
        x_bounds = [1-x_margin, epochs+x_margin]
        y_bounds = [np.min(y)-y_margin, np.max(y)+y_margin]

        mb.update_graph(np.array(graphs), np.array(x_bounds), np.array(y_bounds))