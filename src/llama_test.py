# from transformers import AutoTokenizer, AutoModelForCausalLM

# # model load
# model_path = "meta-llama/Llama-2-70b-chat-hf"
# tokenizer = AutoTokenizer.from_pretrained(model_path)
# model = AutoModelForCausalLM.from_pretrained(model_path)

# # model save
# save_dir = "/home/shkim/ToG-implement/llama_model"
# tokenizer.save_pretrained(save_dir)
# model.save_pretrained(save_dir)

from llama_cpp import Llama
llm = Llama(
    model_path='/home/shkim/ToG-implement/llama_model/Llama-2-70B-chat-hf-Q8_0.gguf', 
    n_gpu_layers=30, 
    n_ctx=3584, 
    n_batch=521, 
    verbose=True)
# adjust n_gpu_layers as per your GPU and model
output = llm("Q: Name the planets in the solar system? A: ", max_tokens=32, stop=["Q:", "\n"], echo=True)
print(output)