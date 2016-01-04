/* CREATE DATABASE eedb CHARACTER SET utf8 COLLATE = utf8_unicode_ci; */
DROP TABLE IF EXISTS periph_history;
DROP TABLE IF EXISTS device;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS devusage;
DROP TABLE IF EXISTS syncjobs;

CREATE TABLE room
(
	room_id INT(32) UNSIGNED NOT NULL,
	room_name varchar(255) NOT NULL,
	PRIMARY KEY (room_id)
) ENGINE = INNODB;

CREATE TABLE devusage
(
	usage_id INT(32) UNSIGNED NOT NULL,
	usage_name varchar(255) NOT NULL,
	PRIMARY KEY (usage_id)
) ENGINE = INNODB;

CREATE TABLE device
(
	periph_id INT(32) UNSIGNED NOT NULL,
	parent_periph_id INT(32) UNSIGNED DEFAULT NULL,
	name varchar(255) NOT NULL,
	room_id INT(32) UNSIGNED NOT NULL,
	usage_id INT(32) UNSIGNED NOT NULL,
	creation_date datetime NOT NULL,
	PRIMARY KEY (periph_id),
	FOREIGN KEY(room_id) 
	     REFERENCES room(room_id)
	     ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY(usage_id)
	     REFERENCES devusage(usage_id)
	     ON UPDATE CASCADE ON DELETE CASCADE 
) ENGINE = INNODB;

CREATE TABLE periph_history
(
	id INT(32) UNSIGNED NOT NULL AUTO_INCREMENT,
	periph_id INT(32) UNSIGNED NOT NULL,
	measurement VARCHAR(255) NOT NULL,
	timestamp datetime NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(periph_id)
		REFERENCES device(periph_id)
		ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE = INNODB;

CREATE TABLE syncjobs
(
	job_id INT(32) UNSIGNED NOT NULL AUTO_INCREMENT,
	execution_date datetime NOT NULL,
	PRIMARY KEY (job_id)
) ENGINE = INNODB;

