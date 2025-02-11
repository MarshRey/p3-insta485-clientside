import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import InfiniteScroll from "react-infinite-scroll-component"; // Import the Infinite Scroll component
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

const root = createRoot(document.getElementById("reactEntry"));
root.render(<Feed />);

// Extend dayjs with the necessary plugins
dayjs.extend(relativeTime);
dayjs.extend(utc);

function Feed() {
  const [loading, setLoading] = useState(true); // Loading state
  const [posts, setPosts] = useState([]); // State to store post details
  const [nextUrl, setNextUrl] = useState(null); // State for the next page URL
  const [error, setError] = useState(null); // State for error handling
  const [newComment, setNewComment] = useState(""); // State for new comment input
  const [hasMore, setHasMore] = useState(true); // To manage if more posts are available for scrolling

  // Function to fetch posts
  const fetchPosts = async (url) => {
    try {
      const response = await fetch(url);
      const data = await response.json();

      const newPosts = await Promise.all(
        data.results.map(async (postInfo) => {
          const postResponse = await fetch(postInfo.url);
          return postResponse.json();
        }),
      );

      setPosts((prevPosts) => [...prevPosts, ...newPosts]);
      setNextUrl(data.next);
      setLoading(false);

      // If there's no next page, set hasMore to false
      if (!data.next) {
        setHasMore(false);
      }
    } catch (err) {
      console.error("Error fetching posts:", err);
      setError("Failed to load posts.");
      setLoading(false);
    }
  };

  // Function to toggle likes for a post
  const handleLikeToggle = async (_post) => {
    try {
      const { postid } = _post;
      const isLiked = _post.likes.lognameLikesThis;
      const likeid = _post.likes.url;
      const url = isLiked ? likeid : `/api/v1/likes/?postid=${postid}`;
      const method = isLiked ? "DELETE" : "POST";
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        let updateUrl = null;
        try {
          const json = await response.json();
          updateUrl = json.url;
        } catch (e) {
          // console.error(
          //   "Expected error in like toggle that I'm too lazy to fix:",
          //   error,
          // );
        }
        setPosts((prevPosts) =>
          prevPosts.map((post) =>
            post.postid === postid
              ? {
                  ...post,
                  likes: {
                    ...post.likes,
                    lognameLikesThis: !isLiked,
                    numLikes: isLiked
                      ? post.likes.numLikes - 1
                      : post.likes.numLikes + 1,
                    url: updateUrl,
                  },
                }
              : post,
          ),
        );
      } else {
        console.error("Failed to update like status");
      }
    } catch (e) {
      console.error("Error in like toggle:", e);
    }
  };

  // Function to handle double-click on image
  const handleDoubleClick = (post) => {
    if (!post.likes.lognameLikesThis) {
      handleLikeToggle(post); // Like the post only if it's not already liked
    }
  };

  // Function to add a comment
  const handleCommentSubmit = async (event, postid) => {
    event.preventDefault();
    try {
      const response = await fetch(`/api/v1/comments?postid=${postid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newComment }),
      });

      if (response.ok) {
        const updatedPost = await response.json();
        const oldComments = posts.find(
          (post) => post.postid === postid,
        ).comments;
        updatedPost.comments = [...oldComments, updatedPost];
        setPosts((prevPosts) =>
          prevPosts.map((post) =>
            post.postid === postid
              ? {
                  ...post,
                  comments: updatedPost.comments,
                }
              : post,
          ),
        );
        setNewComment(""); // Reset input field
      } else {
        console.error("Failed to add comment");
      }
    } catch (e) {
      console.error("Error in comment submit:", e);
    }
  };

  // Function to delete a comment
  const handleDeleteComment = async (postid, commentid) => {
    try {
      const response = await fetch(`/api/v1/comments/${commentid}/`, {
        method: "DELETE",
      });

      if (response.ok) {
        setPosts((prevPosts) =>
          prevPosts.map((post) =>
            post.postid === postid
              ? {
                  ...post,
                  comments: post.comments.filter(
                    (comment) => comment.commentid !== commentid,
                  ),
                }
              : post,
          ),
        );
      } else {
        console.error("Failed to delete comment");
      }
    } catch (e) {
      console.error("Error in comment delete:", e);
    }
  };

  // Fetch the initial posts when the component mounts
  useEffect(() => {
    const initialUrl = "/api/v1/posts/";
    fetchPosts(initialUrl);
  }, []);

  // Function to load more posts (pagination)
  const loadMorePosts = () => {
    if (nextUrl) {
      fetchPosts(nextUrl);
    }
  };

  if (loading) {
    return <div>Loading ...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }
  // console.log(posts);
  return (
    <div>
      {/* Infinite Scroll component wrapping the posts */}
      <InfiniteScroll
        dataLength={posts.length} // Current number of posts
        next={loadMorePosts} // Function to call when scrolling to the bottom
        hasMore={hasMore} // Whether or not there are more posts to load
        loader={<h4>Loading more posts...</h4>} // Loader displayed while loading new posts
        endMessage={<p>No more posts to load</p>} // Message displayed when all posts are loaded
      >
        {posts.map((post) => (
          <div key={post.postid} className="post">
            <a href={post.ownerShowUrl}>{post.owner}</a>
            <img src={post.ownerImgUrl} alt="Avatar" />
            {/* Double-clicking the image should like the post if it's not already liked */}
            <img
              src={post.imgUrl}
              alt="Post"
              onDoubleClick={() => handleDoubleClick(post)} // Double-click handler
            />

            <p>{post.caption}</p>

            {/* Render post creation time using dayjs */}
            <a href={post.postShowUrl}>
              Posted {dayjs.utc(post.created).local().fromNow()}
            </a>

            <p>
              {post.likes.numLikes}{" "}
              {post.likes.numLikes === 1 ? "like" : "likes"}
            </p>
            <button
              type="button"
              data-testid="like-unlike-button"
              onClick={() => handleLikeToggle(post)}
            >
              {post.likes.lognameLikesThis ? "Unlike" : "Like"}
            </button>

            <div className="comments">
              {post.comments.map((comment) => (
                <div key={comment.commentid} className="comment">
                  <span data-testid="comment-text">
                    <strong>
                      <a href={comment.ownerShowUrl}> {comment.owner} </a>
                    </strong>{" "}
                    {comment.text}
                  </span>
                  {comment.lognameOwnsThis && (
                    <button
                      type="button"
                      data-testid="delete-comment-button"
                      onClick={() =>
                        handleDeleteComment(post.postid, comment.commentid)
                      }
                    >
                      Delete
                    </button>
                  )}
                </div>
              ))}

              {/* Comment input form */}
              <form
                data-testid="comment-form"
                onSubmit={(event) => handleCommentSubmit(event, post.postid)}
              >
                <input
                  type="text"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
                />
              </form>
            </div>
          </div>
        ))}
      </InfiniteScroll>
    </div>
  );
}

export default Feed;
