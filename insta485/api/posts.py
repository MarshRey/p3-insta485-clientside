"""REST API for posts."""
import flask
import insta485
from flask import session
from flask import request
from flask import jsonify
import sys
import hashlib
from functools import wraps

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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = flask.request.authorization
        
        # Check for session-based authentication
        if 'username' in flask.session:
            username = flask.session['username']
        elif auth:
            # Basic Authentication logic
            username = auth.username
            password = auth.password

            # Connect to the database
            connection = insta485.model.get_db()

            # Query for the user's password in the database
            db_password = connection.execute(
                "SELECT password FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if not db_password:
                return flask.jsonify({"message": "Invalid credentials", "status_code": 401}), 401

            # Split the stored password (algorithm$salt$hash)
            password_parts = db_password['password'].split('$')
            if len(password_parts) != 3:
                return flask.jsonify({"message": "Invalid password format", "status_code": 500}), 500

            algorithm, db_salt, db_hash = password_parts

            # Use the salt to hash the provided password
            hash_obj = hashlib.new(algorithm)
            salted_password = db_salt + password
            hash_obj.update(salted_password.encode('utf-8'))
            provided_password_hash = hash_obj.hexdigest()

            # Check if the hashed password matches the stored hash
            if provided_password_hash != db_hash:
                return flask.jsonify({"message": "Invalid credentials", "status_code": 401}), 401
        else:
            # No session or authentication provided
            return flask.jsonify({"message": "Authentication required", "status_code": 401}), 401

        # Successful authentication, proceed with the request
        return f(*args, **kwargs)
    
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


@insta485.app.route('/api/v1/likes/', methods=['POST'])
@authenticate
def like_post():
    """Create one like for a specific post."""
    # Get the logged-in user's username
    if 'username' in flask.session:
        logname = flask.session['username']
    else:
        auth = flask.request.authorization
        logname = auth.username

    # Get the postid from the query parameter
    postid = flask.request.args.get('postid', default=None, type=int)

    # If postid is not provided, return 400 Bad Request
    if postid is None:
        return jsonify({"message": "Missing postid", "status_code": 400}), 400

    # Ignore the body for this request if any is sent
    # Proceed only based on the query parameter

    connection = insta485.model.get_db()

    # Verify that the post exists
    cur = connection.execute(
        "SELECT postid FROM posts WHERE postid = ?", (postid,)
    )
    post = cur.fetchone()
    if post is None:
        # Post not found
        return jsonify({"message": "Not Found", "status_code": 404}), 404

    # Check if the logged-in user has already liked the post
    cur = connection.execute(
        """
        SELECT likeid FROM likes
        WHERE postid = ? AND owner = ?
        """, (postid, logname)
    )
    like = cur.fetchone()

    if like is not None:
        # Like already exists, return the existing like with a 200 response
        return jsonify({
            "likeid": like["likeid"],
            "url": f"/api/v1/likes/{like['likeid']}/"
        }), 200

    # If no like exists, insert a new like
    cur = connection.execute(
        """
        INSERT INTO likes (owner, postid)
        VALUES (?, ?)
        """, (logname, postid)
    )
    likeid = cur.lastrowid

    # Return the newly created like with a 201 status
    return jsonify({
        "likeid": likeid,
        "url": f"/api/v1/likes/{likeid}/"
    }), 201
    
@insta485.app.route('/api/v1/likes/<int:likeid>/', methods=['DELETE'])
@authenticate
def delete_like(likeid):
    """Delete a like."""
    # Get the logged-in user's username
    if 'username' in flask.session:
        logname = flask.session['username']
    else:
        auth = flask.request.authorization
        logname = auth.username

    connection = insta485.model.get_db()

    # Check if the like exists
    cur = connection.execute(
        "SELECT likeid, owner FROM likes WHERE likeid = ?",
        (likeid,)
    )
    like = cur.fetchone()

    if like is None:
        # Like does not exist
        return flask.jsonify({"message": "Like Not Found", "status_code": 404}), 404

    # Check if the logged-in user owns the like
    if like['owner'] != logname:
        # User does not own the like
        return flask.jsonify({"message": "Forbidden", "status_code": 403}), 403

    # Delete the like
    connection.execute(
        "DELETE FROM likes WHERE likeid = ?",
        (likeid,)
    )

    # Return 204 No Content on success
    return ('', 204)
  
@insta485.app.route('/api/v1/comments/', methods=['POST'])
@authenticate
def add_comment():
    """Add a new comment to a post."""
    # Get the logged-in user's username
    if 'username' in flask.session:
        logname = flask.session['username']
    else:
        auth = flask.request.authorization
        logname = auth.username

    # Get the postid from the query parameter
    postid = flask.request.args.get('postid', default=None, type=int)
    if postid is None:
        return flask.jsonify({"message": "Missing postid", "status_code": 400}), 400

    # Get the comment text from the query or form data
    comment_text = flask.request.json.get('text', None)
        
    print(f"Comment text: {comment_text}", file=sys.stderr)

    if not comment_text:
        return flask.jsonify({"message": "Missing comment text", "status_code": 400}), 400

    connection = insta485.model.get_db()

    # Verify that the post exists
    cur = connection.execute(
        "SELECT postid FROM posts WHERE postid = ?",
        (postid,)
    )
    post = cur.fetchone()
    if post is None:
        return flask.jsonify({"message": "Post Not Found", "status_code": 404}), 404

    # Insert the new comment into the database
    connection.execute(
        """
        INSERT INTO comments (owner, postid, text)
        VALUES (?, ?, ?)
        """, (logname, postid, comment_text)
    )

    # Get the ID of the newly inserted comment
    cur = connection.execute("SELECT last_insert_rowid() as commentid")
    commentid = cur.fetchone()['commentid']

    # Prepare the response data for the newly added comment
    response_data = {
        "commentid": commentid,
        "lognameOwnsThis": True,
        "owner": logname,
        "ownerShowUrl": f"/users/{logname}/",
        "text": comment_text,
        "url": f"/api/v1/comments/{commentid}/"
    }

    # Return 201 Created with the comment details
    return flask.jsonify(response_data), 201