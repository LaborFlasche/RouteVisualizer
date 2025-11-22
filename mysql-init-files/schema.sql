-- -----------------------------------------------------
-- Schema: Tour Management System
-- Beschreibung: Tabellenstruktur gemäß bereitgestelltem Diagramm
-- -----------------------------------------------------

DROP DATABASE IF EXISTS tour_management;
CREATE DATABASE tour_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tour_management;

-- -----------------------------------------------------
-- Table: user_logins
-- -----------------------------------------------------
CREATE TABLE user_logins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username TEXT,
    password TEXT
);

-- -----------------------------------------------------
-- Table: page_layouts_copy
-- -----------------------------------------------------
CREATE TABLE page_layouts_copy (
    config_url TEXT,
    logo_url TEXT,
    user_id INT,
    CONSTRAINT fk_page_layouts_user FOREIGN KEY (user_id)
        REFERENCES user_logins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table: tours
-- -----------------------------------------------------
CREATE TABLE tours (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name TEXT,
    user_id INT,
    total_distance_malt DOUBLE,
    total_distance_maps DOUBLE,
    total_distance_optim BIGINT,
    file_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tours_user FOREIGN KEY (user_id)
        REFERENCES user_logins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table: single_tours
-- -----------------------------------------------------
CREATE TABLE single_tours (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tour_id BIGINT,
    tour_symbol TEXT,
    tour_number BIGINT,
    total_distance_maltec DOUBLE,
    total_distance_maps DOUBLE,
    total_distance_optim DOUBLE,
    CONSTRAINT fk_single_tour FOREIGN KEY (tour_id)
        REFERENCES tours(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table: children
-- -----------------------------------------------------
CREATE TABLE children (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    surname TEXT,
    forename TEXT,
    street TEXT,
    housenumber BIGINT,
    postcode TEXT,
    region TEXT,
    lat DOUBLE,
    lon DOUBLE
);

-- -----------------------------------------------------
-- Table: school
-- -----------------------------------------------------
CREATE TABLE school (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name TEXT,
    street TEXT,
    number BIGINT,
    postcode TEXT,
    region TEXT,
    lat DOUBLE,
    lon DOUBLE,
    user_id INT,
    CONSTRAINT fk_school_user FOREIGN KEY (user_id)
        REFERENCES user_logins(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- -----------------------------------------------------
-- Table: tour_assignments
-- -----------------------------------------------------
CREATE TABLE tour_assignments (
    tour_id BIGINT,
    children_id BIGINT,
    stop_order BIGINT,
    CONSTRAINT fk_tourassign_tour FOREIGN KEY (tour_id)
        REFERENCES single_tours(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_tourassign_child FOREIGN KEY (children_id)
        REFERENCES children(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table: optimized_tour_assignments
-- -----------------------------------------------------
CREATE TABLE optimized_tour_assignments (
    tour_id BIGINT,
    children_id BIGINT,
    stop_order BIGINT,
    CONSTRAINT fk_opt_tourassign_tour FOREIGN KEY (tour_id)
        REFERENCES single_tours(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_opt_tourassign_child FOREIGN KEY (children_id)
        REFERENCES children(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- INSERT:
-- -----------------------------------------------------
INSERT INTO user_logins (username, password) VALUES ("mariastern", "ms1");
INSERT INTO school (name, street, number, postcode, region) VALUES ("Maria-Stern-Schule", "Felix-Dahn-Str.", 11, "97072", "Würzburg");