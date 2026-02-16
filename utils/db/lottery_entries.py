# SQL SCRIPT
"""CREATE TABLE lottery_entries (
    lottery_id INT,
    user_id BIGINT,
    user_name VARCHAR(255),
    entries BIGINT,
    PRIMARY KEY (lottery_id, user_id),
    FOREIGN KEY (lottery_id) REFERENCES lottery(lottery_id) ON DELETE CASCADE
);"""
