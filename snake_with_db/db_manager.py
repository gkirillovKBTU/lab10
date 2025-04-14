import psycopg2
from config import load_config


def database_init(config=load_config()):
    commands = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(35) NOT NULL UNIQUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS user_scores (
            score_id SERIAL PRIMARY KEY,
            user_id INTEGER,
            score INTEGER NOT NULL DEFAULT 0,
            level INTEGER DEFAULT 1,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
            REFERENCES users (id)
            ON UPDATE CASCADE ON DELETE CASCADE
        );
        """
    ]

    try:
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            with conn.cursor() as cur:
                for command in commands:
                    cur.execute(command)
                conn.commit()
            print('Database tables initialized successfully.')

    except (Exception, psycopg2.DatabaseError) as e:
        print(f'Database initialization error: {e}')
        raise



config = load_config()

def execute_wrapper(query, *args, fetchable=True, commit=True):
    global config
    with psycopg2.connect(**config) as conn:
        print('Connected to the PostgreSQL server.')
        with conn.cursor() as cur:
            # print(query, args, 'QEEEEEEEEEEEEEEEEEEE')
            cur.execute(query, args)
            if commit: conn.commit()
            # print(list(cur))
            return list(cur) if fetchable else None


def add_user(username):
    query = """
        INSERT INTO users (username) 
        VALUES (%s)
        RETURNING id
    """
    result = execute_wrapper(query, username)
    return result[0][0] if result else None


def add_score(user_id, score):
    query = """
        INSERT INTO user_scores (user_id, score) 
        VALUES (%s, %s)
    """
    execute_wrapper(query, user_id, score, fetchable=False)


def get_user_scores(user_id, limit=10):
    query = """
        SELECT score
        FROM user_scores
        WHERE user_id = %s 
        ORDER BY score DESC 
        LIMIT %s
    """
    return execute_wrapper(query, user_id, limit)


def update_user_score(user_id, new_score, new_level):
    query = """
        UPDATE user_scores
        SET score = %s, level = %s
        WHERE user_id = %s
    """
    execute_wrapper(query, user_id, new_score, new_level, fetchable=False, commit=False)


def get_user_data(username):
    query = """
        SELECT users.id, users.username, user_scores.score, user_scores.level
        FROM users
        LEFT JOIN user_scores ON users.id = user_scores.user_id
        WHERE username = %s
    """
    return execute_wrapper(query, username)


def delete_user(user_id):
    query = 'DELETE FROM users WHERE id = %s'
    execute_wrapper(query, user_id, fetchable=False)