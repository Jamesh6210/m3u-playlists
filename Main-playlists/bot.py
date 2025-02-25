import discord
import requests
import os
import git
from dotenv import load_dotenv
from discord import app_commands

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
M3U_FILE = "Movies-playlist.m3u"
GITHUB_REPO_PATH = os.getenv("GITHUB_REPO_PATH")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Bot setup with command tree for slash commands
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)  # Slash command handler

# Function to fetch details from TMDb (Movies & TV Shows)
def get_tmdb_details(title, is_tv=False):
    search_type = "tv" if is_tv else "movie"
    search_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(search_url)
    
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            item = results[0]
            return {
                "title": item["name"] if is_tv else item["title"],
                "year": item.get("first_air_date" if is_tv else "release_date", "N/A").split("-")[0],
                "rating": round(item.get("vote_average", 0), 1),
                "poster_url": f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None

# Function to update GitHub repo
def update_m3u_on_github():
    try:
        repo = git.Repo(GITHUB_REPO_PATH)
        repo.git.add(M3U_FILE)
        repo.index.commit("Update movies playlist")
        origin = repo.remote(name="origin")
        origin.push()
        return True
    except Exception as e:
        print(f"Error updating .m3u file on GitHub: {e}")
        return False

# Function to add a movie
def add_movie(title, m3u_link):
    movie_details = get_tmdb_details(title)
    if not movie_details:
        return f"❌ Movie '{title}' not found on TMDb."
    
    new_entry = f"# {movie_details['title']} ({movie_details['year']})\n"
    new_entry += f'#EXTINF:-1 tvg-logo="{movie_details["poster_url"]}" group-title="Movies", {movie_details["title"]} ({movie_details["year"]}) - IMDb {movie_details["rating"]}\n'
    new_entry += f"{m3u_link}\n\n"
    
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as file:
            existing_content = file.read()
    except FileNotFoundError:
        existing_content = ""
    
    with open(M3U_FILE, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        file.write(new_entry)
        file.write(existing_content.replace("#EXTM3U\n", "", 1))
    
    if update_m3u_on_github():
        return f"✅ {movie_details['title']} added to the TOP of {M3U_FILE} on GitHub!"
    else:
        return "❌ Failed to update GitHub repository."

# Function to add a TV show episode
def add_tv_show(title, season, episode, m3u_link):
    tv_details = get_tmdb_details(title, is_tv=True)
    if not tv_details:
        return f"❌ TV Show '{title}' not found on TMDb."
    
    new_entry = f"#EXTINF:-1 tvg-logo={tv_details['poster_url']} group-title={tv_details['title']}, {tv_details['title']} S{int(season):02d}E{int(episode):02d} - IMDb {tv_details['rating']}\n"
    new_entry += f"{m3u_link}\n\n"
    
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as file:
            existing_content = file.readlines()
    except FileNotFoundError:
        existing_content = ["#EXTM3U\n"]
    
    insert_index = len(existing_content)
    for i in range(len(existing_content) - 1, 0, -1):
        if existing_content[i].startswith("#EXTINF"):
            insert_index = i + 1
            break
    
    with open(M3U_FILE, "w", encoding="utf-8") as file:
        file.writelines(existing_content[:insert_index])
        file.write(new_entry)
        file.writelines(existing_content[insert_index:])
    
    if update_m3u_on_github():
        return f"✅ {tv_details['title']} S{int(season):02d}E{int(episode):02d} added to the BOTTOM of {M3U_FILE} on GitHub!"
    else:
        return "❌ Failed to update GitHub repository."

# Slash command to add a movie
@tree.command(name="addmovie", description="Add a movie to the playlist")
async def addmovie(interaction: discord.Interaction, title: str, m3u_link: str):
    await interaction.response.defer()
    response = add_movie(title, m3u_link)
    await interaction.followup.send(response)

# Slash command to add a TV show
@tree.command(name="addtv", description="Add a TV Show episode to the playlist")
async def addtv(interaction: discord.Interaction, title: str, season: int, episode: int, m3u_link: str):
    await interaction.response.defer()
    response = add_tv_show(title, season, episode, m3u_link)
    await interaction.followup.send(response)

# Event: Bot ready and sync slash commands
@bot.event
async def on_ready():
    await tree.sync()  # Sync commands to Discord server
    print(f"✅ Logged in as {bot.user}")

# Run bot
bot.run(TOKEN)
