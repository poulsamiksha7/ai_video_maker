-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS ai_video_maker;
USE ai_video_maker;

-- Create the Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the Videos table
CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    template_name VARCHAR(50) NOT NULL,
    status ENUM('processing', 'done', 'error') DEFAULT 'processing',
    video_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert a default user for testing
INSERT IGNORE INTO users (username, password_hash) VALUES ('admin', 'pbkdf2:sha256:600000$examplehash'); 