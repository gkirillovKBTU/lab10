import psycopg2
import psycopg2.extras
import os
from config import load_config
from functools import partial

CSV_BASE_PATH = os.path.join(os.path.dirname(__file__), "csv_files")


def database_init(config):
    commands = [
        """
        CREATE TABLE IF NOT EXISTS persons (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(35) NOT NULL,
            second_name VARCHAR(35) NOT NULL,
            username VARCHAR(35) NOT NULL UNIQUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS phones (
            phone_id SERIAL PRIMARY KEY,
            phone VARCHAR(20) NOT NULL UNIQUE,
            person_id INTEGER,
            FOREIGN KEY (person_id)
            REFERENCES persons (id)
            ON UPDATE CASCADE ON DELETE CASCADE
        );
        """,
        """
        CREATE OR REPLACE PROCEDURE add_update_user(
            fname VARCHAR(35),
            sname VARCHAR(35),
            username VARCHAR(35),
            phone VARCHAR(20)
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            personId INTEGER;
        BEGIN
            SELECT INTO personId FROM persons WHERE first_name = fname AND second_name = sname;
            IF personId IS NULL
                THEN
                    INSERT INTO persons (first_name, second_name, username) VALUES (fname, sname, username) RETURNING id INTO personId;
                    INSERT INTO phones (phone, person_id) VALUES (phone, personId);
                ELSE
                    UPDATE phones SET phone = phone WHERE person_id = personId;
            END IF;
        END;
        $$;
        """,
        """
        CREATE OR REPLACE PROCEDURE delete_by_phone_or_name(
            method VARCHAR(2),
            fname VARCHAR(35),
            phone VARCHAR(20)
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF (method = 'ph' AND phone IS NOT NULL) THEN
                    DELETE FROM persons WHERE id = (SELECT person_id from phones where phone = phone);
            ELSIF (method = 'fn' AND fname IS NOT NULL) THEN
                    DELETE FROM persons WHERE first_name = fname;
            ELSE
                RAISE NOTICE 'INVALID INPUT';
            END IF;
        END;
        $$
        """,
        """
            CREATE TYPE person_data AS (
                fname VARCHAR(35),
                sname VARCHAR(35),
                username VARCHAR(35),
                phone VARCHAR(20)
            );
            """,
            """
            CREATE OR REPLACE PROCEDURE insert_many_users(
                persons_data person_data[]
            )
            LANGUAGE plpgsql
            AS $$
            DECLARE
                rec person_data;
                rec_id INTEGER;
            BEGIN
                FOREACH rec IN ARRAY persons_data
                LOOP
                    INSERT INTO persons (first_name, second_name, username)
                    VALUES (rec.fname, rec.sname, rec.username) RETURNING id INTO rec_id;
                    INSERT INTO phones (phone, person_id) VALUES (rec.phone, rec_id);
                END LOOP;
            END;
            $$
            """
    ]

    try:
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            with conn.cursor() as cur:
                for command in commands:
                    cur.execute(command)
                conn.commit()
            psycopg2.extras.register_composite("person_data", conn)

    except (Exception, psycopg2.DatabaseError) as e:
        print(e)


procedure_queries = {
    "UU": "CALL add_update_user(%s, %s, %s, %s);",
    "DD": "CALL delete_by_phone_or_name(%s, %s, %s);",
    "IM": "CALL insert_many_users(%s);"
}


def paginate_wrapper(query, limit, offset, *args, config=load_config()):
    PAGINATION_SUFFIX = 'LIMIT {limit} OFFSET {offset}'
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            result = True
            while result:
                pagination = PAGINATION_SUFFIX.format(limit=limit, offset=offset)
                cur.execute(query + ' ' + pagination, args)
                result = cur.fetchall()
                if not result:
                    print('No more results')
                    break
                yield result
                offset += limit


def execute_wrapper(func_or_query, *args, config=load_config()):
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            if callable(func_or_query):
                result = func_or_query(cur)
            else:
                cur.execute(func_or_query, args)
            try:
                result = cur.fetchall()
            except:
                result = None
            conn.commit()
            print('Changes committed')
            return result


def call_procedure():
    procedure_name = input("""
        Choose the method for inserting:
            Update user  -> UU
            Delete data  -> DD
            Insert several users -> IM
            Exit -> E
    """)
    query = procedure_queries.get(procedure_name, None)
    if not query: return
    args  = []
    input_arg = "_"
    while input_arg != "E" and procedure_name != "IM":
        if input_arg != "_": args.append(input_arg)
        input_arg = input("Input the next argument for procedure \n or E -> Exit")
    if procedure_name == "IM":
        while input_arg != "E":
            first_name = input('Enter first name: ')
            second_name = input('Enter second name: ')
            username = input('Enter username: ')
            phone = input('Enter phone number: ')
            user_data = tuple([first_name, second_name, username, phone])
            args.append(user_data)
            input_arg = input("E to exit, Enter to add new user")
        execute_wrapper(query, args)
    elif args: execute_wrapper(query, *args)


def insert_data(table_type='person'):
    insert_option = input(
        """
        Choose the method for inserting:
            Insert by csv  -> C
            Insert by request  -> R
            Exit -> E
        """
    )
    match insert_option:
        case "C":
            csv_filename = input('Specify the filename ')
            csv_path = os.path.join(CSV_BASE_PATH, csv_filename)
            table_name = 'persons' if table_type == 'person' else 'phones'

            def copy_from_csv(cur):
                with open(csv_path, 'r') as f:
                    next(f)  # Skip header
                    columns = (
                        'first_name,second_name,username'
                        if table_type == 'person'
                        else 'phone,person_id'
                    )
                    cur.copy_from(f, table_name, sep=',', columns=columns.split(','))
            
            execute_wrapper(copy_from_csv)

        case "R":
            if table_type == 'person':
                first_name = input('Enter first name: ')
                second_name = input('Enter second name: ')
                username = input('Enter username: ')
                
                query = """
                    INSERT INTO persons (first_name, second_name, username)
                    VALUES (%s, %s, %s)
                """
                execute_wrapper(query, first_name, second_name, username)
            else:
                phone = input('Enter phone number: ')
                person_id = input('Enter person ID: ')
                
                query = """
                    INSERT INTO phones (phone, person_id)
                    VALUES (%s, %s)
                """
                execute_wrapper(query, phone, person_id)
        case "E":
            return


def update_data(table_type='person'):
    if table_type == 'person':
        person_id = input('Enter person ID to update: ')
        first_name = input('Enter new first name (Enter to skip): ')
        second_name = input('Enter new second name (Enter to skip): ')
        username = input('Enter new username (Enter to skip): ')

        updates = []
        values = []
        if first_name:
            updates.append('first_name = %s')
            values.append(first_name)
        if second_name:
            updates.append('second_name = %s')
            values.append(second_name)
        if username:
            updates.append('username = %s')
            values.append(username)

        if updates:
            values.append(person_id)
            query = f"UPDATE persons SET {', '.join(updates)} WHERE id = %s"
            execute_wrapper(query, *values)
    else:
        phone_id = input('Enter phone ID to update: ')
        phone = input('Enter new phone number ')
        person_id = input('Enter new person ID (Enter to skip): ')

        updates = ['phone = %s']
        values = [phone]
        if person_id:
            updates.append('person_id = %s')
            values.append(person_id)

        values.append(phone_id)
        query = f"UPDATE phones SET {', '.join(updates)} WHERE phone_id = %s"
        execute_wrapper(query, *values)


def delete_data(table_type='person'):
    if table_type == 'person':
        person_id = input('Enter person ID to delete: ')
        query = 'DELETE FROM persons WHERE id = %s'
        execute_wrapper(query, person_id)
    else:
        phone_id = input('Enter phone ID to delete: ')
        query = 'DELETE FROM phones WHERE phone_id = %s'
        execute_wrapper(query, phone_id)


def select_data(paginated=False):
    select_option = input(
        """
        Choose the method for selecting:
            Select all  -> ALL
            Select by part of name  -> PaN
            Select by phone number  -> PhN
            Select by surname  -> SurN
            Exit -> E
        """
    )
    args = []
    match select_option:
        case "ALL":
            query = "SELECT * FROM persons JOIN phones on persons.id = phones.person_id"
        case "PaN":
            part_of_name = input('Enter part of name: ')
            query = "SELECT * FROM persons WHERE first_name LIKE %s"
            args.append(f'%{part_of_name}%')
        case "PhN":
            phone_number = input('Enter phone number: ')
            query = """
                SELECT * FROM persons 
                JOIN phones on persons.id = phones.person_id 
                WHERE phone = %s
            """
            args.append(phone_number)
        case "SurN":
            surname = input('Enter surname: ')
            query = "SELECT * FROM persons WHERE second_name = %s"
            args.append(surname)
        case "E":
            return

    if not paginated:
        data = execute_wrapper(query, *args)
        print(data)
    else:
        offset = input('Enter offset: ')
        limit = input('Enter limit: ')
        data = paginate_wrapper(query, limit, offset, *args)
        for page in data:
            print(page)
            page_call = input('Press anything to continue, or E to exit: ')
            if page_call == "E":
                break


if __name__ == "__main__":
    config = load_config()
    database_init(config)

    handlers = {
        'I': partial(insert_data, 'person'),
        'IP': partial(insert_data, 'phone'),
        'U': partial(update_data, 'person'),
        'UP': partial(update_data, 'phone'),
        'D': partial(delete_data, 'person'),
        'DP': partial(delete_data, 'phone'),
        'S': select_data,
        "SP": partial(select_data, True),
        "uP": call_procedure,
        'E': lambda: exit(0)
    }

    while True:
        try:
            option = str(input(
                """
                Choose what you want to do:
                    Insert Person -> I
                    Insert Phone  -> IP
                    Update Person -> U
                    Update Phone  -> UP
                    Delete Person -> D
                    Delete Phone  -> DP
                    Select Data  -> S
                    Select Data Paginated -> SP
                    Use Procedures -> uP
                    Exit -> E
                """
            ))
            if option in handlers:
                handlers[option]()
            else:
                print('Invalid option. Please try again.')
        except Exception as e:
            print(f'Something went wrong: {e}')