import torch
x = torch.load('slr_model.pth')
print(len(x.get('model_state').get('lstm.bias_ih_l0')))