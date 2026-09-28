import time

import torch
from qwen_vl_utils import process_vision_info

from src.locator_recovery import build_locator_prompt


class QwenSettingsLocator:
    """History-free visual recovery role sharing the Actor's loaded model."""

    def __init__(self, actor):
        self.model_id = actor.model_id
        self.processor = actor.processor
        self.model = actor.model

    def locate(self, image, goal, forbidden_regions=None):
        width, height = image.size
        prompt = build_locator_prompt(
            goal, width, height, forbidden_regions=forbidden_regions
        )
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]
        chat_text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[chat_text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to("cuda")

        start_time = time.perf_counter()
        with torch.inference_mode():
            generated_ids = self.model.generate(
                **inputs, max_new_tokens=64, do_sample=False
            )
        latency_seconds = time.perf_counter() - start_time
        trimmed_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]
        raw_output = self.processor.batch_decode(
            trimmed_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return raw_output, latency_seconds
