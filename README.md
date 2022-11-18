PostgreSQL Account:

Username: mse2143 
Password: 3607

URL of Project:

Parts implemented:

User login and registration (unsecured but functional), forums, channels, instant messaging, simple forum moderation, a friends system, public and private forums, and user customizable themes.

Users may freely create, join, message in, and view forums, add each other as friends, create and swap between theme profiles, and invite each other to forums. 
Parts removed:

Forums having images for their icons, we felt this would have required infrastructure disproportionate to the value added to the application.

Parts Extended: 

A few natural extensions of functionality outlined prior were also introduced to make using the application easier. The ability to delete most things that you “own,” such as theme profiles and user accounts was added to complement the ability to create them. 

Parts Removed / Adjusted:
An extra column was added to the table users to account for which theme they had selected
A few keys were marked ON CASCADE DELETE in order to accommodate things like forum, forum, and user deletion.

Interesting Pages

The dashboard is by far the most interesting page in the application. It combines several queries, one to query all forums the logged in user is a member of, one to query the channels in a given forum, a client-side asynchronous request that continually requests the latest messages from an endpoint which returns all messages sent in a particular channel and forum with a UID higher than the requested UID. This was originally intended to be used as a way to implement long polling, but was discarded in favor of regular requests due to Flask’s and SQLAlchemy trouble with pending requests (this functionality in its most efficient implementation may have required more ORM type features which we naturally avoided). The dashboard also queried a list of users in the currently selected forum, and a subset of those users who were also on the users’ friends list. We think this page is the most interesting due to the “it just works” factor. The experience of chatting is seamless between users and forums.

The second most interesting page in the application is the forum moderation panel. For an admin, it lets them view several interesting statistics about a given forum to help them make moderation decisions. Besides a user list, channel list, and message list, each retrieved in a query, it also runs queries to sort users by activity and message length in order to reveal any suspicious patterns.
