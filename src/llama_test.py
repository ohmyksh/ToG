import os

os.environ['CUDA_VISIBLE_DEVICES'] = '0, 1, 2, 3'
#print(os.environ['CUDA_VISIBLE_DEVICES'])

from transformers import AutoTokenizer
import transformers
import torch

model = "/home/jylee/.cache/huggingface/hub/models--meta-llama--Llama-2-13b-hf/snapshots/5c31dfb671ce7cfe2d7bb7c04375e44c55e815b1"

tokenizer = AutoTokenizer.from_pretrained(model)
pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    torch_dtype=torch.float16,
    device_map="auto",
)

sentence = 'I liked "Breaking Bad" and "Band of Brothers". Do you have any recommendations of other shows I might like?\n',

sequences = pipeline(
    sentence,
    do_sample=True,
    top_k=10,
    num_return_sequences=1,
    eos_token_id=tokenizer.eos_token_id,
    max_length=200,
)

for seq in sequences:
    print(f"Result: {seq['generated_text']}")