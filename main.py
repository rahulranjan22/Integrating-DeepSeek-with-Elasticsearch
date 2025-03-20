import os
import pandas as pd
from elasticsearch import Elasticsearch, helpers
import requests
from dotenv import load_dotenv
import urllib3
import warnings

# Suppress Elasticsearch warnings
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Elasticsearch credentials
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")

# DeepSeek API credentials
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL")

# Load dataset
def load_dataset():
    df = pd.read_csv("data/top-rated-movies-from-tmdb.csv")
    print("Dataset loaded successfully!")
    return df

# Connect to Elasticsearch
def connect_elasticsearch():
    try:
        es = Elasticsearch(
            ELASTICSEARCH_URL,
            basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD),
            verify_certs=False,  # Disable SSL verification for simplicity
            timeout=30  # Increase timeout to 30 seconds
        )
        if es.ping():
            print("Connected to Elasticsearch!")
        else:
            raise Exception("Failed to connect to Elasticsearch.")
        return es
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        raise

# Create Elasticsearch index
def create_index(es, index_name):
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)  # Delete the existing index
            print(f"Index '{index_name}' deleted.")
        
        mapping = {
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "overview": {"type": "text"},
                    "release_date": {"type": "date"},
                    "popularity": {"type": "float"},
                    "vote_average": {"type": "float"},
                    "vote_count": {"type": "integer"}
                }
            }
        }
        es.indices.create(index=index_name, body=mapping)
        print(f"Index '{index_name}' created.")
    except Exception as e:
        print(f"Error creating Elasticsearch index: {e}")
        raise

# Index data into Elasticsearch using bulk API
def index_data(es, index_name, df):
    total_rows = len(df)
    print(f"Total rows to index: {total_rows}")

    actions = []
    for index, row in df.iterrows():
        try:
            # Validate and clean data
            release_date = row.get("release_date")
            if not release_date or not isinstance(release_date, str):
                release_date = "1970-01-01"  # Default value for invalid dates

            doc = {
                "title": row.get("original_title", "Unknown Title"),
                "overview": row.get("overview", ""),
                "release_date": release_date,
                "popularity": float(row.get("popularity", 0.0)),
                "vote_average": float(row.get("vote_average", 0.0)),
                "vote_count": int(row.get("vote_count", 0))
            }
            action = {
                "_index": index_name,
                "_id": row["id"],  # Use the 'id' column as the document ID
                "_source": doc
            }
            actions.append(action)

            # Send batches of 100 documents
            if len(actions) >= 100:
                helpers.bulk(es, actions)
                actions = []  # Clear the batch
                print(f"Indexed {index + 1}/{total_rows} rows...")
        except Exception as e:
            print(f"Error indexing row {index}: {e}")
            print(f"Problematic row data: {row}")  # Log the problematic row
            continue

    # Index any remaining documents
    if actions:
        try:
            helpers.bulk(es, actions)
            print(f"Indexed {total_rows}/{total_rows} rows...")
        except Exception as e:
            print(f"Error indexing final batch: {e}")

    print("Data indexed successfully!")

# Generate search query using DeepSeek API
def generate_search_query(user_input):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": f"Generate a search query for: {user_input}",
        "max_tokens": 50
    }
    try:
        print(f"Sending request to DeepSeek API: {DEEPSEEK_API_URL}")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        else:
            print(f"DeepSeek API returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            return user_input  # Fallback to the original input
    except Exception as e:
        print(f"Failed to generate search query using DeepSeek API: {e}")
        return user_input  # Fallback to the original input

# Search movies in Elasticsearch
def search_movies(es, index_name, query):
    try:
        response = es.search(index=index_name, body=query)
        results = []

        for hit in response["hits"]["hits"]:
            results.append({
                "title": hit["_source"]["title"],
                "overview": hit["_source"]["overview"],
                "release_date": hit["_source"]["release_date"],
                "popularity": hit["_source"]["popularity"],
                "vote_average": hit["_source"]["vote_average"],
                "vote_count": hit["_source"]["vote_count"]
            })

        return results
    except Exception as e:
        print(f"Error searching movies: {e}")
        return []

# Main function
def main():
    # Load dataset
    df = load_dataset()

    # Connect to Elasticsearch
    es = connect_elasticsearch()

    # Create index and index data
    index_name = "imdb_movies"
    create_index(es, index_name)
    index_data(es, index_name, df)

    # Example search
    user_input = "Find action movies with high ratings"
    query = {
        "query": {
            "multi_match": {
                "query": user_input,
                "fields": ["title", "overview"],
                "fuzziness": "AUTO"
            }
        },
        "size": 20  # Fetch 20 results
    }
    results = search_movies(es, index_name, query)

    # Display results
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"Title: {result['title']}")
        print(f"Overview: {result['overview']}")
        print(f"Release Date: {result['release_date']}")
        print(f"Popularity: {result['popularity']}")
        print(f"Vote Average: {result['vote_average']}")
        print(f"Vote Count: {result['vote_count']}")
        print("-" * 40)

if __name__ == "__main__":
    main()