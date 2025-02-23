import requests

# TMDb API Key (Get yours from https://developer.themoviedb.org/)
TMDB_API_KEY = "0e8066a21ffbca4c9ab24e0dd7fd71ab"

# TMDb API base URL
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Function to fetch movie or TV show details from TMDb
def fetch_from_tmdb(query, content_type="movie"):
    """Fetch details for a movie or TV show from TMDb"""
    search_url = f"{TMDB_BASE_URL}/search/{content_type}?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(search_url)

    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            item = results[0]  # Take the first result
            return {
                "id": item["id"],
                "title": item["title"] if content_type == "movie" else item["name"],
                "year": item.get("release_date", item.get("first_air_date", "N/A")).split("-")[0] if item.get("release_date") or item.get("first_air_date") else "N/A",
                "rating": round(item.get("vote_average", 0), 1),
                "poster_url": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None  # Return None if not found

# Function to format a movie or TV show entry
def format_m3u_entry(details, m3u_link, content_type="movie", season=None, episode=None):
    """Formats an M3U entry for a movie or TV show episode"""
    title = details["title"]
    year = details["year"]
    rating = details["rating"]
    poster_url = details["poster_url"]

    if content_type == "tv":
        title_display = f"{title} - S{season:02}E{episode:02}" if season and episode else title
        return f"# {title_display} ({year})\n" \
               f'#EXTINF:-1 tvg-logo="{poster_url}" group-title="{title}", {title_display} - IMDb {rating}\n' \
               f"{m3u_link}\n"
    else:
        return f"# {title} ({year})\n" \
               f'#EXTINF:-1 tvg-logo="{poster_url}" group-title="Movies", {title} ({year}) - IMDb {rating}\n' \
               f"{m3u_link}\n"

# Function to update M3U file
def update_m3u_file(new_entry, content_type="movie", show_title=None):
    """Updates the M3U file by adding movies at the top and TV shows grouped at the bottom"""
    try:
        with open("Movies-playlist.m3u", "r", encoding="utf-8") as file:
            existing_content = file.readlines()
    except FileNotFoundError:
        existing_content = ["#EXTM3U\n"]

    # Ensure the M3U header stays at the top
    if "#EXTM3U\n" not in existing_content[0]:
        existing_content.insert(0, "#EXTM3U\n")

    # Separate movies and TV shows
    movie_entries = []
    tv_show_entries = []
    tv_shows = {}  # Dictionary to store TV show groups
    is_tv_section = False

    for line in existing_content:
        if "group-title=" in line and "Movies" not in line:
            is_tv_section = True
        
        if is_tv_section:
            show_name = line.split('group-title="')[1].split('"')[0] if 'group-title="' in line else None
            if show_name:
                if show_name not in tv_shows:
                    tv_shows[show_name] = []
                tv_shows[show_name].append(line)
            else:
                if tv_shows:
                    last_show = list(tv_shows.keys())[-1]
                    tv_shows[last_show].append(line)
                else:
                    tv_show_entries.append(line)
        else:
            movie_entries.append(line)

    # Insert the new entry
    if content_type == "movie":
        movie_entries.append(new_entry)  # Add movies to the top
    else:
        if show_title in tv_shows:
            tv_shows[show_title].append(new_entry)  # Append to existing show group
        else:
            if tv_shows:
                tv_show_entries.append("\n")  # Add space before new show group
            tv_shows[show_title] = [new_entry]

    # Reconstruct the file with separated movies and grouped TV shows
    with open("Movies-playlist.m3u", "w", encoding="utf-8") as file:
        file.writelines(movie_entries)
        for show, entries in tv_shows.items():
            file.writelines(entries)
        file.writelines(tv_show_entries)

    print(f"✅ {new_entry.splitlines()[1]} added to the {'TOP' if content_type == 'movie' else 'BOTTOM'} of Movies-playlist.m3u!")

# Main loop to add multiple movies or TV shows
while True:
    content_type = input("Enter type (movie/tv) or 'exit' to stop: ").strip().lower()
    if content_type == "exit":
        break
    if content_type not in ["movie", "tv"]:
        print("⚠️ Invalid type! Please enter 'movie' or 'tv'.")
        continue

    content_name = input("Enter name of the movie/TV show: ").strip()
    details = fetch_from_tmdb(content_name, content_type)

    if not details:
        print(f"❌ '{content_name}' not found on TMDb.")
        continue

    if content_type == "tv":
        season = input("Enter season number: ").strip()
        episode = input("Enter episode number: ").strip()
        if not season.isdigit() or not episode.isdigit():
            print("⚠️ Invalid season/episode! Please enter numeric values.")
            continue
        season = int(season)
        episode = int(episode)

    m3u_link = input("Enter M3U link: ").strip()
    
    new_entry = format_m3u_entry(details, m3u_link, content_type, season, episode)
    update_m3u_file(new_entry, content_type, details["title"] if content_type == "tv" else None)

print("🎬 All entries have been added successfully!")
