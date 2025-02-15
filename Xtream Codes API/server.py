from flask import Flask, jsonify, request

app = Flask(__name__)

# Fake user database (replace with actual user authentication)
USER_DB = {
    "username": "test",
    "password": "test",
    "status": "Active",
    "exp_date": "1739569200"
}

# Movie database (replace with actual data)
MOVIES = [
    {
        "stream_id": 101,
        "name": "Oppenheimer (2023)",
        "rating": "8.7",
        "category_name": "Drama",
        "stream_url": "https://example.com/oppenheimer.ts",  # Replace with your actual .ts link
        "cover": "https://image.tmdb.org/t/p/w500/9W7kHbnPZe5INk2HphhQYtSB0He.jpg",
        "plot": "The story of J. Robert Oppenheimer...",
        "cast": ["Cillian Murphy", "Emily Blunt"],
        "director": "Christopher Nolan"
    },
    {
        "stream_id": 102,
        "name": "The Nun II (2023)",
        "rating": "6.1",
        "category_name": "Horror",
        "stream_url": "https://example.com/thenun2.ts",  # Replace with your actual .ts link
        "cover": "https://image.tmdb.org/t/p/w500/5gzzkR7y3hnY8AD1wXjCnVlHba5.jpg",
        "plot": "A sequel to the horror movie The Nun...",
        "cast": ["Taissa Farmiga", "Jonas Bloquet"],
        "director": "Michael Chaves"
    }
]

# Route: Login check (mimics Xtream Codes get.php)
@app.route("/get.php")
def login_check():
    username = request.args.get("username")
    password = request.args.get("password")

    if username == USER_DB["username"] and password == USER_DB["password"]:
        return jsonify({"user_info": USER_DB})
    else:
        return jsonify({"error": "Invalid login"}), 403

# Route: Movie list (mimics Xtream Codes player_api.php)
@app.route("/player_api.php")
def get_movies():
    query_type = request.args.get("type")

    if query_type == "vod":
        # Return the movie list in the required format with .ts links
        return jsonify({
            "vod": [
                {
                    "stream_id": movie["stream_id"],
                    "name": movie["name"],
                    "rating": movie["rating"],
                    "category_name": movie["category_name"],
                    "stream_url": movie["stream_url"],  # The .ts stream URL
                    "cover": movie["cover"],
                    "plot": movie["plot"],
                    "cast": movie["cast"],
                    "director": movie["director"]
                }
                for movie in MOVIES
            ]
        })
    else:
        return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
