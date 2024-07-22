import torch
import logging
from retriever import * 
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import time

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

class BasicGenerator:
    def __init__(self, model_name_or_path):
        logger.info(f"Loading model from {model_name_or_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model_config = AutoConfig.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path, device_map="auto")
        if self.model_config.model_type == "llama":
            self.space_token = "_"
        else:
            self.space_token = self.tokenizer.tokenize(' ')[0]
    def generate(self, input_text, max_length):
        input_ids = self.tokenizer.encode(input_text, return_tensors="pt")
        input_ids = input_ids.to(self.model.device)
        input_length = input_ids.shape[1]
        outputs = self.model.generate(
                input_ids = input_ids, 
                max_new_tokens = max_length
            )
        generated_tokens = outputs.sequences[:, input_length:]
        text = self.tokenizer.decode(generated_tokens[0])
        return text
    

class IO_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        
    def inference(self, question, demo, case):
        # prompt
        prompt = ""
        text = self.generate(prompt, 256) #generate max length
        return text
    
    
class CoT_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        
    def inference(self, question, demo, case):
        cot_prompt = ""
        text = self.generate(cot_prompt, 256)
        return text
    
    
class ToG(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
    
    def initializer(question):
        return []
    
    def prune(question, set, type):
        result = []
        
        if type == 'entity':
            result = []
        elif type == 'relation':
            result = []
        else:
            NotImplementedError

        return result
    
    def retriever(retriever_name, question, set, type):
        retrieve = []
        if retriever_name == "wikidata":
            retriever = WikidataRetriever()
            if type == 'entity':
                retrieve = retriever.entity_set_retriever(question, set)
            elif type == 'relation':
                retrieve = retriever.relation__set_retriever(question, set)
            else:
                NotImplementedError
        elif retriever_name == "freebase":
            NotImplementedError
        return retrieve
    
    def reasoning(self, question, reasoning_path):
        prompt = """Given a question and the associated retrieved knowledge graph triples (entity, relation, entity), 
        you are asked to answer whether it’s sufficient for you to answer the question with these triples and your knowledge (Yes or No)."""
        prompt += "\nQ: "+ question
        Explored_path = "" # reasoning path
        prompt += "\nKnowledge triples: " + reasoning_path
        prompt += "\nA:"
        answer = self.generate(prompt, 256)
        # extract answer???
        return False
    
    def final_ans_generator(self, question, reasoning_path):
        prompt = question + reasoning_path
        answer = self.generate(prompt, 256)
        return answer
    
    def inference(self, question, demo, case, d_max, N):
        text = ""
        E = self.initializer(question)
        reasoning_path = []
        depth= 0
        while depth <= d_max:
            R_cand = self.retriever("wikidata", question, E, "relation")
            R = self.prune(question, R_cand, "relation")
            reasoning_path += R # update reasoning path
            E_cand = self.retriever("wikidata", question, R, "entity")
            E = self.prune(question, E_cand, "entity")
            reasoning_path += E # update reasoning path
            
            if self.reasoning(question, reasoning_path):
                break
            
            depth += 1
        answer = self.final_ans_generator(question, reasoning_path)
        return answer
            
            
          
            