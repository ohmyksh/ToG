import requests
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
        SELECT ?tailEntity 
        WHERE {{
        wd:{entity} wdt:{relation} ?tailEntity .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        sparql_query_2 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?tailEntity 
        WHERE {{
        ?tailEntity wd:{entity} wdt:{relation} .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        results_1 = self.query(sparql_query_1)
        results_2 = self.query(sparql_query_2)
        results.append(results_1)
        results.append(results_2)
        
        for result in results["results"]["bindings"]:
            tail_entity = result["tailEntity"]["value"]
            tail_entity_label = result["tailEntityLabel"]["value"]
            print(f"{tail_entity_label} (URI: {tail_entity})")
            
    
    def entity_set_retriever(self, candidate_relation_set):
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
        }}"""
        
        # incoming relation
        sparql_query_2 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?relation 
        WHERE {{ ?object ?relation wd:{mid} .
        FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}"""
        results = []
        results_1 = self.query(sparql_query_1)
        results_2 = self.query(sparql_query_2)
        results.extend(results_1['results']['bindings'])
        results.extend(results_2['results']['bindings'])
        
        for result in results["results"]["bindings"]:
            relation = result["relation"]["value"]
            relation_id = relation.split('/')[-1]
            relation_label = self.get_property_label(relation)
            print({"id": relation_id, "label": relation_label})
            relations.append({"id": relation_id, "label": relation_label})
        return relations
 
    def relation_set_retriever(self, entity_set):
        all_relations = []
        for entity in entity_set:
            relations = self.relation_retriever(entity)
            all_relations.append({"entity": {entity}, "relations": relations})
        return all_relations
    
# # Test code
# from SPARQLWrapper import SPARQLWrapper, JSON

# class SPARQLQueryDispatcher:
#     def __init__(self, endpoint):
#         self.endpoint = endpoint

#     def query(self, sparql_query):
#         sparql = SPARQLWrapper(self.endpoint)
#         sparql.setQuery(sparql_query)
#         sparql.setReturnFormat(JSON)
#         sparql.addParameter('query', sparql_query)
#         sparql.addCustomHttpHeader('User-Agent', 'CoolBot/0.0 (https://example.org/coolbot/; coolbot@example.org)')
#         response = sparql.query().convert()
#         return response

#     def get_property_label(self, property_uri):
#         property_id = property_uri.split('/')[-1]
#         sparql_query = f"""
#         PREFIX wd: <http://www.wikidata.org/entity/>
#         PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
#         SELECT ?propertyLabel WHERE {{
#           wd:{property_id} rdfs:label ?propertyLabel .
#           FILTER(LANG(?propertyLabel) = "en")
#         }}
#         LIMIT 1
#         """
#         results = self.query(sparql_query)
#         if results["results"]["bindings"]:
#             return results["results"]["bindings"][0]["propertyLabel"]["value"]
#         return "No label"

# def test_entity_retrieval():
#     endpoint_url = 'https://query.wikidata.org/sparql'
#     sparql_query = """
#     PREFIX wd: <http://www.wikidata.org/entity/>
#     PREFIX wdt: <http://www.wikidata.org/prop/direct/>
#     SELECT ?tailEntity ?tailEntityLabel
#     WHERE {
#       wd:Q937 wdt:P39 ?tailEntity .
#       SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
#     }
#     """
    
#     query_dispatcher = SPARQLQueryDispatcher(endpoint_url)
#     results = query_dispatcher.query(sparql_query)

#     print("Tail Entities:")
#     for result in results["results"]["bindings"]:
#         tail_entity = result["tailEntity"]["value"]
#         tail_entity_label = result["tailEntityLabel"]["value"]
#         print(f"{tail_entity_label}")

# def test_relation_retrieval():
#     relations=[]
#     endpoint_url = 'https://query.wikidata.org/sparql'
#     sparql_query = """
#     PREFIX wd: <http://www.wikidata.org/entity/>
#     PREFIX wdt: <http://www.wikidata.org/prop/direct/>
#     SELECT DISTINCT ?relation ?relationLabel
#     WHERE {
#       wd:Q937 ?relation ?object .
#       FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
#       SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
#     }
#     LIMIT 5
#     """
    
#     query_dispatcher = SPARQLQueryDispatcher(endpoint_url)
#     results = query_dispatcher.query(sparql_query)

#     for result in results["results"]["bindings"]:
#         relation = result["relation"]["value"]
#         relation_id = relation.split('/')[-1]
#         relation_label = query_dispatcher.get_property_label(relation)
#         print({"id": relation_id, "label": relation_label})
#         relations.append({"id": relation_id, "label": relation_label})
#     return relations

# if __name__ == "__main__":
#     test_entity_retrieval()
#     test_relation_retrieval()