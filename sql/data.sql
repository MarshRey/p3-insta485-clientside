PRAGMA foreign_keys = ON;

-- Insert data into users table
INSERT INTO users (username, fullname, email, filename, password, created) VALUES
('awdeorio', 'Andrew DeOrio', 'awdeorio@umich.edu', 'e1a7c5c32973862ee15173b0259e3efdb6a391af.jpg', 'sha512$34e94a05cdf247db92a84bc590950336$7eaca2b4169e042120f015666115856c717343f1c75d1c1bd1bf469bd1cd439eb152ccda6a0b8703706dfbcb861b3cef9208325c31f436e8edb9563f01176c48', '2017-06-20 15:47:02'),
('jflinn', 'Jason Flinn', 'jflinn@umich.edu', '505083b8b56c97429a728b68f31b0b2a089e5113.jpg', 'sha512$673d22398b0141c7929f987efee061e6$187dd68d62574a29b40513467cb5376849d6e7651dbd19850b853b912f44d940a42ef6bb96f4bafa82a6b40072ed980bfad377c65faa096281369210841f2b73', '2017-06-20 15:47:02'),
('michjc', 'Michael Cafarella', 'michjc@umich.edu', '5ecde7677b83304132cb2871516ea50032ff7a4f.jpg', 'sha512$d7cde81ee4614141b68fbe8ff5fffa76$8b432b218b18554e58a949a40367a0d0e731dc8f8a46ecaa3ea0aca39169b3a97f12246d2840d6e9c32764907ed7b1951dfc16f213cb7fd4a6a96dc43f52f67b', '2017-06-20 15:47:02'),
('jag', 'H.V. Jagadish', 'jag@umich.edu', '73ab33bd357c3fd42292487b825880958c595655.jpg', 'sha512$0b2b8d18beba4c2ba7dad0365d1dd885$130546cafab793f769a86607466fb07476b03c5de1f32f666c1e72e8b48b5e7e08494ec85ede12df72d259112bca3d5783983937361fe0aa2c341ae7bd0c2da4', '2017-06-20 15:47:02');

-- Insert data into posts table
INSERT INTO posts (filename, owner, created) VALUES
('122a7d27ca1d7420a1072f695d9290fad4501a41.jpg', 'awdeorio', '2017-06-20 15:47:02'),
('ad7790405c539894d25ab8dcf0b79eed3341e109.jpg', 'jflinn', '2017-06-20 15:47:02'),
('9887e06812ef434d291e4936417d125cd594b38a.jpg', 'awdeorio', '2017-06-20 15:47:02'),
('2ec7cf8ae158b3b1f40065abfb33e81143707842.jpg', 'jag', '2017-06-20 15:47:02');

-- Insert data into comments table
INSERT INTO comments (owner, postid, text, created) VALUES
('awdeorio', 3, '#chickensofinstagram', '2017-06-20 15:47:02'),
('jflinn', 3, 'I <3 chickens', '2017-06-20 15:47:02'),
('michjc', 3, 'Cute overload!', '2017-06-20 15:47:02'),
('awdeorio', 2, 'Sick #crossword', '2017-06-20 15:47:02'),
('jflinn', 1, 'Walking the plank #chickensofinstagram', '2017-06-20 15:47:02'),
('awdeorio', 1, 'This was after trying to teach them to do a #crossword', '2017-06-20 15:47:02'),
('jag', 4, 'Saw this on the diag yesterday!', '2017-06-20 15:47:02');

-- Insert data into following table
INSERT INTO following (username1, username2, created) VALUES
('awdeorio', 'jflinn', '2017-06-20 15:47:02'),
('awdeorio', 'michjc', '2017-06-20 15:47:02'),
('jflinn', 'awdeorio', '2017-06-20 15:47:02'),
('jflinn', 'michjc', '2017-06-20 15:47:02'),
('michjc', 'awdeorio', '2017-06-20 15:47:02'),
('michjc', 'jag', '2017-06-20 15:47:02'),
('jag', 'michjc', '2017-06-20 15:47:02');

-- Insert data into likes table
INSERT INTO likes (owner, postid, created) VALUES
('awdeorio', 1, '2017-06-20 15:47:02'),
('michjc', 1, '2017-06-20 15:47:02'),
('jflinn', 1, '2017-06-20 15:47:02'),
('awdeorio', 2, '2017-06-20 15:47:02'),
('michjc', 2, '2017-06-20 15:47:02'),
('awdeorio', 3, '2017-06-20 15:47:02');