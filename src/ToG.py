import torch
import logging
from retriever import * 
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import time

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

class BasicGenerator:
    def __init__(self, args):
        model_info = args.model_name_or_path
        logger.info(f"Loading model from {model_info}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_info)
        self.model_config = AutoConfig.from_pretrained(model_info)
        
        # quantization
        self.model = AutoModelForCausalLM.from_pretrained(
            model_info, 
            device_map="auto", 
            torch_dtype=torch.float32 
            ) 
        print(self.model.get_memory_footprint())
        
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
        generated_tokens = outputs[:, input_length:]
        text = self.tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
        return text
    

class IO_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.io_prompt = """
        Q: What state is home to the university that is represented in sports by George Washington Colonials men’s basketball?
        A: Washington, D.C.
        
        Q: Who lists Pramatha Chaudhuri as an influence and wrote Jana Gana Mana?
        A: Bharoto Bhagyo Bidhata.
        
        Q: Who was the artist nominated for an award for You Drive Me Crazy?
        A: Jason Allen Alexander.
        
        Q: What person born in Siegen influenced the work of Vincent Van Gogh?
        A: Peter Paul Rubens.
        
        Q: What is the country close to Russia where Mikheil Saakashvii holds a government position?
        A: Georgia.
        
        Q: What drug did the actor who portrayed the character Urethane Wheels Guy overdosed on?
        A: Heroin.
        """
    def inference(self, question):
        # prompt
        prompt = self.io_prompt + "\nQ: " + question + "\nA: "
        text = self.generate(prompt) #generate max length
        return text
    
    
class CoT_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.cot_prompt = """
        Q: What state is home to the university that is represented in sports by George Washington Colonials men’s basketball?
        A: First, the education institution has a sports team named George Washington Colonials men’s basketball in is George Washington University, Second, George Washington University is in Washington D.C. The answer is Washington, D.C.
        
        Q: Who lists Pramatha Chaudhuri as an influence and wrote Jana Gana Mana?
        A: First, Bharoto Bhagyo Bidhata wrote Jana Gana Mana. Second, Bharoto Bhagyo Bidhata lists Pramatha Chaudhuri as an influence. The answer is Bharoto Bhagyo Bidhata.
        
        Q: Who was the artist nominated for an award for You Drive Me Crazy?
        A: First, the artist nominated for an award for You Drive Me Crazy is Britney Spears. The answer is Jason Allen Alexander.
        
        Q: What person born in Siegen influenced the work of Vincent Van Gogh?
        A: First, Peter Paul Rubens, Claude Monet and etc. influenced the work of Vincent Van Gogh. Second, Peter Paul Rubens born in Siegen. The answer is Peter Paul Rubens.
        
        Q: What is the country close to Russia where Mikheil Saakashvii holds a government position?
        A: First, China, Norway, Finland, Estonia and Georgia is close to Russia. Second, Mikheil Saakashvii holds a government position at Georgia. The answer is Georgia.
        
        Q: What drug did the actor who portrayed the character Urethane Wheels Guy overdosed on?
        A: First, Mitchell Lee Hedberg portrayed character Urethane Wheels Guy. Second, Mitchell Lee Hedberg overdose Heroin. The answer is Heroin.
        """
        
    def inference(self, question, demo, case):
        prompt = self.cot_prompt + "\nQ: " + question + "\nA: "
        text = self.generate(prompt, 256)
        return text
    
    
class ToG(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.topic_entites = []
    
    def initializer(self, args, question, N):
        # extract top-N topic entites
        # convert entities to wikidata ids. 
        prompt = f"""Please extract up to {N} topic entities (separated by semicolon) in question.\n
        question: {question}"""
        # extracted_topic_entities = self.generate(prompt)
        extracted_topic_entities = "Canberra; Australia; majority party"
        extracted_topic_entities = [entity.strip() for entity in extracted_topic_entities.split(';')]
        if args.knowledge_base == "wikidata":
            retriever = WikidataRetriever()
        elif args.knowledge_base == "freebase":
            NotImplementedError
            
        self.topic_entites = retriever.get_id(extracted_topic_entities)
        print(self.topic_entites)
        return self.topic_entites
    
    def prune(question, set, type):
        result = []
        
        if type == 'entity':
            result = []
        elif type == 'relation':
            result = []
        else:
            NotImplementedError

        return result
    
    def retriever(retriever_name, question, set, type, reasoning_path):
        retrieve = []
        if retriever_name == "wikidata":
            retriever = WikidataRetriever()
            if type == 'entity':
                retrieve = retriever.entity_set_retriever(question, set, reasoning_path)
            elif type == 'relation':
                retrieve = retriever.relation__set_retriever(question, set, reasoning_path)
            else:
                NotImplementedError
        elif retriever_name == "freebase":
            NotImplementedError
        return retrieve
    
    def reasoning(self, question, reasoning_path):
        prompt = """Please answer the question using Topic Entity, Relations Chains and their Candidate Entities that contribute to the question, 
        you are asked to answer whether it’s sufficient for you to answer the question with these triples and your knowledge (Yes or No)."""
        prompt += "\nin context few shot"
        prompt += "\nQ: "+ question
        explored_relation_chains = "" # reasoning path
        prompt += "\nTopic Entity, with relations chains, and their candidate entities: " + explored_relation_chains
        prompt += "\nA:"
        answer = self.generate(prompt)
        # extract answer???
        return False
    
    def final_ans_generator(self, question, reasoning_path):
        prompt = """Given a question and the associated retrieved knowledge graph triples (entity, relation, entity), 
        you are asked to answer the question with these triples and your own knowledge."""
        prompt += """\n in context few shot"""
        prompt += "\nQ: " + question
        # make knowledge triples 
        knowledge_triple = []
        prompt += "\nKnowledge triples: " 
        prompt += "\nA: " 
        answer = self.generate(prompt)
        return answer
    
    def inference(self, args, question, demo, case, d_max, N):
        text = ""
        E = self.initializer(question, N)
        reasoning_path = []
        depth= 0
        while depth <= d_max:
            R_cand = self.retriever(args.knowledge_base, question, E, "relation", reasoning_path)
            R = self.prune(question, R_cand, "relation")
            E_cand = self.retriever(args.knowledge_base, question, R, "entity", reasoning_path)
            E = self.prune(question, E_cand, "entity")
            
            if self.reasoning(question, reasoning_path):
                break
            
            depth += 1
        answer = self.final_ans_generator(question, reasoning_path)
        return answer
            