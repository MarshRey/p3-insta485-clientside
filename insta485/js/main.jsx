import React, { StrictMode,  useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import Post from "./post";
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';

const root = createRoot(document.getElementById("reactEntry"));
root.render(
    <Feed />
);

// Extend dayjs with the necessary plugins
dayjs.extend(relativeTime);
dayjs.extend(utc);

function Feed() {
  const [loading, setLoading] = useState(true);  // Loading state
  const [posts, setPosts] = useState([]);        // State to store post details
  const [nextUrl, setNextUrl] = useState(null);  // State for the next page URL
  const [error, setError] = useState(null);      // State for error handling

  // Function to fetch posts
  const fetchPosts = async (url) => {
    try {
      // Fetch the main posts data
      const response = await fetch(url);
      const data = await response.json();

      // Process results (array of posts)
      const newPosts = await Promise.all(data.results.map(async (postInfo) => {
        // Fetch detailed information for each post by its URL
        const postResponse = await fetch(postInfo.url);
        return await postResponse.json();
      }));

      // Update the state with the new posts and the next page URL
      setPosts((prevPosts) => [...prevPosts, ...newPosts]);
      setNextUrl(data.next);  // Set the URL for fetching the next page
      setLoading(false);      // Data has been loaded
    } catch (err) {
      console.error('Error fetching posts:', err);
      setError('Failed to load posts.');
      setLoading(false);
    }
  };

  // Function to toggle likes for a post
  const handleLikeToggle = async (_post) => {
    try {
      // /api/v1/likes/<int:likeid>
      // Grab likeid from the post object
      const postid = _post.postid;
      const isLiked = _post.likes.lognameLikesThis;  // Check if the user has already liked the post
      const likeid = _post.likes.url;  // Get the likeid for the post
      const url = isLiked ? likeid : `/api/v1/likes/?postid=${postid}`;  // Construct the URL
      const method = isLiked ? 'DELETE' : 'POST';  // Determine the HTTP method
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        var updateUrl = null;
        try{
          const json = await response.json();
          console.log(json);
          updateUrl = json.url;
        }
        catch (error){
          // console.error('Expected error in like toggle that I\'m too lazy to fix:', error);
        }
        // Update the likes count and lognameLikesThis in the state
        setPosts((prevPosts) =>
          prevPosts.map((post) =>
            post.postid === postid
              ? {
                  ...post,
                  likes: {
                    ...post.likes,
                    lognameLikesThis: !isLiked,  // Toggle like status
                    numLikes: isLiked ? post.likes.numLikes - 1 : post.likes.numLikes + 1, // Update likes count
                    url: updateUrl,  // Update the like URL
                  },
                }
              : post
          )
        );
      } else {
        console.error('Failed to update like status');
      }
    } catch (error) {
      console.error('Error in like toggle:', error);
    }
  };

  // Fetch the initial posts when the component mounts
  useEffect(() => {
    const initialUrl = '/api/v1/posts/';  // Initial API endpoint
    fetchPosts(initialUrl);
  }, []);

  // Function to load more posts (pagination)
  const loadMorePosts = () => {
    if (nextUrl) {
      fetchPosts(nextUrl);  // Fetch the next set of posts
    }
  };

  if (loading) {
    return <div>Loading ...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }
  console.log(posts[0]);
  return (
    <div>
      {posts.map((post) => (
        <div key={post.postid} className="post">
          <h2>{post.owner}</h2>
          <img src={post.imgUrl} alt="Post" />
          <p>{post.caption}</p>

          {/* Render post creation time using dayjs */}
          <p>
            Posted {dayjs.utc(post.created).local().fromNow()}  {/* Converts UTC to local time and displays relative time */}
          </p>

          {/* Rendering likes: Ensure numLikes is a number */}
          <p>{post.likes.numLikes} {post.likes.numLikes === 1 ? 'like' : 'likes'}</p>

          {/* Like/Unlike button */}
          <button onClick={() => handleLikeToggle(post)}>
            {post.likes.lognameLikesThis ? 'Unlike' : 'Like'}
          </button>

          {/* Conditionally render if lognameLikesThis is true/false */}
          <p>{post.likes.lognameLikesThis ? 'You like this post.' : 'You haven\'t liked this post yet.'}</p>

          {/* Render comments */}
          <div className="comments">
            {post.comments.map((comment) => (
              <p key={comment.commentid}>
                <strong>{comment.owner}</strong> {comment.text}
              </p>
            ))}
          </div>
        </div>
      ))}

      {/* Button to load more posts if there's a next page */}
      {nextUrl && <button onClick={loadMorePosts}>Load More</button>}
    </div>
  );
}

export default Feed;