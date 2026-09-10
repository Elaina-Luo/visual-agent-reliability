import json
import time

import torch
from qwen_vl_utils import process_vision_info


def build_verifier_prompt(goal, requested_action):
    return f"""
You verify a GUI Agent action using only two screenshots.

Goal:
{goal}

Requested action:
{json.dumps(requested_action)}

The first image is BEFORE the action. The second image is AFTER the action.

Classify the current result:
- complete: the AFTER image visibly shows the full goal is completed and saved.
- changed: the action caused visible progress, but the full goal is not yet complete.
- no_effect: the relevant GUI state did not visibly change.
- uncertain: the screenshots do not provide enough evidence for another label.

Use only visible evidence. You cannot access DOM state, test IDs, execution logs,
or the hidden evaluator. Do not assume a requested click succeeded.

Return exactly one JSON object and no other text:
{{"status": "complete"}}
{{"status": "changed"}}
{{"status": "no_effect"}}
{{"status": "uncertain"}}
""".strip()


class QwenSettingsVerifier:
    """A verification role that reuses the Actor's loaded Qwen model."""

    def __init__(self, actor):
        self.model_id = actor.model_id
        self.processor = actor.processor
        self.model = actor.model

    def verify(self, before_image, after_image, goal, requested_action):
        prompt = build_verifier_prompt(goal, requested_action)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "BEFORE screenshot:"},
                    {"type": "image", "image": before_image},
                    {"type": "text", "text": "AFTER screenshot:"},
                    {"type": "image", "image": after_image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        chat_text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
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
                **inputs,
                max_new_tokens=32,
                do_sample=False,
            )
        latency_seconds = time.perf_counter() - start_time

        trimmed_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(
                inputs.input_ids,
                generated_ids,
            )
        ]
        raw_output = self.processor.batch_decode(
            trimmed_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return raw_output, latency_seconds
