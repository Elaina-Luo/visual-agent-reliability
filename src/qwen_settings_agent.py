import json
import time

import torch
from qwen_vl_utils import process_vision_info
from transformers import (
    AutoProcessor,
    Qwen2_5_VLForConditionalGeneration,
)


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"


def build_reactive_prompt(
    goal,
    recent_actions,
    remaining_steps,
    width,
    height,
    verification_history=None,
):
    action_history = (
        json.dumps(recent_actions[-4:])
        if recent_actions
        else "No previous actions."
    )

    verifier_context = ""
    if verification_history:
        verifier_context = f"""

Recent visual verification results:
{json.dumps(verification_history[-4:])}

Use this feedback when choosing the next action. If a click visibly changed
the intended control, do not immediately click the same control again. If a
click had no visible effect, the recovery policy may already have retried it.
"""

    return f"""
You control a desktop Settings application using only screenshots.

Goal:
{goal}

Current screenshot size:
width = {width} pixels
height = {height} pixels

Coordinate system:
- top-left is (0, 0)
- bottom-right is ({width - 1}, {height - 1})

Recent actions you previously requested:
{action_history}
{verifier_context}

Remaining action budget: {remaining_steps}

Choose exactly one next action from the current screenshot.

STRICT OUTPUT CONTRACT:
- Return exactly one JSON object and no other text.
- Return only one action. Never combine a click and finish.
- For a click, x and y must be two separate integer fields.
- Never put both coordinates inside a list or array.

Valid click format:
{{"type": "click", "x": integer, "y": integer}}

Valid finish format, only when the current screenshot shows that the goal is
fully completed and saved:
{{"type": "finish"}}

Invalid formats include:
{{"type": "click", "x": [420, 210]}}
{{"type": "click", "x": 420, "y": 210}}; {{"type": "finish"}}

Do not include explanation, markdown, or a future action.
""".strip()


class QwenSettingsAgent:
    def __init__(self, model_id=DEFAULT_MODEL_ID):
        self.model_id = model_id
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
        self.model.eval()

    def decide(
        self,
        image,
        goal,
        recent_actions,
        remaining_steps,
        verification_history=None,
    ):
        width, height = image.size
        prompt = build_reactive_prompt(
            goal,
            recent_actions,
            remaining_steps,
            width,
            height,
            verification_history,
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
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
                max_new_tokens=96,
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
