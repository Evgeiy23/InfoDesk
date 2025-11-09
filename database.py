import sqlite3

DB_PATH = "data.db"

def db_connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    
    # Создание таблицы пользователей
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            login TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            theme TEXT NOT NULL
        )
        """
    )
    
    # Создание таблицы вопросов
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            status TEXT NOT NULL,
            operator TEXT
        )
        """
    )
    
    # Добавление колонки theme если её нет
    try:
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "theme" not in cols:
            cur.execute(
                "ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'light'"
            )
    except Exception:
        pass
    
    # Создание администратора по умолчанию
    cur.execute("SELECT COUNT(1) FROM users WHERE login=?", ("admin",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users(login, password, role, name, theme) "
            "VALUES(?,?,?,?,?)",
            ("admin", "admin", "admin", "Administrator", "light"),
        )
    
    conn.commit()
    conn.close()


# ------------- Функции для работы с пользователями --------------
def get_user(login):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT login, password, role, name, theme FROM users WHERE login=?",
        (login,)
    )
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "login": row[0],
        "password": row[1],
        "role": row[2],
        "name": row[3],
        "theme": row[4]
    }


def list_users():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT login, role, name FROM users ORDER BY login ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


def create_user(login, password, role, name, theme="light"):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(login, password, role, name, theme) "
        "VALUES(?,?,?,?,?)",
        (login, password, role, name, theme)
    )
    conn.commit()
    conn.close()


def delete_user_db(login):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE login=?", (login,))
    conn.commit()
    conn.close()


def update_user_name(login, name):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=? WHERE login=?", (name, login))
    conn.commit()
    conn.close()


def update_user_theme(login, theme):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET theme=? WHERE login=?", (theme, login))
    conn.commit()
    conn.close()


def update_user_password(login, password):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password=? WHERE login=?", (password, login))
    conn.commit()
    conn.close()


# ----------- Функции для работы с вопросами ------------
def list_pending_questions():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user, question FROM questions WHERE status='pending' "
        "ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_question_by_id(qid):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user, question, answer, status, operator "
        "FROM questions WHERE id=?",
        (qid,)
    )
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "user": row[1],
        "question": row[2],
        "answer": row[3],
        "status": row[4],
        "operator": row[5]
    }


def set_answer(qid, answer, operator):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE questions SET answer=?, status='answered', operator=? WHERE id=?",
        (answer, operator, qid)
    )
    conn.commit()
    conn.close()


def add_question(user, question, answer=None, status="pending", operator=None):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO questions(user, question, answer, status, operator) "
        "VALUES(?,?,?,?,?)",
        (user, question, answer, status, operator)
    )
    conn.commit()
    conn.close()


def list_user_questions_all(user):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, question, answer, status, operator FROM questions "
        "WHERE user=? ORDER BY id DESC",
        (user,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_user_questions_recent(user, limit=20):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, question, answer, status, operator FROM questions "
        "WHERE user=? ORDER BY id DESC LIMIT ?",
        (user, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_questions_by_status(status):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user, question, answer, status, operator FROM questions "
        "WHERE status=? ORDER BY id DESC",
        (status,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_all_questions():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user, question, answer, status, operator FROM questions "
        "ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_faq_items():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, question, answer, status FROM questions WHERE user='FAQ' "
        "ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows

