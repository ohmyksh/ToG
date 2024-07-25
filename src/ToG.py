import torch
import logging
from retriever import * 
from prompt_list import *
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import time
import re

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

reasoning_temperature=0.0
exploration_temperature = 0.4

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
    def generate(self, input_text, max_length, temperature):
        print("----------llm generate----------")
        input_ids = self.tokenizer.encode(input_text, return_tensors="pt")
        input_ids = input_ids.to(self.model.device)
        input_length = input_ids.shape[1]
        outputs = self.model.generate(
                input_ids = input_ids, 
                max_new_tokens = max_length,
                temperature = temperature
            )
        generated_tokens = outputs[:, input_length:]
        text = self.tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
        return text
    

class IO_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.io_prompt = io_prompt
    def inference(self, question, topic_entity=None, max_length=256):
        # prompt
        prompt = self.io_prompt + "\nQ: " + question + "\nA: "
        text = self.generate(prompt, max_length, reasoning_temperature) #generate max length
        return text
    
    
class CoT_prompt(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.cot_prompt = cot_prompt
        
    def inference(self, question, topic_entity=None, max_length=256):
        prompt = self.cot_prompt + "\nQ: " + question + "\nA: "
        text = self.generate(prompt, 256, reasoning_temperature)
        return text
    
    
class ToG(BasicGenerator):
    def __init__(self, args):
        super().__init__(args)
        self.topic_entites = []
        self.generate_max_length = args.generate_max_length
        self.N = args.beamsearch_width
        self.D_max = args.beamsearch_depth
        self.knowledge_base = args.knowledge_base
    
    def initializer(self, question, topic_entity, N):
        # extract top-N topic entites
        # convert entities to wikidata ids. 
        if topic_entity:
            self.topic_entites = [{'id': entity_id, 'name': name} for entity_id, name in topic_entity.items()]
            
        llm_topic_entity = []
        # prompt = f"""Please extract up to {N} topic entities (separated by semicolon) in question.\n
        # question: {question}"""
        # extracted_topic_entities = self.generate(prompt, self.generate_max_length, exploration_temperature)
        # extracted_topic_entities = [entity.strip() for entity in extracted_topic_entities.split(';')]
        
        # if self.knowledge_base  == "wikidata":
        #     retriever = WikidataRetriever()
        # elif self.knowledge_base  == "freebase":
        #     NotImplementedError
        # #llm_topic_entity = retriever.get_id(extracted_topic_entities)
        # if llm_topic_entity is not None:
        #     intersection_set = set(llm_topic_entity).intersection(set(prepared_topic_entity))
        #     self.topic_entites = list(intersection_set)
        # else: 
        #     self.topic_entites = prepared_topic_entity
            
        # self.topic_entites = retriever.get_id(self.topic_entites)
        
        return self.topic_entites
    
    # util function from tog github code 
    def get_entity_with_score(string, entity_candidates):
        scores = re.findall(r'\d+\.\d+', string)
        scores = [float(number) for number in scores]
        if len(scores) == len(entity_candidates):
            return scores
        else:
            print("All entities are created equal.")
            return [1/len(entity_candidates)] * len(entity_candidates)
    
    def entity_scoring_by_llm(self, question, entity_candidate_set):
        relation = '' # 구현 필요: entity_candidate_set에서 대응하는 relation 찾아서 리턴
        prompt = score_entity_candidates_prompt_wiki.format(question, relation) + "; ".join(entity_candidate_set) + '\nScore: '
        llm_result = self.generate(prompt, self.generate_max_length, exploration_temperature)
        print("llm entity scoring result: ", llm_result)
        pruned_entities_scores = self.get_entity_with_score(llm_result, entity_candidate_set)
        pruned_entities = [float(x) * score for x in pruned_entities_scores], # entity_candidates_set[], entity_candidates_id
        print("pruned_entities: ", pruned_entities)
        entity_with_score = []
        return entity_with_score
        
        
    def entity_prune(self, question, set):
        entity_candidates_set = set
        print("entity_candidates_set: ", entity_candidates_set)
        entity_candidates_with_score = self.entity_scoring_by_llm(question, entity_candidates_set)
        
        pruned_entities = []
    
    # code from tog
    def get_pruned_relations(self, string, relations):
        relation_dict = {rel['name']: rel['id'] for rel in relations}
        pattern = r"{\s*(?P<relation>[^()]+)\s+\(Score:\s+(?P<score>[0-9.]+)\)}"
        relations=[]
        for match in re.finditer(pattern, string):
            relation = match.group("relation").strip()
            score = match.group("score")
            if not relation or not score:
                return "output uncompleted.."
            try:
                score = float(score)
            except ValueError:
                return "Invalid score"
            if relation:
                relation_id = relation_dict[relation]
                relations.append({'id': relation_id, 'name': relation, 'score': score})
        if not relations:
            return "No relations found"
        return relations

    
    def relation_pruning_by_llm(self, question, entity, relations):
        prompt = extract_relation_prompt_wiki % (self.N, self.N)+question+'\nTopic Entity: '+entity+ '\nRelations:\n'+'\n'.join([f"{i}. {item['name']}" for i, item in enumerate(relations, start=1)])+'\nA:'
        # print("prompt: ", prompt)
        llm_result = self.generate(prompt, self.generate_max_length, exploration_temperature)
        print("llm result: ", llm_result)
        pruned_relations = self.get_pruned_relations(llm_result, relations)
        print("pruned_relations: ", pruned_relations)
        # add relation id 
        return pruned_relations
        
        
    def relation_prune(self, question, set):
        relation_candidates_set = set
        print("---------relation_prune function--------")
        # print("relation_candidates_set: ", relation_candidates_set)
        for elem in relation_candidates_set:
            entity = elem['entity']
            entity_name = entity['name']
            relations = elem['relations']
            pruned_relation = self.relation_pruning_by_llm(question, entity_name, relations)
            
        
    def prune(self, question, set, type):
        result = []
        
        if type == 'entity':
            result = self.entity_prune(question, set)
        elif type == 'relation':
            result = self.relation_prune(question, set)
        else:
            NotImplementedError

        return result
    
    def retriever(self, retriever_name, question, set, type):
        retrieve = []
        if retriever_name == "wikidata":
            retriever = WikidataRetriever()
            if type == 'entity':
                print("\n-------entity retriever start-------\n")
                retrieve = retriever.entity_set_retriever(question, set)
                print("\n-------entity retriever end-------\n")
            elif type == 'relation':
                print("\n-------relation retriever start-------\n")
                retrieve = retriever.relation_set_retriever(set)
                print("\n-------relation retriever end-------\n")
            else:
                NotImplementedError
        elif retriever_name == "freebase":
            NotImplementedError
        return retrieve
    
    def extract_answer(text):
        start_index = text.find("{")
        end_index = text.find("}")
        if start_index != -1 and end_index != -1:
            result = text[start_index+1:end_index].strip()
        else:
            result = ""
        if result.lower().strip().replace(" ","")=="yes": return True
        else: return False
    
    def reasoning(self, question, reasoning_path):
        prompt = prompt_evaluate_wiki + question
        explored_relation_chains = "" # reasoning path
        # chain_prompt = '\n'.join([', '.join([str(x) for x in chain]) for sublist in cluster_chain_of_entities for chain in sublist])
        prompt += "\nKnowledge Triplets: " + explored_relation_chains + 'A: '
        answer = self.generate(prompt, self.generate_max_length, reasoning_temperature)
        result = self.extract_answer(answer)
        return result
    
    def final_ans_generator(self, question, reasoning_path):
        prompt = answer_prompt_wiki + question
        # make knowledge triples 
        knowledge_triple = []
        explored_relation_chains = "" # reasoning path
        # chain_prompt = '\n'.join([', '.join([str(x) for x in chain]) for sublist in cluster_chain_of_entities for chain in sublist])
        prompt += "\nKnowledge Triplets: " + explored_relation_chains + 'A: '
        answer = self.generate(prompt, self.generate_max_length, reasoning_temperature)
        return answer
    
    def inference(self, question, topic_entity):
        text = ""
        E = self.initializer(question, topic_entity, self.N)
        print("quesiton: ", question)
        print("Topic entity: ", E)
        reasoning_path = []
        depth= 0
        while depth <= self.D_max:
            R_cand = self.retriever(self.knowledge_base, question, E, "relation")
            print("R_cand: ", R_cand)
            R = self.prune(question, R_cand, "relation")
            E_cand = self.retriever(self.knowledge_base, question, R, "entity")
            # E, top_n_triples = self.prune(question, E_cand, "entity")
            # reasoning_path.append(top_n_triples)
            # if self.reasoning(question, reasoning_path):
            #     break
            
        #     depth += 1
        # answer = self.final_ans_generator(question, reasoning_path)
        answer = ''
        return answer
            