import discord
import requests
import os
import git
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
M3U_FILE = "Movies-playlist.m3u"
GITHUB_REPO_PATH = os.getenv("GITHUB_REPO_PATH")  # Path to your cloned GitHub repo
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub Personal Access Token

# Initialize bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Function to fetch movie/TV show details from TMDb
def get_tmdb_details(title, is_tv=False):
    search_type = "tv" if is_tv else "movie"
    search_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(search_url)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            item = results[0]  # Take first result
            return {
                "title": item["name"] if is_tv else item["title"],
                "year": item["first_air_date"].split("-")[0] if is_tv and "first_air_date" in item else item.get("release_date", "N/A").split("-")[0],
                "rating": round(item.get("vote_average", 0), 1),
                "poster_url": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None

# Function to update the .m3u file on GitHub
def update_m3u_on_github():
    try:
        # Initialize git repo object
        repo = git.Repo(GITHUB_REPO_PATH)
        repo.git.add(M3U_FILE)  # Stage the .m3u file
        repo.index.commit("Update movies playlist")  # Commit changes
        origin = repo.remote(name="origin")
        origin.push()  # Push changes to GitHub
        return True
    except Exception as e:
        print(f"Error updating .m3u file on GitHub: {e}")
        return False

# Function to add a movie at the top
def add_movie(title, m3u_link):
    movie_details = get_tmdb_details(title)
    if not movie_details:
        return f"❌ Movie '{title}' not found on TMDb."
    
    new_entry = f"# {movie_details['title']} ({movie_details['year']})\n"
    new_entry += f'#EXTINF:-1 tvg-logo="{movie_details["poster_url"]}" group-title="Movies", {movie_details["title"]} ({movie_details["year"]}) - IMDb {movie_details["rating"]}\n'
    new_entry += f"{m3u_link}\n\n"
    
    # Read existing content
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as file:
            existing_content = file.read()
    except FileNotFoundError:
        existing_content = ""
    
    # Write new content
    with open(M3U_FILE, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        file.write(new_entry)
        file.write(existing_content.replace("#EXTM3U\n", "", 1))
    
    # Update on GitHub
    if update_m3u_on_github():
        return f"✅ {movie_details['title']} added to the TOP of {M3U_FILE} on GitHub!"
    else:
        return "❌ Failed to update GitHub repository."

# Function to add a TV show at the bottom
def add_tv_show(title, season, episode, m3u_link):
    tv_details = get_tmdb_details(title, is_tv=True)
    if not tv_details:
        return f"❌ TV Show '{title}' not found on TMDb."
    
    new_entry = f"#EXTINF:-1 tvg-logo={tv_details['poster_url']} group-title={tv_details['title']}, {tv_details['title']} S{int(season):02d}E{int(episode):02d} - IMDb {tv_details['rating']}\n"
    new_entry += f"{m3u_link}\n\n"
    
    # Read existing content
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as file:
            existing_content = file.readlines()
    except FileNotFoundError:
        existing_content = ["#EXTM3U\n"]
    
    # Find where to insert
    insert_index = len(existing_content)  # Default to end
    for i in range(len(existing_content) - 1, 0, -1):
        if existing_content[i].startswith("#EXTINF"):
            insert_index = i + 1
            break
    
    # Write updated content
    with open(M3U_FILE, "w", encoding="utf-8") as file:
        file.writelines(existing_content[:insert_index])
        file.write(new_entry)
        file.writelines(existing_content[insert_index:])
    
    # Update on GitHub
    if update_m3u_on_github():
        return f"✅ {tv_details['title']} S{int(season):02d}E{int(episode):02d} added to the BOTTOM of {M3U_FILE} on GitHub!"
    else:
        return "❌ Failed to update GitHub repository."

# Discord event handlers
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore messages from the bot itself

    print(f"Raw message content: '{message.content}'")  # Log raw message content
    print(f"Message from {message.author}: '{message.content}'")

    content = message.content.strip()  # Strip spaces from the message

    print(f"Stripped content: '{content}'")  # Log stripped content

    if content.startswith("!addmovie"):
        print("!addmovie command received")
        parts = content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Usage: !addmovie <Movie Name> <M3U Link>")
            return
        response = add_movie(parts[1], parts[2])
        await message.channel.send(response)

    elif content.startswith("!addtv"):
        print("!addtv command received")
        parts = content.split(" ", 4)
        if len(parts) < 5:
            await message.channel.send("❌ Usage: !addtv <TV Show Name> <Season> <Episode> <M3U Link>")
            return
        response = add_tv_show(parts[1], parts[2], parts[3], parts[4])
        await message.channel.send(response)



# Run bot
client.run(TOKEN)
