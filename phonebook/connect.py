import psycopg2
from config import load_config


def connect(config):
    """ Connect to the PostgreSQL database server """
    try:
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            yield conn
    except (Exception, psycopg2.DatabaseError) as e:
        print(e)
