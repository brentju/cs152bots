import torch
import torch.nn as nn

class CNNModel(nn.Module):
    def __init__(self):
        super(CNNModel, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, (3, 3), stride=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.relu1 = nn.LeakyReLU()
        self.pool1 = nn.MaxPool2d((2, 2), stride=2)
        
        self.conv2 = nn.Conv2d(16, 32, (3, 3), stride=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.relu2 = nn.LeakyReLU()
        self.pool2 = nn.MaxPool2d((2, 2), stride=2)
        
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(32 * 54 * 54, 256)
        self.relu3 = nn.LeakyReLU()
        self.fc2 = nn.Linear(256, 2)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu1(x)
        x = self.pool1(x)
        
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu2(x)
        x = self.pool2(x)
        
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.relu3(x)
        x = self.fc2(x)
        return x