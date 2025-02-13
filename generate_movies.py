import requests

# TMDb API Key (Get yours from https://developer.themoviedb.org/)
TMDB_API_KEY = "0e8066a21ffbca4c9ab24e0dd7fd71ab"

# Base URL for streaming (Modify this if needed)
STREAM_BASE_URL = "https://111movies.com/movie/"

# Function to get popular movies from TMDb
def get_popular_movies():
    """Fetches popular movies from TMDb API"""
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print("Error fetching movies:", response.status_code)
        return []

# Function to generate M3U playlist
def generate_m3u(movies):
    """Generates an M3U playlist from TMDb movie data"""
    m3u_content = "#EXTM3U\n"

    for movie in movies:
        movie_id = movie["id"]
        title = movie["title"]
        year = movie["release_date"].split("-")[0]
        rating = movie["vote_average"]
        poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
        stream_url = f"{STREAM_BASE_URL}{movie_id}"

        m3u_content += f'#EXTINF:-1 tvg-logo="{poster_url}" group-title="Movies", {title} ({year}) - IMDb {rating}\n'
        m3u_content += f"{stream_url}\n"

    with open("movies.m3u", "w", encoding="utf-8") as file:
        file.write(m3u_content)

    print("✅ Updated movies.m3u file generated!")

# Run the script
movies = get_popular_movies()
generate_m3u(movies)
