import requests

# TMDb API Key (Get yours from https://developer.themoviedb.org/)
TMDB_API_KEY = "0e8066a21ffbca4c9ab24e0dd7fd71ab"

# Function to fetch movie details from TMDb
def get_movie_details(movie_name):
    """Fetch movie details from TMDb"""
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    response = requests.get(search_url)

    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            movie = results[0]  # Take the first result
            return {
                "title": movie["title"],
                "year": movie["release_date"].split("-")[0] if "release_date" in movie else "N/A",
                "rating": round(movie.get("vote_average", 0), 1),
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None  # Return None if movie not found

# Function to generate M3U playlist
def generate_m3u(movie_name, m3u_link):
    """Generates an M3U entry for a given movie"""
    movie_details = get_movie_details(movie_name)

    if movie_details:
        m3u_content = "#EXTM3U\n"

        m3u_content += f'#EXTINF:-1 tvg-logo="{movie_details["poster_url"]}" group-title="Movies", {movie_details["title"]} ({movie_details["year"]}) - IMDb {movie_details["rating"]}\n'
        m3u_content += f"{m3u_link}\n"

        with open("movies.m3u", "a", encoding="utf-8") as file:  # Append mode to add new movies
            file.write(m3u_content)

        print(f"✅ {movie_details['title']} added to movies.m3u!")
    else:
        print(f"❌ Movie '{movie_name}' not found on TMDb.")

# Example usage: Just input the movie name and M3U link
movie_name = input("Enter movie name: ")
m3u_link = input("Enter M3U link: ")

generate_m3u(movie_name, m3u_link)
