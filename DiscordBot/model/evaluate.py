import torch
import torch.nn as nn
import os
from torch.utils.data import DataLoader
from torchvision import transforms, datasets, models
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from tqdm import tqdm
from model import CNNModel

# Define a function to evaluate the model
def evaluate_model(model, dataloader, device):
    model.eval()  # Set the model to evaluation mode
    criterion = nn.CrossEntropyLoss()

    all_preds = []
    all_labels = []
    running_loss = 0.0

    with torch.no_grad():
        for images, labels in tqdm(dataloader):
            images, labels = images.to(device), labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item()

            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = running_loss / len(dataloader)
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds)
    recall = recall_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds)
    conf_matrix = confusion_matrix(all_labels, all_preds)

    metrics = {
        'loss': avg_loss,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': conf_matrix
    }

    return metrics

# Example usage:
if __name__ == "__main__":
    model = CNNModel()
    model.load_state_dict(torch.load("cnn_finetuned.pth"))
    test_dir = './data/test'
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    # Define transformations for the training and testing sets
    data_transforms = {
        'test': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # Load the datasets with ImageFolder
    image_datasets = {
        'test': datasets.ImageFolder(os.path.join(test_dir), data_transforms['test'])
    }

    # Create data loaders
    test_dataloader = DataLoader(image_datasets['test'], batch_size=32, shuffle=False, num_workers=4)

    # Move the model to the correct device
    model.to(device)

    # Evaluate the model
    metrics = evaluate_model(model, test_dataloader, device)

    # Print the metrics
    print(f"Loss: {metrics['loss']:.4f}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1_score']:.4f}")
    print("Confusion Matrix:")
    print(metrics['confusion_matrix'])
