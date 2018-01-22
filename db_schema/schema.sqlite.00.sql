-- LXCompute Schema v0.0
PRAGMA foreign_keys = ON;

CREATE TABLE 'group' (
	gid INTEGER PRIMARY KEY ASC,
	is_super INTEGER,
	name TEXT UNIQUE				--   name that identifies group
);

CREATE TABLE 'user' (
	uid INTEGER PRIMARY KEY ASC,
	username TEXT UNIQUE,				--   username (uid)
	group_id INTEGER,
	is_admin INTEGER,
	sshkey TEXT,
	FOREIGN KEY(group_id) REFERENCES 'group'(gid)
);

CREATE TABLE 'host' (
	hid INTEGER PRIMARY KEY ASC,
	name TEXT,					--   compute server hostname
	ncpu INTEGER,					-- \
	nram INTEGER,					-- | available resources
	nhdd INTEGER					-- /
);

CREATE TABLE 'nfs' (
	nid INTEGER PRIMARY KEY ASC,
	path TEXT,					--   nfs server share path
	mapping TEXT,					--   path in vm
	group_id INTEGER,
	FOREIGN KEY(group_id) REFERENCES 'group'(gid)
);

CREATE TABLE 'container' (
	cid INTEGER PRIMARY KEY ASC,
	name TEXT UNIQUE,
	host_id INTEGER,
	creator_id INTEGER,
	image TEXT,
	FOREIGN KEY(creator_id) REFERENCES user(uid),
	FOREIGN KEY(host_id) REFERENCES host(hid)
);

CREATE TABLE 'container_user' (
	container_id INTEGER,
	user_id INTEGER,
	FOREIGN KEY(container_id) REFERENCES container(cid),
	FOREIGN KEY(user_id) REFERENCES user(uid)
);

CREATE TABLE 'slot' (
	sid INTEGER PRIMARY KEY ASC,
	container_id INTEGER,
	host_id INTEGER,
	hours INTEGER,
	hours_used INTEGER,
	ncpu INTEGER,
	nram INTEGER,
	FOREIGN KEY(container_id) REFERENCES container(cid)
	FOREIGN KEY(host_id) REFERENCES host(hid)
);

