import React, { StrictMode,  useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import Post from "./post";

// // Create a root
const root = createRoot(document.getElementById("reactEntry"));
root.render(
    <Feed />
);

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

  // Fetch the initial posts when the component mounts
  useEffect(() => {
    // console.log("CALLED")
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
  return (
    <div>
      {posts.map((post) => (
        <div key={post.postid} className="post">
          <h2>{post.username}</h2>
          <img src={post.imgUrl} alt="Post" />
          <p>{post.caption}</p>
          {/* <p>{post.likes} {post.likes === 1 ? 'like' : 'likes'}</p> */}

          {/* Render comments */}
          <div className="comments">
            {post.comments.map((comment) => (
              <p key={comment.commentid}>
                <strong>{comment.username}</strong> {comment.text}
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