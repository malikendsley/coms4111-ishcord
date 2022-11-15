-- table friends_with has structure (uid_sender, uid_receiver, status)
-- table users has structure (uid, name)
-- table member_of has structure (uid, fid)

-- get all people in a particular server



select name from (select uid, name from member_of natural join users where member_of.fid = 1)


-- get all uids in friends_with where uid_