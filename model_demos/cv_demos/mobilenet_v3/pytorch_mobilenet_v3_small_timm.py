# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0

# MobileNetV3 Demo Script - TIMM (small)

import os
import urllib

import pybuda
import requests
import timm
import torch
from PIL import Image
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform


def run_mobilenetv3_small_timm():

    # Set PyBuda configuration parameters
    compiler_cfg = pybuda.config._get_global_compiler_config()
    compiler_cfg.balancer_policy = "Ribbon"
    compiler_cfg.default_dram_parameters = False
    compiler_cfg.default_df_override = pybuda._C.DataFormat.Float16_b
    os.environ["PYBUDA_LEGACY_KERNEL_BROADCAST"] = "1"

    # Create PyBuda module from PyTorch model
    # Both options are good
    # model = timm.create_model('mobilenetv3_small_100', pretrained=True)
    model = timm.create_model("hf_hub:timm/mobilenetv3_small_100.lamb_in1k", pretrained=True)
    tt_model = pybuda.PyTorchModule("mobilenet_v3_small__hf_timm", model)

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
    run_mobilenetv3_small_timm()
