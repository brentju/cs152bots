import os
from torchvision import datasets, models, transforms
import torch
from torch.utils.data import DataLoader
from torch import nn, optim
import certifi
from tqdm import tqdm
import torch.nn as nn

def train_model(model, criterion, optimizer, num_epochs=10):
    for epoch in range(num_epochs):
        print(f'Epoch {epoch}/{num_epochs - 1}')
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'test']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data
            for inputs, labels in tqdm(dataloaders[phase], desc=f'{phase} Epoch {epoch + 1}/{num_epochs}', unit='batch'):
                inputs = inputs.to(device)
                labels = labels.to(device)

                # Zero the parameter gradients
                optimizer.zero_grad()

                # Forward
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    # Backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # Statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

    return model

if __name__ == '__main__':
    # Set the SSL_CERT_FILE environment variable
    os.environ['SSL_CERT_FILE'] = certifi.where()

    # Define directories
    train_dir = './data/train'
    test_dir = './data/test'

    # Define transformations for the training and testing sets
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'test': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # Load the datasets with ImageFolder
    image_datasets = {
        'train': datasets.ImageFolder(os.path.join(train_dir), data_transforms['train']),
        'test': datasets.ImageFolder(os.path.join(test_dir), data_transforms['test'])
    }

    # Create data loaders
    dataloaders = {
        'train': DataLoader(image_datasets['train'], batch_size=32, shuffle=True, num_workers=4),
        'test': DataLoader(image_datasets['test'], batch_size=32, shuffle=False, num_workers=4)
    }

    # Get dataset sizes and class names
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'test']}
    class_names = image_datasets['train'].classes

    # Check if GPU/metal is available
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Training on: {device}")
    
    # For the sake of time, train a simple CNN
    model = nn.Sequential(
        nn.Conv2d(3, 16, (3,3), stride=1),
        nn.BatchNorm2d(16),
        nn.LeakyReLU(),
        nn.MaxPool2d((2,2), stride=2),
        nn.Conv2d(16, 32, (3,3), stride=1),
        nn.BatchNorm2d(32),
        nn.LeakyReLU(),
        nn.MaxPool2d((2,2), stride=2),
        nn.Flatten(),
        nn.Linear(93312, 256),
        nn.LeakyReLU(),
        nn.Linear(256, 2)
    )

    # Load a pretrained ResNet model and modify the final layer
    # weights = models.ResNet18_Weights.IMAGENET1K_V1
    # model = models.resnet18(weights=weights)
    # num_ftrs = model.fc.in_features
    # model.fc = nn.Linear(num_ftrs, len(class_names))  # Adjust final layer for our number of classes

    # Move the model to the appropriate device
    model = model.to(device)

    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)

    # Train the model
    model = train_model(model, criterion, optimizer, num_epochs=8)

    # Save the trained model
    torch.save(model.state_dict(), 'cnn_finetuned.pth')
