import discord
import requests
import os
from github import Github
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_NAME = os.getenv(
    "GITHUB_REPO_NAME")  # Format: "YourUsername/M3U-Playlist"
M3U_FILE = "Main-playlists/Movies-playlist.m3u"

# Initialize bot with commands
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Flask Keep-Alive (for Replit)
app = Flask('')


@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()


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
                "title":
                item["name"] if is_tv else item["title"],
                "year":
                item.get("first_air_date" if is_tv else "release_date",
                         "N/A").split("-")[0],
                "rating":
                round(item.get("vote_average", 0), 1),
                "poster_url":
                f"https://image.tmdb.org/t/p/w500{item['poster_path']}"
                if item.get("poster_path") else
                "https://via.placeholder.com/500x750?text=No+Image"
            }
    return None


# Function to update the M3U file on GitHub
def update_m3u_on_github(new_content):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO_NAME)
        file = repo.get_contents(M3U_FILE)
        old_content = file.decoded_content.decode("utf-8")

        # Add new entry at the top
        updated_content = "#EXTM3U\n" + new_content + old_content.replace(
            "#EXTM3U\n", "", 1)

        # Commit and update file
        repo.update_file(
            path=M3U_FILE,
            message="Update M3U playlist",
            content=updated_content,
            sha=file.sha,
        )

        return True
    except Exception as e:
        print(f"Error updating M3U file on GitHub: {e}")
        return False


# Function to add a movie
async def add_movie(interaction: discord.Interaction, title: str,
                    m3u_link: str):
    await interaction.response.defer()
    movie_details = get_tmdb_details(title)

    if not movie_details:
        await interaction.followup.send(f"❌ Movie '{title}' not found on TMDb."
                                        )
        return

    new_entry = f"# {movie_details['title']} ({movie_details['year']})\n"
    new_entry += f'#EXTINF:-1 tvg-logo="{movie_details["poster_url"]}" group-title="Movies", {movie_details["title"]} ({movie_details["year"]}) - IMDb {movie_details["rating"]}\n'
    new_entry += f"{m3u_link}\n\n"

    if update_m3u_on_github(new_entry):
        await interaction.followup.send(
            f"✅ {movie_details['title']} added to the playlist!")
    else:
        await interaction.followup.send("❌ Failed to update GitHub repository."
                                        )


# Function to add a TV show
async def add_tv_show(interaction: discord.Interaction, title: str,
                      season: int, episode: int, m3u_link: str):
    await interaction.response.defer()
    tv_details = get_tmdb_details(title, is_tv=True)

    if not tv_details:
        await interaction.followup.send(
            f"❌ TV Show '{title}' not found on TMDb.")
        return

    new_entry = f"#EXTINF:-1 tvg-logo={tv_details['poster_url']} group-title={tv_details['title']}, {tv_details['title']} S{season:02d}E{episode:02d} - IMDb {tv_details['rating']}\n"
    new_entry += f"{m3u_link}\n\n"

    if update_m3u_on_github(new_entry):
        await interaction.followup.send(
            f"✅ {tv_details['title']} S{season:02d}E{episode:02d} added to the playlist!"
        )
    else:
        await interaction.followup.send("❌ Failed to update GitHub repository."
                                        )


# Register commands
@tree.command(name="addmovie", description="Add a movie to the playlist")
async def addmovie(interaction: discord.Interaction, title: str,
                   m3u_link: str):
    await add_movie(interaction, title, m3u_link)


@tree.command(name="addtv", description="Add a TV show to the playlist")
async def addtv(interaction: discord.Interaction, title: str, season: int,
                episode: int, m3u_link: str):
    await add_tv_show(interaction, title, season, episode, m3u_link)


# Discord event handlers
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    await tree.sync()  # Sync slash commands with Discord


# Run bot
client.run(TOKEN)
