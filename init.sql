USE calls;

CREATE TABLE IF not EXISTS ChatParameters (
    id_str VARCHAR(30),
    login_ai VARCHAR(30) NULL,
    login_1c VARCHAR(30) NULL,
    prompt TEXT NULL,
    category VARCHAR(50) NULL,
    step VARCHAR(150) NULL,
    dt DATETIME NULL,
    id_int MEDIUMTEXT NULL,
    contract VARCHAR(10) NULL,
    story TEXT NULL,
    chat_bot VARCHAR(70) NULL
);


CREATE TABLE IF not EXISTS ChatStory (
    id_str VARCHAR(30),
    mes TEXT NULL,
    dt DATETIME NULL,
    messageId VARCHAR(100) NULL,
    id_int MEDIUMTEXT NULL,
    empl TINYINT(1) NULL,
    ai_take TINYINT(1) NULL,
    ai_send TINYINT(1) NULL,
    ai_not_send TINYINT(1) NULL,
    chat_bot VARCHAR(70) NULL,
    category VARCHAR(50) NULL
);