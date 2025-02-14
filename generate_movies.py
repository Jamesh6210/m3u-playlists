import requests

# TMDb API Key (Get yours from https://developer.themoviedb.org/)
TMDB_API_KEY = "0e8066a21ffbca4c9ab24e0dd7fd71ab"

# Movies111 Base URL
MOVIES111_URL = "https://111movies.com/movie/"

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
                "id": movie["id"],  # TMDb Movie ID
                "title": movie["title"],
                "year": movie["release_date"].split("-")[0] if "release_date" in movie else "N/A",
                "rating": round(movie.get("vote_average", 0), 1),
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None  # Return None if movie not found

# Function to insert a new movie at the top of the M3U file with Movies111 details
def add_movie_to_top(movie_name, m3u_link):
    """Adds a new movie at the top of the M3U file with Movies111 details link"""
    movie_details = get_movie_details(movie_name)

    if movie_details:
        # Generate the Movies111 details link
        details_url = f"{MOVIES111_URL}{movie_details['id']}"

        # Create the M3U entry
        new_entry = f"# {movie_details['title']} ({movie_details['year']})\n"
        new_entry += f'#EXTINF:-1 tvg-id="{details_url}" tvg-logo="{movie_details["poster_url"]}" group-title="Movies", {movie_details["title"]} ({movie_details["year"]}) - IMDb {movie_details["rating"]}\n'
        new_entry += f"{m3u_link}\n\n"  # Double newline for spacing

        # Read existing content
        try:
            with open("movies.m3u", "r", encoding="utf-8") as file:
                existing_content = file.read()
        except FileNotFoundError:
            existing_content = ""

        # Write new content (new movie first, then existing content)
        with open("movies.m3u", "w", encoding="utf-8") as file:
            file.write("#EXTM3U\n")  # Ensure #EXTM3U stays at the top
            file.write(new_entry)
            file.write(existing_content.replace("#EXTM3U\n", "", 1))  # Remove duplicate #EXTM3U

        print(f"✅ {movie_details['title']} added to the TOP of movies.m3u!")
    else:
        print(f"❌ Movie '{movie_name}' not found on TMDb.")

# Loop to add multiple movies
while True:
    movie_name = input("Enter movie name (or 'exit' to stop): ")
    if movie_name.lower() == "exit":
        break
    m3u_link = input("Enter M3U link: ")
    add_movie_to_top(movie_name, m3u_link)

print("🎬 All movies have been added successfully!")
