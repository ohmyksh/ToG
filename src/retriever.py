from SPARQLWrapper import SPARQLWrapper, JSON

class SPARQLQueryDispatcher:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def query(self, sparql_query):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        sparql.addParameter('query', sparql_query)
        sparql.addCustomHttpHeader('User-Agent', 'CoolBot/0.0 (https://example.org/coolbot/; coolbot@example.org)')
        response = sparql.query().convert()
        return response
    
    def get_id(self, entity_set):
        entity_ids = []
        for entity_name in entity_set:
            sparql_query = f"""
            SELECT ?entity ?entityLabel WHERE {{
            ?entity rdfs:label "{entity_name}"@en.
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}
            """
            response = self.query(sparql_query)
            results = response.get('results', {}).get('bindings', [])
            if results:
                entity_url = results[0]['entity']['value']
                entity_id = entity_url.split('/')[-1]
                entity_ids.append(entity_id)
                # print("entity_name: ", entity_name, "id: ", "entity_id")
            else: 
                # print("entity_name: ", entity_name, "no id") 
                NotImplementedError
        return entity_ids
        
    def get_property_label(self, property_uri):
        property_id = property_uri.split('/')[-1]
        sparql_query = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?propertyLabel WHERE {{
          wd:{property_id} rdfs:label ?propertyLabel .
          FILTER(LANG(?propertyLabel) = "en")
        }}
        LIMIT 1
        """
        results = self.query(sparql_query)
        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["propertyLabel"]["value"]
        return "No label"


class WikidataRetriever(SPARQLQueryDispatcher):
    def __init__(self):
        super().__init__('https://query.wikidata.org/sparql')
    
    def entity_retrieval(self, entity, relation):
        results=[]
        endpoint_url = 'https://query.wikidata.org/sparql'
        sparql_query_1 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?tailEntity ?tailEntityLabel
        WHERE {{
        wd:{entity} wdt:{relation} ?tailEntity .
        FILTER(STRSTARTS(STR(?tailEntity), "http://www.wikidata.org/entity/Q"))
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        sparql_query_2 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?tailEntity 
        WHERE {{
        ?tailEntity wd:{entity} wdt:{relation} .
        FILTER(STRSTARTS(STR(?tailEntity), "http://www.wikidata.org/entity/Q"))
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        results_1 = self.query(sparql_query_1)
        results_2 = self.query(sparql_query_2)
        results.extend(results_1['results']['bindings'])
        results.extend(results_2['results']['bindings'])
        # results.append(results_1)
        # results.append(results_2)
        
        for result in results:
            tail_entity = result["tailEntity"]["value"]
            tail_entity_label = result["tailEntityLabel"]["value"]
            print(f"{tail_entity_label} (URI: {tail_entity})")
    
    def entity_set_retriever(self, candidate_relation_set, reasoning_path):
        for entity_relation_pairs in candidate_relation_set:
            entity = entity_relation_pairs['entity']
            for relation in entity_relation_pairs['relations']:
                relation_id = relation['id']
                self.entity_retrieval(entity, relation_id)

    def relation_retriever(self, mid):
        relations = []
        # outcoming relation 
        sparql_query_1 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?relation 
        WHERE {{ wd:{mid} ?relation ?object .
        FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5
        """
        
        # incoming relation
        sparql_query_2 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?relation 
        WHERE {{ ?object ?relation wd:{mid} .
        FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5
        """
        results = []
        results_1 = self.query(sparql_query_1)
        results_2 = self.query(sparql_query_2)
        results.extend(results_1['results']['bindings'])
        results.extend(results_2['results']['bindings'])
        
        for result in results:
            relation = result["relation"]["value"]
            relation_id = relation.split('/')[-1]
            relation_label = self.get_property_label(relation)
            print({"id": relation_id, "label": relation_label})
            relation_info = {"id": relation_id, "label": relation_label}
            relations.append(relation_info)
        return relations
 
    def relation_set_retriever(self, entity_set, reasoning_path):
        all_relations = []
        for entity in entity_set:
            print(f"\n--- relation_retriever for {entity} ---\n")
            relations = self.relation_retriever(entity)
            all_relations.append({"entity": entity, "relations": relations})
        return all_relations

# Test code for Entity, Relation retriever
# if __name__ == "__main__":
#     retriever = WikidataRetriever()
#     entity_set = ["Q937", "Q42", "Q1"]  # Example entities: Albert Einstein, Douglas Adams, Universe
#     candidate_relation_set = retriever.relation_set_retriever(entity_set)

#     print("\n--- relation_set_retriever Output ---")
#     for entity_relations in candidate_relation_set:
#         entity = entity_relations['entity']
#         print(f"Entity: {entity}")
#         for relation in entity_relations["relations"]:
#             relation_id = relation['id']
#             relation_label = relation['label']
#             print(f"  Relation ID: {relation_id} - Label: {relation_label}")

#     print("\n--- entity_set_retriever Execution ---")
#     retriever.entity_set_retriever(candidate_relation_set)

# Test code for get_id function
# if __name__ == "__main__":
#     retriever = WikidataRetriever()
#     entities = ['Canberra', 'Australia', 'majority party']
#     result = retriever.get_id(entities)
#     print("Result:", result)
#
# output example:
    # entity_name:  Canberra id:  entity_id
    # entity_name:  Australia id:  entity_id
    # entity_name:  majority party no id
    # Result: ['Q3114', 'Q408']
