INDEX_SETTINGS: dict = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
        "tokenizer": {
            "edge_ngram_tokenizer": {
                "type": "edge_ngram",
                "min_gram": 2,
                "max_gram": 20,
                "token_chars": ["letter", "digit"],
            }
        },
        "analyzer": {
            "search_text_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding"],
            },
            "search_text_edge_analyzer": {
                "type": "custom",
                "tokenizer": "edge_ngram_tokenizer",
                "filter": ["lowercase", "asciifolding"],
            },
        },
    },
}

INDEX_MAPPINGS: dict = {
    "properties": {
        "id": {"type": "keyword"},
        "type": {"type": "keyword"},
        "display": {
            "type": "text",
            "analyzer": "search_text_analyzer",
            "fields": {"keyword": {"type": "keyword"}},
        },
        "searchable_text": {
            "type": "text",
            "analyzer": "search_text_analyzer",
            "fields": {
                "edge": {
                    "type": "text",
                    "analyzer": "search_text_edge_analyzer",
                    "search_analyzer": "search_text_analyzer",
                }
            },
        },
        "iata": {"type": "keyword"},
        "icao": {"type": "keyword"},
        "name": {"type": "text", "analyzer": "search_text_analyzer"},
        "city": {"type": "text", "analyzer": "search_text_analyzer"},
        "country": {"type": "keyword"},
        "airline": {"type": "keyword"},
        "iata_flight": {"type": "keyword"},
        "icao_flight": {"type": "keyword"},
        "flight_number": {"type": "keyword"},
        "airport_code": {"type": "keyword"},
        "gate": {"type": "keyword"},
        "aliases": {"type": "text", "analyzer": "search_text_analyzer"},
        "metadata": {"type": "object", "enabled": True},
    }
}
