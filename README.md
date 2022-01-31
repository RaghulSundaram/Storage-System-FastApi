
# Filexchange

A file storage and sharing application.


## Description

A blob storage system which offers features like file upload, file download, file rename, file delete and file sharing.

The application is developed using: FastAPI (Backend), React (Frontend), MongoDB (Database).

Users can register themselves and start using the application.

A file uploaded can have only one owner (the user who uploaded it). It can be shared with other users
only by the owner of the file. The share access of a user to 
the owner's file can be revoked only by the owner. Only the owner can rename or delete a file.
The owner can also download a file.


A user can only download a file that is shared with him/her. No other
operations are allowed for the user for that file.

In the database, user collection stores the user details. A separate
collection for storing file's metadata where the owner id of the file is also
stored. 

When a file is shared, a new entry
is added in a collection named "shares" where the shared file's id 
and the user's id for whom the file is shared is stored. The content
of the files are stored in a separate collection as chunks.


## Link

https://filexchange-ui.herokuapp.com/
