import torch
import logging
from retriever import * 
from prompt_list import *
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import time
import re
from langchain_community.llms import LlamaCpp

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

reasoning_temperature=0.0
exploration_temperature = 0.4

class BasicGenerator:
    def __init__(self, args):
        model_info = '/home/shkim/ToG-implement/llama_model/Llama-2-70B-chat-hf-Q8_0.gguf'
        # logger.info(f"Loading model from {model_info}")
        
        # Using huggingface model
        # self.tokenizer = AutoTokenizer.from_pretrained(model_info)
        # self.model_config = AutoConfig.from_pretrained(model_info)
        # self.model = AutoModelForCausalLM.from_pretrained(
        #     model_info, 
        #     device_map="auto", 
        #     torch_dtype=torch.float32 
        #     ) 
        # if self.model_config.model_type == "llama":
        #     self.space_token = "_"
        # else:
        #     self.space_token = self.tokenizer.tokenize(' ')[0]
        self.model = LlamaCpp(
            model_path=model_info,
            max_tokens=2000,
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose = True)
            
    def generate(self, input_text, max_length, temperature):
        # print("----------llm generate----------")
        # input_ids = self.tokenizer.encode(input_text, return_tensors="pt")
        # input_ids = input_ids.to(self.model.device)
        # input_length = input_ids.shape[1]
        # outputs = self.model.generate(
        #         input_ids = input_ids, 
        #         max_new_tokens = max_length,
        #         temperature = temperature

        response = self.model.invoke(
                 input_text,
                 max_tokens=256,
                 echo=True,
                 temperature=temperature)
        print("\n\nllama generate: ", response)
        return response
    

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
    
    # # util function from tog github code 
    # def get_entity_with_score(string, entity_num):
    #     scores = re.findall(r'\d+\.\d+', string)
    #     scores = [float(number) for number in scores]
    #     if len(scores) == entity_num
    #         return scores
    #     else:
    #         print("All entities are created equal.")
    #         return [1/entity_num] * entity_num
    
    def entity_scoring_by_llm(self, question, relation, tail_entities):
        tail_entities_name = []
        for entity in tail_entities:
            tail_entities_name.append(entity['name'])
        relation_name = relation['name']
        prompt = score_entity_candidates_prompt_wiki.format(question, relation_name) + "; ".join(tail_entities_name) + '\nScore: '
        # print("llm prompt for entity scoring:\n", prompt)
        # print("------llm entity scoring------")
        llm_result = self.generate(prompt, self.generate_max_length, exploration_temperature)
        # print("llm entity scoring result: ", llm_result)
        scores = re.findall(r'\d+\.\d+', llm_result)
        scores = [float(number) for number in scores]
        if len(scores) > len(tail_entities): # llm output이 이상하여서 여기서 score를 찾기 힘듬. 
            scores = scores[:len(tail_entities)]
        for i, tail_entity in enumerate(tail_entities):
            # print("tail entity score update: ")
            tail_entity['score'] = scores[i]
        # print(tail_entities)

    def top_N_triples(self, entity_candidates_set):
        all_triples = []
        # all possibiel triples
        for candidate in entity_candidates_set:
            entity = candidate['entity']
            relation = candidate['relation']
            tail_entities = candidate['tail_entities']
            if tail_entities:
                for tail_entity in tail_entities:
                    triple = {
                        'entity': entity,
                        'relation': relation,
                        'tail_entity': tail_entity
                    }
                    all_triples.append(triple)
        sorted_triples = sorted(all_triples, key=lambda x: x['tail_entity']['score'], reverse=True)
        print("\n--------sorted triples---------\n", sorted_triples)
        for triple in sorted_triples:
            print(f"Entity: {triple['entity']}, Relation: {triple['relation']}, Tail Entity: {triple['tail_entity']}")
        # 상위 N개의 triple 선택
        top_N_triples = sorted_triples[:self.N]

        return top_N_triples
    
    def entity_prune(self, question, set):
        entity_candidates_set = set
        for elem in entity_candidates_set:
            relation = elem['relation']
            tail_entities = elem['tail_entities']
            if tail_entities:
                pruned_entities = self.entity_scoring_by_llm(question, relation, tail_entities)
                elem['tail_entities'] = pruned_entities
            print("\n\nscored entity: ", pruned_entities)
        top_N_triples = self.top_N_triples(entity_candidates_set)
        # sorting all triple
        # truncate by self.N
        return top_N_triples
    
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
                relation = relation.replace("wiki.relation.", "").replace("_", " ")
                relation_id = relation_dict[relation]
                relations.append({'id': relation_id, 'name': relation, 'score': score})
        if not relations:
            return "No relations found"
        return relations

    
    def relation_pruning_by_llm(self, question, entity, relations):
        formatted_relations = []
        for relation in relations:
            formatted_name = "wiki.relation." + relation['name'].replace(" ", "_")
            formatted_relation = {'id': relation['id'], 'name': formatted_name}
            formatted_relations.append(formatted_relation)
        prompt = extract_relation_prompt_wiki % (self.N, self.N)+question+'\nTopic Entity: '+entity+ '\nRelations:\n'+'\n'.join([f"{i}. {item['name']}" for i, item in enumerate(formatted_relations, start=1)])+'\nA:'
        # print("prompt: ", prompt)
        llm_result = self.generate(prompt, self.generate_max_length, exploration_temperature)
        # print("llm result: ", llm_result)
        pruned_relations = self.get_pruned_relations(llm_result, relations)
        # print("pruned_relations: ", pruned_relations)
        # add relation id 
        return pruned_relations
        
        
    def relation_prune(self, question, set):
        relation_candidates_set = set
        # print("relation_candidates_set: ", relation_candidates_set)
        for elem in relation_candidates_set:
            entity = elem['entity']
            entity_name = entity['name']
            relations = elem['relations']
            pruned_relation = self.relation_pruning_by_llm(question, entity_name, relations)
            elem['relations'] = pruned_relation
        return relation_candidates_set
        
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
                retrieve = retriever.entity_set_retriever(set)
            elif type == 'relation':
                retrieve = retriever.relation_set_retriever(set)
            else:
                NotImplementedError
        elif retriever_name == "freebase":
            NotImplementedError
        return retrieve
    
    # util function from paper code 
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
        explored_relation_chains = '\n'.join([f"{triple['Entity']['name']}, {triple['Relation']['name']}, {triple['Tail Entity']['name']}" for triple in reasoning_path])
        # chain_prompt = '\n'.join([', '.join([str(x) for x in chain]) for sublist in reasoning_path for chain in sublist])
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
        topic_entity = self.initializer(question, topic_entity, self.N)
        print("\nquesiton: ", question)
        print("\nTopic entity: ", topic_entity)
        reasoning_path = []
        depth= 0
        while depth <= self.D_max:
            R_cand = self.retriever(self.knowledge_base, question, topic_entity, "relation")
            print("\n\n------Relation retrieve------\nR_cand: ", R_cand)
            R = self.prune(question, R_cand, "relation")
            print("\n\n------Relation pruning------\npruned R: ", R)
            E_cand = self.retriever(self.knowledge_base, question, R, "entity")
            E_cand=[{'entity': {'id': 'Q20640708', 'name': 'Sarah J. Maas'}, 'relation': {'id': 'P21', 'name': 'sex or gender', 'score': 0.4}, 'tail_entities': [{'id': 'Q6581072', 'name': 'female'}]}, {'entity': {'id': 'Q20640708', 'name': 'Sarah J. Maas'}, 'relation': {'id': 'P19', 'name': 'place of birth', 'score': 0.3}, 'tail_entities': [{'id': 'Q60', 'name': 'New York City'}]}, {'entity': {'id': 'Q20640708', 'name': 'Sarah J. Maas'}, 'relation': {'id': 'P27', 'name': 'country of citizenship', 'score': 0.2}, 'tail_entities': [{'id': 'Q30', 'name': 'United States of America'}]}]
            print("\n\n------Entity retrieve------\nE_cand: ", E_cand)
            top_N_triples = self.prune(question, E_cand, "entity")
            print("\n\n------Top N triples------\ntriples: ", top_N_triples)
            break
            # print("\n\n------Entity pruning------\nE: ", top_N_triples)
            # reasoning_path.append(top_N_triples)
            # if self.reasoning(question, reasoning_path):
            #      break
            # depth += 1
            
            new_topic_entity = []
            for triple in top_N_triples:
                tail_entity = triple['tail_entity']
                new_topic_entity.append({'id': tail_entity['id'], 'name': tail_entity['name']})
            topic_entity = new_topic_entity
        # answer = self.final_ans_generator(question, reasoning_path)
        answer = ''
        return answer
            