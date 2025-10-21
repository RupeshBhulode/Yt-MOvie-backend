# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from firebase_admin import firestore  # ✅ Add this line
from utils import db, CATEGORIES

app = FastAPI(
    title="🎬 Movie API with Pagination",
    version="1.0.0",
    description="Fetch movies by category with pagination (5 per page)"
)

# ✅ Allow CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------
# 🏠 Root (health check)
# -------------------------------------------
@app.get("/")
def home():
    return {"message": "🔥 Movie API is live and running!"}


# -------------------------------------------
# ⚙️ Helper function for pagination
# -------------------------------------------
def fetch_movies(category: str, page: int):
    per_page = 5
    offset = (page - 1) * per_page

    docs = db.collection(category).limit(per_page).offset(offset).stream()
    movies = [doc.to_dict() for doc in docs]

    return {
        "category": category,
        "page": page,
        "per_page": per_page,
        "count": len(movies),
        "movies": movies
    }


# -------------------------------------------
# 🧩 CATEGORY ROUTES (each category separate)
# -------------------------------------------

@app.get("/movies/hindi-action")
def hindi_action(page: int = Query(1, ge=1)):
    """Fetch Hindi Action movies (5 per page)"""
    return fetch_movies("Hindi Action", page)


@app.get("/movies/hindi-comedy")
def hindi_comedy(page: int = Query(1, ge=1)):
    """Fetch Hindi Comedy movies (5 per page)"""
    return fetch_movies("Hindi Comedy", page)


@app.get("/movies/hindi-family")
def hindi_family(page: int = Query(1, ge=1)):
    """Fetch Hindi Family movies (5 per page)"""
    return fetch_movies("Hindi Family", page)


@app.get("/movies/hindi-horror")
def hindi_horror(page: int = Query(1, ge=1)):
    """Fetch Hindi Horror movies (5 per page)"""
    return fetch_movies("Hindi Horror", page)


@app.get("/movies/hindi-suspense-thriller")
def hindi_thriller(page: int = Query(1, ge=1)):
    """Fetch Hindi Suspense Thriller movies (5 per page)"""
    return fetch_movies("Hindi Suspense Thriller", page)


@app.get("/movies/hindi-animated")
def hindi_animated(page: int = Query(1, ge=1)):
    """Fetch Hindi Animated movies (5 per page)"""
    return fetch_movies("Hindi Animated", page)


# -------------------------------------------
# 🎥 SINGLE MOVIE DETAILS ROUTE
# -------------------------------------------
@app.get("/movie/{video_id}")
def get_movie(
    video_id: str,
    user_id: str = Query(..., description="User ID or name who is performing the action"),
    liked: bool = Query(False, description="Mark movie as liked (default = false)"),
    watched: bool = Query(False, description="Mark movie as watched (default = false)")
):
    """
    Fetch a specific movie by its video ID from any category.
    If liked or watched = True → store that info in Firestore under user_data/{user_id}.
    """
    for category in CATEGORIES:
        doc_ref = db.collection(category).document(video_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["category"] = category
            data["liked"] = liked
            data["watched"] = watched

            user_ref = db.collection("user_data").document(user_id)

            # ✅ Store liked movie
            if liked:
                user_ref.collection("likedMovies").document(video_id).set({
                    "videoId": video_id,
                    "title": data.get("title"),
                    "category": category,
                    "thumbnail": data.get("thumbnail", ""),  # ✅ added thumbnail
                    "timestamp": firestore.SERVER_TIMESTAMP
                })

            # ✅ Store watched movie
            if watched:
                user_ref.collection("watchedMovies").document(video_id).set({
                     "videoId": video_id,
                    "title": data.get("title"),
                    "category": category,
                    "thumbnail": data.get("thumbnail", ""),  # ✅ added thumbnail
                    "timestamp": firestore.SERVER_TIMESTAMP
                })

            return {
                "movie": data,
                "user": user_id,
                "message": f"Movie fetched for user '{user_id}' (liked/watched saved if true)"
            }

    return {"error": f"No movie found with videoId: {video_id}"}   





@app.get("/user/{user_id}/liked")
def get_liked_movies(user_id: str):
    """
    Fetch all liked movies for a specific user.
    Data is retrieved from Firestore under: user_data/{user_id}/likedMovies
    """
    liked_ref = db.collection("user_data").document(user_id).collection("likedMovies").stream()
    liked_movies = [doc.to_dict() for doc in liked_ref]

    if not liked_movies:
        return {"user": user_id, "liked_movies": [], "message": "No liked movies found."}

    return {
        "user": user_id,
        "count": len(liked_movies),
        "liked_movies": liked_movies
    }


# -------------------------------------------
# 🎞️ FETCH WATCHED MOVIES OF A USER
# -------------------------------------------
@app.get("/user/{user_id}/watched")
def get_watched_movies(user_id: str):
    """
    Fetch all watched movies for a specific user.
    Data is retrieved from Firestore under: user_data/{user_id}/watchedMovies
    """
    watched_ref = db.collection("user_data").document(user_id).collection("watchedMovies").stream()
    watched_movies = [doc.to_dict() for doc in watched_ref]

    if not watched_movies:
        return {"user": user_id, "watched_movies": [], "message": "No watched movies found."}

    return {
        "user": user_id,
        "count": len(watched_movies),
        "watched_movies": watched_movies
    }


# -------------------------------------------
# 🌟 RECOMMENDED MOVIES FOR A USER (Proportional Distribution)
# -------------------------------------------
@app.get("/user/{user_id}/recommended")
def get_recommended_movies(user_id: str):
    """
    Recommend up to 8 movies based on the user's liked and watched history.
    Distributes recommendations proportionally to the category scores.
    """
    import math, random

    user_ref = db.collection("user_data").document(user_id)

    # Fetch liked and watched movies
    liked_ref = user_ref.collection("likedMovies").stream()
    watched_ref = user_ref.collection("watchedMovies").stream()

    liked = [doc.to_dict() for doc in liked_ref]
    watched = [doc.to_dict() for doc in watched_ref]

    if not liked and not watched:
        return {"user": user_id, "recommendations": [], "message": "No history found to generate recommendations."}

    # Count category weights (liked=+2, watched=+1)
    category_score = {}
    for m in watched:
        category_score[m["category"]] = category_score.get(m["category"], 0) + 1
    for m in liked:
        category_score[m["category"]] = category_score.get(m["category"], 0) + 2

    # Sort categories by descending score
    sorted_categories = sorted(category_score.items(), key=lambda x: x[1], reverse=True)

    # Keep only top 3 categories
    top_categories = sorted_categories[:3]
    total_score = sum(score for _, score in top_categories)

    # Exclude already seen movie IDs
    seen_ids = {m["videoId"] for m in liked + watched}

    total_recommendations = 8
    recommendations = []

    # 🎯 Proportional allocation
    allocations = {}
    remaining = total_recommendations

    for i, (cat, score) in enumerate(top_categories):
        if i == len(top_categories) - 1:
            # Assign remaining to last category to make total = 8
            allocations[cat] = remaining
        else:
            alloc = round((score / total_score) * total_recommendations)
            allocations[cat] = alloc
            remaining -= alloc

    # 🧩 Fetch movies proportionally from each category
    for cat, limit in allocations.items():
        if limit <= 0:
            continue
        docs = list(db.collection(cat).stream())
        random.shuffle(docs)  # randomize within the category

        count = 0
        for d in docs:
            movie = d.to_dict()
            if movie.get("videoId") not in seen_ids:
                recommendations.append(movie)
                count += 1
            if count >= limit:
                break

    # Shuffle final list for variety
    random.shuffle(recommendations)

    return {
        "user": user_id,
        "based_on": [c for c, _ in top_categories],
        "allocation": allocations,
        "count": len(recommendations),
        "recommendations": recommendations[:8]
    }