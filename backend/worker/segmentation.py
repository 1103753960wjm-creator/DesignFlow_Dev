from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SegmentationConfig:
    max_side: int = 1024
    num_classes: int = 4
    encoder_name: str = "resnet34"
    encoder_weights: str | None = "imagenet"


class LocalSegmentationModel:
    def __init__(self, *, device: str | None = None, config: SegmentationConfig | None = None) -> None:
        self.config = config or SegmentationConfig()

        torch = self._torch()
        self.device = self._resolve_device(torch, device)
        self.model = self._build_model_with_retries()
        self.model.eval()
        self.model.to(self.device)

    def predict(self, image_path: str | Path) -> np.ndarray:
        cv2 = self._cv2()
        torch = self._torch()

        image_path = Path(image_path)
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")

        h0, w0 = int(bgr.shape[0]), int(bgr.shape[1])
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        resized, _ = self._resize_max_side(rgb, max_side=self.config.max_side)
        x = self._preprocess_to_tensor(resized).to(self.device, dtype=torch.float32)

        try:
            class_map_small = self._infer_class_map(x)
        except RuntimeError as e:
            msg = str(e).lower()
            if self.device.type == "cuda" and "out of memory" in msg:
                logger.warning("GPU OOM, switching to CPU...")
                torch.cuda.empty_cache()
                self.model.to("cpu")
                self.device = torch.device("cpu")
                x_cpu = x.to("cpu", dtype=torch.float32)
                class_map_small = self._infer_class_map(x_cpu)
            elif self.device.type == "cuda" and (
                "no kernel image is available" in msg
                or "not compiled with cuda enabled" in msg
                or "cuda error" in msg
            ):
                logger.warning("GPU inference failed, switching to CPU...")
                torch.cuda.empty_cache()
                self.model.to("cpu")
                self.device = torch.device("cpu")
                x_cpu = x.to("cpu", dtype=torch.float32)
                class_map_small = self._infer_class_map(x_cpu)
            else:
                raise
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        class_map = cv2.resize(
            class_map_small.astype(np.uint8),
            (w0, h0),
            interpolation=cv2.INTER_NEAREST,
        )
        return class_map

    def _infer_class_map(self, x):
        torch = self._torch()
        with torch.no_grad():
            logits = self.model(x)
            if isinstance(logits, (tuple, list)):
                logits = logits[0]
            logits = logits.float()
            probs = torch.softmax(logits, dim=1)
            class_map = torch.argmax(probs, dim=1).squeeze(0).detach().cpu().numpy()
            return class_map

    def _preprocess_to_tensor(self, rgb: np.ndarray):
        torch = self._torch()
        x = rgb.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
        x = np.transpose(x, (2, 0, 1))
        x = np.expand_dims(x, axis=0)
        return torch.from_numpy(x).contiguous()

    def _resize_max_side(self, rgb: np.ndarray, *, max_side: int) -> tuple[np.ndarray, float]:
        h, w = int(rgb.shape[0]), int(rgb.shape[1])
        scale = min(1.0, float(max_side) / float(max(h, w)))
        if scale >= 1.0:
            return rgb, 1.0
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        cv2 = self._cv2()
        out = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return out, scale

    def _build_model_with_retries(self):
        smp = self._smp()
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                return smp.DeepLabV3Plus(
                    encoder_name=self.config.encoder_name,
                    encoder_weights=self.config.encoder_weights,
                    classes=self.config.num_classes,
                    activation=None,
                )
            except Exception as e:
                last_exc = e
                sleep_s = 2.0 * float(attempt)
                logger.warning("Failed to init DeepLabV3Plus (attempt %s/3): %s", attempt, e)
                time.sleep(sleep_s)

        if self.config.encoder_weights is not None:
            logger.warning("Falling back to encoder_weights=None due to init failures: %s", last_exc)
            return smp.DeepLabV3Plus(
                encoder_name=self.config.encoder_name,
                encoder_weights=None,
                classes=self.config.num_classes,
                activation=None,
            )

        raise RuntimeError(f"Failed to init segmentation model: {last_exc}")

    def _resolve_device(self, torch, requested: str | None):
        if requested is not None:
            return torch.device(requested)
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def _torch(self):
        try:
            import torch
        except Exception as e:
            raise RuntimeError("Missing dependency: torch") from e
        return torch

    def _smp(self):
        try:
            import segmentation_models_pytorch as smp
        except Exception as e:
            raise RuntimeError("Missing dependency: segmentation-models-pytorch") from e
        return smp

    def _cv2(self):
        try:
            import cv2
        except Exception as e:
            raise RuntimeError("Missing dependency: opencv-python-headless") from e
        return cv2

