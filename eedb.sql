/* CREATE DATABASE eedb CHARACTER SET utf8 COLLATE = utf8_unicode_ci; */
DROP TABLE IF EXISTS device;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS devusage;
DROP TABLE IF EXISTS syncjobs;

CREATE TABLE device
(
	periph_id INT(32) NOT NULL,
	parent_periph_id INT(32),
	name varchar(255) NOT NULL,
	room_id INT(32),
	usage_id INT(32),
	creation_date datetime,
	PRIMARY KEY (periph_id)
) ENGINE = INNODB;

CREATE TABLE room
(
	room_id INT(32),
	room_name varchar(255),
	PRIMARY KEY (room_id)
) ENGINE = INNODB;

CREATE TABLE devusage
(
	usage_id INT(32),
	usage_name varchar(255),
	PRIMARY KEY (usage_id)
) ENGINE = INNODB;

CREATE TABLE syncjobs
(
	job_id INT(32),
	execution_date datetime,
	PRIMARY KEY (job_id)
) ENGINE = INNODB;

