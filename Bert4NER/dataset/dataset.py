# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/dataset.dataset.ipynb (unless otherwise specified).

__all__ = ['EntityDataset']

# Cell
import os
import torch
import transformers

import pandas as pd
import numpy as np
import Bert4NER.config as config

from sklearn.preprocessing import LabelEncoder

# Cell
class EntityDataset(torch.utils.data.Dataset):
    def __init__(self, texts, pos, tags):
        self.texts = texts
        self.pos = pos
        self.tags = tags

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = self.texts[item]
        pos = self.pos[item]
        tag = self.tags[item]

        tokens = []
        target_pos = []
        target_tag = []

        # tokenize the each word in the text string
        for i, word in enumerate(text):
            inputs = config.TOKENIZER.encode(
                word,
                add_special_tokens = False,
#                 truncation = True
            )

            input_len = len(inputs)
            tokens.extend(inputs)

            # the tag for that particular word should be the same for all the
            # sub tokens of the word

            target_pos.extend([pos[i]] * input_len)
            target_tag.extend([tag[i]] * input_len)

        tokens = tokens[:config.MAX_SEQ_LEN - 2]
        target_pos = target_pos[:config.MAX_SEQ_LEN - 2]
        target_tag = target_tag[:config.MAX_SEQ_LEN - 2]

        tokens = [101] + tokens + [102]
        target_pos = [0] + target_pos + [0]
        target_tag = [0] + target_tag + [0]

        mask = [1] * len(tokens)
        token_type_ids = [0] * len(tokens)

        pad_len = (config.MAX_SEQ_LEN) - len(tokens)

        tokens = tokens + ([0] * pad_len)
        mask = mask + ([0] * pad_len)
        token_type_ids = token_type_ids + ([0] * pad_len)
        target_pos = target_pos + ([0] * pad_len)
        target_tag = target_tag + ([0] * pad_len)

        return {
            'input_ids': torch.tensor(tokens, dtype=torch.long),
            'attention_mask': torch.tensor(mask, dtype=torch.long),
            'token_type_ids': torch.tensor(token_type_ids, dtype=torch.long),
            'target_pos': torch.tensor(target_pos, dtype=torch.long),
            'target_tag': torch.tensor(target_tag, dtype=torch.long),
        }