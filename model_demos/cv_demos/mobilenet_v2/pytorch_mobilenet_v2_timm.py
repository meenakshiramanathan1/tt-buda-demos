# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0


# MobileNetV2 Demo Script - TIMM

import os
import urllib

import pybuda
import requests
import timm
import torch
from PIL import Image
from pybuda._C.backend_api import BackendDevice
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform


def run_mobilenetv2_timm():

    # Set PyBuda configuration parameters
    compiler_cfg = pybuda.config._get_global_compiler_config()
    compiler_cfg.balancer_policy = "Ribbon"
    compiler_cfg.default_df_override = pybuda._C.DataFormat.Float16_b
    available_devices = pybuda.detect_available_devices()
    if available_devices:
        if available_devices[0] == BackendDevice.Grayskull:
            os.environ["PYBUDA_RIBBON2"] = "1"

    # Create PyBuda module from PyTorch model
    model = timm.create_model("mobilenetv2_100", pretrained=True)
    tt_model = pybuda.PyTorchModule("mobilenet_v2__hf_timm", model)

    # Image load and pre-processing into pixel_values
    config = resolve_data_config({}, model=model)
    transform = create_transform(**config)
    url = "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg"
    img = Image.open(requests.get(url, stream=True).raw).convert("RGB")
    img_tensor = transform(img).unsqueeze(0)  # transform and add batch dimension

    # Run inference on Tenstorrent device
    output_q = pybuda.run_inference(tt_model, inputs=([img_tensor]))
    output = output_q.get(timeout=0.5)

    # Data postprocessing
    probabilities = torch.nn.functional.softmax(output[0].value())[0]

    # Get ImageNet class mappings
    url = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
    image_classes = urllib.request.urlopen(url)
    categories = [s.decode("utf-8").strip() for s in image_classes.readlines()]

    # Print top categories per image
    top5_prob, top5_catid = torch.topk(probabilities, 5)
    for i in range(top5_prob.size(0)):
        print(categories[top5_catid[i]], top5_prob[i].item())


if __name__ == "__main__":
    run_mobilenetv2_timm()
