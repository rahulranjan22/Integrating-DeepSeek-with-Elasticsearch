import streamlit as st
from main import connect_elasticsearch, search_movies, generate_search_query

# Custom CSS for styling
st.markdown("""
    <style>
    .stButton button {
        background-color: #4CAF50;
        color: white;
        font-size: 16px;
        padding: 10px 24px;
        border-radius: 8px;
        border: none;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .stTextInput input {
        font-size: 16px;
        padding: 10px;
    }
    .stMarkdown h1 {
        color: #4CAF50;
    }
    .stMarkdown h2 {
        color: #2E86C1;
    }
    </style>
""", unsafe_allow_html=True)

# Streamlit UI
st.title("🎬 IMDb Movie Search")
st.markdown("""
    **Search for your favorite movies using Elasticsearch and DeepSeek!**  
    Enter a custom question, apply filters, and discover movies that match your preferences.
""")

# Connect to Elasticsearch
es = connect_elasticsearch()

# Initialize search_clicked
search_clicked = False

# Create columns for layout
col1, col2 = st.columns([3, 1])

# Search bar in the first column
with col1:
    user_input = st.text_input("Enter your custom question:", "Find action movies with high ratings")

# Search button in the second column
with col2:
    st.write("")  # Add space for alignment
    if st.button("🔍 Search"):
        search_clicked = True

# Sidebar for filters
with st.sidebar:
    st.title("🔍 Filters")
    release_year = st.slider("Release Year", 1900, 2023, (2000, 2023))
    min_popularity = st.slider("Minimum Popularity", 0.0, 100.0, 0.0)
    min_vote_average = st.slider("Minimum Vote Average", 0.0, 10.0, 6.0)
    size = st.slider("Number of results to display:", 1, 50, 10)

# Perform search
if search_clicked:
    # Generate a search query using DeepSeek API
    search_query = generate_search_query(user_input)
    st.write(f"Generated search query: {search_query}")

    # Build the Elasticsearch query with filters
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": search_query,
                            "fields": ["title", "overview"],
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "release_date": {
                                "gte": f"{release_year[0]}-01-01",
                                "lte": f"{release_year[1]}-12-31"
                            }
                        }
                    },
                    {
                        "range": {
                            "popularity": {
                                "gte": min_popularity
                            }
                        }
                    },
                    {
                        "range": {
                            "vote_average": {
                                "gte": min_vote_average
                            }
                        }
                    }
                ]
            }
        },
        "size": size
    }

    # Perform the search
    results = search_movies(es, "imdb_movies", query)
    st.markdown("---")
    st.subheader("🎥 Search Results")
    st.write(f"Found {len(results)} results:")

    # Display results in a grid layout
    for result in results:
        with st.container():
            col1, col2 = st.columns([1, 3])

            # Poster image (placeholder)
            with col1:
                st.image("https://via.placeholder.com/150", caption=result["title"])

            # Movie details
            with col2:
                st.subheader(result["title"])
                st.write(f"**Release Date:** {result['release_date']}")
                st.write(f"**Popularity:** {result['popularity']}")
                st.write(f"**Vote Average:** {result['vote_average']}")
                st.write(f"**Vote Count:** {result['vote_count']}")
                st.write(f"**Overview:** {result['overview']}")
                st.markdown("---")

# Footer
st.markdown("---")
st.markdown("""
    **Built using Streamlit, Elasticsearch, and DeepSeek.**  
    [GitHub Repository](https://github.com/rahulranjan22/Integrating-DeepSeek-with-Elasticsearch) 
    [Website](https://rahulranjan.org)
""")