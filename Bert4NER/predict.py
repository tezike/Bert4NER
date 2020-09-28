# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/predict.py.ipynb (unless otherwise specified).

__all__ = ['process_output', 'sentence', 'sentence']

# Cell
import os
import torch

import pandas as pd
import numpy as np
import warnings

import Bert4NER.config as config
import Bert4NER.model.model as model
import Bert4NER.utils.utils as utils
import Bert4NER.utils.engine as engine
import Bert4NER.dataset.dataset as dataset


warnings.filterwarnings("ignore")

# Cell
le_tag, le_pos = utils.load_label_encoders()

# Cell
def process_output(sentence, model):
    test_dl = utils.create_loader([sentence],
                               [[0]*len(sentence)],
                               [[0]*len(sentence)],
                               bs=1)
    pred_tag_list, pred_pos_list = [], []
    input_ids_list = []
    for i, batch in enumerate(test_dl):
        target_tag = batch.pop('target_tag')
        target_pos = batch.pop('target_pos')
        with torch.no_grad():
            out = model(**batch)
        pred_tag, pred_pos = out
        pred_tag = pred_tag.softmax(dim=2).argmax(dim=2).cpu().numpy()
        pred_pos = pred_pos.softmax(dim=2).argmax(dim=2).cpu().numpy()
        input_ids = batch['input_ids'][i]
        input_ids_list.append(input_ids.cpu().numpy()[torch.nonzero(batch['attention_mask'][i]).flatten()])
        pred_tag_list.append(pred_tag[i][torch.nonzero(batch['attention_mask'][i]).flatten()])
        pred_pos_list.append(pred_pos[i][torch.nonzero(batch['attention_mask'][i]).flatten()])
    return input_ids_list, pred_tag_list, pred_pos_list

# Cell
sentence = "The southern English resort of Brighton"
sentence = sentence.split()