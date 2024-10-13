"""Views for the index page."""
import sys
import pathlib
import uuid
import hashlib
import os
import flask
from flask import send_from_directory
import insta485
from insta485.api.posts import get_password


@insta485.app.route('/')
def show_index():
    """Display the index page."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")

    # Connect to database
    connection = insta485.model.get_db()

    # Replace with actual logged-in user from session todo: replace with actual
    # logged-in user from session
    logname = flask.session.get('username')

    # Fetch all users that the logged-in user is following
    cur = connection.execute(
        "SELECT username, fullname, filename AS profile_pic "
        "FROM users "
        "WHERE username IN "
        "(SELECT username2 FROM following WHERE username1 = ?)",
        (logname,)
    )
    users = cur.fetchall()

    print(f"users: {users}", file=sys.stderr)
    # Query database for the first three posts with owner details Only include
    # posts from users that the current logged in user is following cur =
    # connection.execute( "SELECT posts.postid, posts.created, posts.filename,"
    #     "users.username, users.fullname, users.filename AS user_filename "
    #     "FROM posts " "JOIN users ON posts.owner = users.username " "WHERE
    #     posts.owner IN (SELECT username2 FROM following WHERE username1 = ?)
    #     ", "ORDER BY posts.created DESC " (logname, ) )
    cur = connection.execute(
        "SELECT posts.postid, posts.created, posts.filename, "
        "users.username, users.fullname, users.filename AS user_filename "
        "FROM posts "
        "JOIN users ON posts.owner = users.username "
        "ORDER BY posts.created DESC "
    )
    posts = cur.fetchall()
    # Remove posts from users that the logged-in user is not following
    posts = [post for post in posts if
             (post['username'] in [user['username'] for user in users]
              or post['username'] == logname)]
    print(posts, file=sys.stderr)

    # Fetch likes, comments, and user following info for each post
    for post in posts:
        if post['username'] \
            not in [user['username']
                    for user in users] and post['username'] != logname:
            print(f"Skipping post: {post['username']}", file=sys.stderr)
            continue
        # Likes
        cur = connection.execute(
            "SELECT COUNT(*) AS like_count FROM likes WHERE postid = ?",
            (post['postid'], )
        )
        post['likes'] = cur.fetchone()['like_count']

        # User like status
        cur = connection.execute(
            "SELECT 1 FROM likes WHERE postid = ? AND owner = ?",
            (post['postid'], logname)
        )
        post['is_liked'] = cur.fetchone() is not None

        # Comments
        cur = connection.execute(
            "SELECT comments.text, comments.created, users.username, \
            users.fullname, users.filename AS user_filename "
            "FROM comments JOIN users ON comments.owner = users.username "
            "WHERE comments.postid = ? "
            "ORDER BY comments.created ASC",
            (post['postid'], )
        )
        post['comments'] = cur.fetchall()

    # Get the following and follower counts for logged-in user
    cur = connection.execute(
        "SELECT COUNT(*) AS following_count \
            FROM following WHERE username1 = ?",
        (logname,)
    )
    following_count = cur.fetchone()['following_count']

    cur = connection.execute(
        "SELECT COUNT(*) AS followers_count \
            FROM following WHERE username2 = ?",
        (logname,)
    )
    followers_count = cur.fetchone()['followers_count']

    # Add database info to context
    context = {
        "users": users,
        "posts": posts,
        "logged_in_user": logname,
        "following_count": following_count,
        "followers_count": followers_count
    }
    return flask.render_template("index.html", **context)


@insta485.app.route('/uploads/<filename>')
def show_uploads(filename):
    """Serve an uploaded file if the user is authenticated."""
    print(f"Request received for file: {filename}", file=sys.stderr)
    # Redirect to login page if user is not authenticated
    if "username" not in flask.session:
        flask.abort(403)

    # Define the upload folder path
    upload_folder = insta485.app.config['UPLOAD_FOLDER']

    # Check if the file exists
    if not os.path.exists(os.path.join(upload_folder, filename)):
        flask.abort(404)

    # Check if the file belongs to the logged-in user connection =
    # insta485.model.get_db() cur = connection.execute( "SELECT 1 FROM users
    # WHERE username = ? AND filename = ?", (flask.session['username'],
    #     filename) ) print(f"Checking if file belongs to user:
    #     {flask.session['username']}", file=sys.stderr) if cur.fetchone() is
    # None: flask.abort(403) Serve the file
    return send_from_directory(upload_folder, filename)


@insta485.app.route('/users/<user_url_slug>/')
def show_users(user_url_slug):
    """Display user profile page."""
    print(f"Request received for user: {user_url_slug}", file=sys.stderr)
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")

    # Connect to database
    connection = insta485.model.get_db()

    # Check if user exists
    cur = connection.execute(
        "SELECT username, fullname, filename AS profile_picture_url "
        "FROM users WHERE username = ?",
        (user_url_slug, )
    )
    user = cur.fetchone()
    if user is None:
        flask.abort(404)

    logname = flask.session.get('username')  # Example logged-in user

    # Determine relationship status
    if logname == user_url_slug:
        relationship = ""
    else:
        cur = connection.execute(
            "SELECT 1 FROM following WHERE username1 = ? AND username2 = ?",
            (logname, user_url_slug)
        )
        relationship = "following" if cur.fetchone() else "not following"

    # Get number of posts
    cur = connection.execute(
        "SELECT COUNT(*) AS post_count FROM posts WHERE owner = ?",
        (user_url_slug, )
    )
    post_count = cur.fetchone()['post_count']

    # Get number of followers
    cur = connection.execute(
        "SELECT COUNT(*) AS follower_count FROM following WHERE username2 = ?",
        (user_url_slug, )
    )
    follower_count = cur.fetchone()['follower_count']

    # Get number following
    cur = connection.execute(
        "SELECT COUNT(*) AS following_count \
            FROM following WHERE username1 = ?",
        (user_url_slug, )
    )
    following_count = cur.fetchone()['following_count']

    # Get posts
    cur = connection.execute(
        "SELECT postid, filename \
            FROM posts WHERE owner = ? ORDER BY created DESC",
        (user_url_slug, )
    )
    posts = cur.fetchall()

    # Add database info to context
    context = {
        "user": user,
        "relationship": relationship,
        "post_count": post_count,
        "follower_count": follower_count,
        "following_count": following_count,
        "posts": posts,
        "logged_in_user": logname
        }
    return flask.render_template("users.html", **context)


@insta485.app.route('/users/<user_url_slug>/followers/')
def show_users_followers(user_url_slug):
    """Display the followers of user_url_slug."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")

    # Connect to the database
    connection = insta485.model.get_db()

    # Check if user_url_slug exists in the database
    cur = connection.execute(
        "SELECT username FROM users WHERE username = ?",
        (user_url_slug,)
    )
    user = cur.fetchone()
    if user is None:
        flask.abort(404)  # Abort if user does not exist

    # Fetch the followers of user_url_slug
    cur = connection.execute(
        "SELECT users.username, users.fullname, users.filename AS profile_pic "
        "FROM following "
        "JOIN users ON following.username1 = users.username "
        "WHERE following.username2 = ?",
        (user_url_slug,)
    )
    followers = cur.fetchall()

    # Get logged-in user
    logname = flask.session["username"]

    # For each follower, determine the relationship status with the logged-in
    # user
    for follower in followers:
        if logname == follower['username']:
            follower['relationship'] = ""
        else:
            cur = connection.execute(
                "SELECT 1 FROM following \
                    WHERE username1 = ? AND username2 = ?",
                (logname, follower['username'])
            )
            follower['relationship'] = "following" \
                if cur.fetchone() else "not following"

    # Add database info to context
    context = {
        "user_url_slug": user_url_slug,
        "followers": followers,
        "logged_in_user": logname
    }

    return flask.render_template("users_followers.html", **context)


@insta485.app.route('/users/<user_url_slug>/following/')
def show_following(user_url_slug):
    """Display the users that user_url_slug is following."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    # Connect to the database
    connection = insta485.model.get_db()

    # Check if user_url_slug exists in the database
    cur = connection.execute(
        "SELECT username FROM users WHERE username = ?",
        (user_url_slug,)
    )
    user = cur.fetchone()
    if user is None:
        flask.abort(404)  # Abort if user does not exist

    # Fetch the users that user_url_slug is following
    cur = connection.execute(
        "SELECT users.username, users.fullname, users.filename AS profile_pic "
        "FROM following "
        "JOIN users ON following.username2 = users.username "
        "WHERE following.username1 = ?",
        (user_url_slug,)
    )
    following = cur.fetchall()

    # Get logged-in user
    logname = flask.session["username"]

    # For each followed user, determine the relationship status with the
    # logged-in user
    for followed_user in following:
        if logname == followed_user['username']:
            followed_user['relationship'] = ""
        else:
            cur = connection.execute(
                "SELECT 1 FROM following \
                    WHERE username1 = ? AND username2 = ?",
                (logname, followed_user['username'])
            )
            followed_user['relationship'] = "following" \
                if cur.fetchone() else "not following"

    # Add database info to context
    context = {
        "user_url_slug": user_url_slug,
        "following": following,
        "logged_in_user": logname
    }

    return flask.render_template("users_following.html", **context)


@insta485.app.route("/posts/<int:post_id>/")
def show_post(post_id):
    """Show a single post by post_id, including comments and delete buttons."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    # Connect to the database
    connection = insta485.model.get_db()

    # Get logged-in user
    logname = flask.session["username"]

    # Fetch the post details, including the owner's profile picture
    post = connection.execute(
        "SELECT posts.postid, posts.filename, posts.owner, posts.created, "
        "       users.username AS owner_username, \
            users.filename AS profile_pic "
        "FROM posts "
        "JOIN users ON posts.owner = users.username "
        "WHERE posts.postid = ?",
        (post_id,)
    ).fetchone()

    # If the post does not exist, abort
    if post is None:
        flask.abort(404)

    # Check if the logged-in user is the owner of the post
    post['is_owner'] = logname == post['owner_username']
    # Fetch likes for the post
    cur = connection.execute(
        "SELECT COUNT(*) AS like_count "
        "FROM likes "
        "WHERE postid = ?",
        (post_id, )
    )
    post['likes'] = cur.fetchone()['like_count']

    # Check if the logged-in user has liked the post
    cur = connection.execute(
        "SELECT 1 FROM likes WHERE postid = ? AND owner = ?",
        (post_id, logname)
    )
    post['is_liked'] = cur.fetchone() is not None
    # operation is like if not is_liked, unlike if is_liked
    post['operation'] = "like" if not post['is_liked'] else "unlike"
    # Fetch comments for the post
    comments = connection.execute(
        "SELECT comments.commentid, comments.text, \
            comments.owner, comments.postid, "
        "       users.username AS comment_owner_username "
        "FROM comments "
        "JOIN users ON comments.owner = users.username "
        "WHERE comments.postid = ?",
        (post_id,)
    ).fetchall()

    for comment in comments:
        comment['is_owner'] = comment['owner'] == logname

    # Prepare context for template rendering
    context = {
        "post": post,
        "comments": comments,
        "logged_in_user": logname,
    }

    return flask.render_template("posts.html", **context)


@insta485.app.route("/explore/")
def explore():
    """Show users that the logged-in user is not following."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    # Connect to the database
    connection = insta485.model.get_db()

    # Get the logged-in user from the session (replace 'awdeorio' with
    # session-based user)
    logname = flask.session["username"]

    # Fetch all users except the logged-in user and those they are already
    # following
    users_to_follow = connection.execute(
        "SELECT username, filename AS profile_pic "
        "FROM users "
        "WHERE username != ? "
        "AND username NOT IN \
            (SELECT username2 FROM following WHERE username1 = ?)",
        (logname, logname)
    ).fetchall()

    # Prepare context for the template
    context = {
        "users": users_to_follow,
        "logged_in_user": logname
    }

    # Render the explore template with the list of users to follow
    return flask.render_template("explore.html", **context)


@insta485.app.route("/accounts/login/", methods=["GET", "POST"])
def login():
    """Log in the user."""
    return flask.render_template("login.html")


@insta485.app.route("/accounts/auth/")
def check_auth():
    """Check if the user is authenticated."""
    # Check if the user is logged in
    if "username" in flask.session:
        # If logged in, return a 200 status code with no content
        return "", 200

    flask.abort(403)


LOGGER = flask.logging.create_logger(insta485.app)


@insta485.app.route("/likes/", methods=["POST"])
def update_likes():
    """Create or delete a like based on the operation and redirect."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")

    LOGGER.debug("operation = %s", flask.request.form["operation"])
    LOGGER.debug("postid = %s", flask.request.form["postid"])
    connection = insta485.model.get_db()

    # Get logged-in user
    logname = flask.session["username"]
    # Get form data
    operation = flask.request.form.get("operation")
    postid = flask.request.form.get("postid")
    target_url = flask.request.args.get("target", "/")

    # Debugging log
    LOGGER.debug("operation = %s", operation)
    LOGGER.debug("postid = %s", postid)

    # Check if postid exists
    post = connection.execute(
        "SELECT postid FROM posts WHERE postid = ?", (postid,)
    ).fetchone()

    if post is None:
        flask.abort(404)  # Post does not exist

    # Handle the 'like' operation
    if operation == "like":
        # Check if the user already liked the post
        like_exists = connection.execute(
            "SELECT * FROM likes WHERE postid = ? \
                AND owner = ?", (postid, logname)
        ).fetchone()

        if like_exists:
            flask.abort(409)  # User already liked the post

        # Insert the like
        connection.execute(
            "INSERT INTO likes (owner, postid) \
                VALUES (?, ?)", (logname, postid)
        )

    # Handle the 'unlike' operation
    elif operation == "unlike":
        # Check if the user has liked the post
        like_exists = connection.execute(
            "SELECT * FROM likes WHERE postid = ? \
                AND owner = ?", (postid, logname)
        ).fetchone()

        if not like_exists:
            flask.abort(409)  # User has not liked the post

        # Delete the like
        connection.execute(
            "DELETE FROM likes WHERE owner = ? \
                AND postid = ?", (logname, postid)
        )

    # If the operation is neither 'like' nor 'unlike', abort with a 400 error
    else:
        flask.abort(400)

    # Redirect to the target URL
    return flask.redirect(target_url)


@insta485.app.route("/comments/", methods=["POST"])
def update_comments():
    """Create or delete a comment based on the operation and redirect."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    operation = flask.request.form["operation"]
    #  print(f"postid: {postid}", file=sys.stderr)
    logname = flask.session["username"]
    connection = insta485.model.get_db()

    if operation == "create":
        postid = flask.request.form["postid"]
        text = flask.request.form["text"].strip()
        if not text:
            # flask.abort(69)
            flask.abort(400)  # Bad Request: Empty comment

        # Insert new comment into the database
        connection.execute(
            "INSERT INTO comments (postid, owner, text) VALUES (?, ?, ?)",
            (postid, logname, text)
        )
    elif operation == "delete":
        commentid = flask.request.form["commentid"]
        print(f"commentid: {commentid}", file=sys.stderr)
        if not commentid:
            print(f"commentid: {commentid}", file=sys.stderr)
            flask.abort(400)

        comment = connection.execute(
            "SELECT owner FROM comments WHERE commentid = ?",
            (commentid,)
        ).fetchone()
        if comment is None:
            flask.abort(404)  # Comment does not exist
        if comment['owner'] != logname:
            flask.abort(403)
        # Delete comment from database
        connection.execute(
            "DELETE FROM comments WHERE commentid = ?",
            (commentid,)
        )
    connection.commit()
    # Redirect to the target URL
    target_url = flask.request.args.get("target", "/")
    return flask.redirect(target_url)


@insta485.app.route('/posts/', methods=['POST'])
def handle_post():
    """Handle post creation and deletion."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    operation = flask.request.form["operation"]
    target = flask.request.args.get("target")
    # If the value of target is not set, redirect to /users/<logname>/
    if not target or target == "/":
        target = f"/users/{flask.session.get('username')}/"

    if operation == "create":
        file = flask.request.files.get("file")
        if not file or file.filename == '':
            flask.abort(400)
        filename = file.filename
        # Save the file to disk
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"
        file.save(os.path.join(insta485.app.config['UPLOAD_FOLDER'],
                               uuid_basename))
        # Insert post details into the database
        connection = insta485.model.get_db()
        connection.execute(
            "INSERT INTO posts (filename, owner) VALUES (?, ?)",
            (uuid_basename, flask.session.get('username'))
        )

    elif operation == "delete":
        postid = flask.request.form["postid"]
        # Check if the user owns the post
        connection = insta485.model.get_db()
        post = connection.execute(
            "SELECT owner, filename FROM posts WHERE postid = ?",
            (postid,)
        ).fetchone()
        if post['owner'] != flask.session.get('username'):
            flask.abort(403)
        # Delete the image file from the filesystem
        os.remove(os.path.join(insta485.app.config['UPLOAD_FOLDER'],
                               post['filename']))
        # Delete post details from the database
        connection.execute(
            "DELETE FROM posts WHERE postid = ?",
            (postid,)
        )
        connection.execute(
            "DELETE FROM comments WHERE postid = ?",
            (postid,)
        )
        connection.execute(
            "DELETE FROM likes WHERE postid = ?",
            (postid,)
        )

    connection.commit()
    return flask.redirect(target)


@insta485.app.route('/following/', methods=['POST'])
def handle_following():
    """Handle follow and unfollow operations."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    operation = flask.request.form["operation"]
    username = flask.request.form["username"]
    target = flask.request.args.get("target")
    connection = insta485.model.get_db()
    logname = flask.session.get('username')

    if operation == "follow":
        # Check if already following
        follow = connection.execute(
            "SELECT 1 FROM following WHERE username1 = ? AND username2 = ?",
            (logname, username)
        ).fetchone()
        if follow:
            flask.abort(409)
        # Insert follow relationship
        connection.execute(
            "INSERT INTO following (username1, username2) VALUES (?, ?)",
            (logname, username)
        )

    elif operation == "unfollow":
        # Check if not following
        follow = connection.execute(
            "SELECT 1 FROM following WHERE username1 = ? AND username2 = ?",
            (logname, username)
        ).fetchone()
        if not follow:
            flask.abort(409)
        # Delete follow relationship
        connection.execute(
            "DELETE FROM following WHERE username1 = ? AND username2 = ?",
            (logname, username)
        )
    connection.commit()
    return flask.redirect(target)


@insta485.app.route('/accounts/create/', methods=['GET'])
def show_create_account():
    """Show the account creation page."""
    if "username" in flask.session:
        return flask.redirect("/accounts/edit/")
    return flask.render_template("create_account.html")


@insta485.app.route('/accounts/edit/', methods=['GET'])
def show_edit_account():
    """Show the account edit page."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT username, fullname, filename AS profile_picture_url, email "
        "FROM users WHERE username = ?",
        (flask.session.get("username"),)
    )
    user = cur.fetchone()
    context = {
        "user": user
    }
    return flask.render_template("edit_account.html", **context)


@insta485.app.route('/accounts/password/', methods=['GET'])
def show_update_password():
    """Show the password update page."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    logged_in_user = flask.session.get('username')
    context = {
        "logged_in_user": logged_in_user
    }
    return flask.render_template("change_password.html", **context)


@insta485.app.route('/accounts/delete/', methods=['GET'])
def show_delete_account():
    """Show the account deletion page."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")

    context = {
        "username": flask.session.get('username')
    }
    return flask.render_template("delete_account.html", **context)


@insta485.app.route('/accounts/', methods=['POST'])
def handle_account():
    """Handle account creation, deletion, and editing."""
    operation = flask.request.form["operation"]
    target = flask.request.args.get("target")
    connection = insta485.model.get_db()

    if operation == "login":
        login_seq(connection)
    elif operation == "create":
        create(connection)
    elif operation == "delete":
        delete(connection)
    elif operation == "edit_account":
        edit_account(connection)
    elif operation == "update_password":
        update_password(connection)

    connection.commit()

    print(f"target: {target}", file=sys.stderr)
    if target is None or target == "":
        target = "/"
    return flask.redirect(target)


@insta485.app.route('/accounts/logout/', methods=['POST'])
def logout():
    """Log out the user."""
    # Clear the session
    flask.session.clear()
    # Redirect to login page
    return flask.redirect(flask.url_for('login'))


def login_seq(connection):
    """Log in the user."""
    username = flask.request.form["username"]
    password = flask.request.form["password"]

    if not username or not password:
        flask.abort(400)

    # Grab the password from the database
    db_password = get_password(connection, username)
    if not db_password:
        flask.abort(403)
    # Password is stored as algorithm$salt$hash, split to get the salt
    db_salt = db_password['password'].split('$')[1]
    # Use the salt to hash the password
    password = plaintext_to_password_hash(password, db_salt)
    print(f"Logging in with username: {username} \
        and password: {password}", file=sys.stderr)

    # Log in with the sha256 hashed password
    user = connection.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()

    if not user:
        flask.abort(403)

    # Set session cookie with minimal information
    flask.session['username'] = username


def create(connection):
    """Create a new user."""
    username = flask.request.form.get("username")
    password = flask.request.form.get("password")
    fullname = flask.request.form.get("fullname")
    email = flask.request.form.get("email")
    file = flask.request.files.get("file")

    if not username or not password \
            or not fullname or not email or not file:
        flask.abort(400)

    # Check if username already exists
    existing_user = connection.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing_user:
        flask.abort(409)

    # Save the file to disk
    filename = file.filename
    stem = uuid.uuid4().hex
    suffix = pathlib.Path(filename).suffix.lower()
    uuid_basename = f"{stem}{suffix}"

    file.save(os.path.join(
        insta485.app.config['UPLOAD_FOLDER'],
        uuid_basename
    ))

    # Hash the password
    password_hash = plaintext_to_password_hash(password)

    # Insert the new user into the database
    connection.execute(
        "INSERT INTO users (username, password, \
            fullname, email, filename) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, fullname, email, filename)
    )
    flask.session['username'] = username


def delete(connection):
    """Delete the user."""
    if "username" not in flask.session:
        return flask.redirect("/accounts/login/")
    # Delete all post files created by this user. Delete user icon file.
    # Delete all related entries in all tables.
    logname = flask.session.get('username')

    if not logname:
        flask.abort(403)
    if flask.session.get('username') is None:
        flask.abort(403)

    # Delete all posts created by the user
    posts = connection.execute(
        "SELECT filename FROM posts WHERE owner = ?",
        (logname,)
    ).fetchall()
    for post in posts:
        os.remove(os.path.join(
            insta485.app.config['UPLOAD_FOLDER'],
            post['filename']
        ))
    # Delete user icon file
    user = connection.execute(
        "SELECT filename FROM users WHERE username = ?",
        (logname,)
    ).fetchone()
    os.remove(os.path.join(
        insta485.app.config['UPLOAD_FOLDER'],
        user['filename']
    ))

    # Delete all related entries in all tables
    connection.execute(
        "DELETE FROM comments WHERE owner = ?",
        (logname,)
    )
    connection.execute(
        "DELETE FROM likes WHERE owner = ?",
        (logname,)
    )
    connection.execute(
        "DELETE FROM posts WHERE owner = ?",
        (logname,)
    )

    # Delete from user, follow, and following tables
    connection.execute(
        "DELETE FROM users WHERE username = ?",
        (logname,)
    )
    connection.execute(
        "DELETE FROM following WHERE username1 = ? OR username2 = ?",
        (logname, logname)
    )
    flask.session.clear()

    return flask.redirect("/accounts/login/")


def edit_account(connection):
    """Edit the user's account."""
    if 'username' not in flask.session:
        flask.abort(403)

    fullname = flask.request.form.get("fullname")
    email = flask.request.form.get("email")
    file = flask.request.files.get("file")

    if not fullname or not email:
        flask.abort(400)

    username = flask.session['username']

    if file:
        # Save the new file to disk
        filename = file.filename
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"
        file.save(os.path.join(
            insta485.app.config['UPLOAD_FOLDER'],
            uuid_basename
        ))

        # Get the old filename
        old_file = connection.execute(
            "SELECT filename FROM users WHERE username = ?",
            (username,)
        ).fetchone()['filename']

        # Delete the old photo from the filesystem
        os.remove(os.path.join(
            insta485.app.config['UPLOAD_FOLDER'],
            old_file
        ))

        # Update the user's photo, name, and email in the database
        connection.execute(
            "UPDATE users SET fullname = ?, email = ?, filename = ? \
                WHERE username = ?",
            (fullname, email, uuid_basename, username)
        )
    else:
        # Update only the user's name and email
        connection.execute(
            "UPDATE users SET fullname = ?, email = ? WHERE username = ?",
            (fullname, email, username)
        )


def update_password(connection):
    """Update the user's password."""
    print("update_password", file=sys.stderr)
    if 'username' not in flask.session:
        flask.abort(403)

    password = flask.request.form.get("password")
    new_password1 = flask.request.form.get("new_password1")
    new_password2 = flask.request.form.get("new_password2")

    if not password or not new_password1 or not new_password2:
        flask.abort(400)

    username = flask.session['username']

    # Verify current password
    user = connection.execute(
        "SELECT password FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    db_pass = user['password']
    db_hash = db_pass.split('$')[1]
    # Convert password to hash
    password = plaintext_to_password_hash(password, db_hash)
    # print(f"password: {password}", file=sys.stderr) print(f"db_pass:
    # {db_pass}", file=sys.stderr)
    if password != db_pass:
        flask.abort(403)

    if not user:
        flask.abort(403)

    # Verify new passwords match
    if new_password1 != new_password2:
        flask.abort(401)

    # Hash the new password
    new_password_hash = plaintext_to_password_hash(new_password1)

    # Update the password in the database
    connection.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (new_password_hash, username)
    )


def plaintext_to_password_hash(plain_text_password, salt=uuid.uuid4().hex):
    """Convert a plain text password to a hashed password."""
    algorithm = 'sha512'
    print(f"salt: {salt}", file=sys.stderr)
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + plain_text_password
    print(f"password_salted: {password_salted}", file=sys.stderr)
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    print(f"password_hash: {password_hash}", file=sys.stderr)
    print(f"algorithm: {algorithm}", file=sys.stderr)
    # print(f"salt: {salt}", file=sys.stderr)
    return "$".join([algorithm, salt, password_hash])
