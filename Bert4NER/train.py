# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/train.ipynb (unless otherwise specified).

__all__ = ['SEED', 'train_dl', 'valid_dl', 'modeller', 'no_decay', 'optimizer_params', 'lr', 'optimizer',
           'num_train_steps', 'scheduler', 'learn', 'NUM_EPOCHS']

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


from functools import partial
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from transformers import AdamW, get_linear_schedule_with_warmup

warnings.filterwarnings("ignore")

# Cell
SEED = 42
utils.seed_everything(SEED)

# Cell
df['Sentence #'] = df['Sentence #'].fillna(method='ffill')

# Cell
utils.save_label_encoders(le_tag=le_tag, le_pos=le_pos)

# Cell
le_pos, le_tag = utils.load_label_encoders()

# Cell
sentences, tags, pos = utils.process_data(df)

# Cell
train_sentences, valid_sentences, train_tag, valid_tag, train_pos, valid_pos = train_test_split(sentences, tags, pos, test_size=0.2)

# Cell
train_dl = utils.create_loader(train_sentences, train_tag, train_pos, bs=config.TRAIN_BATCH_SIZE)
valid_dl = utils.create_loader(valid_sentences, valid_tag, valid_pos, bs=config.VALID_BATCH_SIZE)

# Cell
modeller = model.EntityModel(num_tag=len(le_tag.classes_), num_pos=len(le_pos.classes_))

# Cell
# we don't want weight decay for these
no_decay = ['bias', 'LayerNorm.weight', 'LayerNorm.bias']

optimizer_params = [
    {'params': [p for n, p in model_params if not any(nd in n for nd in no_decay)],
    'weight_decay':0.001},
    #  no weight decay should be applied
    {'params': [p for n, p in model_params if any(nd in n for nd in no_decay)],
    'weight_decay':0.0}
]

# Cell
lr = config.LR

# Cell
optimizer = AdamW(optimizer_params, lr=lr)

# Cell
num_train_steps = int(len(sentences) / config.TRAIN_BATCH_SIZE * config.NUM_EPOCHS)

# Cell
scheduler = get_linear_schedule_with_warmup(optimizer=optimizer,
                                                num_warmup_steps=0,
                                                num_training_steps=num_train_steps)

# Cell
learn = engine.BertFitter(modeller, (train_dl, valid_dl), optimizer, [accuracy_score, partial(f1_score, average='macro')], config.DEVICE, scheduler=scheduler, log_file='training_log.txt')

# Cell
NUM_EPOCHS = config.NUM_EPOCHS + 2
learn.fit(NUM_EPOCHS, model_path=config.MODEL_PATH/'entity_model.bin')