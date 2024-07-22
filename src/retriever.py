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
    
    def entity_retrieval(self, mid, relation):
        results=[]
        
        endpoint_url = 'https://query.wikidata.org/sparql'
        sparql_query_1 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?tailEntity 
        WHERE {{
        wd:{mid} wdt:{relation} ?tailEntity .
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        sparql_query_2 = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?tailEntity 
        WHERE {{
        ?tailEntity wd:{mid} wdt:{relation} .
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
    
    def entity_set_retriever(self, relation_set):
        return 

    def relation_retriever(self, mid, x):
        result = []
        sparql_query_1 = """
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?relation WHERE {
        wd:mid ?relation ?x .
        }"""
        sparql_query_2 = """
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT ?relation WHERE {
        ?x ?relation wd:mid .
        }"""
        results_1 = self.query(sparql_query_1)
        results_2 = self.query(sparql_query_2)
        result.extend(results_1['results']['bindings'])
        result.extend(results_2['results']['bindings'])
        return result
    
    def relation_set_retriever(self, entity_set):
        return

# import requests

# class SPARQLQueryDispatcher:
#     def __init__(self, endpoint):
#         self.endpoint = endpoint

#     def query(self, sparql_query):
#         full_url = self.endpoint
#         headers = {
#             'Accept': 'application/sparql-results+json'
#         }
#         params = {
#             'query': sparql_query
#         }
        
#         response = requests.get(full_url, headers=headers, params=params)
#         response.raise_for_status()  # Raise an HTTPError for bad responses
#         return response.json()

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
#       wd:Q6279 wdt:P39 ?tailEntity .
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
#     endpoint_url = 'https://query.wikidata.org/sparql'
#     sparql_query = """
#     PREFIX wd: <http://www.wikidata.org/entity/>
#     PREFIX wdt: <http://www.wikidata.org/prop/direct/>
#     SELECT DISTINCT ?relation ?relationLabel
#     WHERE {
#       wd:Q6279 ?relation ?object .
#       FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
#       SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
#     }
#     LIMIT 10
#     """
    
#     query_dispatcher = SPARQLQueryDispatcher(endpoint_url)
#     results = query_dispatcher.query(sparql_query)

#     for result in results["results"]["bindings"]:
#         relation = result["relation"]["value"]
#         relation_label = query_dispatcher.get_property_label(relation)
#         print(f"Relation Label: {relation_label}")

# if __name__ == "__main__":
#     test_entity_retrieval()
#     test_relation_retrieval()



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
#       wd:Q6279 wdt:P39 ?tailEntity .
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
#     endpoint_url = 'https://query.wikidata.org/sparql'
#     sparql_query = """
#     PREFIX wd: <http://www.wikidata.org/entity/>
#     PREFIX wdt: <http://www.wikidata.org/prop/direct/>
#     SELECT DISTINCT ?relation ?relationLabel
#     WHERE {
#       wd:Q6279 ?relation ?object .
#       FILTER(STRSTARTS(STR(?relation), "http://www.wikidata.org/prop/direct/"))
#       SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
#     }
#     """
    
#     query_dispatcher = SPARQLQueryDispatcher(endpoint_url)
#     results = query_dispatcher.query(sparql_query)

#     for result in results["results"]["bindings"]:
#         relation = result["relation"]["value"]
#         relation_label = query_dispatcher.get_property_label(relation)
#         print(f"Relation Label: {relation_label}")

# if __name__ == "__main__":
#     test_entity_retrieval()
#     test_relation_retrieval()