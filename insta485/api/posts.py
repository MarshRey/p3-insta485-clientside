"""REST API for posts."""
import flask
import insta485
from flask import session
from flask import request
from flask import jsonify
import sys

## TODO: PROJECT 3 STARTS HERE  ##
@insta485.app.route('/api/v1/', methods=['GET'])
def api_root():
    """Return list of available services."""
    response = {
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/"
    }
    return jsonify(response)
    
def authenticate(f):
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if 'username' in session:
            return f(*args, **kwargs)
        elif auth:
            username = auth.username
            password = auth.password
            # Replace with your actual authentication logic
            if username == 'awdeorio' and password == 'chickens':
                return f(*args, **kwargs)
        return jsonify({"message": "Forbidden", "status_code": 403}), 403

    # Manually set the attributes to preserve metadata
    decorated_function.__name__ = f.__name__
    decorated_function.__doc__ = f.__doc__
    decorated_function.__module__ = f.__module__
    return decorated_function

@insta485.app.route('/api/v1/posts/', methods=['GET'])
@authenticate
def get_post():
    """Return paginated posts filtered by postid_lte, size, and page."""
    # Get the logged-in user's username, either from the session or Basic Auth
    if 'username' in flask.session:
        logname = flask.session['username']
    else:
        auth = flask.request.authorization
        logname = auth.username

    # Get query parameters
    postid_lte = flask.request.args.get('postid_lte', default=None, type=int)
    size = flask.request.args.get('size', default=10, type=int)  # Default size is 10 posts
    page = flask.request.args.get('page', default=0, type=int)  # Default page is 0 (first page)

    # Ensure size is positive and page is non-negative
    if size <= 0 or page < 0:
        return jsonify({"message": "Invalid size or page parameter", "status_code": 400}), 400

    connection = insta485.model.get_db()

    # If postid_lte is not provided, get the most recent postid
    if postid_lte is None:
        cur = connection.execute(
            """
            SELECT MAX(postid) as max_postid FROM posts
            WHERE owner = ? OR owner IN (SELECT username2 FROM following WHERE username1 = ?)
            """, (logname, logname)
        )
        row = cur.fetchone()
        if row is not None:
            postid_lte = row['max_postid']

    # Calculate the number of posts to skip based on the page number
    offset = page * size

    # Build the SQL query to fetch the posts
    query = """
        SELECT DISTINCT posts.postid, posts.filename
        FROM posts
        LEFT JOIN following ON following.username2 = posts.owner
        WHERE (following.username1 = ? OR posts.owner = ?)
        AND posts.postid <= ?
        ORDER BY posts.postid DESC LIMIT ? OFFSET ?
    """
    query_params = (logname, logname, postid_lte, size, offset)

    # Execute the query with size and offset for pagination
    cur = connection.execute(query, query_params)
    posts = cur.fetchall()

    # Create a list of posts with postid and URL
    results = [{"postid": post['postid'], "url": f"/api/v1/posts/{post['postid']}/"} for post in posts]

    # Determine the "next" URL for pagination if we have more results to show
    next_url = ""
    if len(posts) == size:
        next_url = f"/api/v1/posts/?size={size}&page={page + 1}&postid_lte={postid_lte}"
    
    
    current_url = flask.request.path
    query_params = request.args.to_dict()
    query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])
    if query_string:
        current_url += f"?{query_string}"
        
    return jsonify({
        "next": next_url,
        "results": results,
        "url": current_url
    })
    
@insta485.app.route('/api/v1/posts/<int:postid>/', methods=['GET'])
@authenticate
def get_single_post(postid):
    print("Executing get_single_post route", file=sys.stderr)
    """Return the details for a specific post."""
    # Get the logged-in user's username
    if 'username' in flask.session:
        logname = flask.session['username']
    else:
        auth = flask.request.authorization
        logname = auth.username

    connection = insta485.model.get_db()

    # Fetch post details
    cur = connection.execute(
    """
    SELECT posts.postid, posts.created, posts.filename AS post_img, posts.owner,
           users.filename AS owner_img, users.username
    FROM posts
    JOIN users ON posts.owner = users.username
    WHERE posts.postid = ?
    """, (postid,)
    )
    post = cur.fetchone()

    if post is None:
        # Post not found
        return jsonify({"message": "Posts Not Found", "status_code": 404}), 404

    # Fetch comments for the post
    cur = connection.execute(
        """
        SELECT comments.commentid, comments.text, comments.owner,
               users.username, users.filename AS user_img
        FROM comments
        JOIN users ON comments.owner = users.username
        WHERE comments.postid = ?
        ORDER BY comments.commentid ASC
        """, (postid,)
    )
    comments = cur.fetchall()
    
    if comments is None:
        return jsonify({"message": "Commonts Not Found", "status_code": 404}), 404
    
    # Prepare comments list
    comments_list = [
        {
            "commentid": comment["commentid"],
            "lognameOwnsThis": logname == comment["owner"],
            "owner": comment["owner"],
            "ownerShowUrl": f"/users/{comment['owner']}/",
            "text": comment["text"],
            "url": f"/api/v1/comments/{comment['commentid']}/"
        }
        for comment in comments
    ]
    response = {
        "comments": comments_list
    }

    # Fetch likes for the post
    cur = connection.execute(
        """
        SELECT likeid, owner FROM likes WHERE postid = ?
        """, (postid,)
    )
    likes = cur.fetchall()

    # Count likes and check if the logged-in user liked the post
    num_likes = len(likes)
    logname_likes_this = False
    like_url = None

    for like in likes:
        if like["owner"] == logname:
            logname_likes_this = True
            like_url = f"/api/v1/likes/{like['likeid']}/"

    # Prepare the JSON response
    response = {
        "comments": comments_list,
        "comments_url": f"/api/v1/comments/?postid={postid}",
        "created": post["created"],  # Keep this as a timestamp, not human-readable
        "imgUrl": f"/uploads/{post['post_img']}",
        "likes": {
            "lognameLikesThis": logname_likes_this,
            "numLikes": num_likes,
            "url": like_url
        },
        "owner": post["owner"],
        "ownerImgUrl": f"/uploads/{post['owner_img']}",
        "ownerShowUrl": f"/users/{post['owner']}/",
        "postShowUrl": f"/posts/{postid}/",
        "postid": postid,
        "url": f"/api/v1/posts/{postid}/"
    }

    return jsonify(response)


# @insta485.app.route('/api/v1/posts/<int:postid_url_slug>/')
# def get_post(postid_url_slug):
#     """Return post on postid.

#     Example:
#     {
#       "created": "2017-09-28 04:33:28",
#       "imgUrl": "/uploads/122a7d27ca1d7420a1072f695d9290fad4501a41.jpg",
#       "owner": "awdeorio",
#       "ownerImgUrl": "/uploads/e1a7c5c32973862ee15173b0259e3efdb6a391af.jpg",
#       "ownerShowUrl": "/users/awdeorio/",
#       "postShowUrl": "/posts/1/",
#       "postid": 1,
#       "url": "/api/v1/posts/1/"
#     }
#     """
#     context = {
#         "created": "2017-09-28 04:33:28",
#         "imgUrl": "/uploads/122a7d27ca1d7420a1072f695d9290fad4501a41.jpg",
#         "owner": "awdeorio",
#         "ownerImgUrl": "/uploads/e1a7c5c32973862ee15173b0259e3efdb6a391af.jpg",
#         "ownerShowUrl": "/users/awdeorio/",
#         "postShowUrl": f"/posts/{postid_url_slug}/",
#         "postid": postid_url_slug,
#         "url": flask.request.path,
#     }
#     return flask.jsonify(**context)
