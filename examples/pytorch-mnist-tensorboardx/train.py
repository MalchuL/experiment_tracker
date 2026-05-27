from __future__ import annotations

import argparse
import random
from pathlib import Path
import uuid
import torch
from PIL import Image, ImageDraw
from tensorboardX import SummaryWriter
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

MNIST_MEAN = 0.1307
MNIST_STD = 0.3081


class MnistClassifier(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(32 * 7 * 7, 64)
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a small MNIST classifier.")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--max-train-batches", type=int, default=20)
    parser.add_argument("--max-val-batches", type=int, default=5)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("runs/mnist-tensorboardx" + str(uuid.uuid4())),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_loaders(data_dir: Path, batch_size: int) -> tuple[DataLoader, DataLoader]:
    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((MNIST_MEAN,), (MNIST_STD,)),
        ]
    )
    train_dataset = datasets.MNIST(
        root=data_dir,
        train=True,
        download=True,
        transform=transform,
    )
    val_dataset = datasets.MNIST(
        root=data_dir,
        train=False,
        download=True,
        transform=transform,
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    return train_loader, val_loader


def limited_batches(loader: DataLoader, max_batches: int):
    for batch_index, batch in enumerate(loader):
        if max_batches > 0 and batch_index >= max_batches:
            break
        yield batch


def annotated_digit_grid(
    images: torch.Tensor,
    targets: torch.Tensor,
    predictions: torch.Tensor,
    max_images: int = 16,
) -> torch.Tensor:
    count = min(max_images, images.size(0))
    tile_size = 40
    label_height = 12
    columns = 4
    rows = (count + columns - 1) // columns
    grid = Image.new("RGB", (columns * tile_size, rows * tile_size), "white")
    draw = ImageDraw.Draw(grid)

    for index in range(count):
        image = images[index].detach().cpu().squeeze(0)
        image = (image * MNIST_STD + MNIST_MEAN).clamp(0, 1)
        image = Image.fromarray((image.numpy() * 255).astype("uint8"), mode="L")
        image = image.resize((28, 28), resample=Image.Resampling.NEAREST).convert("RGB")

        x = (index % columns) * tile_size
        y = (index // columns) * tile_size
        grid.paste(image, (x + 6, y + label_height))
        draw.text(
            (x + 2, y),
            f"p:{int(predictions[index])} g:{int(targets[index])}",
            fill=(0, 0, 0),
        )

    tensor = torch.frombuffer(bytearray(grid.tobytes()), dtype=torch.uint8)
    tensor = tensor.view(grid.height, grid.width, 3)
    return tensor.permute(2, 0, 1)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    writer: SummaryWriter,
    epoch: int,
    max_batches: int,
) -> int:
    model.train()
    correct = 0
    total = 0
    steps = 0
    for images, targets in limited_batches(loader, max_batches):
        images = images.to(device)
        targets = targets.to(device)

        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = F.cross_entropy(logits, targets)
        loss.backward()
        optimizer.step()

        batch_size = targets.size(0)
        correct += (logits.argmax(dim=1) == targets).sum().item()
        total += batch_size
        steps += 1

        global_step = epoch * max_batches + steps
        writer.add_scalar("train/loss", loss.item(), global_step)
        writer.add_scalar("train/accuracy", correct / total, global_step)
        writer.add_scalar(
            "train/learning_rate",
            optimizer.param_groups[0]["lr"],
            global_step,
        )
        if steps == 1:
            writer.add_image(
                "train/predictions",
                annotated_digit_grid(
                    images=images,
                    targets=targets,
                    predictions=logits.argmax(dim=1),
                ),
                global_step,
            )
    return steps


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    writer: SummaryWriter,
    epoch: int,
    max_batches: int,
) -> None:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    steps = 0
    for images, targets in limited_batches(loader, max_batches):
        images = images.to(device)
        targets = targets.to(device)
        logits = model(images)
        loss = F.cross_entropy(logits, targets)

        batch_size = targets.size(0)
        total_loss += loss.item() * batch_size
        correct += (logits.argmax(dim=1) == targets).sum().item()
        total += batch_size
        steps += 1

        if steps == 1:
            writer.add_image(
                "val/predictions",
                annotated_digit_grid(
                    images=images,
                    targets=targets,
                    predictions=logits.argmax(dim=1),
                ),
                epoch,
            )

    if total == 0:
        return

    writer.add_scalar("val/loss", total_loss / total, epoch)
    writer.add_scalar("val/accuracy", correct / total, epoch)
    print(
        f"epoch={epoch + 1} "
        f"val_loss={total_loss / total:.4f} "
        f"val_accuracy={correct / total:.4f} "
        f"val_batches={steps}"
    )


def main() -> None:
    args = parse_args()
    seed_everything(args.seed)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader = build_loaders(args.data_dir, args.batch_size)
    model = MnistClassifier().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    with SummaryWriter(logdir=str(args.log_dir)) as writer:
        writer.add_hparams(
            {
                "batch_size": args.batch_size,
                "epochs": args.epochs,
                "lr": args.lr,
                "max_train_batches": args.max_train_batches,
                "max_val_batches": args.max_val_batches,
                "seed": args.seed,
                "device": device.type,
                "optimizer": "Adam",
            },
            {},
            name="mnist-run-config",
        )
        for epoch in range(args.epochs):
            train_steps = train_one_epoch(
                model=model,
                loader=train_loader,
                optimizer=optimizer,
                device=device,
                writer=writer,
                epoch=epoch,
                max_batches=args.max_train_batches,
            )
            validate(
                model=model,
                loader=val_loader,
                device=device,
                writer=writer,
                epoch=epoch,
                max_batches=args.max_val_batches,
            )
            print(
                f"epoch={epoch + 1} "
                f"train_batches={train_steps} "
                f"device={device.type} "
                f"log_dir={args.log_dir}"
            )


if __name__ == "__main__":
    main()
