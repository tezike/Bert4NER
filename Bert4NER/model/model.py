# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/model.model.ipynb (unless otherwise specified).

__all__ = ['EntityModel']

# Cell
import torch
import torch.nn as nn
import transformers

# Cell
class EntityModel(nn.Module):
    def __init__(self, num_tag, num_pos, drop=0.3, model_name='bert-base-uncased'):
        super().__init__()
        _config = transformers.BertConfig.from_pretrained(model_name)
        self.model = transformers.BertModel.from_pretrained(model_name, config=_config)

        self.num_tag = num_tag
        self.num_pos = num_pos

        self.tok = transformers.BertTokenizer.from_pretrained(
            pretrained_model_name_or_path=model_name,
            do_lower_case=True,
            )
        out_size = getattr(self.model, 'pooler').dense.out_features
        self.drop_tag = nn.Dropout(drop)
        self.drop_pos = nn.Dropout(drop)

        self.classifier_tag = nn.Linear(out_size, self.num_tag)
        self.classifier_pos = nn.Linear(out_size, self.num_pos)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        enc_hidden, enc_attn_mask = self.model(input_ids,
                            attention_mask=attention_mask,
                            token_type_ids=token_type_ids,
                           )
#         enc_hidden: (batch_size, sequence_length, hidden_size)
#         enc_attn_mask: (batch_size, sequence_length)
#         We don't need the enc_attn_mask as we are not building a decoder
        out_tag = self.drop_tag(enc_hidden)
        out_pos = self.drop_pos(enc_hidden)
#         each token in the sequence has `out_tag` or `out_pos` num of predictions
#         so we need to softmax the predictions and take the max
        return self.classifier_tag(out_tag), self.classifier_pos(out_pos)